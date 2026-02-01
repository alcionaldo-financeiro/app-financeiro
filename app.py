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
        /* Ajuste de métricas para celular */
        [data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #eee;
            padding: 10px;
            border-radius: 10px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
        }
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
    return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

def limpar_cpf(t):
    if pd.isna(t) or t == "": return ""
    texto = re.sub(r'\D', '', str(t).replace('.0', ''))
    return texto.zfill(11)

def limpar_valor_monetario(valor):
    if pd.isna(valor) or valor == "" or valor == "-": return 0.0
    if isinstance(valor, (int, float)): return float(valor)
    if isinstance(valor, str):
        valor = valor.replace('R$', '').replace('.', '').replace(',', '.').strip()
    try: return float(valor)
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

# --- 3. LOGIN ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False

params = st.query_params
q_nome = params.get("n", "")
q_cpf = limpar_cpf(params.get("c", ""))

if not st.session_state['autenticado']:
    if q_nome and len(q_cpf) == 11:
        st.session_state.update({'usuario': q_nome.lower(), 'cpf_usuario': q_cpf, 'autenticado': True})
        st.rerun()
    
    st.title("💎 BYD Pro")
    n_in = st.text_input("Seu Nome:")
    c_in = st.text_input("Seu CPF:", max_chars=11)
    if st.button("ENTRAR ✅", type="primary"):
        c_l = limpar_cpf(c_in)
        if n_in and len(c_l) == 11:
            st.session_state.update({'usuario': n_in.lower(), 'cpf_usuario': c_l, 'autenticado': True})
            st.rerun()
    st.stop()

# --- 4. SISTEMA ---
CPF_LOGADO = st.session_state['cpf_usuario']
df_total = carregar_dados()
df_user = df_total[(df_total['CPF'] == CPF_LOGADO) & (df_total['Status'] != 'Lixeira')].copy()

# AQUI ESTÁ O SEGREDO: Usamos 'key' para travar a aba
aba = st.tabs(["📝 LANÇAR DADOS", "📊 DASHBOARD"], key="aba_principal")

# --- ABA DE LANÇAMENTO ---
with aba[0]:
    with st.expander("⚙️ Importar Excel"):
        arq = st.file_uploader("Suba o arquivo .xlsx", type=["xlsx"])
        if arq and st.button("Processar Importação"):
            df_ex = pd.read_excel(arq)
            mapping = {'Data':'Data','Urbano':'Urbano','Boraali':'Boraali','app163':'app163','Outros':'Outros_Receita','Energia':'Energia','Manuten':'Manuten','Seguro':'Seguro','Documento':'Outros_Custos','Aplicativo':'Aplicativo','KM Inicial':'KM_Inicial','KM final':'KM_Final'}
            novas = []
            for i, row in df_ex.iterrows():
                n = {col: 0 for col in COLUNAS_OFICIAIS}
                for ex, ap in mapping.items():
                    if ex in row:
                        if 'Data' in ex: 
                            try: n[ap] = pd.to_datetime(row[ex]).strftime("%Y-%m-%d")
                            except: n[ap] = datetime.now(FUSO_BR).strftime("%Y-%m-%d")
                        elif 'KM' in ex: n[ap] = float(row[ex])
                        else: n[ap] = limpar_valor_monetario(row[ex])
                n.update({'ID_Unico': str(int(time.time())+i), 'Status': 'Ativo', 'Usuario': st.session_state['usuario'], 'CPF': CPF_LOGADO})
                novas.append(n)
            conn = st.connection("gsheets", type=GSheetsConnection)
            conn.update(worksheet=0, data=pd.concat([carregar_dados(), pd.DataFrame(novas)], ignore_index=True))
            st.cache_data.clear(); st.success("Importado!"); time.sleep(1); st.rerun()

    st.markdown("### 💰 Receitas")
    v1 = st.number_input("99 / Uber (R$)", min_value=0.0, step=10.0)
    v2 = st.number_input("BoraAli (R$)", min_value=0.0, step=10.0)
    v3 = st.number_input("App 163 (R$)", min_value=0.0, step=10.0)
    v4 = st.number_input("Particular / Outros (R$)", min_value=0.0, step=10.0)

    st.markdown("### 💸 Custos")
    c1 = st.number_input("Energia / Combustível (R$)", min_value=0.0, step=5.0)
    c2 = st.number_input("Manutenção / Lavagem (R$)", min_value=0.0, step=5.0)
    c3 = st.number_input("Seguro / Docs (R$)", min_value=0.0, step=5.0)
    c4 = st.number_input("Alimentação (R$)", min_value=0.0, step=5.0)
    c5 = st.number_input("Internet / Apps (R$)", min_value=0.0, step=5.0)
    c6 = st.number_input("Outros Custos (R$)", min_value=0.0, step=5.0)

    st.markdown("### 🚗 KM do Veículo")
    u_km = int(df_user['KM_Final'].max()) if not df_user.empty else 0
    k_ini = st.number_input("KM Inicial (Confirme ou edite)", value=u_km)
    k_fim = st.number_input("KM Final Atual", min_value=0)
    
    if st.button("SALVAR AGORA ✅", type="primary"):
        nova = {col: 0 for col in COLUNAS_OFICIAIS}
        nova.update({
            'Urbano':v1, 'Boraali':v2, 'app163':v3, 'Outros_Receita':v4,
            'Energia':c1, 'Manuten':c2, 'Seguro':c3, 'Alimentacao':c4, 'Aplicativo':c5, 'Outros_Custos':c6,
            'KM_Inicial':k_ini, 'KM_Final':k_fim if k_fim > 0 else k_ini,
            'ID_Unico': str(int(time.time())), 'Status': 'Ativo', 'Usuario': st.session_state['usuario'], 
            'CPF': CPF_LOGADO, 'Data': datetime.now(FUSO_BR).strftime("%Y-%m-%d")
        })
        conn = st.connection("gsheets", type=GSheetsConnection)
        conn.update(worksheet=0, data=pd.concat([carregar_dados(), pd.DataFrame([nova])], ignore_index=True))
        st.cache_data.clear(); st.success("Salvo com sucesso!"); time.sleep(1); st.rerun()

# --- ABA DE DASHBOARD ---
with aba[1]:
    if df_user.empty: st.info("Sem dados para exibir.")
    else:
        # Preparação
        df_bi = df_user.copy().sort_values('Data', ascending=False)
        df_bi['Rec'] = df_bi[['Urbano','Boraali','app163','Outros_Receita']].sum(axis=1)
        df_bi['Cus'] = df_bi[['Energia','Manuten','Seguro','Aplicativo','Alimentacao','Outros_Custos']].sum(axis=1)
        df_bi['Lucro'] = df_bi['Rec'] - df_bi['Cus']
        df_bi['KMR'] = (df_bi['KM_Final'] - df_bi['KM_Inicial']).clip(lower=0)
        
        # Filtros em Português
        st.markdown("### 🔍 Filtros de Visualização")
        
        anos_disponiveis = df_bi['Data'].dt.year.dropna().unique()
        lista_anos = ["Todos"] + sorted([str(int(y)) for y in anos_disponiveis], reverse=True)
        sel_ano = st.selectbox("Escolha o Ano", lista_anos, key="f_ano")
        
        meses_pt = ["Todos", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        sel_mes = st.selectbox("Escolha o Mês", meses_pt, key="f_mes")
        
        sel_dia = st.date_input("Filtrar por um Dia específico", value=None, key="f_dia")

        # Aplicar Filtros
        df_f = df_bi.copy()
        if sel_ano != "Todos": df_f = df_f[df_f['Data'].dt.year == int(sel_ano)]
        if sel_mes != "Todos": df_f = df_f[df_f['Data'].dt.month == meses_pt.index(sel_mes)]
        if sel_dia: df_f = df_f[df_f['Data'].dt.date == sel_dia]

        # MÉTRICAS NO TOPO (KPIs)
        tr, tc, tl, tk = df_f['Rec'].sum(), df_f['Cus'].sum(), df_f['Lucro'].sum(), df_f['KMR'].sum()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Faturamento Total", format_br(tr))
            st.metric("Lucro Líquido", format_br(tl))
            st.metric("Faturamento por KM", format_br(tr/tk if tk > 0 else 0))
        with col2:
            st.metric("Custos Totais", format_br(tc))
            st.metric("KM Rodado Total", f"{tk:,.0f} km".replace(",", "."))
            st.metric("Lucro por KM", format_br(tl/tk if tk > 0 else 0))

        with st.expander("📋 Ver Dados em Tabela"):
            st.dataframe(df_f, use_container_width=True)

        # GRÁFICOS
        st.divider()
        st.markdown("### 📊 Gráficos de Performance")
        df_f['Dia_Mes'] = df_f['Data'].dt.strftime('%d/%m')
        df_g = df_f.groupby('Dia_Mes').agg({'Rec':'sum','Cus':'sum','KMR':'sum'}).reset_index()

        st.write("**Ganhos vs Custos por Dia (R$)**")
        fig1 = px.bar(df_g, x='Dia_Mes', y=['Rec', 'Cus'], barmode='group', 
                      labels={'value':'Valor R$', 'Dia_Mes':'Dia', 'variable':'Legenda'},
                      color_discrete_map={'Rec':'#28a745','Cus':'#dc3545'}, text_auto='.2s')
        st.plotly_chart(fig1, use_container_width=True)

        st.write("**Faturamento por App (R$)**")
        apps = df_f[['Urbano','Boraali','app163','Outros_Receita']].sum()
        fig2 = px.bar(x=apps.index, y=apps.values, text_auto='.2s', color_discrete_sequence=['#28a745'], labels={'x':'Aplicativo','y':'Total R$'})
        st.plotly_chart(fig2, use_container_width=True)

        st.write("**Distribuição de Custos (%)**")
        gastos = df_f[['Energia','Manuten','Seguro','Aplicativo','Alimentacao','Outros_Custos']].sum()
        fig3 = px.pie(names=gastos.index, values=gastos.values, hole=0.4)
        st.plotly_chart(fig3, use_container_width=True)

if st.button("Sair"):
    st.session_state['autenticado'] = False
    st.rerun()
