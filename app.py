import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import PIL.Image as PILImage
import pytesseract
import re
from datetime import datetime
import plotly.express as px

# Configuração de Identidade
st.set_page_config(page_title="BYD Pro - Gestão SaaS", page_icon="💎", layout="wide")

# Conexão com o Banco de Dados (Google Sheets)
conn = st.connection("gsheets", type=GSheetsConnection)

# --- LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.title("💎 Faturamento Pro - Lucas do Rio Verde")
    usuario = st.text_input("Quem está acessando? (Digite seu nome):").strip().lower()
    if st.button("Entrar no Sistema"):
        if usuario:
            st.session_state['usuario'] = usuario
            st.session_state['autenticado'] = True
            st.rerun()
    st.stop()

# --- CARREGAR DADOS ---
NOME_USUARIO = st.session_state['usuario']
try:
    df_geral = conn.read(worksheet="Lancamentos", ttl="0")
    if df_geral is None or df_geral.empty:
        # Cria as colunas se a planilha estiver vazia
        colunas = ['Usuario', 'Data', 'Urbano', 'Boraali', 'app163', 'Outros_Receita', 'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Outros_Custos', 'KM_Final']
        df_geral = pd.DataFrame(columns=colunas)
    df_usuario = df_geral[df_geral['Usuario'] == NOME_USUARIO].copy()
except Exception:
    st.error("⚠️ Erro de conexão com o Banco de Dados. Tente novamente em instantes.")
    st.stop()

# --- INTELIGÊNCIA DE LANÇAMENTO ---
def processar_fala_motorista(frase):
    frase = frase.lower().replace(',', '.')
    res = {'Ganhos': {}, 'Gastos': {}, 'Duvidas': []}
    
    # Dicionário de busca
    mapa = {
        'urbano': ('Ganhos', 'Urbano'), 'bora': ('Ganhos', 'Boraali'), '163': ('Ganhos', 'app163'),
        'particula': ('Ganhos', 'Outros_Receita'), 'viagem': ('Ganhos', 'Outros_Receita'),
        'energia': ('Gastos', 'Energia'), 'carga': ('Gastos', 'Energia'), 'gasolina': ('Gastos', 'Energia'),
        'combust': ('Gastos', 'Energia'), 'manut': ('Gastos', 'Manuten'), 'lavag': ('Gastos', 'Manuten'),
        'seguro': ('Gastos', 'Seguro'), 'marmita': ('Gastos', 'Outros_Custos'), 'almoço': ('Gastos', 'Outros_Custos')
    }
    
    # Busca números e palavras
    pedacos = re.findall(r'([a-z1-9á-ú]+)\s*(\d+[\.]?\d*)', frase)
    
    for item, valor_str in pedacos:
        valor = float(valor_str)
        identificado = False
        for chave, (tipo, col) in mapa.items():
            if chave in item:
                res[tipo][col] = valor
                identificado = True; break
        
        if not identificado:
            # Se não entendeu, joga em outros e avisa
            res['Ganhos']['Outros_Receita'] = res['Ganhos'].get('Outros_Receita', 0) + valor
            res['Duvidas'].append(item)
            
    return res

# --- INTERFACE ---
st.sidebar.subheader(f"Motorista: {NOME_USUARIO.capitalize()}")
if st.sidebar.button("Sair"):
    st.session_state['autenticado'] = False
    st.rerun()

aba1, aba2 = st.tabs(["📥 Novo Lançamento", "📈 Meu Financeiro"])

with aba1:
    st.write("### O que rodamos hoje?")
    texto_bruto = st.text_area("Descreva seus ganhos e gastos", placeholder="Ex: urbano 150, marmita 35, gasolina 50")
    foto = st.file_uploader("📷 Foto do Painel (KM)", type=['png', 'jpg', 'jpeg'])
    
    if st.button("🚀 Gravar Dados com Segurança"):
        if not texto_bruto and not foto:
            st.warning("Por favor, digite algo ou envie uma foto.")
        else:
            dados = processar_fala_motorista(texto_bruto)
            
            # Alerta de dúvida
            if dados['Duvidas']:
                st.warning(f"⚠️ Atenção: Não reconheci os termos: {', '.join(dados['Duvidas'])}. Lançamos como 'Outros', verifique depois!")

            km_lido = 0
            if foto:
                try:
                    txt_img = pytesseract.image_to_string(PILImage.open(foto))
                    nums = [int(n) for n in re.findall(r'\d+', txt_img) if int(n) > 100]
                    if nums: km_lido = max(nums)
                except: st.error("Não consegui ler o KM da foto automaticamente.")

            # Montar a linha
            nova_linha = {
                'Usuario': NOME_USUARIO, 'Data': datetime.now().strftime("%Y-%m-%d"),
                'Urbano': dados['Ganhos'].get('Urbano', 0), 'Boraali': dados['Ganhos'].get('Boraali', 0),
                'app163': dados['Ganhos'].get('app163', 0), 'Outros_Receita': dados['Ganhos'].get('Outros_Receita', 0),
                'Energia': dados['Gastos'].get('Energia', 0), 'Manuten': dados['Gastos'].get('Manuten', 0),
                'Seguro': dados['Gastos'].get('Seguro', 0), 'Aplicativo': dados['Gastos'].get('Aplicativo', 0),
                'Outros_Custos': dados['Gastos'].get('Outros_Custos', 0), 'KM_Final': km_lido
            }
            
            # Enviar para o Google
            try:
                df_final = pd.concat([df_geral, pd.DataFrame([nova_linha])], ignore_index=True)
                conn.update(worksheet="Lancamentos", data=df_final)
                st.success("✅ Tudo pronto! Dados salvos na nuvem.")
                st.balloons()
            except:
                st.error("❌ Falha crítica ao salvar. Verifique sua conexão.")

with aba2:
    if not df_usuario.empty:
        rec = df_usuario[['Urbano', 'Boraali', 'app163', 'Outros_Receita']].sum().sum()
        gas = df_usuario[['Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Outros_Custos']].sum().sum()
        
        st.subheader("Resumo do Período")
        c1, c2, c3 = st.columns(3)
        c1.metric("Ganhos", f"R$ {rec:,.2f}")
        c2.metric("Despesas", f"R$ {gas:,.2f}")
        c3.metric("Líquido", f"R$ {rec-gas:,.2f}")
        
        st.write("---")
        fig = px.bar(df_usuario, x='Data', y=['Urbano', 'Boraali', 'app163', 'Outros_Receita'], title="Seus Ganhos Diários")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Ainda não temos dados para exibir gráficos.")
