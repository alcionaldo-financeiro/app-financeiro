import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import PIL.Image as PILImage
import pytesseract
import re
from datetime import datetime
import plotly.express as px

# --- CONFIGURAÇÃO DE ELITE ---
st.set_page_config(page_title="BYD Pro - Gestão Inteligente", page_icon="💎", layout="wide")

# Colunas que o sistema exige
COLUNAS_OFICIAIS = [
    'Usuario', 'Data', 'Urbano', 'Boraali', 'app163', 'Outros_Receita', 
    'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Outros_Custos', 
    'KM_Final', 'Detalhes'
]

conn = st.connection("gsheets", type=GSheetsConnection)

# --- SISTEMA DE BUSCA DE ABAS (CHAVE MESTRA) ---
def conectar_banco_universal():
    """
    Tenta encontrar a planilha em qualquer aba que exista (Página1, Sheet1, etc).
    Não importa o nome, o robô vai achar.
    """
    nomes_teste = ["Lancamentos", "Página1", "Pagina1", "Sheet1"]
    
    for nome in nomes_teste:
        try:
            # Tenta ler a aba
            df = conn.read(worksheet=nome, ttl="0")
            
            # Se a aba existe mas está vazia ou sem cabeçalho, a gente arruma
            if df is None or df.empty or not set(COLUNAS_OFICIAIS).issubset(df.columns):
                # Recria o cabeçalho na aba que achou
                df_novo = pd.DataFrame(columns=COLUNAS_OFICIAIS)
                conn.update(worksheet=nome, data=df_novo)
                return df_novo, nome
            
            return df, nome # Achou e está pronta!
        except:
            continue # Se deu erro, tenta o próximo nome da lista

    # Se chegou aqui, não achou nada. Tenta criar 'Lancamentos' na força bruta.
    try:
        df_novo = pd.DataFrame(columns=COLUNAS_OFICIAIS)
        conn.update(worksheet="Lancamentos", data=df_novo)
        return df_novo, "Lancamentos"
    except Exception as e:
        st.error(f"⚠️ Erro de Conexão Crítico: {e}")
        return pd.DataFrame(columns=COLUNAS_OFICIAIS), "Erro"

# --- INICIALIZAÇÃO INTELIGENTE ---
df_geral, ABA_ATIVA = conectar_banco_universal()

# --- LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.markdown("# 💎 BYD Pro")
    st.markdown("### O Sistema do Motorista de Elite")
    usuario = st.text_input("Identifique-se (Nome):").strip().lower()
    if st.button("Acessar Painel 🚀"):
        if usuario:
            st.session_state['usuario'] = usuario
            st.session_state['autenticado'] = True
            st.rerun()
    st.stop()

# --- CARREGAR DADOS DO USUÁRIO ---
NOME_USUARIO = st.session_state['usuario']

try:
    # Tratamento numérico para evitar erros de soma
    cols_num = ['Urbano', 'Boraali', 'app163', 'Outros_Receita', 'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Outros_Custos', 'KM_Final']
    for col in cols_num:
        if col in df_geral.columns:
            df_geral[col] = pd.to_numeric(df_geral[col], errors='coerce').fillna(0)
    
    df_usuario = df_geral[df_geral['Usuario'] == NOME_USUARIO].copy()
except:
    df_usuario = pd.DataFrame(columns=COLUNAS_OFICIAIS)

# --- CÉREBRO: INTERPRETADOR DE TEXTO ---
def processar_texto_inteligente(frase):
    frase = frase.lower().replace(',', '.')
    res = {'Ganhos': {}, 'Gastos': {}, 'Detalhes': []}
    
    mapa = {
        'urbano': ('Ganhos', 'Urbano'), 'bora': ('Ganhos', 'Boraali'), '163': ('Ganhos', 'app163'),
        'particula': ('Ganhos', 'Outros_Receita'), 'viagem': ('Ganhos', 'Outros_Receita'),
        'energia': ('Gastos', 'Energia'), 'luz': ('Gastos', 'Energia'), 'carreg': ('Gastos', 'Energia'),
        'gasolina': ('Gastos', 'Energia'), 'alcool': ('Gastos', 'Energia'),
        'manut': ('Gastos', 'Manuten'), 'oficina': ('Gastos', 'Manuten'), 'pneu': ('Gastos', 'Manuten'),
        'seguro': ('Gastos', 'Seguro'), 'app': ('Gastos', 'Aplicativo'),
        'marmita': ('Gastos', 'Outros_Custos'), 'almoco': ('Gastos', 'Outros_Custos'), 
        'lanche': ('Gastos', 'Outros_Custos'), 'agua': ('Gastos', 'Outros_Custos'),
        'lavagem': ('Gastos', 'Manuten')
    }
    
    pedacos = re.findall(r'([a-z1-9á-ú]+)\s*(\d+[\.]?\d*)', frase)
    
    for item, valor_str in pedacos:
        valor = float(valor_str)
        identificado = False
        
        for chave, (tipo, col) in mapa.items():
            if chave in item:
                res[tipo][col] = res[tipo].get(col, 0) + valor
                identificado = True
                break
        
        if not identificado:
            # Se não sabe o que é, joga em Outros Receita (padrão otimista) e anota
            res['Ganhos']['Outros_Receita'] = res['Ganhos'].get('Outros_Receita', 0) + valor
            res['Detalhes'].append(f"{item} ({valor})")
        else:
            if 'Outros' in col:
                res['Detalhes'].append(f"{item}")

    return res

# --- INTERFACE ---
st.sidebar.markdown(f"## 🚘 Piloto: {NOME_USUARIO.capitalize()}")
if st.sidebar.button("Sair"):
    st.session_state['autenticado'] = False
    st.rerun()

aba1, aba2 = st.tabs(["📝 Lançar Agora", "💰 Meu Bolso"])

with aba1:
    st.info(f"Conectado na planilha: **{ABA_ATIVA}**") # Mostra onde está salvando
    st.write("### O que rolou no plantão?")
    texto = st.text_area("", placeholder="Ex: urbano 200, boraali 50, marmita 30")
    foto = st.file_uploader("📸 Foto do KM (Se tiver)", type=['png', 'jpg', 'jpeg'])
    
    if st.button("GRAVAR 🚀", use_container_width=True):
        if not texto and not foto:
            st.warning("Opa, digite algo para eu lançar!")
        else:
            with st.spinner("Processando..."):
                dados = processar_texto_inteligente(texto)
                
                km_lido = 0
                if foto:
                    try:
                        img = PILImage.open(foto)
                        txt_img = pytesseract.image_to_string(img)
                        nums = [int(n) for n in re.findall(r'\d+', txt_img) if int(n) > 500]
                        if nums: km_lido = max(nums)
                    except: pass

                nova_linha = {col: 0 for col in COLUNAS_OFICIAIS}
                nova_linha.update({
                    'Usuario': NOME_USUARIO,
                    'Data': datetime.now().strftime("%Y-%m-%d"),
                    'Urbano': dados['Ganhos'].get('Urbano', 0),
                    'Boraali': dados['Ganhos'].get('Boraali', 0),
                    'app163': dados['Ganhos'].get('app163', 0),
                    'Outros_Receita': dados['Ganhos'].get('Outros_Receita', 0),
                    'Energia': dados['Gastos'].get('Energia', 0),
                    'Manuten': dados['Gastos'].get('Manuten', 0),
                    'Seguro': dados['Gastos'].get('Seguro', 0),
                    'Aplicativo': dados['Gastos'].get('Aplicativo', 0),
                    'Outros_Custos': dados['Gastos'].get('Outros_Custos', 0),
                    'KM_Final': km_lido,
                    'Detalhes': ", ".join(dados['Detalhes'])
                })
                
                try:
                    # Lê de novo a aba certa para garantir atualização
                    df_atual = conn.read(worksheet=ABA_ATIVA, ttl="0")
                    if df_atual is None: df_atual = pd.DataFrame(columns=COLUNAS_OFICIAIS)
                    
                    df_final = pd.concat([df_atual, pd.DataFrame([nova_linha])], ignore_index=True)
                    conn.update(worksheet=ABA_ATIVA, data=df_final)
                    st.success("✅ Tá na mão! Salvo com sucesso.")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

with aba2:
    if not df_usuario.empty:
        ganhos = df_usuario[['Urbano', 'Boraali', 'app163', 'Outros_Receita']].sum().sum()
        custos = df_usuario[['Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Outros_Custos']].sum().sum()
        lucro = ganhos - custos
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Faturamento", f"R$ {ganhos:,.2f}")
        col2.metric("Custos", f"R$ {custos:,.2f}", delta_color="inverse")
        col3.metric("Lucro Líquido", f"R$ {lucro:,.2f}")
        
        st.divider()
        st.write("📋 Histórico:")
        visivel = ['Data', 'Urbano', 'Boraali', 'Energia', 'Detalhes', 'KM_Final']
        st.dataframe(df_usuario[[c for c in visivel if c in df_usuario.columns]].tail(10), use_container_width=True)
    else:
        st.info("Nenhum dado lançado ainda. Manda ver no primeiro!")
