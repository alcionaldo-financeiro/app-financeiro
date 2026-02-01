import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime
import time
import pytz
import plotly.express as px

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="BYD Pro", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

# CSS para VISIBILIDADE e Estilo
st.markdown("""
    <style>
        #MainMenu, header, footer, .stDeployButton {display: none !important;}
        [data-testid="stToolbar"], [data-testid="stDecoration"] {display: none !important;}
        .block-container {padding-top: 1rem !important; padding-bottom: 5rem !important;}
        
        div.stButton > button[kind="primary"] {
            background-color: #28a745 !important;
            color: white !important;
            border-radius: 12px !important;
            height: 3.5rem !important;
            font-weight: bold !important;
            width: 100% !important;
        }
        
        [data-testid="stMetric"] {
            background-color: #ffffff !important;
            border: 1px solid #cccccc !important;
            padding: 15px !important;
            border-radius: 10px !important;
        }
        [data-testid="stMetricLabel"] { color: #333333 !important; font-weight: bold !important; font-size: 1rem !important; }
        [data-testid="stMetricValue"] { color: #000000 !important; font-weight: 800 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNÇÕES AUXILIARES ---
FUSO_BR = pytz.timezone('America/Sao_Paulo')
COLUNAS_OFICIAIS = ['ID_Unico', 'Status', 'Usuario', 'CPF', 'Data', 'Urbano', 'Boraali', 'app163', 'Outros_Receita', 'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos', 'KM_Inicial', 'KM_Final', 'Detalhes']

def format_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

def limpar_cpf(t):
    if pd.isna(t) or t == "": return ""
    return re.sub(r'\D', '', str(t)).zfill(11)

@st.cache_data(ttl=2)
def carregar_dados():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet=0, ttl=0)
        if df is None or df.empty: return pd.DataFrame(columns=COLUNAS_OFICIAIS)
        df['CPF'] = df['CPF'].apply(limpar_cpf)
        # Converter colunas numéricas
        cols_num = ['Urbano', 'Boraali', 'app163', 'Outros_Receita', 'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos', 'KM_Inicial', 'KM_Final']
        for c in cols_num: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
        # IMPORTANTE: Converter Data corretamente
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        return df
    except: return pd.DataFrame(columns=COLUNAS_OFICIAIS)

# --- 3. LOGIN COM PERSISTÊNCIA ---
# Recupera dados da URL se existirem
params = st.query_params
user_url = params.get("user", "")
cpf_url = params.get("cpf", "")

if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.title("💎 BYD Pro")
    # Os campos são preenchidos com o que está na URL, mas permanecem editáveis
    n_in = st.text_input("Nome:", value=user_url)
    c_in = st.text_input("CPF (Apenas números):", value=cpf_url, max_chars=11)
    
    if st.button("ENTRAR ✅", type="primary"):
        c_l = limpar_cpf(c_in)
        if n_in and len(c_l) == 11:
            st.session_state.update({'usuario': n_in, 'cpf_usuario': c_l, 'autenticado': True})
            # Salva na URL para a próxima vez
            st.query_params.update({"user": n_in, "cpf": c_l})
            st.rerun()
        else:
            st.error("⚠️ Verifique os dados.")
    st.stop()

# --- 4. APLICATIVO ---
df_total = carregar_dados()
df_user = df_total[(df_total['CPF'] == st.session_state['cpf_usuario']) & (df_total['Status'] != 'Lixeira')].copy()

# Uso de "key" no tabs para manter a aba selecionada ao filtrar
tab1, tab2 = st.tabs(["📝 LANÇAR", "📊 DASHBOARD"])

with tab1:
    st.markdown(f"### Bem-vindo, {st.session_state['usuario']}!")
    # ... (Seu código de inputs de Receitas, Custos e KM aqui continua igual)
    st.markdown("### 💰 Receitas")
    v1 = st.number_input("99 / Uber", min_value=0.0, key="v1")
    v2 = st.number_input("BoraAli", min_value=0.0, key="v2")
    v3 = st.number_input("App 163", min_value=0.0, key="v3")
    v4 = st.number_input("Particular / Outros", min_value=0.0, key="v4")
    
    st.markdown("### 🚗 KM")
    u_km = int(df_user['KM_Final'].max()) if not df_user.empty else 0
    k_ini = st.number_input("KM Inicial", value=u_km)
    k_fim = st.number_input("KM Final Atual", min_value=0)

    if st.button("SALVAR AGORA ✅", type="primary"):
        nova = {col: 0 for col in COLUNAS_OFICIAIS}
        nova.update({
            'ID_Unico': str(int(time.time())),
            'Status': 'Ativo',
            'Usuario': st.session_state['usuario'],
            'CPF': st.session_state['cpf_usuario'],
            'Data': datetime.now(FUSO_BR).strftime("%Y-%m-%d"),
            'Urbano': v1, 'Boraali': v2, 'app163': v3, 'Outros_Receita': v4,
            'KM_Inicial': k_ini, 'KM_Final': k_fim if k_fim > 0 else k_ini
        })
        conn = st.connection("gsheets", type=GSheetsConnection)
        conn.update(worksheet=0, data=pd.concat([carregar_dados(), pd.DataFrame([nova])], ignore_index=True))
        st.cache_data.clear()
        st.success("Salvo!")
        time.sleep(1)
        st.rerun()

with tab2:
    if df_user.empty:
        st.info("Sem dados para exibir no momento.")
    else:
        # Preparação dos dados para filtros
        df_bi = df_user.copy()
        df_bi['Rec'] = df_bi[['Urbano','Boraali','app163','Outros_Receita']].sum(axis=1)
        df_bi['Cus'] = df_bi[['Energia','Manuten','Seguro','Aplicativo','Alimentacao','Outros_Custos']].sum(axis=1)
        df_bi['Lucro'] = df_bi['Rec'] - df_bi['Cus']
        df_bi['KMR'] = (df_bi['KM_Final'] - df_bi['KM_Inicial']).clip(lower=0)

        st.markdown("### 🔍 Filtros")
        # Correção do Filtro de Dia
        f_dia = st.date_input("Filtrar Dia Específico", value=None)
        
        col_f1, col_f2 = st.columns(2)
        anos = ["Todos"] + sorted(df_bi['Data'].dt.year.unique().astype(str).tolist(), reverse=True)
        sel_ano = col_f1.selectbox("Ano", anos)
        meses_pt = ["Todos","Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
        sel_mes = col_f2.selectbox("Mês", meses_pt)
        
        # Lógica de Filtragem Aplicada
        df_f = df_bi.copy()
        
        if f_dia:
            # Garante que a comparação seja entre Date e Date (ignorando horas)
            df_f = df_f[df_f['Data'].dt.date == f_dia]
        
        if sel_ano != "Todos":
            df_f = df_f[df_f['Data'].dt.year == int(sel_ano)]
            
        if sel_mes != "Todos":
            df_f = df_f[df_f['Data'].dt.month == meses_pt.index(sel_mes)]

        # KPIs
        tr, tc, tl, tk = df_f['Rec'].sum(), df_f['Cus'].sum(), df_f['Lucro'].sum(), df_f['KMR'].sum()
        
        st.metric("Faturamento Total", format_br(tr))
        st.metric("Lucro Líquido", format_br(tl))
        st.metric("Custos Totais", format_br(tc))
        st.metric("KM Rodado", f"{tk:,.0f} km".replace(",", "."))

        if not df_f.empty:
            st.markdown("### 📊 Gráfico do Período")
            df_f = df_f.sort_values('Data')
            df_f['Dia_Formatado'] = df_f['Data'].dt.strftime('%d/%m')
            fig = px.bar(df_f, x='Dia_Formatado', y=['Rec', 'Cus'], 
                         barmode='group', 
                         color_discrete_map={'Rec':'#28a745','Cus':'#dc3545'},
                         labels={'value': 'Valor', 'Dia_Formatado': 'Dia'})
            st.plotly_chart(fig, use_container_width=True)

if st.button("Sair"): 
    st.session_state['autenticado'] = False
    st.query_params.clear() # Limpa a URL ao sair se desejar
    st.rerun()
