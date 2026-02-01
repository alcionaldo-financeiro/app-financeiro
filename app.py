import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime
import time
import pytz

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="BYD Pro", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

# --- 2. CSS PARA LIMPAR A INTERFACE (CORRIGIDO) ---
# Aqui removemos os menus, o rodapé e tentamos bloquear o tradutor
st.markdown("""
    <style>
        /* Esconde o menu superior (três pontinhos) e o botão Deploy */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stDeployButton {display:none;}
        
        /* Remove o espaço em branco no topo */
        .block-container {padding-top: 0rem !important;}

        /* Estilo do Botão Principal */
        div.stButton > button[kind="primary"] {
            background-color: #28a745 !important;
            color: white !important;
            border-radius: 12px;
            height: 3.5em;
            font-weight: bold;
            width: 100%;
            border: none;
        }

        /* Estilo dos campos de entrada */
        .stNumberInput input {
            font-size: 20px !important;
            font-weight: bold;
            text-align: center;
        }
    </style>
    
    <!-- Instrução para o navegador não traduzir a página -->
    <meta name="google" content="notranslate">
    """, unsafe_allow_html=True)

# --- 3. CONFIGURAÇÕES DE DADOS ---
COLUNAS_OFICIAIS = [
    'ID_Unico', 'Status', 'Usuario', 'CPF', 'Data', 
    'Urbano', 'Boraali', 'app163', 'Outros_Receita', 
    'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos', 
    'KM_Inicial', 'KM_Final', 'Detalhes'
]
FUSO_BR = pytz.timezone('America/Sao_Paulo')
conn = st.connection("gsheets", type=GSheetsConnection)

def limpar_texto(t): return re.sub(r'\D', '', str(t))

# Função de carregamento otimizada (Usa cache para ser rápido)
@st.cache_data(ttl=60)
def carregar_dados_seguros():
    try:
        df = conn.read(worksheet=0, ttl=0) 
        if df is None or df.empty: return pd.DataFrame(columns=COLUNAS_OFICIAIS)
        df['CPF'] = df['CPF'].apply(limpar_texto)
        return df
    except:
        return pd.DataFrame(columns=COLUNAS_OFICIAIS)

# --- 4. LÓGICA DE LOGIN "LEMBRAR MOTORISTA" ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

# Recupera dados salvos para não ter que digitar sempre
query_params = st.query_params
saved_nome = query_params.get("n", "")
saved_cpf = query_params.get("c", "")

if not st.session_state['autenticado']:
    st.title("💎 BYD Pro")
    st.markdown("### Identificação do Motorista")
    
    nome_input = st.text_input("Nome Completo:", value=saved_nome, placeholder="Ex: João Silva")
    cpf_input = st.text_input("CPF (Apenas números):", value=saved_cpf, max_chars=11, placeholder="00000000000")

    if st.button("ACESSAR SISTEMA 🚀", type="primary"):
        cpf_limpo = limpar_texto(cpf_input)
        nome_limpo = nome_input.lower().strip()
        
        if len(cpf_limpo) == 11 and nome_limpo:
            # Salva na URL para a próxima vez
            st.query_params["n"] = nome_limpo
            st.query_params["c"] = cpf_limpo
            
            st.session_state['usuario'] = nome_limpo
            st.session_state['cpf_usuario'] = cpf_limpo
            st.session_state['autenticado'] = True
            st.rerun()
        else:
            st.error("⚠️ Digite o Nome e os 11 números do CPF.")
    st.stop()

# --- 5. SISTEMA LOGADO ---
NOME_LOGADO = st.session_state['usuario']
CPF_LOGADO = st.session_state['cpf_usuario']

# FILTRO DE PRIVACIDADE: O motorista só vê os dados dele
df_geral = carregar_dados_seguros()
df_usuario = df_geral[(df_geral['CPF'] == CPF_LOGADO) & (df_geral['Status'] != 'Lixeira')].copy()

# Interface Principal
st.markdown(f"#### Olá, {NOME_LOGADO.title()} 👤")

aba1, aba2 = st.tabs(["📝 LANÇAR", "📊 RELATÓRIOS"])

with aba1:
    if 'conferir' not in st.session_state: st.session_state['conferir'] = False
    
    if not st.session_state['conferir']:
        with st.expander("💰 GANHOS", expanded=True):
            u = st.number_input("Urbano/99", min_value=0.0, step=10.0, value=None)
            b = st.number_input("BoraAli", min_value=0.0, step=10.0, value=None)
        
        with st.expander("💸 GASTOS", expanded=False):
            en = st.number_input("Energia", min_value=0.0, step=5.0, value=None)
            ma = st.number_input("Manutenção", min_value=0.0, step=5.0, value=None)

        st.markdown("---")
        ult_km = int(df_usuario['KM_Final'].max()) if not df_usuario.empty else 0
        k1 = st.number_input("KM Inicial", value=ult_km)
        k2 = st.number_input("KM Final", value=None, placeholder="Digite o KM atual")

        if st.button("AVANÇAR ➡️", type="primary"):
            st.session_state['temp'] = {'u':u,'b':b,'en':en,'ma':ma,'k1':k1,'k2':k2 if k2 else k1}
            st.session_state['conferir'] = True
            st.rerun()
    else:
        t = st.session_state['temp']
        st.warning("Confirma os dados?")
        if st.button("✅ SALVAR"):
            with st.spinner("Gravando..."):
                nova = {col: 0 for col in COLUNAS_OFICIAIS}
                nova.update({
                    'ID_Unico': str(int(time.time())), 'Status': 'Ativo',
                    'Usuario': NOME_LOGADO, 'CPF': CPF_LOGADO, 
                    'Data': datetime.now(FUSO_BR).strftime("%Y-%m-%d"),
                    'Urbano': t['u'], 'Boraali': t['b'], 'Energia': t['en'], 'Manuten': t['ma'],
                    'KM_Inicial': t['k1'], 'KM_Final': t['k2']
                })
                df_db = conn.read(worksheet=0, ttl=0)
                df_final = pd.concat([df_db, pd.DataFrame([nova])], ignore_index=True)
                conn.update(worksheet=0, data=df_final)
                st.success("Sucesso!")
                time.sleep(1)
                st.session_state['conferir'] = False
                st.rerun()

with aba2:
    if df_usuario.empty:
        st.info("Você ainda não tem lançamentos.")
    else:
        # Mostra apenas os dados do motorista atual
        st.dataframe(df_usuario[['Data', 'Urbano', 'Boraali', 'KM_Final']].sort_values('Data', ascending=False), use_container_width=True, hide_index=True)

if st.button("Sair / Trocar Motorista"):
    st.session_state['autenticado'] = False
    st.rerun()
