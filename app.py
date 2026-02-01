import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime
import time
import pytz
import plotly.express as px

# --- 1. CONFIGURAÇÃO E ESTILO (MOBILE FIRST + ALTO CONTRASTE) ---
st.set_page_config(page_title="BYD Pro", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        /* Limpeza Geral */
        #MainMenu, header, footer, .stDeployButton {display: none !important;}
        [data-testid="stToolbar"], [data-testid="stDecoration"] {display: none !important;}
        
        .block-container {
            padding-top: 0.5rem !important; 
            padding-bottom: 2rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        
        /* Botões de Ação (Salvar/Excluir) */
        div.stButton > button[kind="primary"] {
            background-color: #28a745 !important;
            color: white !important;
            border-radius: 12px !important;
            height: 3.8rem !important;
            font-weight: 800 !important;
            font-size: 1.2rem !important;
            width: 100% !important;
            border: none !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        }
        
        /* --- ESTILO NOVO DAS ABAS (RADIO) --- */
        div[role="radiogroup"] {
            display: flex;
            gap: 10px;
            background: transparent;
            border: none;
            justify-content: center;
        }
        
        div[role="radiogroup"] label {
            flex: 1;
            text-align: center;
            border-radius: 12px;
            padding: 15px 5px;
            font-size: 1rem;
            cursor: pointer;
            border: 1px solid #ddd;
            background-color: #f8f9fa; /* Fundo inativo claro */
            color: #888; /* Texto inativo cinza */
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        /* ESTADO SELECIONADO (BEM VISÍVEL) */
        div[role="radiogroup"] label[data-checked="true"] {
            background-color: #1e7e34 !important; /* Verde Forte */
            color: white !important;
            font-weight: 900 !important;
            border: 2px solid #145523 !important;
            transform: scale(1.03); /* Leve aumento */
            box-shadow: 0 4px 10px rgba(30, 126, 52, 0.4);
        }

        /* KPIs (Cards) */
        [data-testid="stMetric"] {
            background-color: white !important;
            border: 1px solid #e0e0e0 !important;
            padding: 10px !important;
            border-radius: 10px !important;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        [data-testid="stMetricLabel"] { font-size: 0.8rem !important; color: #555; font-weight: bold; }
        [data-testid="stMetricValue"] { font-size: 1.1rem !important; font-weight: 800; color: #000; }
        
        /* Ajuste para Tabelas no Mobile */
        .stDataFrame { width: 100% !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNÇÕES ---
FUSO_BR = pytz.timezone('America/Sao_Paulo')
HOJE_BR = datetime.now(FUSO_BR).date()
COLUNAS_OFICIAIS = ['ID_Unico', 'Status', 'Usuario', 'CPF', 'Data', 'Urbano', 'Boraali', 'app163', 'Outros_Receita', 'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos', 'KM_Inicial', 'KM_Final', 'Detalhes']

def format_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

def format_int_br(valor):
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
        for col in COLUNAS_OFICIAIS:
            if col not in df.columns: df[col] = pd.NA
        return df
    except: return pd.DataFrame(columns=COLUNAS_OFICIAIS)

def salvar_no_banco(df_novo):
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(worksheet=0, data=df_novo)
    st.cache_data.clear()

# --- 3. LOGIN AUTO (CORRIGIDO) ---
params = st.query_params
u_url = params.get("user", "")
c_url = limpar_cpf(params.get("cpf", ""))

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    # 1. Tenta Login Direto via URL
    if u_url and len(c_url) == 11:
        st.session_state.update({'usuario': u_url, 'cpf_usuario': c_url, 'autenticado': True})
        st.rerun()
    else:
        # 2. Mostra tela de Login (Com memória)
        st.title("💎 BYD Pro Login")
        
        # Recupera dados da memória se existirem
        def_user = u_url if u_url else st.session_state.get('last_user', '')
        def_cpf = c_url if c_url else st.session_state.get('last_cpf', '')
        
        n_in = st.text_input("Nome:", value=def_user)
        c_in = st.text_input("CPF:", value=def_cpf, max_chars=11)
        
        if st.button("ENTRAR ✅", type="primary"):
            c_l = limpar_cpf(c_in)
            if n_in and len(c_l) == 11:
                st.session_state.update({'usuario': n_in, 'cpf_usuario': c_l, 'autenticado': True})
                # Salva na memória para reuso
                st.session_state.last_user = n_in
                st.session_state.last_cpf = c_l
                # Força atualização da URL (Para Favoritos)
                st.query_params.update({"user": n_in, "cpf": c_l})
                st.rerun()
            else: st.error("CPF inválido.")
        st.stop()

# --- 4. APP ---
df_total = carregar_dados()
df_user = df_total[(df_total['CPF'] == st.session_state.cpf_usuario) & 
                   (df_total['Status'] != 'Lixeira') & 
                   (df_total['Data'].dt.date <= HOJE_BR)].copy()

# Navegação High Contrast
nav_opcao = st.radio("", ["📝 LANÇAR DADOS", "📊 RELATÓRIOS"], horizontal=True, label_visibility="collapsed")

# Função para travar gráfico (Evita erro e zoom no mobile)
def configurar_grafico(fig):
    fig.update_layout(
        xaxis=dict(fixedrange=True),
        yaxis=dict(fixedrange=True),
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        font=dict(size=12)
    )
    return fig

if nav_opcao == "📝 LANÇAR DADOS":
    st.subheader(f"Olá, {st.session_state.usuario}")
    data_lanc = st.date_input("Data do Trabalho:", value=HOJE_BR, format="DD/MM/YYYY")
    
    st.markdown("### 💰 Receitas")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        v1 = c1.number_input("Urbano (99/Uber)", min_value=0.0, value=None, placeholder="0,00")
        v2 = c2.number_input("BoraAli", min_value=0.0, value=None, placeholder="0,00")
        v3 = c1.number_input("app163", min_value=0.0, value=None, placeholder="0,00")
        v4 = c2.number_input("Outros", min_value=0.0, value=None, placeholder="0,00")

    st.markdown("### 💸 Despesas")
    with st.container(border=True):
        d1, d2 = st.columns(2)
        cust_e = d1.number_input("Energia (Carregamento)", min_value=0.0, value=None, placeholder="0,00")
        cust_m = d2.number_input("Manutenção", min_value=0.0, value=None, placeholder="0,00")
        cust_s = d1.number_input("Seguro", min_value=0.0, value=None, placeholder="0,00")
        cust_o = d2.number_input("Docs/Multas", min_value=0.0, value=None, placeholder="0,00")
        cust_a = d1.number_input("Assinaturas Apps", min_value=0.0, value=None, placeholder="0,00")
        cust_f = d2.number_input("Alimentação", min_value=0.0, value=None, placeholder="0,00")
    
    st.subheader("🚗 Quilometragem")
    u_km = 0
    if not df_user.empty:
        try:
            df_km_valid = df_user.sort_values(by='Data', ascending=False)
            df_km_valid = df_km_valid[df_km_valid['KM_Final'] > 0]
            if not df_km_valid.empty: u_km = int(df_km_valid.iloc[0]['KM_Final'])
        except: u_km = 0

    k1, k2 = st.columns(2)
    k_ini = k1.number_input("KM Inicial", value=u_km)
    k_fim = k2.number_input("KM Final", min_value=0, value=None, placeholder="Ex: 125000")

    if st.button("💾 SALVAR DADOS", type="primary"):
        km_f_real = float(k_fim) if k_fim and float(k_fim) > 0 else float(k_ini)
        nova = {col: 0 for col in COLUNAS_OFICIAIS}
        nova.update({
            'ID_Unico': str(int(time.time())), 'Status': 'Ativo', 
            'Usuario': st.session_state.usuario, 'CPF': st.session_state.cpf_usuario, 
            'Data': data_lanc.strftime("%Y-%m-%d"), 
            'Urbano': v(v1), 'Boraali': v(v2), 'app163': v(v3), 'Outros_Receita': v(v4), 
            'Energia': v(cust_e), 'Manuten': v(cust_m), 'Seguro': v(cust_s), 
            'Outros_Custos': v(cust_o), 'Aplicativo': v(cust_a), 'Alimentacao': v(cust_f), 
            'KM_Inicial': float(k_ini), 'KM_Final': km_f_real
        })
        salvar_no_banco(pd.concat([df_total, pd.DataFrame([nova])], ignore_index=True))
        st.success("Salvo!"); time.sleep(1); st.rerun()

elif nav_opcao == "📊 RELATÓRIOS":
    if df_user.empty: st.info("Sem dados.")
    else:
        df_bi = df_user.copy().sort_values('Data', ascending=False)
        
        # FILTROS
        with st.expander("🔍 Toque para Filtrar Data", expanded=False):
            f_dia = st.date_input("Dia Específico", value=None, format="DD/MM/YYYY")
            fc1, fc2 = st.columns(2)
            
            anos_disp = sorted(df_bi['Data'].dt.year.dropna().unique().astype(int).astype(str).tolist(), reverse=True)
            if str(HOJE_BR.year) not in anos_disp: anos_disp.insert(0, str(HOJE_BR.year))
            
            meses_map = {1:"Janeiro", 2:"Fevereiro", 3:"Março", 4:"Abril", 5:"Maio", 6:"Junho", 7:"Julho", 8:"Agosto", 9:"Setembro", 10:"Outubro", 11:"Novembro", 12:"Dezembro"}
            try: idx_ano = anos_disp.index(str(HOJE_BR.year))
            except: idx_ano = 0
            idx_mes = HOJE_BR.month - 1
            
            sel_ano = fc1.selectbox("Ano", ["Todos"] + anos_disp, index=idx_ano+1 if "Todos" in ["Todos"]+anos_disp else 0)
            sel_mes = fc2.selectbox("Mês", ["Todos"] + list(meses_map.values()), index=idx_mes+1)
        
        # APLICAÇÃO
        df_f = df_bi.copy()
        if f_dia: 
            df_f = df_f[df_f['Data'].dt.date == f_dia]
        else:
            if sel_ano != "Todos": df_f = df_f[df_f['Data'].dt.year == int(sel_ano)]
            if sel_mes != "Todos": 
                m_num = list(meses_map.keys())[list(meses_map.values()).index(sel_mes)]
                df_f = df_f[df_f['Data'].dt.month == m_num]

        # KPI
        df_f['Receita'] = df_f[['Urbano','Boraali','app163','Outros_Receita']].sum(axis=1)
        df_f['Custos'] = df_f[['Energia','Manuten','Seguro','Outros_Custos','Aplicativo','Alimentacao']].sum(axis=1)
        df_f['Km rodados'] = (df_f['KM_Final'] - df_f['KM_Inicial']).clip(lower=0)
        df_f['Lucro'] = df_f['Receita'] - df_f['Custos']
        
        tr, tc, tl, tk = df_f['Receita'].sum(), df_f['Custos'].sum(), df_f['Lucro'].sum(), df_f['Km rodados'].sum()
        
        st.markdown("#### 💵 Resumo")
        m1, m2, m3 = st.columns(3)
        m1.metric("Faturamento", format_br(tr))
        m2.metric("Lucro Líq.", format_br(tl))
        m3.metric("Custos", format_br(tc))
        
        m4, m5, m6 = st.columns(3)
        m4.metric("KM Total", format_int_br(tk))
        m5.metric("Fat/KM", format_br(tr/tk if tk > 0 else 0)) 
        m6.metric("Lucro/KM", format_br(tl/tk if tk > 0 else 0))

        # --- TABELA COMPLETA (ROLAGEM NATIVA) ---
        st.divider()
        st.markdown("#### 📋 Histórico Completo")
        st.caption("Arraste a tabela para ver colunas escondidas ➡️")
        
        df_ex = df_f.copy()
        df_ex['Data'] = df_ex['Data'].dt.strftime('%d/%m/%Y')
        cols_display = [c for c in COLUNAS_OFICIAIS if c in df_ex.columns]
        
        st.dataframe(
            df_ex[cols_display], 
            use_container_width=True, 
            height=400,
            hide_index=True,
            column_config={
                "ID_Unico": st.column_config.TextColumn("ID", width="small"),
                "Data": st.column_config.TextColumn("Data", width="medium"),
                "Detalhes": st.column_config.TextColumn("Obs", width="large")
            }
        )
        
        with st.expander("🗑️ Apagar Lançamento"):
            ids = df_f['ID_Unico'].tolist()
            if ids:
                item_ex = st.selectbox("ID", ids)
                if st.button("Confirmar Exclusão"):
                    df_total.loc[df_total['ID_Unico'] == item_ex, 'Status'] = 'Lixeira'
                    salvar_no_banco(df_total)
                    st.rerun()

        # GRÁFICOS
        st.divider()
        st.markdown("#### 📈 Análise Visual")
        df_graph = df_f.sort_values('Data')
        df_graph['Dia'] = df_graph['Data'].dt.strftime('%d/%m')

        # G1: Pizza
        st.caption("Faturamento por App")
        apps_sum = df_f[['Urbano', 'Boraali', 'app163', 'Outros_Receita']].sum().reset_index()
        apps_sum.columns = ['App', 'Valor']
        apps_sum = apps_sum[apps_sum['Valor'] > 0]
        if not apps_sum.empty:
            fig_pie = px.pie(apps_sum, values='Valor', names='App', hole=0.4)
            st.plotly_chart(configurar_grafico(fig_pie), use_container_width=True, config={'displayModeBar': False})

        # G2: Barras
        st.caption("Faturamento vs Lucro")
        if not df_graph.empty:
            fig_ev = px.bar(df_graph, x='Dia', y=['Receita', 'Lucro'], barmode='group', text_auto='.2s',
                           color_discrete_map={'Receita': '#28a745', 'Lucro': '#007bff'})
            st.plotly_chart(configurar_grafico(fig_ev), use_container_width=True, config={'displayModeBar': False})

        # G3: Eficiência
        st.caption("Eficiência por KM")
        if not df_graph.empty:
            df_graph['Fat_KM'] = df_graph.apply(lambda x: x['Receita']/x['Km rodados'] if x['Km rodados'] > 0 else 0, axis=1)
            df_graph['Lucro_KM'] = df_graph.apply(lambda x: x['Lucro']/x['Km rodados'] if x['Km rodados'] > 0 else 0, axis=1)
            fig_ef = px.bar(df_graph, x='Dia', y=['Fat_KM', 'Lucro_KM'], barmode='group',
                            color_discrete_map={'Fat_KM': '#17a2b8', 'Lucro_KM': '#6c757d'})
            st.plotly_chart(configurar_grafico(fig_ef), use_container_width=True, config={'displayModeBar': False})

st.markdown("<br><br>", unsafe_allow_html=True)
if st.button("Sair (Deslogar)"): 
    st.session_state.autenticado = False
    st.query_params.clear(); st.rerun()
