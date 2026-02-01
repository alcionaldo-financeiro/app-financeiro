import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime
import time
import pytz
import plotly.express as px

# --- 1. CONFIGURAÇÃO E ESTILO (DESIGN PREMIUM) ---
st.set_page_config(page_title="BYD Pro", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        /* --- LIMPEZA GERAL --- */
        #MainMenu, header, footer, .stDeployButton {display: none !important;}
        [data-testid="stToolbar"], [data-testid="stDecoration"] {display: none !important;}
        
        .block-container {
            padding-top: 1rem !important; 
            padding-bottom: 2rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }
        
        /* --- BOTÃO PRINCIPAL --- */
        div.stButton > button[kind="primary"] {
            background: linear-gradient(45deg, #28a745, #218838) !important;
            color: white !important;
            border-radius: 15px !important;
            height: 3.8rem !important;
            font-weight: 700 !important;
            font-size: 1.1rem !important;
            width: 100% !important;
            border: none !important;
            box-shadow: 0 4px 10px rgba(40, 167, 69, 0.3);
            transition: all 0.3s ease;
        }
        div.stButton > button[kind="primary"]:active {
            transform: scale(0.98);
        }

        /* --- ABAS DE NAVEGAÇÃO --- */
        div[role="radiogroup"] {
            display: flex;
            gap: 8px;
            background: transparent;
            border: none;
            justify-content: center;
            margin-bottom: 15px;
        }
        div[role="radiogroup"] label {
            flex: 1;
            text-align: center;
            border-radius: 12px;
            padding: 12px 5px;
            font-size: 0.9rem;
            cursor: pointer;
            border: 1px solid #e0e0e0;
            background-color: #ffffff;
            color: #666;
            font-weight: 600;
            box-shadow: 0 2px 5px rgba(0,0,0,0.03);
        }
        div[role="radiogroup"] label[data-checked="true"] {
            background-color: #1e2a38 !important; /* Dark Navy */
            color: white !important;
            border: 1px solid #1e2a38 !important;
            font-weight: 800 !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        /* --- CARDS KPI --- */
        [data-testid="stMetric"] {
            background-color: #f8f9fa !important;
            border: 1px solid #eee !important;
            padding: 10px !important;
            border-radius: 12px !important;
            text-align: center;
        }
        [data-testid="stMetricLabel"] { font-size: 0.75rem !important; color: #666; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
        [data-testid="stMetricValue"] { font-size: 1.1rem !important; font-weight: 800; color: #111; }
        
        /* --- ESTILO DE LOGIN --- */
        .login-header {
            text-align: center;
            padding: 2rem 0;
            animation: fadeIn 1s ease-in;
        }
        .login-logo { font-size: 4rem; margin-bottom: 0.5rem; }
        .login-title { font-size: 2rem; font-weight: 800; color: #1e2a38; margin: 0; }
        .login-subtitle { font-size: 1rem; color: #888; font-weight: 400; margin-top: 5px; }
        
        /* --- AJUSTES TABELA --- */
        .stDataFrame { width: 100% !important; }
        
        @keyframes fadeIn {
            0% { opacity: 0; transform: translateY(20px); }
            100% { opacity: 1; transform: translateY(0); }
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

# --- 3. TELA DE LOGIN ---
params = st.query_params
u_url = params.get("user", "")
c_url = limpar_cpf(params.get("cpf", ""))

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    if u_url and len(c_url) == 11:
        st.session_state.update({'usuario': u_url, 'cpf_usuario': c_url, 'autenticado': True})
        st.rerun()
    else:
        st.markdown("""
            <div class="login-header">
                <div class="login-logo">💎</div>
                <h1 class="login-title">BYD Pro</h1>
                <p class="login-subtitle">Gestão Financeira de Alta Performance</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            n_in = st.text_input("Nome do Motorista", placeholder="Como você quer ser chamado?")
            c_in = st.text_input("CPF de Acesso", placeholder="Apenas números", max_chars=11)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("ACESSAR SISTEMA", type="primary"):
                c_l = limpar_cpf(c_in)
                if n_in and len(c_l) == 11:
                    st.session_state.update({'usuario': n_in, 'cpf_usuario': c_l, 'autenticado': True})
                    st.query_params.update({"user": n_in, "cpf": c_l})
                    st.rerun()
                else:
                    st.toast("⚠️ CPF inválido ou Nome vazio.", icon="🚫")
        st.stop()

# --- 4. APLICAÇÃO ---
df_total = carregar_dados()
# Carrega TUDO do usuário (sem filtro de data para não sumir dados futuros/recentes)
df_user = df_total[(df_total['CPF'] == st.session_state.cpf_usuario) & 
                   (df_total['Status'] != 'Lixeira')].copy()

nav_opcao = st.radio("", ["📝 LANÇAR", "📊 DASHBOARD"], horizontal=True, label_visibility="collapsed")

def configurar_grafico(fig):
    fig.update_layout(
        xaxis=dict(fixedrange=True),
        yaxis=dict(fixedrange=True),
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        font=dict(size=12),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

if nav_opcao == "📝 LANÇAR":
    st.markdown(f"<h3 style='margin-bottom: 5px;'>Olá, {st.session_state.usuario} 👋</h3>", unsafe_allow_html=True)
    st.caption(f"Data de hoje: {HOJE_BR.strftime('%d/%m/%Y')}")
    
    data_lanc = st.date_input("Data do Lançamento:", value=HOJE_BR, format="DD/MM/YYYY", label_visibility="collapsed")
    
    st.markdown("##### 💰 Ganhos do Dia")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        v1 = c1.number_input("Urbano (99/Uber)", min_value=0.0, value=None, placeholder="R$ 0,00")
        v2 = c2.number_input("BoraAli", min_value=0.0, value=None, placeholder="R$ 0,00")
        v3 = c1.number_input("app163", min_value=0.0, value=None, placeholder="R$ 0,00")
        v4 = c2.number_input("Outros (Receita)", min_value=0.0, value=None, placeholder="R$ 0,00")

    st.markdown("##### 💸 Custos do Dia")
    with st.container(border=True):
        d1, d2 = st.columns(2)
        # Campos renomeados conforme solicitado
        cust_e = d1.number_input("Combustível/Energia", min_value=0.0, value=None, placeholder="R$ 0,00")
        cust_m = d2.number_input("Manutenção", min_value=0.0, value=None, placeholder="R$ 0,00")
        cust_s = d1.number_input("Seguro", min_value=0.0, value=None, placeholder="R$ 0,00")
        cust_o = d2.number_input("Documentos/Multas", min_value=0.0, value=None, placeholder="R$ 0,00")
        cust_a = d1.number_input("Mensalidades Apps", min_value=0.0, value=None, placeholder="R$ 0,00")
        # "Outros" mapeado para Alimentacao (Coluna original) para manter compatibilidade
        cust_f = d2.number_input("Outros", min_value=0.0, value=None, placeholder="R$ 0,00")
    
    st.markdown("##### 🚗 Hodômetro")
    u_km = 0
    # Lógica Blindada para KM: Busca no DF completo, ordenado por data
    if not df_user.empty:
        try:
            df_km_valid = df_user.sort_values(by='Data', ascending=False)
            df_km_valid = df_km_valid[df_km_valid['KM_Final'] > 0]
            if not df_km_valid.empty: u_km = int(df_km_valid.iloc[0]['KM_Final'])
        except: u_km = 0

    with st.container(border=True):
        k1, k2 = st.columns(2)
        k_ini = k1.number_input("KM Inicial", value=u_km)
        k_fim = k2.number_input("KM Final", min_value=0, value=None, placeholder="Ex: 125800")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("SALVAR REGISTRO", type="primary"):
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
        st.success("Lançamento salvo com sucesso!"); time.sleep(1); st.rerun()

elif nav_opcao == "📊 DASHBOARD":
    # Verifica DF completo (sem filtro de data <= hoje)
    if df_user.empty: st.info("Nenhum dado lançado ainda.")
    else:
        df_bi = df_user.copy().sort_values('Data', ascending=False)
        
        # Smart Filter: Pega a última data registrada no banco
        if not df_bi.empty:
            ultima_data_registrada = df_bi['Data'].max()
            ano_padrao = ultima_data_registrada.year
            mes_padrao = ultima_data_registrada.month
        else:
            ano_padrao = HOJE_BR.year
            mes_padrao = HOJE_BR.month
            
        with st.expander("📅 Filtrar Período", expanded=False):
            f_dia = st.date_input("Dia Específico", value=None, format="DD/MM/YYYY")
            fc1, fc2 = st.columns(2)
            
            anos_disp = sorted(df_bi['Data'].dt.year.dropna().unique().astype(int).astype(str).tolist(), reverse=True)
            if str(HOJE_BR.year) not in anos_disp: anos_disp.insert(0, str(HOJE_BR.year))
            
            meses_map = {1:"Janeiro", 2:"Fevereiro", 3:"Março", 4:"Abril", 5:"Maio", 6:"Junho", 7:"Julho", 8:"Agosto", 9:"Setembro", 10:"Outubro", 11:"Novembro", 12:"Dezembro"}
            try: idx_ano = anos_disp.index(str(ano_padrao))
            except: idx_ano = 0
            idx_mes = mes_padrao - 1
            
            sel_ano = fc1.selectbox("Ano", ["Todos"] + anos_disp, index=idx_ano+1 if "Todos" in ["Todos"]+anos_disp else 0)
            sel_mes = fc2.selectbox("Mês", ["Todos"] + list(meses_map.values()), index=idx_mes+1)
        
        # Aplica Filtros
        df_f = df_bi.copy()
        if f_dia: 
            df_f = df_f[df_f['Data'].dt.date == f_dia]
        else:
            if sel_ano != "Todos": df_f = df_f[df_f['Data'].dt.year == int(sel_ano)]
            if sel_mes != "Todos": 
                m_num = list(meses_map.keys())[list(meses_map.values()).index(sel_mes)]
                df_f = df_f[df_f['Data'].dt.month == m_num]

        # Cálculos
        df_f['Receita'] = df_f[['Urbano','Boraali','app163','Outros_Receita']].sum(axis=1)
        df_f['Custos'] = df_f[['Energia','Manuten','Seguro','Outros_Custos','Aplicativo','Alimentacao']].sum(axis=1)
        df_f['Km rodados'] = (df_f['KM_Final'] - df_f['KM_Inicial']).clip(lower=0)
        df_f['Lucro'] = df_f['Receita'] - df_f['Custos']
        tr, tc, tl, tk = df_f['Receita'].sum(), df_f['Custos'].sum(), df_f['Lucro'].sum(), df_f['Km rodados'].sum()
        
        st.markdown("#### 💵 Performance Financeira")
        m1, m2, m3 = st.columns(3)
        m1.metric("Faturamento", format_br(tr))
        m2.metric("Lucro Líquido", format_br(tl))
        m3.metric("Custos", format_br(tc))
        
        m4, m5, m6 = st.columns(3)
        m4.metric("KM Total", format_int_br(tk))
        m5.metric("Fat/KM", format_br(tr/tk if tk > 0 else 0)) 
        m6.metric("Lucro/KM", format_br(tl/tk if tk > 0 else 0))

        st.divider()
        st.markdown("#### 📋 Extrato Completo")
        st.caption("↔️ Arraste para o lado para ver mais detalhes")
        
        df_ex = df_f.copy()
        df_ex['Data'] = df_ex['Data'].dt.strftime('%d/%m/%Y')
        cols_display = [c for c in COLUNAS_OFICIAIS if c in df_ex.columns and c != 'CPF']
        
        st.dataframe(
            df_ex[cols_display], 
            use_container_width=True, 
            height=350,
            hide_index=True,
            column_config={
                "ID_Unico": st.column_config.TextColumn("ID", width="small"),
                "Data": st.column_config.TextColumn("Data", width="medium"),
                "Detalhes": st.column_config.TextColumn("Obs", width="large"),
                "Usuario": st.column_config.TextColumn("Motorista", width="medium")
            }
        )
        
        with st.expander("🗑️ Excluir um Registro"):
            ids = df_f['ID_Unico'].tolist()
            if ids:
                item_ex = st.selectbox("Selecione o ID", ids)
                if st.button("Confirmar Exclusão"):
                    df_total.loc[df_total['ID_Unico'] == item_ex, 'Status'] = 'Lixeira'
                    salvar_no_banco(df_total)
                    st.rerun()

        st.divider()
        st.markdown("#### 📈 Visão Gráfica")
        df_graph = df_f.sort_values('Data')
        df_graph['Dia'] = df_graph['Data'].dt.strftime('%d/%m')

        st.caption("Faturamento por App")
        apps_sum = df_f[['Urbano', 'Boraali', 'app163', 'Outros_Receita']].sum().reset_index()
        apps_sum.columns = ['App', 'Valor']
        apps_sum = apps_sum[apps_sum['Valor'] > 0]
        if not apps_sum.empty:
            fig_pie = px.pie(apps_sum, values='Valor', names='App', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(configurar_grafico(fig_pie), use_container_width=True, config={'displayModeBar': False})

        st.caption("Comparativo: Faturamento x Lucro")
        if not df_graph.empty:
            fig_ev = px.bar(df_graph, x='Dia', y=['Receita', 'Lucro'], barmode='group', text_auto='.2s',
                           color_discrete_map={'Receita': '#28a745', 'Lucro': '#1e2a38'})
            st.plotly_chart(configurar_grafico(fig_ev), use_container_width=True, config={'displayModeBar': False})

        st.caption("Eficiência por KM")
        if not df_graph.empty:
            df_graph['Fat_KM'] = df_graph.apply(lambda x: x['Receita']/x['Km rodados'] if x['Km rodados'] > 0 else 0, axis=1)
            df_graph['Lucro_KM'] = df_graph.apply(lambda x: x['Lucro']/x['Km rodados'] if x['Km rodados'] > 0 else 0, axis=1)
            fig_ef = px.bar(df_graph, x='Dia', y=['Fat_KM', 'Lucro_KM'], barmode='group',
                            color_discrete_map={'Fat_KM': '#17a2b8', 'Lucro_KM': '#6c757d'})
            st.plotly_chart(configurar_grafico(fig_ef), use_container_width=True, config={'displayModeBar': False})

st.markdown("<br><div style='text-align:center; color:#ccc;'>BYD Pro Mobile v12</div><br>", unsafe_allow_html=True)
if st.button("Sair"): 
    st.session_state.autenticado = False
    st.query_params.clear(); st.rerun()
