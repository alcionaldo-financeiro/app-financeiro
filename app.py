import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime
import time
import pytz
import plotly.express as px

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="BYD Pro", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

# CSS customizado para botões e métricas
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

# --- 2. FUNÇÕES DE SUPORTE ---
FUSO_BR = pytz.timezone('America/Sao_Paulo')
COLUNAS_OFICIAIS = ['ID_Unico', 'Status', 'Usuario', 'CPF', 'Data', 'Urbano', 'Boraali', 'app163', 'Outros_Receita', 'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos', 'KM_Inicial', 'KM_Final', 'Detalhes']

def format_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

def limpar_cpf(t):
    if pd.isna(t) or t == "" or t is None: return ""
    s = str(t).split('.')[0]
    s = re.sub(r'\D', '', s)
    return s.zfill(11)

@st.cache_data(ttl=2)
def carregar_dados():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet=0, ttl=0)
        if df is None or df.empty: return pd.DataFrame(columns=COLUNAS_OFICIAIS)
        df['CPF'] = df['CPF'].apply(limpar_cpf)
        cols_num = ['Urbano', 'Boraali', 'app163', 'Outros_Receita', 'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos', 'KM_Inicial', 'KM_Final']
        for c in cols_num: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        return df
    except:
        return pd.DataFrame(columns=COLUNAS_OFICIAIS)

# --- 3. LOGIN E PERSISTÊNCIA ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

params = st.query_params
user_url = params.get("user", "")
cpf_url = limpar_cpf(params.get("cpf", ""))

# Auto-login se houver dados na URL
if not st.session_state.autenticado and user_url and len(cpf_url) == 11:
    st.session_state.usuario = user_url
    st.session_state.cpf_usuario = cpf_url
    st.session_state.autenticado = True

if not st.session_state.autenticado:
    st.title("💎 BYD Pro")
    n_in = st.text_input("Nome:", value=user_url)
    c_in = st.text_input("CPF (11 dígitos):", value=cpf_url, max_chars=11)
    
    if st.button("ENTRAR ✅", type="primary"):
        c_l = limpar_cpf(c_in)
        if n_in and len(c_l) == 11:
            st.session_state.usuario = n_in
            st.session_state.cpf_usuario = c_l
            st.session_state.autenticado = True
            st.query_params.update({"user": n_in, "cpf": c_l})
            st.rerun()
        else:
            st.error("⚠️ Preencha os dados corretamente.")
    st.stop()

# --- 4. APP PRINCIPAL ---
df_total = carregar_dados()
df_user = df_total[(df_total['CPF'] == st.session_state.cpf_usuario) & (df_total['Status'] != 'Lixeira')].copy()

# Tabs com chave única para evitar pulos indesejados
tab1, tab2 = st.tabs(["📝 LANÇAR", "📊 DASHBOARD"])

with tab1:
    st.markdown(f"### Olá, {st.session_state.usuario}")
    st.markdown("---")
    
    st.subheader("💰 Receitas")
    v1 = st.number_input("99 / Uber", min_value=0.0, step=10.0)
    v2 = st.number_input("BoraAli", min_value=0.0, step=10.0)
    v3 = st.number_input("App 163", min_value=0.0, step=10.0)
    v4 = st.number_input("Particular / Outros", min_value=0.0, step=10.0)
    
    st.subheader("🚗 Quilometragem")
    u_km = int(df_user['KM_Final'].max()) if not df_user.empty else 0
    k_ini = st.number_input("KM Inicial", value=u_km)
    k_fim = st.number_input("KM Final Atual", min_value=0)

    if st.button("SALVAR AGORA ✅", type="primary"):
        nova = {col: 0 for col in COLUNAS_OFICIAIS}
        nova.update({
            'ID_Unico': str(int(time.time())),
            'Status': 'Ativo',
            'Usuario': st.session_state.usuario,
            'CPF': st.session_state.cpf_usuario,
            'Data': datetime.now(FUSO_BR).strftime("%Y-%m-%d"),
            'Urbano': v1, 'Boraali': v2, 'app163': v3, 'Outros_Receita': v4,
            'KM_Inicial': k_ini, 'KM_Final': k_fim if k_fim > 0 else k_ini
        })
        conn = st.connection("gsheets", type=GSheetsConnection)
        conn.update(worksheet=0, data=pd.concat([carregar_dados(), pd.DataFrame([nova])], ignore_index=True))
        st.cache_data.clear()
        st.success("Salvo com sucesso!")
        time.sleep(1)
        st.rerun()

with tab2:
    if df_user.empty:
        st.info("Nenhum dado para exibir. Faça seu primeiro lançamento!")
    else:
        # Preparação dos dados
        df_bi = df_user.copy()
        df_bi['Rec'] = df_bi[['Urbano','Boraali','app163','Outros_Receita']].sum(axis=1)
        df_bi['Cus'] = df_bi[['Energia','Manuten','Seguro','Aplicativo','Alimentacao','Outros_Custos']].sum(axis=1)
        df_bi['Lucro'] = df_bi['Rec'] - df_bi['Cus']
        df_bi['KMR'] = (df_bi['KM_Final'] - df_bi['KM_Inicial']).clip(lower=0)

        st.markdown("### 🔍 Filtros")
        
        # Correção 1: Formato da data para Português/Brasil
        f_dia = st.date_input("Filtrar Dia Específico", value=None, format="DD/MM/YYYY")
        
        c_f1, c_f2 = st.columns(2)
        anos = ["Todos"] + sorted(df_bi['Data'].dt.year.dropna().unique().astype(int).astype(str).tolist(), reverse=True)
        sel_ano = c_f1.selectbox("Ano", anos)
        
        meses_pt = ["Todos","Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
        sel_mes = c_f2.selectbox("Mês", meses_pt)
        
        # Aplicação dos Filtros
        df_f = df_bi.copy()
        if f_dia:
            df_f = df_f[df_f['Data'].dt.date == f_dia]
        if sel_ano != "Todos":
            df_f = df_f[df_f['Data'].dt.year == int(sel_ano)]
        if sel_mes != "Todos":
            df_f = df_f[df_f['Data'].dt.month == meses_pt.index(sel_mes)]

        # --- RESTAURAÇÃO DOS 6 INDICADORES ---
        tr, tc, tl, tk = df_f['Rec'].sum(), df_f['Cus'].sum(), df_f['Lucro'].sum(), df_f['KMR'].sum()
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Faturamento Total", format_br(tr))
        col_m2.metric("Lucro Líquido", format_br(tl))
        col_m3.metric("Custos Totais", format_br(tc))
        
        col_m4, col_m5, col_m6 = st.columns(3)
        col_m4.metric("KM Rodado", f"{tk:,.0f} km".replace(",", "."))
        col_m5.metric("Faturamento / KM", format_br(tr/tk if tk > 0 else 0))
        col_m6.metric("Lucro / KM", format_br(tl/tk if tk > 0 else 0))

        # --- RESTAURAÇÃO DOS GRÁFICOS ---
        if not df_f.empty:
            st.markdown("### 📊 Desempenho Diário")
            df_g = df_f.sort_values('Data')
            df_g['Dia'] = df_g['Data'].dt.strftime('%d/%m')
            
            # Gráfico 1: Receita vs Lucro
            fig1 = px.bar(df_g, x='Dia', y=['Rec', 'Lucro'], 
                          barmode='group', 
                          color_discrete_map={'Rec':'#28a745','Lucro':'#007bff'},
                          labels={'value': 'Valor (R$)', 'variable': 'Tipo'})
            st.plotly_chart(fig1, use_container_width=True)
            
            # Gráfico 2: Distribuição de Custos
            st.markdown("### 💸 Composição de Custos")
            labels_custos = ['Energia','Manuten','Seguro','Apps','Alimentos','Outros']
            valores_custos = [df_f['Energia'].sum(), df_f['Manuten'].sum(), df_f['Seguro'].sum(), 
                              df_f['Aplicativo'].sum(), df_f['Alimentacao'].sum(), df_f['Outros_Custos'].sum()]
            
            if sum(valores_custos) > 0:
                fig2 = px.pie(names=labels_custos, values=valores_custos, hole=0.4,
                              color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Sem custos registrados no período para gerar o gráfico.")

st.divider()
if st.button("Sair / Trocar de Usuário"): 
    st.session_state.autenticado = False
    st.query_params.clear()
    st.rerun()
