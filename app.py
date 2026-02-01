import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime
import time
import pytz

# --- 1. CONFIGURAÇÃO E CSS PARA SUMIR ÍCONES ---
st.set_page_config(page_title="BYD Pro", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        #MainMenu, header, footer, .stDeployButton {display: none !important; visibility: hidden !important;}
        [data-testid="stToolbar"], [data-testid="stStatusWidget"], [data-testid="stDecoration"] {display: none !important;}
        button[title="Manage app"] {display: none !important;}
        .block-container {padding-top: 1rem !important;}
        
        /* Estilo dos Botões */
        div.stButton > button[kind="primary"] {
            background-color: #28a745 !important;
            color: white !important;
            border-radius: 12px; height: 3.5em; font-weight: bold; width: 100%;
        }
    </style>
    <meta name="google" content="notranslate">
    """, unsafe_allow_html=True)

# --- 2. CONFIGURAÇÕES DE DADOS ---
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
        # Converter colunas numéricas
        cols_num = ['Urbano', 'Boraali', 'app163', 'Outros_Receita', 'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos', 'KM_Inicial', 'KM_Final']
        for c in cols_num: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        return df
    except: return pd.DataFrame(columns=COLUNAS_OFICIAIS)

# --- 3. LOGIN COM MEMÓRIA ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False

params = st.query_params
q_nome, q_cpf = params.get("n", ""), params.get("c", "")

if not st.session_state['autenticado']:
    st.title("💎 BYD Pro")
    st.markdown("### Identificação do Motorista")
    n_in = st.text_input("Nome Completo:", value=q_nome)
    c_in = st.text_input("CPF (Apenas números):", value=q_cpf, max_chars=11)

    if st.button("ACESSAR SISTEMA 🚀", type="primary"):
        c_limpo = limpar_texto(c_in)
        if len(c_limpo) == 11 and n_in:
            st.query_params["n"], st.query_params["c"] = n_in, c_limpo
            st.session_state.update({'usuario': n_in.lower(), 'cpf_usuario': c_limpo, 'autenticado': True})
            st.rerun()
        else: st.error("⚠️ Verifique os dados.")
    st.stop()

# --- 4. SISTEMA LOGADO ---
CPF = st.session_state['cpf_usuario']
df_total = carregar_dados_seguros()
df_user = df_total[(df_total['CPF'] == CPF) & (df_total['Status'] != 'Lixeira')].copy()

st.markdown(f"#### Olá, {st.session_state['usuario'].title()} 👤")

aba1, aba2 = st.tabs(["📝 LANÇAR", "📊 DASHBOARD & RELATÓRIOS"])

with aba1:
    if 'conf' not in st.session_state: st.session_state['conf'] = False
    
    if not st.session_state['conf']:
        with st.expander("💰 FATURAMENTO (RECEITAS)", expanded=True):
            c1, c2 = st.columns(2)
            v_urb = c1.number_input("Urbano / 99", min_value=0.0, step=10.0, value=None)
            v_bora = c2.number_input("BoraAli", min_value=0.0, step=10.0, value=None)
            v_163 = c1.number_input("App 163", min_value=0.0, step=10.0, value=None)
            v_out_r = c2.number_input("Particular / Outros", min_value=0.0, step=10.0, value=None)
        
        with st.expander("💸 GASTOS (CUSTOS)", expanded=False):
            c3, c4 = st.columns(2)
            v_ene = c3.number_input("Energia / Combustível", min_value=0.0, step=5.0, value=None)
            v_ali = c4.number_input("Alimentação", min_value=0.0, step=5.0, value=None)
            v_man = c3.number_input("Manutenção / Lavagem", min_value=0.0, step=5.0, value=None)
            v_seg = c4.number_input("Seguro", min_value=0.0, step=5.0, value=None)
            v_int = c3.number_input("Internet / Apps", min_value=0.0, step=5.0, value=None)
            v_out_c = c4.number_input("Outros Custos", min_value=0.0, step=5.0, value=None)

        st.markdown("---")
        u_km = int(df_user['KM_Final'].max()) if not df_user.empty else 0
        k1 = st.number_input("KM Inicial", value=u_km)
        k2 = st.number_input("KM Final", value=None, placeholder="Digite o KM atual")
        obs = st.text_input("Observação:")

        if st.button("CONFERIR LANÇAMENTO ➡️", type="primary"):
            st.session_state['tmp'] = {
                'Urbano':v_urb,'Boraali':v_bora,'app163':v_163,'Outros_Receita':v_out_r,
                'Energia':v_ene,'Alimentacao':v_ali,'Manuten':v_man,'Seguro':v_seg,
                'Aplicativo':v_int,'Outros_Custos':v_out_c,'KM_Inicial':k1,'KM_Final':k2 if k2 else k1, 'Detalhes':obs
            }
            st.session_state['conf'] = True
            st.rerun()
    else:
        # TELA DE CONFERÊNCIA
        d = st.session_state['tmp']
        receita = sum([d['Urbano'] or 0, d['Boraali'] or 0, d['app163'] or 0, d['Outros_Receita'] or 0])
        custo = sum([d['Energia'] or 0, d['Alimentacao'] or 0, d['Manuten'] or 0, d['Seguro'] or 0, d['Aplicativo'] or 0, d['Outros_Custos'] or 0])
        
        st.subheader("📝 Tudo certo?")
        st.write(f"**Ganhos:** R$ {receita:.2f} | **Custos:** R$ {custo:.2f} | **KM:** {d['KM_Final'] - d['KM_Inicial']}")
        
        c_v, c_s = st.columns(2)
        if c_v.button("⬅️ Editar"): st.session_state['conf'] = False; st.rerun()
        if c_s.button("✅ SALVAR AGORA", type="primary"):
            with st.spinner("Gravando..."):
                nova = {col: 0 for col in COLUNAS_OFICIAIS}
                nova.update(d)
                nova.update({'ID_Unico': str(int(time.time())), 'Status': 'Ativo', 'Usuario': st.session_state['usuario'], 'CPF': CPF, 'Data': datetime.now(FUSO_BR).strftime("%Y-%m-%d")})
                df_db = conn.read(worksheet=0, ttl=0)
                conn.update(worksheet=0, data=pd.concat([df_db, pd.DataFrame([nova])], ignore_index=True))
                st.success("Salvo!"); time.sleep(1); st.session_state['conf'] = False; st.rerun()

with aba2:
    if df_user.empty: st.info("Sem dados.")
    else:
        # --- CÁLCULOS DE BUSINESS INTELLIGENCE (BI) ---
        df_res = df_user.copy()
        df_res['Receita_T'] = df_res[['Urbano','Boraali','app163','Outros_Receita']].sum(axis=1)
        df_res['Custo_T'] = df_res[['Energia','Manuten','Seguro','Aplicativo','Alimentacao','Outros_Custos']].sum(axis=1)
        df_res['Lucro'] = df_res['Receita_T'] - df_res['Custo_T']
        df_res['KM_R'] = (df_res['KM_Final'] - df_res['KM_Inicial']).clip(lower=0)
        
        # Métricas de Cabeçalho
        m1, m2, m3, m4 = st.columns(4)
        total_km = df_res['KM_R'].sum()
        total_lucro = df_res['Lucro'].sum()
        m1.metric("Lucro Total", f"R$ {total_lucro:,.2f}")
        m2.metric("KM Rodado", f"{total_km:,.0f} km")
        m3.metric("R$ / KM", f"R$ {total_lucro/total_km:.2f}" if total_km > 0 else "R$ 0,00")
        m4.metric("Custo / KM", f"R$ {df_res['Custo_T'].sum()/total_km:.2f}" if total_km > 0 else "R$ 0,00")

        # --- GRÁFICOS ESTRATÉGICOS ---
        st.markdown("### 📈 Visão de Performance")
        
        # 1. Gráfico de Evolução de Lucro
        st.area_chart(df_res.set_index('Data')[['Receita_T', 'Lucro']])
        
        c_gr1, c_gr2 = st.columns(2)
        with c_gr1:
            st.markdown("**💰 Faturamento por App**")
            apps = df_res[['Urbano','Boraali','app163','Outros_Receita']].sum()
            st.bar_chart(apps)
        
        with c_gr2:
            st.markdown("**💸 Onde está o Custo?**")
            gastos = df_res[['Energia','Manuten','Seguro','Aplicativo','Alimentacao','Outros_Custos']].sum()
            st.bar_chart(gastos)

        # Tabela Detalhada
        st.markdown("### 📋 Histórico Detalhado")
        st.dataframe(df_res[['Data', 'Receita_T', 'Custo_T', 'Lucro', 'KM_R']].sort_values('Data', ascending=False), use_container_width=True, hide_index=True)

if st.button("Sair / Trocar Conta"):
    st.session_state['autenticado'] = False
    st.rerun()
