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
        #MainMenu, header, footer, .stDeployButton {display: none !important; visibility: hidden !important;}
        [data-testid="stToolbar"], [data-testid="stStatusWidget"], [data-testid="stDecoration"] {display: none !important;}
        .block-container {padding-top: 0.5rem !important;}
        div.stButton > button[kind="primary"] {
            background-color: #28a745 !important; color: white !important;
            border-radius: 8px; height: 3em; font-weight: bold; width: 100%;
        }
        .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e1e4e8; box-shadow: 0px 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNÇÕES DE APOIO ---
FUSO_BR = pytz.timezone('America/Sao_Paulo')
COLUNAS_OFICIAIS = [
    'ID_Unico', 'Status', 'Usuario', 'CPF', 'Data', 
    'Urbano', 'Boraali', 'app163', 'Outros_Receita', 
    'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos', 
    'KM_Inicial', 'KM_Final', 'Detalhes'
]

def format_br(valor):
    # Corrigido de .2d para .2f para aceitar centavos
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_km(valor):
    return f"{valor:,.0f} km".replace(",", ".")

def limpar_cpf(t):
    texto = re.sub(r'\D', '', str(t).replace('.0', ''))
    return texto.zfill(11)

def limpar_valor_monetario(valor):
    if pd.isna(valor) or valor == "" or valor == "-": return 0.0
    if isinstance(valor, (int, float)): return float(valor)
    if isinstance(valor, str):
        valor = valor.replace('R$', '').replace('.', '').replace(',', '.').strip()
    try: return float(valor)
    except: return 0.0

@st.cache_data(ttl=5)
def carregar_dados():
    try:
        df = conn.read(worksheet=0, ttl=0)
        if df is None or df.empty: return pd.DataFrame(columns=COLUNAS_OFICIAIS)
        df['CPF'] = df['CPF'].apply(limpar_cpf)
        cols_num = ['Urbano', 'Boraali', 'app163', 'Outros_Receita', 'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos', 'KM_Inicial', 'KM_Final']
        for c in cols_num: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        # Anti-duplicidade
        df = df.drop_duplicates(subset=['Data', 'Urbano', 'KM_Final', 'CPF'], keep='first')
        return df
    except: return pd.DataFrame(columns=COLUNAS_OFICIAIS)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. LOGIN ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
p = st.query_params
q_nome, q_cpf = p.get("n", ""), limpar_cpf(p.get("c", ""))

if not st.session_state['autenticado']:
    if q_nome and len(q_cpf) == 11:
        st.session_state.update({'usuario': q_nome.lower(), 'cpf_usuario': q_cpf, 'autenticado': True})
        st.rerun()
    st.stop()

CPF_LOGADO = st.session_state['cpf_usuario']
df_total = carregar_dados()
df_user = df_total[(df_total['CPF'] == CPF_LOGADO) & (df_total['Status'] != 'Lixeira')].copy()

# --- INTERFACE ---
aba1, aba2 = st.tabs(["📝 LANÇAR DADOS", "📊 PERFORMANCE E BI"])

with aba1:
    with st.expander("⚙️", expanded=False):
        arq = st.file_uploader("Importar Excel", type=["xlsx"])
        if arq and st.button("Confirmar Importação"):
            df_ex = pd.read_excel(arq)
            mapping = {'Data':'Data','Urbano':'Urbano','Boraali':'Boraali','app163':'app163','Outros':'Outros_Receita','Energia':'Energia','Manuten':'Manuten','Seguro':'Seguro','Documento':'Outros_Custos','Aplicativo':'Aplicativo','KM Inicial':'KM_Inicial','KM final':'KM_Final'}
            novas = []
            for i, row in df_ex.iterrows():
                n = {col: 0 for col in COLUNAS_OFICIAIS}
                for ex, ap in mapping.items():
                    if ex in row:
                        if 'Data' in ex: n[ap] = pd.to_datetime(row[ex]).strftime("%Y-%m-%d")
                        elif 'KM' in ex: n[ap] = float(row[ex])
                        else: n[ap] = limpar_valor_monetario(row[ex])
                n.update({'ID_Unico': str(int(time.time())+i), 'Status': 'Ativo', 'Usuario': st.session_state['usuario'], 'CPF': CPF_LOGADO})
                novas.append(n)
            conn.update(worksheet=0, data=pd.concat([carregar_dados(), pd.DataFrame(novas)], ignore_index=True))
            st.cache_data.clear(); st.success("Importado!"); time.sleep(1); st.rerun()

    col_r, col_c = st.columns(2)
    with col_r:
        st.subheader("Ganhos")
        v_urb = st.number_input("99 / Uber", min_value=0.0, step=10.0)
        v_bora = st.number_input("BoraAli", min_value=0.0, step=10.0)
        v_163 = st.number_input("App 163", min_value=0.0, step=10.0)
        v_out_r = st.number_input("Particular", min_value=0.0, step=10.0)
    with col_c:
        st.subheader("Custos")
        v_ene = st.number_input("Energia / Comb", min_value=0.0, step=5.0)
        v_man = st.number_input("Manutenção", min_value=0.0, step=5.0)
        v_seg = st.number_input("Seguro / Docs", min_value=0.0, step=5.0)
        v_ali = st.number_input("Alimentação", min_value=0.0, step=5.0)

    st.subheader("Rodagem")
    c_k1, c_k2 = st.columns(2)
    u_km = int(df_user['KM_Final'].max()) if not df_user.empty else 0
    k1 = c_k1.number_input("KM Inicial (Inalterável)", value=u_km, disabled=True)
    k2 = c_k2.number_input("KM Final (Painel)", value=0)
    
    if st.button("CONFERIR E SALVAR ➡️", type="primary"):
        if k2 > 0 and k2 <= k1: st.error("Erro: KM Final deve ser maior.")
        else:
            nova = {col: 0 for col in COLUNAS_OFICIAIS}
            nova.update({'Urbano':v_urb,'Boraali':v_bora,'app163':v_163,'Outros_Receita':v_out_r,'Energia':v_ene,'Manuten':v_man,'Seguro':v_seg,'Alimentacao':v_ali,'KM_Inicial':k1,'KM_Final':k2 if k2 > 0 else k1,'ID_Unico': str(int(time.time())), 'Status': 'Ativo', 'Usuario': st.session_state['usuario'], 'CPF': CPF_LOGADO, 'Data': datetime.now(FUSO_BR).strftime("%Y-%m-%d")})
            conn.update(worksheet=0, data=pd.concat([carregar_dados(), pd.DataFrame([nova])], ignore_index=True))
            st.cache_data.clear(); st.success("Salvo!"); time.sleep(1); st.rerun()

with aba2:
    if df_user.empty: st.info("Sem dados.")
    else:
        df_bi = df_user.copy().sort_values('Data', ascending=False)
        df_bi['Receita'] = df_bi[['Urbano','Boraali','app163','Outros_Receita']].sum(axis=1)
        df_bi['Custos'] = df_bi[['Energia','Manuten','Seguro','Aplicativo','Alimentacao','Outros_Custos']].sum(axis=1)
        df_bi['Lucro'] = df_bi['Receita'] - df_bi['Custos']
        df_bi['Km_rodado'] = (df_bi['KM_Final'] - df_bi['KM_Inicial']).clip(lower=0)
        
        st.subheader("🔍 Filtros")
        c_f1, c_f2 = st.columns(2)
        anos = ["Todos"] + sorted(list(df_bi['Data'].dt.year.unique().astype(str)), reverse=True)
        ano_sel = c_f1.selectbox("Filtrar Ano", anos)
        meses = ["Todos", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        mes_sel = c_f2.selectbox("Filtrar Mês", meses)
        
        df_filt = df_bi.copy()
        if ano_sel != "Todos": df_filt = df_filt[df_filt['Data'].dt.year == int(ano_sel)]
        if mes_sel != "Todos": df_filt = df_filt[df_filt['Data'].dt.month == meses.index(mes_sel)]
        
        # --- CARDS TOTAIS ---
        t_rec, t_cus, t_luc, t_km = df_filt['Receita'].sum(), df_filt['Custos'].sum(), df_filt['Lucro'].sum(), df_filt['Km_rodado'].sum()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Faturamento Total", format_br(t_rec))
        m2.metric("Lucro Líquido", format_br(t_luc))
        m3.metric("KM Total", format_km(t_km))
        m4.metric("Lucro por KM", format_br(t_luc/t_km if t_km > 0 else 0))

        # --- TABELA (NO TOPO) ---
        st.subheader("📋 Detalhamento dos Lançamentos")
        st.dataframe(df_filt, use_container_width=True, hide_index=True)

        # --- GRÁFICOS DE BARRA ---
        st.divider()
        df_filt['Data_Graf'] = df_filt['Data'].dt.strftime('%d/%m/%Y')
        df_graf = df_filt.groupby('Data_Graf').agg({'Receita':'sum', 'Custos':'sum', 'Lucro':'sum', 'Km_rodado':'sum'}).reset_index()

        c_g1, c_g2 = st.columns(2)
        with c_g1:
            st.write("**💰 Ganhos vs Custos**")
            fig1 = px.bar(df_graf, x='Data_Graf', y=['Receita', 'Custos'], barmode='group', color_discrete_map={'Receita':'#28a745', 'Custos':'#dc3545'})
            st.plotly_chart(fig1, use_container_width=True)
            
            st.write("**🏆 Faturamento por App**")
            apps = df_filt[['Urbano','Boraali','app163','Outros_Receita']].sum()
            fig2 = px.bar(x=apps.index, y=apps.values, labels={'x':'App', 'y':'R$'}, color_discrete_sequence=['#28a745'])
            st.plotly_chart(fig2, use_container_width=True)

        with c_g2:
            st.write("**🚗 KM Rodados por Dia**")
            fig3 = px.bar(df_graf, x='Data_Graf', y='Km_rodado', color_discrete_sequence=['#007bff'])
            st.plotly_chart(fig3, use_container_width=True)
            
            st.write("**🍕 Divisão de Custos**")
            custos_pie = df_filt[['Energia','Manuten','Seguro','Alimentacao']].sum()
            fig4 = px.pie(names=custos_pie.index, values=custos_pie.values, hole=0.4)
            st.plotly_chart(fig4, use_container_width=True)

if st.button("Sair"):
    st.session_state['autenticado'] = False; st.rerun()
