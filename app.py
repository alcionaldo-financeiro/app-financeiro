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
            padding: 10px !important;
            border-radius: 10px !important;
        }
        [data-testid="stMetricLabel"] { color: #333333 !important; font-weight: bold !important; font-size: 0.9rem !important; }
        [data-testid="stMetricValue"] { color: #000000 !important; font-weight: 800 !important; font-size: 1.2rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNÇÕES ---
FUSO_BR = pytz.timezone('America/Sao_Paulo')
HOJE_BR = datetime.now(FUSO_BR).date()
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
    except: return pd.DataFrame(columns=COLUNAS_OFICIAIS)

def salvar_no_banco(df_novo):
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(worksheet=0, data=df_novo)
    st.cache_data.clear()

# --- 3. LOGIN COM PERSISTÊNCIA ---
params = st.query_params
u_url = params.get("user", "")
c_url = limpar_cpf(params.get("cpf", ""))

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("💎 BYD Pro Login")
    n_in = st.text_input("Nome:", value=u_url)
    c_in = st.text_input("CPF:", value=c_url, max_chars=11)
    
    if st.button("ENTRAR ✅", type="primary"):
        c_l = limpar_cpf(c_in)
        if n_in and len(c_l) == 11:
            st.session_state.update({'usuario': n_in, 'cpf_usuario': c_l, 'autenticado': True})
            st.query_params.update({"user": n_in, "cpf": c_l})
            st.rerun()
        else: st.error("⚠️ Verifique os dados.")
    st.stop()

# --- 4. APP ---
df_total = carregar_dados()
df_user = df_total[(df_total['CPF'] == st.session_state.cpf_usuario) & 
                   (df_total['Status'] != 'Lixeira') & 
                   (df_total['Data'].dt.date <= HOJE_BR)].copy()

tab1, tab2 = st.tabs(["📝 LANÇAR", "📊 DASHBOARD"])

with tab1:
    st.subheader(f"Olá, {st.session_state.usuario}")
    data_lanc = st.date_input("Data do Trabalho:", value=HOJE_BR, format="DD/MM/YYYY")
    col1, col2 = st.columns(2)
    v1 = col1.number_input("Urbano (99/Uber)", min_value=0.0)
    v2 = col2.number_input("BoraAli", min_value=0.0)
    v3 = col1.number_input("app163", min_value=0.0)
    v4 = col2.number_input("Outros (Receita)", min_value=0.0)
    st.divider()
    c1 = col1.number_input("Energia", min_value=0.0)
    c2 = col2.number_input("Manutenção", min_value=0.0)
    c3 = col1.number_input("Seguro", min_value=0.0)
    c4 = col2.number_input("Outros Custos (Documento)", min_value=0.0)
    c5 = col1.number_input("Aplicativo", min_value=0.0)
    c6 = col2.number_input("Alimentação", min_value=0.0)
    st.subheader("🚗 KM")
    u_km = int(df_user['KM_Final'].max()) if not df_user.empty else 0
    k_ini = st.number_input("KM Inicial", value=u_km)
    k_fim = st.number_input("KM Final", min_value=0)

    if st.button("SALVAR AGORA ✅", type="primary"):
        nova = {col: 0 for col in COLUNAS_OFICIAIS}
        nova.update({'ID_Unico': str(int(time.time())), 'Status': 'Ativo', 'Usuario': st.session_state.usuario, 'CPF': st.session_state.cpf_usuario, 'Data': data_lanc.strftime("%Y-%m-%d"), 'Urbano': v1, 'Boraali': v2, 'app163': v3, 'Outros_Receita': v4, 'Energia': c1, 'Manuten': c2, 'Seguro': c3, 'Outros_Custos': c4, 'Aplicativo': c5, 'Alimentacao': c6, 'KM_Inicial': k_ini, 'KM_Final': k_fim if k_fim > 0 else k_ini})
        salvar_no_banco(pd.concat([df_total, pd.DataFrame([nova])], ignore_index=True))
        st.success("Salvo!"); time.sleep(1); st.rerun()

with tab2:
    if df_user.empty: st.info("Sem dados.")
    else:
        df_bi = df_user.copy().sort_values('Data', ascending=False)
        
        # CÁLCULOS PARA A TABELA EXCEL
        df_bi['Receita'] = df_bi[['Urbano','Boraali','app163','Outros_Receita']].sum(axis=1)
        df_bi['Custos'] = df_bi[['Energia','Manuten','Seguro','Outros_Custos','Aplicativo','Alimentacao']].sum(axis=1)
        df_bi['Km rodados'] = (df_bi['KM_Final'] - df_bi['KM_Inicial']).clip(lower=0)
        df_bi['Lucro/prejuizo'] = df_bi['Receita'] - df_bi['Custos']
        
        # Cálculos de Eficiência (Prevenir divisão por zero)
        df_bi['Lucro/km'] = df_bi.apply(lambda r: r['Lucro/prejuizo']/r['Km rodados'] if r['Km rodados'] > 0 else 0, axis=1)
        df_bi['Receita/R$/KM'] = df_bi.apply(lambda r: r['Receita']/r['Km rodados'] if r['Km rodados'] > 0 else 0, axis=1)
        df_bi['R$/combust/km'] = df_bi.apply(lambda r: r['Energia']/r['Km rodados'] if r['Km rodados'] > 0 else 0, axis=1)
        df_bi['Qtd dias'] = 1

        # 1. INDICADORES (KPIs)
        tr, tc, tl, tk = df_bi['Receita'].sum(), df_bi['Custos'].sum(), df_bi['Lucro/prejuizo'].sum(), df_bi['Km rodados'].sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("Faturamento", format_br(tr))
        m2.metric("Lucro Líquido", format_br(tl))
        m3.metric("Custos", format_br(tc))
        m4, m5, m6 = st.columns(3)
        m4.metric("KM Rodado", f"{tk:,.0f} km")
        m5.metric("R$/KM", format_br(tr/tk if tk > 0 else 0))
        m6.metric("Lucro/KM", format_br(tl/tk if tk > 0 else 0))

        # 2. TABELA COMPLETA (CONFORME EXCEL)
        st.markdown("### 📋 Lançamentos até Hoje")
        df_exibir = df_bi.copy()
        df_exibir['Data'] = df_exibir['Data'].dt.strftime('%d/%m/%Y')
        
        # Ordem exata das colunas baseada na imagem enviada
        cols_final = [
            'Data', 'Usuario', 'Receita', 'Urbano', 'Boraali', 'app163', 
            'Outros_Receita', 'Custos', 'Energia', 'Manuten', 'Seguro', 
            'Outros_Custos', 'Aplicativo', 'Alimentacao', 'KM_Inicial', 
            'KM_Final', 'Km rodados', 'Lucro/prejuizo', 'Lucro/km', 
            'Receita/R$/KM', 'R$/combust/km', 'Qtd dias', 'ID_Unico'
        ]
        
        # Renomear para bater com o Excel
        df_exibir = df_exibir.rename(columns={
            'Outros_Receita': 'Outros (Rec)', 
            'Outros_Custos': 'Documento', 
            'Alimentacao': 'Alimentação',
            'KM_Inicial': 'KM Inicial',
            'KM_Final': 'KM final'
        })
        
        cols_renomeadas = [
            'Data', 'Usuario', 'Receita', 'Urbano', 'Boraali', 'app163', 
            'Outros (Rec)', 'Custos', 'Energia', 'Manuten', 'Seguro', 
            'Documento', 'Aplicativo', 'Alimentação', 'KM Inicial', 
            'KM final', 'Km rodados', 'Lucro/prejuizo', 'Lucro/km', 
            'Receita/R$/KM', 'R$/combust/km', 'Qtd dias', 'ID_Unico'
        ]
        
        st.dataframe(df_exibir[cols_renomeadas], use_container_width=True, height=350)

        # 3. EXCLUSÃO
        with st.expander("🗑️ Excluir lançamento"):
            item_ex = st.selectbox("ID", df_bi['ID_Unico'].tolist())
            if st.button("CONFIRMAR"):
                df_total.loc[df_total['ID_Unico'] == item_ex, 'Status'] = 'Lixeira'
                salvar_no_banco(df_total)
                st.rerun()

        # 4. GRÁFICOS
        st.markdown("### 📊 Gráficos")
        df_g = df_bi.sort_values('Data')
        df_g['Dia'] = df_g['Data'].dt.strftime('%d/%m')
        fig1 = px.bar(df_g, x='Dia', y=['Receita', 'Lucro/prejuizo'], barmode='group', color_discrete_map={'Receita':'#28a745','Lucro/prejuizo':'#007bff'})
        st.plotly_chart(fig1, use_container_width=True)
        
        custos_p = {'Energia': df_bi['Energia'].sum(), 'Manutenção': df_bi['Manuten'].sum(), 'Seguro': df_bi['Seguro'].sum(), 'Alimentação': df_bi['Alimentacao'].sum(), 'Outros': df_bi['Outros_Custos'].sum()}
        fig2 = px.pie(names=list(custos_p.keys()), values=list(custos_p.values()), hole=0.4)
        st.plotly_chart(fig2, use_container_width=True)

st.divider()
if st.button("Sair"): 
    st.session_state.autenticado = False
    st.query_params.clear(); st.rerun()
