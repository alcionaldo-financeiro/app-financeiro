import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime
import time
import pytz
import plotly.express as px
import plotly.graph_objects as go

# --- 1. CONFIGURAÇÃO E ESTILO (MOBILE FIRST) ---
st.set_page_config(page_title="BYD Pro", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        /* Remove itens padrões do Streamlit para parecer App Nativo */
        #MainMenu, header, footer, .stDeployButton {display: none !important;}
        [data-testid="stToolbar"], [data-testid="stDecoration"] {display: none !important;}
        
        /* Ajuste de Container para Celular (Menos borda branca) */
        .block-container {
            padding-top: 1rem !important; 
            padding-bottom: 3rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        
        /* Botões Grandes e Fáceis de Tocar (Touch Friendly) */
        div.stButton > button[kind="primary"] {
            background-color: #28a745 !important;
            color: white !important;
            border-radius: 12px !important;
            height: 4rem !important; /* Mais alto para o dedo */
            font-weight: bold !important;
            font-size: 1.1rem !important;
            width: 100% !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        /* Cards de Métricas (KPIs) */
        [data-testid="stMetric"] {
            background-color: #ffffff !important;
            border: 1px solid #e6e6e6 !important;
            padding: 10px !important;
            border-radius: 12px !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            text-align: center; /* Centraliza no mobile */
        }
        [data-testid="stMetricLabel"] { 
            color: #666666 !important; 
            font-weight: 600 !important; 
            font-size: 0.85rem !important; 
        }
        [data-testid="stMetricValue"] { 
            color: #000000 !important; 
            font-weight: 800 !important; 
            font-size: 1.1rem !important; /* Ajustado para não quebrar linha */
        }
        
        /* Menu de Navegação (Radio) Adaptável */
        div[role="radiogroup"] {
            display: flex;
            flex-wrap: wrap; /* Permite quebrar linha em telas muito pequenas */
            justify-content: center;
            width: 100%;
            background-color: #f8f9fa;
            padding: 8px;
            border-radius: 15px;
            margin-bottom: 20px;
            border: 1px solid #eee;
        }
        div[role="radiogroup"] label {
            flex: 1 1 auto; /* Cresce e encolhe conforme necessário */
            min-width: 120px; /* Largura mínima para o toque */
            text-align: center;
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 10px;
            margin: 4px;
            padding: 12px;
            font-weight: bold;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        div[role="radiogroup"] label[data-checked="true"] {
            background-color: #28a745 !important;
            color: white !important;
            border-color: #28a745 !important;
            box-shadow: 0 2px 5px rgba(40, 167, 69, 0.3);
        }

        /* Inputs de formulário mais espaçados */
        .stNumberInput input {
            padding: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNÇÕES ---
FUSO_BR = pytz.timezone('America/Sao_Paulo')
HOJE_BR = datetime.now(FUSO_BR).date()
COLUNAS_OFICIAIS = ['ID_Unico', 'Status', 'Usuario', 'CPF', 'Data', 'Urbano', 'Boraali', 'app163', 'Outros_Receita', 'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos', 'KM_Inicial', 'KM_Final', 'Detalhes']

def format_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

def format_int_br(valor):
    """Formata inteiro com ponto de milhar: 5.262"""
    return f"{int(valor):,}".replace(",", ".")

def limpar_cpf(t):
    if pd.isna(t) or t == "" or t is None: return ""
    s = str(t).split('.')[0]
    s = re.sub(r'\D', '', s)
    return s.zfill(11)

def v(valor):
    if valor is None: return 0.0
    return float(valor)

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

# --- 3. LOGIN ---
params = st.query_params
u_url = params.get("user", "")
c_url = limpar_cpf(params.get("cpf", ""))

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("💎 BYD Pro Login")
    default_user = u_url if u_url else st.session_state.get('last_user', '')
    default_cpf = c_url if c_url else st.session_state.get('last_cpf', '')
    
    n_in = st.text_input("Nome:", value=default_user)
    c_in = st.text_input("CPF:", value=default_cpf, max_chars=11)
    
    if st.button("ENTRAR ✅", type="primary"):
        c_l = limpar_cpf(c_in)
        if n_in and len(c_l) == 11:
            st.session_state.update({'usuario': n_in, 'cpf_usuario': c_l, 'autenticado': True})
            st.session_state.last_user = n_in
            st.session_state.last_cpf = c_l
            st.query_params.update({"user": n_in, "cpf": c_l})
            st.rerun()
        else: st.error("⚠️ Dados inválidos.")
    st.stop()

# --- 4. APP ---
df_total = carregar_dados()
df_user = df_total[(df_total['CPF'] == st.session_state.cpf_usuario) & 
                   (df_total['Status'] != 'Lixeira') & 
                   (df_total['Data'].dt.date <= HOJE_BR)].copy()

nav_opcao = st.radio("", ["📝 LANÇAR", "📊 DASHBOARD"], horizontal=True, label_visibility="collapsed")

# --- FUNÇÃO AUXILIAR PARA LAYOUT DE GRÁFICO MOBILE ---
def mobile_chart_layout(fig):
    fig.update_layout(
        margin=dict(l=10, r=10, t=30, b=10), # Margens mínimas
        legend=dict(
            orientation="h", # Legenda Horizontal
            yanchor="bottom", y=1.02, # Acima do gráfico
            xanchor="center", x=0.5
        ),
        font=dict(size=11) # Fonte legível
    )
    return fig

if nav_opcao == "📝 LANÇAR":
    st.subheader(f"Olá, {st.session_state.usuario}")
    data_lanc = st.date_input("Data do Trabalho:", value=HOJE_BR, format="DD/MM/YYYY")
    
    # Inputs organizados em colunas (O Streamlit empilha automaticamente no mobile)
    st.markdown("### 💰 Faturamento")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        v1 = c1.number_input("Urbano (99/Uber)", min_value=0.0, value=None, placeholder="0,00")
        v2 = c2.number_input("BoraAli", min_value=0.0, value=None, placeholder="0,00")
        v3 = c1.number_input("app163", min_value=0.0, value=None, placeholder="0,00")
        v4 = c2.number_input("Outros (Receita)", min_value=0.0, value=None, placeholder="0,00")

    st.markdown("### 💸 Custos")
    with st.container(border=True):
        d1, d2 = st.columns(2)
        cust_e = d1.number_input("Energia", min_value=0.0, value=None, placeholder="0,00")
        cust_m = d2.number_input("Manutenção", min_value=0.0, value=None, placeholder="0,00")
        cust_s = d1.number_input("Seguro", min_value=0.0, value=None, placeholder="0,00")
        cust_o = d2.number_input("Documento/Outros", min_value=0.0, value=None, placeholder="0,00")
        cust_a = d1.number_input("Apps (Assinatura)", min_value=0.0, value=None, placeholder="0,00")
        cust_f = d2.number_input("Alimentação", min_value=0.0, value=None, placeholder="0,00")
    
    st.subheader("🚗 Hodômetro")
    u_km = 0
    if not df_user.empty:
        try:
            df_km_valid = df_user.sort_values(by='Data', ascending=False)
            df_km_valid = df_km_valid[df_km_valid['KM_Final'] > 0]
            if not df_km_valid.empty:
                u_km = int(df_km_valid.iloc[0]['KM_Final'])
        except: u_km = 0

    k1, k2 = st.columns(2)
    k_ini = k1.number_input("KM Inicial", value=u_km)
    k_fim = k2.number_input("KM Final", min_value=0, value=None, placeholder="Digite...")

    if st.button("SALVAR LANÇAMENTO ✅", type="primary"):
        km_f_real = float(k_fim) if k_fim and float(k_fim) > 0 else float(k_ini)
        
        nova = {col: 0 for col in COLUNAS_OFICIAIS}
        nova.update({
            'ID_Unico': str(int(time.time())), 
            'Status': 'Ativo', 
            'Usuario': st.session_state.usuario, 
            'CPF': st.session_state.cpf_usuario, 
            'Data': data_lanc.strftime("%Y-%m-%d"), 
            'Urbano': v(v1), 'Boraali': v(v2), 'app163': v(v3), 'Outros_Receita': v(v4), 
            'Energia': v(cust_e), 'Manuten': v(cust_m), 'Seguro': v(cust_s), 
            'Outros_Custos': v(cust_o), 'Aplicativo': v(cust_a), 'Alimentacao': v(cust_f), 
            'KM_Inicial': float(k_ini), 'KM_Final': km_f_real
        })
        salvar_no_banco(pd.concat([df_total, pd.DataFrame([nova])], ignore_index=True))
        st.success("Salvo com sucesso!"); time.sleep(1); st.rerun()

elif nav_opcao == "📊 DASHBOARD":
    if df_user.empty: st.info("Sem dados.")
    else:
        df_bi = df_user.copy().sort_values('Data', ascending=False)
        
        # FILTROS
        with st.expander("🔍 Filtros (Toque para abrir)", expanded=True):
            f_dia = st.date_input("Dia Específico", value=None, format="DD/MM/YYYY")
            fc1, fc2 = st.columns(2)
            anos = ["Todos"] + sorted(df_bi['Data'].dt.year.dropna().unique().astype(int).astype(str).tolist(), reverse=True)
            sel_ano = fc1.selectbox("Ano", anos)
            meses = ["Todos","Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
            sel_mes = fc2.selectbox("Mês", meses)
        
        # APLICAÇÃO DOS FILTROS
        df_f = df_bi.copy()
        if f_dia: df_f = df_f[df_f['Data'].dt.date == f_dia]
        if sel_ano != "Todos": df_f = df_f[df_f['Data'].dt.year == int(sel_ano)]
        if sel_mes != "Todos": df_f = df_f[df_f['Data'].dt.month == meses.index(sel_mes)]

        # CÁLCULOS
        df_f['Receita'] = df_f[['Urbano','Boraali','app163','Outros_Receita']].sum(axis=1)
        df_f['Custos'] = df_f[['Energia','Manuten','Seguro','Outros_Custos','Aplicativo','Alimentacao']].sum(axis=1)
        df_f['Km rodados'] = (df_f['KM_Final'] - df_f['KM_Inicial']).clip(lower=0)
        df_f['Lucro/prejuizo'] = df_f['Receita'] - df_f['Custos']
        
        # TOTAIS
        tr, tc, tl, tk = df_f['Receita'].sum(), df_f['Custos'].sum(), df_f['Lucro/prejuizo'].sum(), df_f['Km rodados'].sum()
        
        # KPI GRID (3 COLUNAS É APERTADO NO MOBILE, MAS STREAMLIT AJUSTA)
        # Vamos usar CSS para garantir que não quebre
        st.markdown("#### Resumo Financeiro")
        m1, m2, m3 = st.columns(3)
        m1.metric("Faturamento", format_br(tr))
        m2.metric("Lucro Líq.", format_br(tl))
        m3.metric("Custos", format_br(tc))
        
        m4, m5, m6 = st.columns(3)
        m4.metric("KM Total", f"{format_int_br(tk)}")
        m5.metric("Fat/KM", format_br(tr/tk if tk > 0 else 0)) 
        m6.metric("Lucro/KM", format_br(tl/tk if tk > 0 else 0))

        # TABELA (Scroll Horizontal Automático)
        st.divider()
        st.markdown("#### 📋 Histórico")
        df_ex = df_f.copy()
        df_ex['Data'] = df_ex['Data'].dt.strftime('%d/%m') # Encurtado para mobile
        cols_mob = ['Data', 'Receita', 'Custos', 'Lucro/prejuizo', 'Km rodados', 'ID_Unico']
        
        st.dataframe(
            df_ex[cols_mob].rename(columns={'Lucro/prejuizo':'Lucro', 'Km rodados':'KM'}), 
            use_container_width=True, 
            height=300,
            hide_index=True
        )

        with st.expander("🗑️ Excluir lançamento"):
            item_ex = st.selectbox("ID para excluir", df_f['ID_Unico'].tolist())
            if st.button("EXCLUIR"):
                df_total.loc[df_total['ID_Unico'] == item_ex, 'Status'] = 'Lixeira'
                salvar_no_banco(df_total)
                st.rerun()

        # GRÁFICOS (Legends no topo para economizar largura)
        st.divider()
        st.markdown("#### 📈 Gráficos")
        
        df_graph = df_f.sort_values('Data')
        df_graph['Dia'] = df_graph['Data'].dt.strftime('%d/%m')

        # G1
        st.caption("Faturamento por Aplicativo")
        apps_sum = df_f[['Urbano', 'Boraali', 'app163', 'Outros_Receita']].sum().reset_index()
        apps_sum.columns = ['App', 'Total']
        apps_sum = apps_sum[apps_sum['Total'] > 0]
        if not apps_sum.empty:
            fig_apps = px.bar(apps_sum, x='Total', y='App', orientation='h', text_auto=True, color='App')
            st.plotly_chart(mobile_chart_layout(fig_apps), use_container_width=True)

        # G2
        st.caption("Share (%) Diário")
        if not df_graph.empty:
            df_melt = df_graph.melt(id_vars=['Dia'], value_vars=['Urbano', 'Boraali', 'app163', 'Outros_Receita'], var_name='App', value_name='Fat')
            df_melt = df_melt[df_melt['Fat'] > 0]
            dt = df_melt.groupby('Dia')['Fat'].transform('sum')
            df_melt['Pct'] = (df_melt['Fat']/dt*100).fillna(0)
            df_melt['Txt'] = df_melt['Pct'].apply(lambda x: f"{x:.0f}%")
            
            fig_share = px.bar(df_melt, x='Dia', y='Pct', color='App', text='Txt')
            st.plotly_chart(mobile_chart_layout(fig_share), use_container_width=True)

        # G3
        st.caption("Faturamento vs Lucro")
        if not df_graph.empty:
            fig_ev = px.bar(df_graph, x='Dia', y=['Receita', 'Lucro/prejuizo'], barmode='group', text_auto='.2s',
                           color_discrete_map={'Receita': '#28a745', 'Lucro/prejuizo': '#007bff'})
            st.plotly_chart(mobile_chart_layout(fig_ev), use_container_width=True)
            
        # G4
        st.caption("Eficiência (R$/KM)")
        if not df_graph.empty:
            fig_ef = px.line(df_graph, x='Dia', y=['Receita/R$/KM', 'Lucro/km'], markers=True)
            st.plotly_chart(mobile_chart_layout(fig_ef), use_container_width=True)

st.divider()
if st.button("Sair da Conta"): 
    st.session_state.autenticado = False
    st.query_params.clear(); st.rerun()
