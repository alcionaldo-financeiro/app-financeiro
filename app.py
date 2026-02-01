import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime
import time
import pytz

# --- 1. CONFIGURAÇÃO E BLOQUEIO DE TRADUTOR ---
st.set_page_config(page_title="BYD Pro", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

# --- CSS PARA LIMPAR A INTERFACE E REMOVER ÍCONES ---
st.markdown("""
    <html lang="pt-br">
    <style>
    /* Remove menu, rodapé e ícone do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stStatusWidget"] {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* Estilização dos botões e inputs */
    div.stButton > button[kind="primary"] {
        background-color: #28a745 !important; 
        color: white !important;
        border-radius: 12px; height: 3.5em; font-weight: bold; width: 100%;
    }
    .stNumberInput input { font-size: 20px !important; font-weight: bold; text-align: center; }
    
    /* Evita que o Google tradutor mude o layout */
    .notranslate { translate: no !important; }
    </style>
    </html>
    """, unsafe_allow_html=True)

# --- CONFIGURAÇÕES ---
COLUNAS_OFICIAIS = [
    'ID_Unico', 'Status', 'Usuario', 'CPF', 'Data', 
    'Urbano', 'Boraali', 'app163', 'Outros_Receita', 
    'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos', 
    'KM_Inicial', 'KM_Final', 'Detalhes'
]
FUSO_BR = pytz.timezone('America/Sao_Paulo')
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÕES DE DADOS (MAIS LEVES) ---
def limpar_texto(t): return re.sub(r'\D', '', str(t))

def carregar_dados_seguros():
    try:
        # ttl=600 faz o app abrir rápido (cache de 10 min), mas o 'read' no save ignora isso
        df = conn.read(worksheet=0, ttl=0) 
        if df is None or df.empty: return pd.DataFrame(columns=COLUNAS_OFICIAIS)
        df['CPF'] = df['CPF'].apply(limpar_texto)
        return df
    except:
        return pd.DataFrame(columns=COLUNAS_OFICIAIS)

# --- LÓGICA DE LOGIN COM "LEMBRAR-ME" ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

# Tenta recuperar dados salvos na URL (Query Params) para não precisar digitar
query_params = st.query_params
saved_nome = query_params.get("n", "")
saved_cpf = query_params.get("c", "")

if not st.session_state['autenticado']:
    st.title("💎 BYD Pro")
    st.markdown("### Identificação do Motorista")
    
    # Preenche automaticamente se houver dados salvos
    nome_input = st.text_input("Nome Completo:", value=saved_nome, placeholder="Ex: João Silva")
    cpf_input = st.text_input("CPF (Apenas números):", value=saved_cpf, max_chars=11, placeholder="00000000000")

    if st.button("ACESSAR SISTEMA 🚀", type="primary"):
        cpf_limpo = limpar_texto(cpf_input)
        nome_limpo = nome_input.lower().strip()
        
        if len(cpf_limpo) == 11 and nome_limpo:
            # Salva no navegador do motorista (via URL) para a próxima vez
            st.query_params["n"] = nome_limpo
            st.query_params["c"] = cpf_limpo
            
            st.session_state['usuario'] = nome_limpo
            st.session_state['cpf_usuario'] = cpf_limpo
            st.session_state['autenticado'] = True
            st.rerun()
        else:
            st.error("⚠️ Por favor, preencha o Nome e os 11 números do CPF.")
    st.stop()

# --- SISTEMA APÓS LOGIN (PRIVACIDADE TOTAL) ---
NOME_LOGADO = st.session_state['usuario']
CPF_LOGADO = st.session_state['cpf_usuario']

# Carrega os dados e filtra IMEDIATAMENTE. O motorista só "enxerga" o que é dele.
df_geral = carregar_dados_seguros()
df_usuario = df_geral[(df_geral['CPF'] == CPF_LOGADO) & (df_geral['Status'] != 'Lixeira')].copy()

# Header
st.markdown(f"#### Bem-vindo, {NOME_LOGADO.title()} 👤")
if st.button("Sair / Trocar Motorista", help="Clique para deslogar"):
    st.session_state['autenticado'] = False
    st.rerun()

aba1, aba2 = st.tabs(["📝 NOVO LANÇAMENTO", "📊 MEUS RELATÓRIOS"])

with aba1:
    if 'conferir' not in st.session_state: st.session_state['conferir'] = False
    
    if not st.session_state['conferir']:
        with st.expander("💰 GANHOS DO DIA", expanded=True):
            col1, col2 = st.columns(2)
            u = col1.number_input("Urbano/99", min_value=0.0, step=10.0, value=None)
            b = col2.number_input("BoraAli", min_value=0.0, step=10.0, value=None)
            a = col1.number_input("App 163", min_value=0.0, step=10.0, value=None)
            o = col2.number_input("Outros Ganhos", min_value=0.0, step=10.0, value=None)

        with st.expander("💸 GASTOS DO DIA", expanded=False):
            col3, col4 = st.columns(2)
            en = col3.number_input("Energia", min_value=0.0, step=5.0, value=None)
            al = col4.number_input("Alimentação", min_value=0.0, step=5.0, value=None)
            ma = col3.number_input("Manutenção", min_value=0.0, step=5.0, value=None)

        st.markdown("---")
        # Busca último KM do motorista para facilitar
        ult_km = int(df_usuario['KM_Final'].max()) if not df_usuario.empty else 0
        k1 = st.number_input("KM Inicial", value=ult_km)
        k2 = st.number_input("KM Final", value=None, placeholder="Digite o KM atual")

        if st.button("AVANÇAR ➡️", type="primary"):
            st.session_state['temp'] = {
                'u':u,'b':b,'a':a,'o':o,'en':en,'al':al,'ma':ma,'k1':k1,'k2':k2 if k2 else k1
            }
            st.session_state['conferir'] = True
            st.rerun()
    else:
        # Tela de Confirmação
        t = st.session_state['temp']
        ganho = sum([t['u'] or 0, t['b'] or 0, t['a'] or 0, t['o'] or 0])
        gasto = sum([t['en'] or 0, t['al'] or 0, t['ma'] or 0])
        
        st.warning(f"Confirma os valores? Ganhos: R$ {ganho:.2f} | Gastos: R$ {gasto:.2f}")
        if st.button("✅ SALVAR AGORA"):
            with st.spinner("Gravando..."):
                nova = {col: 0 for col in COLUNAS_OFICIAIS}
                nova.update({
                    'ID_Unico': str(int(time.time())), 'Status': 'Ativo',
                    'Usuario': NOME_LOGADO, 'CPF': CPF_LOGADO, 
                    'Data': datetime.now(FUSO_BR).strftime("%Y-%m-%d"),
                    'Urbano': t['u'], 'Boraali': t['b'], 'app163': t['a'], 'Outros_Receita': t['o'],
                    'Energia': t['en'], 'Alimentacao': t['al'], 'Manuten': t['ma'],
                    'KM_Inicial': t['k1'], 'KM_Final': t['k2']
                })
                df_db = conn.read(worksheet=0, ttl=0)
                df_final = pd.concat([df_db, pd.DataFrame([nova])], ignore_index=True)
                conn.update(worksheet=0, data=df_final)
                st.success("Salvo!")
                time.sleep(1)
                st.session_state['conferir'] = False
                st.rerun()

with aba2:
    if df_usuario.empty:
        st.info("Você ainda não possui lançamentos.")
    else:
        # Exibe apenas os dados filtrados pelo CPF do motorista logado
        df_view = df_usuario.sort_values('Data', ascending=False)
        st.markdown(f"**Total de registros:** {len(df_view)}")
        st.dataframe(df_view[['Data', 'Urbano', 'Boraali', 'KM_Final']], use_container_width=True, hide_index=True)
