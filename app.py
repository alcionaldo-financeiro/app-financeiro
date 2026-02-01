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

# --- 3. LOGIN E PERSISTÊNCIA ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

params = st.query_params
u_url = params.get("user", "")
c_url = limpar_cpf(params.get("cpf", ""))

if not st.session_state.autenticado:
    if u_url and len(c_url) == 11:
        st.session_state.usuario, st.session_state.cpf_usuario, st.session_state.autenticado = u_url, c_url, True
    else:
        st.title("💎 BYD Pro")
        n_in = st.text_input("Nome:", value=u_url)
        c_in = st.text_input("CPF:", value=c_url, max_chars=11)
        if st.button("ENTRAR ✅", type="primary"):
            c_l = limpar_cpf(c_in)
            if n_in and len(c_l) == 11:
                st.session_state.update({'usuario': n_in, 'cpf_usuario': c_l, 'autenticado': True})
                st.query_params.update({"user": n_in, "cpf": c_l})
                st.rerun()
            else: st.error("Dados inválidos.")
        st.stop()

# --- 4. APP ---
df_total = carregar_dados()
df_user = df_total[(df_total['CPF'] == st.session_state.cpf_usuario) & (df_total['Status'] != 'Lixeira')].copy()

# Tabs com Key para evitar pulos de página
tab1, tab2 = st.tabs(["📝 LANÇAR", "📊 DASHBOARD"])

with tab1:
    st.subheader(f"Bem-vindo, {st.session_state.usuario}")
    col1, col2 = st.columns(2)
    v1 = col1.number_input("99 / Uber", min_value=0.0)
    v2 = col2.number_input("BoraAli", min_value=0.0)
    v3 = col1.number_input("App 163", min_value=0.0)
    v4 = col2.number_input("Particular / Outros", min_value=0.0)
    
    st.divider()
    c1 = col1.number_input("Energia", min_value=0.0)
    c2 = col2.number_input("Alimentação", min_value=0.0)
    
    st.subheader("🚗 Quilometragem")
    u_km = int(df_user['KM_Final'].max()) if not df_user.empty else 0
    k_ini = st.number_input("KM Inicial", value=u_km)
    k_fim = st.number_input("KM Final Atual", min_value=0)

    if st.button("SALVAR AGORA ✅", type="primary", use_container_width=True):
        nova = {col: 0 for col in COLUNAS_OFICIAIS}
        nova.update({'ID_Unico': str(int(time.time())), 'Status': 'Ativo', 'Usuario': st.session_state.usuario, 'CPF': st.session_state.cpf_usuario, 'Data': datetime.now(FUSO_BR).strftime("%Y-%m-%d"), 'Urbano': v1, 'Boraali': v2, 'app163': v3, 'Outros_Receita': v4, 'Energia': c1, 'Alimentacao': c2, 'KM_Inicial': k_ini, 'KM_Final': k_fim if k_fim > 0 else k_ini})
        salvar_no_banco(pd.concat([df_total, pd.DataFrame([nova])], ignore_index=True))
        st.success("Salvo!"); time.sleep(1); st.rerun()

with tab2:
    if df_user.empty: st.info("Sem dados.")
    else:
        df_bi = df_user.copy().sort_values('Data', ascending=False)
        df_bi['Rec'] = df_bi[['Urbano','Boraali','app163','Outros_Receita']].sum(axis=1)
        df_bi['Cus'] = df_bi[['Energia','Manuten','Seguro','Aplicativo','Alimentacao','Outros_Custos']].sum(axis=1)
        df_bi['Lucro'] = df_bi['Rec'] - df_bi['Cus']
        df_bi['KMR'] = (df_bi['KM_Final'] - df_bi['KM_Inicial']).clip(lower=0)

        # Filtros
        st.markdown("### 🔍 Filtros")
        f_dia = st.date_input("Filtrar Dia", value=None, format="DD/MM/YYYY")
        c_f1, c_f2 = st.columns(2)
        anos = ["Todos"] + sorted(df_bi['Data'].dt.year.unique().astype(str).tolist(), reverse=True)
        sel_ano = c_f1.selectbox("Ano", anos)
        meses_pt = ["Todos","Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
        sel_mes = c_f2.selectbox("Mês", meses_pt)
        
        df_f = df_bi.copy()
        if f_dia: df_f = df_f[df_f['Data'].dt.date == f_dia]
        if sel_ano != "Todos": df_f = df_f[df_f['Data'].dt.year == int(sel_ano)]
        if sel_mes != "Todos": df_f = df_f[df_f['Data'].dt.month == meses_pt.index(sel_mes)]

        # 1. INDICADORES (KPIs)
        tr, tc, tl, tk = df_f['Rec'].sum(), df_f['Cus'].sum(), df_f['Lucro'].sum(), df_f['KMR'].sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("Faturamento", format_br(tr))
        m2.metric("Lucro Líquido", format_br(tl))
        m3.metric("Custos", format_br(tc))
        m4, m5, m6 = st.columns(3)
        m4.metric("KM Rodado", f"{tk:,.0f} km")
        m5.metric("Faturamento/KM", format_br(tr/tk if tk > 0 else 0))
        m6.metric("Lucro/KM", format_br(tl/tk if tk > 0 else 0))

        # 2. TABELA DE DADOS (COM ROLAGEM)
        st.markdown("### 📋 Tabela Completa de Lançamentos")
        df_exibir = df_f.copy()
        df_exibir['Data'] = df_exibir['Data'].dt.strftime('%d/%m/%Y')
        # Reordenar para ver o que importa primeiro
        cols_view = ['Data', 'KM_Inicial', 'KM_Final', 'KMR', 'Rec', 'Cus', 'Lucro', 'Urbano', 'Boraali', 'app163', 'Outros_Receita', 'Energia', 'Alimentacao', 'ID_Unico']
        st.dataframe(df_exibir[cols_view], use_container_width=True, height=300)

        # 3. BOTÃO DE EXCLUSÃO (SUPER DISCRETO)
        with st.expander("🗑️ Excluir um lançamento errado"):
            st.write("Selecione o lançamento pelo ID para remover:")
            item_excluir = st.selectbox("ID do Lançamento", df_f['ID_Unico'].tolist(), format_func=lambda x: f"ID: {x} - Data: {df_f[df_f['ID_Unico']==x]['Data'].dt.strftime('%d/%m/%Y').values[0]}")
            if st.button("CONFIRMAR EXCLUSÃO", type="secondary"):
                df_total.loc[df_total['ID_Unico'] == item_excluir, 'Status'] = 'Lixeira'
                salvar_no_banco(df_total)
                st.warning("Excluído!"); time.sleep(1); st.rerun()

        # 4. GRÁFICOS
        if not df_f.empty:
            st.markdown("### 📊 Gráficos de Desempenho")
            df_g = df_f.sort_values('Data')
            df_g['Dia'] = df_g['Data'].dt.strftime('%d/%m')
            fig1 = px.bar(df_g, x='Dia', y=['Rec', 'Lucro'], barmode='group', color_discrete_map={'Rec':'#28a745','Lucro':'#007bff'})
            st.plotly_chart(fig1, use_container_width=True)
            
            # Pizza de Custos
            custos_pie = {'Energia': df_f['Energia'].sum(), 'Alimentos': df_f['Alimentacao'].sum(), 'Outros': df_f['Outros_Custos'].sum()}
            fig2 = px.pie(names=list(custos_pie.keys()), values=list(custos_pie.values()), hole=0.4, title="Distribuição de Custos")
            st.plotly_chart(fig2, use_container_width=True)

st.divider()
if st.button("Sair"): 
    st.session_state.autenticado = False
    st.query_params.clear(); st.rerun()
