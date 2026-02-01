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
        
        /* Botões */
        div.stButton > button[kind="primary"] {
            background-color: #28a745 !important;
            color: white !important;
            border-radius: 12px !important;
            height: 3.5rem !important;
            font-weight: bold !important;
            width: 100% !important;
        }
        
        /* Métricas */
        [data-testid="stMetric"] {
            background-color: #ffffff !important;
            border: 1px solid #cccccc !important;
            padding: 10px !important;
            border-radius: 10px !important;
        }
        [data-testid="stMetricLabel"] { color: #333333 !important; font-weight: bold !important; font-size: 0.9rem !important; }
        [data-testid="stMetricValue"] { color: #000000 !important; font-weight: 800 !important; font-size: 1.2rem !important; }
        
        /* Ajuste do Radio para parecer Abas */
        div[role="radiogroup"] {
            display: flex;
            justify-content: center;
            width: 100%;
            background-color: #f0f2f6;
            padding: 5px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        div[role="radiogroup"] label {
            flex: 1;
            text-align: center;
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            margin: 0 5px;
            padding: 10px;
            font-weight: bold;
        }
        div[role="radiogroup"] label[data-checked="true"] {
            background-color: #28a745 !important;
            color: white !important;
            border-color: #28a745 !important;
        }
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
# Recupera parametros da URL para preencher automaticamente
params = st.query_params
u_url = params.get("user", "")
c_url = limpar_cpf(params.get("cpf", ""))

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# Se já tem dados na URL e não está autenticado, tenta autenticar direto (Opcional, ou preenche os campos)
# Aqui optamos por preencher os campos para o usuário confirmar
if not st.session_state.autenticado:
    st.title("💎 BYD Pro Login")
    
    # Se houver dados na sessão anterior ou URL, usa como valor padrão
    default_user = u_url if u_url else st.session_state.get('last_user', '')
    default_cpf = c_url if c_url else st.session_state.get('last_cpf', '')
    
    n_in = st.text_input("Nome:", value=default_user)
    c_in = st.text_input("CPF:", value=default_cpf, max_chars=11)
    
    if st.button("ENTRAR ✅", type="primary"):
        c_l = limpar_cpf(c_in)
        if n_in and len(c_l) == 11:
            st.session_state.update({'usuario': n_in, 'cpf_usuario': c_l, 'autenticado': True})
            # Salva na sessão para facilitar re-login
            st.session_state.last_user = n_in
            st.session_state.last_cpf = c_l
            # Atualiza URL para salvar estado se o usuário favoritar a página
            st.query_params.update({"user": n_in, "cpf": c_l})
            st.rerun()
        else: st.error("⚠️ Dados inválidos.")
    st.stop()

# --- 4. APP ---
df_total = carregar_dados()
df_user = df_total[(df_total['CPF'] == st.session_state.cpf_usuario) & 
                   (df_total['Status'] != 'Lixeira') & 
                   (df_total['Data'].dt.date <= HOJE_BR)].copy()

# NAVEGAÇÃO SEGURA (Substituindo Tabs por Radio para evitar pulos)
nav_opcao = st.radio("", ["📝 LANÇAR", "📊 DASHBOARD"], horizontal=True, label_visibility="collapsed")

if nav_opcao == "📝 LANÇAR":
    st.subheader(f"Olá, {st.session_state.usuario}")
    data_lanc = st.date_input("Data do Trabalho:", value=HOJE_BR, format="DD/MM/YYYY")
    
    # --- BLOCO 1: FATURAMENTO (RECEITAS) ---
    st.markdown("### 💰 Faturamento (Entradas)")
    with st.container(border=True):
        col_rec1, col_rec2 = st.columns(2)
        v1 = col_rec1.number_input("Urbano (99/Uber)", min_value=0.0)
        v2 = col_rec2.number_input("BoraAli", min_value=0.0)
        v3 = col_rec1.number_input("app163", min_value=0.0)
        v4 = col_rec2.number_input("Outros (Receita)", min_value=0.0)

    # --- BLOCO 2: CUSTOS (SAÍDAS) ---
    st.markdown("### 💸 Custos (Saídas)")
    with st.container(border=True):
        col_cus1, col_cus2 = st.columns(2)
        c1 = col_cus1.number_input("Energia", min_value=0.0)
        c2 = col_cus2.number_input("Manutenção", min_value=0.0)
        c3 = col_cus1.number_input("Seguro", min_value=0.0)
        c4 = col_cus2.number_input("Outros Custos (Documento)", min_value=0.0)
        c5 = col_cus1.number_input("Aplicativo", min_value=0.0)
        c6 = col_cus2.number_input("Alimentação", min_value=0.0)
    
    st.subheader("🚗 KM")
    
    # Lógica Ajustada: Busca o último KM Final válido (>0) pela DATA mais recente
    u_km = 0
    if not df_user.empty:
        try:
            # Ordena por data decrescente
            df_km_valid = df_user.sort_values(by='Data', ascending=False)
            # Filtra onde KM > 0 para ignorar dias zerados/futuros
            df_km_valid = df_km_valid[df_km_valid['KM_Final'] > 0]
            
            if not df_km_valid.empty:
                u_km = int(df_km_valid.iloc[0]['KM_Final'])
        except:
            u_km = 0

    col_km1, col_km2 = st.columns(2)
    k_ini = col_km1.number_input("KM Inicial", value=u_km)
    k_fim = col_km2.number_input("KM Final", min_value=0)

    if st.button("SALVAR AGORA ✅", type="primary"):
        nova = {col: 0 for col in COLUNAS_OFICIAIS}
        nova.update({'ID_Unico': str(int(time.time())), 'Status': 'Ativo', 'Usuario': st.session_state.usuario, 'CPF': st.session_state.cpf_usuario, 'Data': data_lanc.strftime("%Y-%m-%d"), 'Urbano': v1, 'Boraali': v2, 'app163': v3, 'Outros_Receita': v4, 'Energia': c1, 'Manuten': c2, 'Seguro': c3, 'Outros_Custos': c4, 'Aplicativo': c5, 'Alimentacao': c6, 'KM_Inicial': k_ini, 'KM_Final': k_fim if k_fim > 0 else k_ini})
        salvar_no_banco(pd.concat([df_total, pd.DataFrame([nova])], ignore_index=True))
        st.success("Salvo!"); time.sleep(1); st.rerun()

elif nav_opcao == "📊 DASHBOARD":
    if df_user.empty: st.info("Sem dados até hoje.")
    else:
        df_bi = df_user.copy().sort_values('Data', ascending=False)
        
        # FILTROS
        st.markdown("### 🔍 Filtros")
        
        f_dia = st.date_input("Filtrar Dia Específico", value=None, format="DD/MM/YYYY")
        
        col_f1, col_f2 = st.columns(2)
        anos = ["Todos"] + sorted(df_bi['Data'].dt.year.dropna().unique().astype(int).astype(str).tolist(), reverse=True)
        sel_ano = col_f1.selectbox("Ano", anos)
        
        meses_pt = ["Todos","Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
        sel_mes = col_f2.selectbox("Mês", meses_pt)
        
        # APLICAÇÃO DOS FILTROS
        df_f = df_bi.copy()
        if f_dia:
            df_f = df_f[df_f['Data'].dt.date == f_dia]
        if sel_ano != "Todos":
            df_f = df_f[df_f['Data'].dt.year == int(sel_ano)]
        if sel_mes != "Todos":
            df_f = df_f[df_f['Data'].dt.month == meses_pt.index(sel_mes)]

        # CÁLCULOS
        df_f['Receita'] = df_f[['Urbano','Boraali','app163','Outros_Receita']].sum(axis=1)
        df_f['Custos'] = df_f[['Energia','Manuten','Seguro','Outros_Custos','Aplicativo','Alimentacao']].sum(axis=1)
        df_f['Km rodados'] = (df_f['KM_Final'] - df_f['KM_Inicial']).clip(lower=0)
        df_f['Lucro/prejuizo'] = df_f['Receita'] - df_f['Custos']
        df_f['Lucro/km'] = df_f.apply(lambda r: r['Lucro/prejuizo']/r['Km rodados'] if r['Km rodados'] > 0 else 0, axis=1)
        df_f['Receita/R$/KM'] = df_f.apply(lambda r: r['Receita']/r['Km rodados'] if r['Km rodados'] > 0 else 0, axis=1)
        df_f['R$/combust/km'] = df_f.apply(lambda r: r['Energia']/r['Km rodados'] if r['Km rodados'] > 0 else 0, axis=1)
        df_f['Qtd dias'] = 1

        # 1. INDICADORES (KPIs)
        tr, tc, tl, tk = df_f['Receita'].sum(), df_f['Custos'].sum(), df_f['Lucro/prejuizo'].sum(), df_f['Km rodados'].sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("Faturamento", format_br(tr))
        m2.metric("Lucro Líquido", format_br(tl))
        m3.metric("Custos", format_br(tc))
        m4, m5, m6 = st.columns(3)
        m4.metric("KM Rodado", f"{tk:,.0f} km")
        m5.metric("R$/KM", format_br(tr/tk if tk > 0 else 0))
        m6.metric("Lucro/KM", format_br(tl/tk if tk > 0 else 0))

        # 2. TABELA COMPLETA
        st.markdown("### 📋 Lançamentos")
        df_ex = df_f.copy()
        df_ex['Data'] = df_ex['Data'].dt.strftime('%d/%m/%Y')
        
        df_ex = df_ex.rename(columns={'Outros_Receita':'Outros (Rec)', 'Outros_Custos':'Documento', 'Alimentacao':'Alimentação', 'KM_Inicial':'KM Inicial', 'KM_Final':'KM final'})
        
        cols_final = [
            'Data', 'Usuario', 'Receita', 'Urbano', 'Boraali', 'app163', 
            'Outros (Rec)', 'Custos', 'Energia', 'Manuten', 'Seguro', 
            'Documento', 'Aplicativo', 'Alimentação', 'KM Inicial', 
            'KM final', 'Km rodados', 'Lucro/prejuizo', 'Lucro/km', 
            'Receita/R$/KM', 'R$/combust/km', 'Qtd dias', 'ID_Unico'
        ]
        
        st.dataframe(df_ex[cols_final], use_container_width=True, height=350)

        # 3. EXCLUSÃO
        with st.expander("🗑️ Excluir lançamento"):
            item_ex = st.selectbox("Selecione pelo ID", df_f['ID_Unico'].tolist())
            if st.button("CONFIRMAR EXCLUSÃO"):
                df_total.loc[df_total['ID_Unico'] == item_ex, 'Status'] = 'Lixeira'
                salvar_no_banco(df_total)
                st.rerun()

        # 4. GRÁFICOS
        st.markdown("### 📊 Desempenho")
        df_g = df_f.sort_values('Data')
        df_g['Dia'] = df_g['Data'].dt.strftime('%d/%m')
        fig1 = px.bar(df_g, x='Dia', y=['Receita', 'Lucro/prejuizo'], barmode='group', color_discrete_map={'Receita':'#28a745','Lucro/prejuizo':'#007bff'})
        st.plotly_chart(fig1, use_container_width=True)
        
        custos_p = {'Energia': df_f['Energia'].sum(), 'Manutenção': df_f['Manuten'].sum(), 'Seguro': df_f['Seguro'].sum(), 'Alimentação': df_f['Alimentacao'].sum(), 'Outros': df_f['Outros_Custos'].sum()}
        fig2 = px.pie(names=list(custos_p.keys()), values=list(custos_p.values()), hole=0.4)
        st.plotly_chart(fig2, use_container_width=True)

st.divider()
if st.button("Sair"): 
    st.session_state.autenticado = False
    st.query_params.clear(); st.rerun()
