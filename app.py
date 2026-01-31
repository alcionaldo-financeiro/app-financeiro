import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import PIL.Image as PILImage
import pytesseract
import re
from datetime import datetime
import plotly.express as px
import time # Importante para dar tempo de ver a mensagem de sucesso

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="BYD Pro - Gestão Inteligente", page_icon="💎", layout="wide")

# Colunas Oficiais
COLUNAS_OFICIAIS = [
    'Usuario', 'Data', 'Urbano', 'Boraali', 'app163', 'Outros_Receita', 
    'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Outros_Custos', 
    'KM_Final', 'Detalhes'
]

conn = st.connection("gsheets", type=GSheetsConnection)

# --- SISTEMA DE CONEXÃO "CORINGA" ---
def conectar_banco():
    try:
        # Lê a PRIMEIRA aba (Index 0) para evitar erro de nome
        df = conn.read(worksheet=0, ttl="0")
        
        if df is None or df.empty or len(df.columns) < 2:
            df_novo = pd.DataFrame(columns=COLUNAS_OFICIAIS)
            conn.update(worksheet=0, data=df_novo)
            return df_novo, "Primeira Aba (Auto)"
            
        return df, "Conectado!"
    except Exception as e:
        return pd.DataFrame(columns=COLUNAS_OFICIAIS), f"Erro: {e}"

# Carrega os dados
df_geral, STATUS_CONEXAO = conectar_banco()

# --- LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.markdown("# 💎 BYD Pro")
    st.write("### O Sistema do Motorista de Elite")
    usuario = st.text_input("Identifique-se (Nome):").strip().lower()
    if st.button("Acessar Painel 🚀"):
        if usuario:
            st.session_state['usuario'] = usuario
            st.session_state['autenticado'] = True
            st.rerun()
    st.stop()

# --- DADOS DO USUÁRIO ---
NOME_USUARIO = st.session_state['usuario']

try:
    cols_num = ['Urbano', 'Boraali', 'app163', 'Outros_Receita', 'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Outros_Custos', 'KM_Final']
    if not df_geral.empty:
        for col in cols_num:
            if col in df_geral.columns:
                df_geral[col] = pd.to_numeric(df_geral[col], errors='coerce').fillna(0)
    
    if 'Usuario' in df_geral.columns:
        df_usuario = df_geral[df_geral['Usuario'] == NOME_USUARIO].copy()
    else:
        df_usuario = pd.DataFrame(columns=COLUNAS_OFICIAIS)
except:
    df_usuario = pd.DataFrame(columns=COLUNAS_OFICIAIS)

# --- CÉREBRO ---
def processar_texto(frase):
    frase = frase.lower().replace(',', '.')
    res = {'Ganhos': {}, 'Gastos': {}, 'Detalhes': []}
    mapa = {
        'urbano': ('Ganhos', 'Urbano'), 'bora': ('Ganhos', 'Boraali'), '163': ('Ganhos', 'app163'),
        'particula': ('Ganhos', 'Outros_Receita'), 'viagem': ('Ganhos', 'Outros_Receita'),
        'energia': ('Gastos', 'Energia'), 'gasolina': ('Gastos', 'Energia'), 'alcool': ('Gastos', 'Energia'),
        'manut': ('Gastos', 'Manuten'), 'seguro': ('Gastos', 'Seguro'), 'app': ('Gastos', 'Aplicativo'),
        'marmita': ('Gastos', 'Outros_Custos'), 'almoco': ('Gastos', 'Outros_Custos')
    }
    pedacos = re.findall(r'([a-z1-9á-ú]+)\s*(\d+[\.]?\d*)', frase)
    for item, valor_str in pedacos:
        valor = float(valor_str)
        achou = False
        for chave, (tipo, col) in mapa.items():
            if chave in item:
                res[tipo][col] = res[tipo].get(col, 0) + valor
                achou = True; break
        if not achou:
            res['Ganhos']['Outros_Receita'] = res['Ganhos'].get('Outros_Receita', 0) + valor
            res['Detalhes'].append(f"{item}")
    return res

# --- TELA ---
st.sidebar.markdown(f"## 🚘 {NOME_USUARIO.capitalize()}")
if st.sidebar.button("Sair"):
    st.session_state['autenticado'] = False
    st.rerun()

aba1, aba2 = st.tabs(["📝 Lançar", "💰 Extrato"])

with aba1:
    if "Erro" in STATUS_CONEXAO:
        st.error(f"🚨 {STATUS_CONEXAO}")
    else:
        st.success(f"✅ {STATUS_CONEXAO}")
    
    # CRIA CHAVES DE MEMÓRIA PARA PODER LIMPAR DEPOIS
    if "texto_input" not in st.session_state: st.session_state.texto_input = ""
    
    # Campo de texto vinculado à memória
    texto = st.text_area("O que rolou?", key="texto_input", placeholder="Ex: urbano 200, boraali 50")
    # Campo de foto com chave para resetar
    foto = st.file_uploader("Foto KM", key="foto_input", type=['png', 'jpg', 'jpeg'])
    
    if st.button("GRAVAR 🚀", use_container_width=True):
        if "Erro" in STATUS_CONEXAO:
            st.error("Sem conexão.")
        elif not texto and not foto:
            st.warning("Digite algo!")
        else:
            dados = processar_texto(texto)
            km_lido = 0
            
            nova = {col: 0 for col in COLUNAS_OFICIAIS}
            nova.update({
                'Usuario': NOME_USUARIO, 'Data': datetime.now().strftime("%Y-%m-%d"),
                'Urbano': dados['Ganhos'].get('Urbano', 0), 'Boraali': dados['Ganhos'].get('Boraali', 0),
                'app163': dados['Ganhos'].get('app163', 0), 'Outros_Receita': dados['Ganhos'].get('Outros_Receita', 0),
                'Energia': dados['Gastos'].get('Energia', 0), 'Manuten': dados['Gastos'].get('Manuten', 0),
                'Seguro': dados['Gastos'].get('Seguro', 0), 'Aplicativo': dados['Gastos'].get('Aplicativo', 0),
                'Outros_Custos': dados['Gastos'].get('Outros_Custos', 0), 'KM_Final': km_lido,
                'Detalhes': ", ".join(dados['Detalhes'])
            })
            
            try:
                df_atual = conn.read(worksheet=0, ttl="0")
                df_final = pd.concat([df_atual, pd.DataFrame([nova])], ignore_index=True)
                conn.update(worksheet=0, data=df_final)
                
                st.balloons()
                st.success("Salvo com Sucesso! Atualizando...")
                
                # --- O SEGREDO DO REFRESH ---
                time.sleep(1.5) # Espera 1.5s pro motorista ler a mensagem
                st.rerun()      # Recarrega a página (Limpa campos e Atualiza Gráfico)
                
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

with aba2:
    if not df_usuario.empty:
        # Métricas
        g = df_usuario[['Urbano', 'Boraali', 'app163', 'Outros_Receita']].sum().sum()
        d = df_usuario[['Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Outros_Custos']].sum().sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ganhos", f"R$ {g:,.2f}")
        c2.metric("Despesas", f"R$ {d:,.2f}")
        c3.metric("Lucro", f"R$ {g-d:,.2f}")
        
        st.divider()
        
        # Histórico (Agora mostra o mais recente no topo!)
        st.write("📋 **Últimos Lançamentos:**")
        # Inverte a ordem para mostrar o último primeiro
        df_view = df_usuario.iloc[::-1] 
        visivel = ['Data', 'Urbano', 'Boraali', 'Energia', 'Detalhes']
        st.dataframe(df_view[[c for c in visivel if c in df_usuario.columns]].head(10), use_container_width=True)
    else:
        st.info("Nenhum dado lançado ainda.")
