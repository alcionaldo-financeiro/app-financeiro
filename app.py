import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime
import time
import pytz
import plotly.express as px

# --- 1. CONFIGURAÇÃO MOBILE-FIRST ---
st.set_page_config(page_title="BYD Pro", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

# CSS para VISIBILIDADE TOTAL e Botões Verdes
st.markdown("""
    <style>
        #MainMenu, header, footer, .stDeployButton {display: none !important;}
        [data-testid="stToolbar"], [data-testid="stDecoration"] {display: none !important;}
        .block-container {padding-top: 1rem !important; padding-bottom: 5rem !important;}
        
        /* Botão Salvar Verde */
        div.stButton > button[kind="primary"] {
            background-color: #28a745 !important;
            color: white !important;
            border-radius: 12px !important;
            height: 3.5rem !important;
            font-weight: bold !important;
            width: 100% !important;
        }
        
        /* CORREÇÃO DE VISIBILIDADE DOS CARDS */
        [data-testid="stMetric"] {
            background-color: #ffffff !important;
            border: 1px solid #cccccc !important;
            padding: 15px !important;
            border-radius: 10px !important;
        }
        [data-testid="stMetricLabel"] {
            color: #333333 !important; /* Cinza Escuro quase preto */
            font-weight: bold !important;
            font-size: 1rem !important;
        }
        [data-testid="stMetricValue"] {
            color: #000000 !important; /* Preto Puro */
            font-weight: 800 !important;
        }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNÇÕES ---
FUSO_BR = pytz.timezone('America/Sao_Paulo')
COLUNAS_OFICIAIS = ['ID_Unico', 'Status', 'Usuario', 'CPF', 'Data', 'Urbano', 'Boraali', 'app163', 'Outros_Receita', 'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos', 'KM_Inicial', 'KM_Final', 'Detalhes']

def format_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

def limpar_cpf(t):
    if pd.isna(t) or t == "": return ""
    return re.sub(r'\D', '', str(t).replace('.0', '')).zfill(11)

def limpar_valor(v):
    if pd.isna(v) or v == "" or v == "-": return 0.0
    if isinstance(v, str): v = v.replace('R$', '').replace('.', '').replace(',', '.').strip()
    try: return float(v)
    except: return 0.0

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
    except: return pd.DataFrame(columns=COLUNAS_OFICIAIS)

# --- 3. LOGIN COM MEMÓRIA ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
if 'usuario' not in st.session_state: st.session_state['usuario'] = ""
if 'cpf_usuario' not in st.session_state: st.session_state['cpf_usuario'] = ""

params = st.query_params
q_n = params.get("n", st.session_state['usuario'])
q_c = limpar_cpf(params.get("c", st.session_state['cpf_usuario']))

if not st.session_state['autenticado']:
    if q_n and len(q_c) == 11:
        st.session_state.update({'usuario': q_n, 'cpf_usuario': q_c, 'autenticado': True})
        st.rerun()
    
    st.title("💎 BYD Pro")
    n_in = st.text_input("Nome:", value=st.session_state['usuario'])
    c_in = st.text_input("CPF (Apenas números):", value=st.session_state['cpf_usuario'], max_chars=11)
    
    if st.button("ENTRAR ✅", type="primary"):
        c_l = limpar_cpf(c_in)
        if n_in and len(c_l) == 11:
            st.session_state.update({'usuario': n_in, 'cpf_usuario': c_l, 'autenticado': True})
            st.rerun()
        else: st.error("⚠️ Verifique os dados.")
    st.stop()

# --- 4. APP ---
df_user = carregar_dados()
df_user = df_user[(df_user['CPF'] == st.session_state['cpf_usuario']) & (df_user['Status'] != 'Lixeira')].copy()

tab1, tab2 = st.tabs(["📝 LANÇAR", "📊 DASHBOARD"])

with tab1:
    with st.expander("⚙️ Importar Excel"):
        arq = st.file_uploader("Arquivo .xlsx", type=["xlsx"])
        if arq and st.button("Processar"):
            df_ex = pd.read_excel(arq)
            mapping = {'Data':'Data','Urbano':'Urbano','Boraali':'Boraali','app163':'app163','Outros':'Outros_Receita','Energia':'Energia','Manuten':'Manuten','Seguro':'Seguro','Documento':'Outros_Custos','Aplicativo':'Aplicativo','KM Inicial':'KM_Inicial','KM final':'KM_Final'}
            novas = []
            for i, row in df_ex.iterrows():
                n = {col: 0 for col in COLUNAS_OFICIAIS}
                for ex, ap in mapping.items():
                    if ex in row:
                        if 'Data' in ex: n[ap] = pd.to_datetime(row[ex]).strftime("%Y-%m-%d")
                        elif 'KM' in ex: n[ap] = float(row[ex])
                        else: n[ap] = limpar_valor(row[ex])
                n.update({'ID_Unico': str(int(time.time())+i), 'Status': 'Ativo', 'Usuario': st.session_state['usuario'], 'CPF': st.session_state['cpf_usuario']})
                novas.append(n)
            conn = st.connection("gsheets", type=GSheetsConnection)
            conn.update(worksheet=0, data=pd.concat([carregar_dados(), pd.DataFrame(novas)], ignore_index=True))
            st.cache_data.clear(); st.success("Importado!"); time.sleep(1); st.rerun()

    st.markdown("### 💰 Receitas")
    v1 = st.number_input("99 / Uber", min_value=0.0)
    v2 = st.number_input("BoraAli", min_value=0.0)
    v3 = st.number_input("App 163", min_value=0.0)
    v4 = st.number_input("Particular / Outros", min_value=0.0)
    st.markdown("### 💸 Custos")
    col_c1, col_c2 = st.columns(2)
    c1 = col_c1.number_input("Energia", min_value=0.0)
    c2 = col_c2.number_input("Manutenção", min_value=0.0)
    c3 = col_c1.number_input("Seguro", min_value=0.0)
    c4 = col_c2.number_input("Alimentação", min_value=0.0)
    c5 = col_c1.number_input("Apps/Internet", min_value=0.0)
    c6 = col_c2.number_input("Outros", min_value=0.0)
    st.markdown("### 🚗 KM")
    u_km = int(df_user['KM_Final'].max()) if not df_user.empty else 0
    k_ini = st.number_input("KM Inicial (Editável)", value=u_km)
    k_fim = st.number_input("KM Final Atual", min_value=0)
    if st.button("SALVAR AGORA ✅", type="primary"):
        nova = {col: 0 for col in COLUNAS_OFICIAIS}
        nova.update({'Urbano':v1,'Boraali':v2,'app163':v3,'Outros_Receita':v4,'Energia':c1,'Manuten':c2,'Seguro':c3,'Alimentacao':c4,'Aplicativo':c5,'Outros_Custos':c6,'KM_Inicial':k_ini,'KM_Final':k_fim if k_fim > 0 else k_ini,'ID_Unico':str(int(time.time())),'Status':'Ativo','Usuario':st.session_state['usuario'],'CPF':st.session_state['cpf_usuario'],'Data':datetime.now(FUSO_BR).strftime("%Y-%m-%d")})
        conn = st.connection("gsheets", type=GSheetsConnection)
        conn.update(worksheet=0, data=pd.concat([carregar_dados(), pd.DataFrame([nova])], ignore_index=True))
        st.cache_data.clear(); st.success("Salvo!"); time.sleep(1); st.rerun()

with tab2:
    if df_user.empty: st.info("Sem dados.")
    else:
        df_bi = df_user.copy().sort_values('Data', ascending=False)
        df_bi['Rec'] = df_bi[['Urbano','Boraali','app163','Outros_Receita']].sum(axis=1)
        df_bi['Cus'] = df_bi[['Energia','Manuten','Seguro','Aplicativo','Alimentacao','Outros_Custos']].sum(axis=1)
        df_bi['Lucro'] = df_bi['Rec'] - df_bi['Cus']
        df_bi['KMR'] = (df_bi['KM_Final'] - df_bi['KM_Inicial']).clip(lower=0)
        
        st.markdown("### 🔍 Filtros")
        f_dia = st.date_input("Filtrar Dia Específico", value=None)
        col_f1, col_f2 = st.columns(2)
        anos = ["Todos"] + sorted([str(int(y)) for y in df_bi['Data'].dt.year.dropna().unique()], reverse=True)
        sel_ano = col_f1.selectbox("Ano", anos)
        meses_pt = ["Todos","Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
        sel_mes = col_f2.selectbox("Mês", meses_pt)
        
        df_f = df_bi.copy()
        if f_dia: df_f = df_f[df_f['Data'].dt.date == f_dia]
        if sel_ano != "Todos": df_f = df_f[df_f['Data'].dt.year == int(sel_ano)]
        if sel_mes != "Todos": df_f = df_f[df_f['Data'].dt.month == meses_pt.index(sel_mes)]

        tr, tc, tl, tk = df_f['Rec'].sum(), df_f['Cus'].sum(), df_f['Lucro'].sum(), df_f['KMR'].sum()
        
        # INDICADORES (KPIs)
        st.metric("Faturamento Total", format_br(tr))
        st.metric("Lucro Líquido", format_br(tl))
        st.metric("Custos Totais", format_br(tc))
        st.metric("KM Rodado", f"{tk:,.0f} km".replace(",", "."))
        st.metric("Faturamento / KM", format_br(tr/tk if tk > 0 else 0))
        st.metric("Lucro / KM", format_br(tl/tk if tk > 0 else 0))

        st.markdown("### 📊 Gráficos")
        df_f['Dia'] = df_f['Data'].dt.strftime('%d/%m')
        df_g = df_f.groupby('Dia').agg({'Rec':'sum','Cus':'sum','KMR':'sum'}).reset_index().sort_values('Dia')
        
        fig1 = px.bar(df_g, x='Dia', y=['Rec', 'Cus'], barmode='group', color_discrete_map={'Rec':'#28a745','Cus':'#dc3545'}, text_auto='.2s')
        st.plotly_chart(fig1, use_container_width=True)
        
        fig2 = px.pie(names=['Energia','Manuten','Seguro','Apps','Alimentos','Outros'], values=[df_f['Energia'].sum(), df_f['Manuten'].sum(), df_f['Seguro'].sum(), df_f['Aplicativo'].sum(), df_f['Alimentacao'].sum(), df_f['Outros_Custos'].sum()], hole=0.4)
        st.plotly_chart(fig2, use_container_width=True)

if st.button("Sair"): 
    st.session_state['autenticado'] = False
    st.rerun()
