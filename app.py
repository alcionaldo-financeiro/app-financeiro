import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime
import time
import pytz

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="BYD Pro", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

# --- 2. CSS "NUCLEAR" PARA REMOVER TUDO (ÍCONES, BOTÕES E RODAPÉ) ---
st.markdown("""
    <style>
        /* Esconde o menu, cabeçalho e rodapé padrão */
        #MainMenu {visibility: hidden; display: none !important;}
        header {visibility: hidden; display: none !important;}
        footer {visibility: hidden; display: none !important;}
        
        /* Esconde o botão 'Deploy' e o 'Manage App' (Ícones da direita) */
        .stDeployButton {display:none !important;}
        [data-testid="stToolbar"] {visibility: hidden !important; display: none !important;}
        [data-testid="stDecoration"] {display: none !important;}
        [data-testid="stStatusWidget"] {display: none !important;}
        
        /* Remove o botão vermelho 'Manage App' que aparece no Streamlit Cloud */
        button[title="Manage app"] {display: none !important;}
        #streamlit_viewer_action_container {display: none !important;}

        /* Ajusta o espaçamento para o conteúdo subir */
        .block-container {padding-top: 1rem !important; padding-bottom: 0rem !important;}

        /* Estilo do Botão Principal do Sistema */
        div.stButton > button[kind="primary"] {
            background-color: #28a745 !important;
            color: white !important;
            border-radius: 12px;
            height: 3.5em;
            font-weight: bold;
            width: 100%;
        }
    </style>
    
    <script>
        // Bloqueia o tradutor do Google de aparecer
        document.documentElement.setAttribute('lang', 'pt');
        document.documentElement.setAttribute('class', 'notranslate');
    </script>
    """, unsafe_allow_html=True)

# --- 3. CONFIGURAÇÕES E CONEXÃO ---
COLUNAS_OFICIAIS = [
    'ID_Unico', 'Status', 'Usuario', 'CPF', 'Data', 
    'Urbano', 'Boraali', 'app163', 'Outros_Receita', 
    'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos', 
    'KM_Inicial', 'KM_Final', 'Detalhes'
]
FUSO_BR = pytz.timezone('America/Sao_Paulo')
conn = st.connection("gsheets", type=GSheetsConnection)

def limpar_texto(t): return re.sub(r'\D', '', str(t))

@st.cache_data(ttl=60)
def carregar_dados_seguros():
    try:
        df = conn.read(worksheet=0, ttl=0)
        if df is None or df.empty: return pd.DataFrame(columns=COLUNAS_OFICIAIS)
        df['CPF'] = df['CPF'].apply(limpar_texto)
        return df
    except: return pd.DataFrame(columns=COLUNAS_OFICIAIS)

# --- 4. LOGIN COM MEMÓRIA (QUERY PARAMS) ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

# Busca dados salvos na URL para preencher automático
params = st.query_params
q_nome = params.get("n", "")
q_cpf = params.get("c", "")

if not st.session_state['autenticado']:
    st.title("💎 BYD Pro")
    st.markdown("### Identificação do Motorista")
    
    nome_input = st.text_input("Nome Completo:", value=q_nome)
    cpf_input = st.text_input("CPF (Apenas números):", value=q_cpf, max_chars=11)

    if st.button("ACESSAR SISTEMA 🚀", type="primary"):
        cpf_limpo = limpar_texto(cpf_input)
        if len(cpf_limpo) == 11 and nome_input:
            # Salva na URL para a próxima vez
            st.query_params["n"] = nome_input
            st.query_params["c"] = cpf_limpo
            
            st.session_state['usuario'] = nome_input.lower().strip()
            st.session_state['cpf_usuario'] = cpf_limpo
            st.session_state['autenticado'] = True
            st.rerun()
        else:
            st.error("⚠️ Preencha Nome e CPF corretamente.")
    st.stop()

# --- 5. SISTEMA LOGADO ---
NOME = st.session_state['usuario']
CPF = st.session_state['cpf_usuario']

# Carrega e Filtra: Segurança máxima (um motorista não vê o outro)
df_total = carregar_dados_seguros()
df_user = df_total[(df_total['CPF'] == CPF) & (df_total['Status'] != 'Lixeira')].copy()

st.markdown(f"#### Olá, {NOME.title()}")

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
        ult_km = int(df_user['KM_Final'].max()) if not df_user.empty else 0
        k1 = st.number_input("KM Inicial", value=ult_km)
        k2 = st.number_input("KM Final", value=None)

        if st.button("AVANÇAR ➡️", type="primary"):
            st.session_state['temp'] = {'u':u,'b':b,'en':en,'ma':ma,'k1':k1,'k2':k2 if k2 else k1}
            st.session_state['conferir'] = True
            st.rerun()
    else:
        t = st.session_state['temp']
        st.warning("Confirmar lançamento?")
        if st.button("✅ SALVAR"):
            with st.spinner("Gravando..."):
                nova = {col: 0 for col in COLUNAS_OFICIAIS}
                nova.update({
                    'ID_Unico': str(int(time.time())), 'Status': 'Ativo',
                    'Usuario': NOME, 'CPF': CPF, 
                    'Data': datetime.now(FUSO_BR).strftime("%Y-%m-%d"),
                    'Urbano': t['u'], 'Boraali': t['b'], 'Energia': t['en'], 'Manuten': t['ma'],
                    'KM_Inicial': t['k1'], 'KM_Final': t['k2']
                })
                df_db = conn.read(worksheet=0, ttl=0)
                df_final = pd.concat([df_db, pd.DataFrame([nova])], ignore_index=True)
                conn.update(worksheet=0, data=df_final)
                st.success("Salvo com sucesso!")
                time.sleep(1)
                st.session_state['conferir'] = False
                st.rerun()

with aba2:
    if df_user.empty:
        st.info("Nenhum dado encontrado.")
    else:
        st.dataframe(df_user[['Data', 'Urbano', 'Boraali', 'KM_Final']].sort_values('Data', ascending=False), use_container_width=True, hide_index=True)

if st.button("Sair / Trocar Usuário"):
    st.session_state['autenticado'] = False
    st.rerun()
