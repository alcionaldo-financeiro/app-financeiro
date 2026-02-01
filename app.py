import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime
import time
import pytz

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="BYD Pro", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        #MainMenu, header, footer, .stDeployButton {display: none !important; visibility: hidden !important;}
        [data-testid="stToolbar"], [data-testid="stStatusWidget"], [data-testid="stDecoration"] {display: none !important;}
        .block-container {padding-top: 1rem !important;}
        /* Botão Salvar Verde */
        div.stButton > button[kind="primary"] {
            background-color: #28a745 !important; color: white !important;
            border-radius: 12px; height: 3.5em; font-weight: bold; width: 100%;
        }
        /* Estilo para métricas */
        [data-testid="stMetricValue"] { font-size: 1.8rem !important; color: #28a745; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONFIGURAÇÕES DE DADOS ---
COLUNAS_OFICIAIS = [
    'ID_Unico', 'Status', 'Usuario', 'CPF', 'Data', 
    'Urbano', 'Boraali', 'app163', 'Outros_Receita', 
    'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos', 
    'KM_Inicial', 'KM_Final', 'Detalhes'
]
FUSO_BR = pytz.timezone('America/Sao_Paulo')
conn = st.connection("gsheets", type=GSheetsConnection)

def limpar_cpf(t):
    if pd.isna(t): return ""
    texto = re.sub(r'\D', '', str(t).replace('.0', ''))
    return texto.zfill(11) # Garante os 11 dígitos (corrige o zero que some no Excel)

def limpar_valor_monetario(valor):
    if pd.isna(valor) or valor == "" or valor == "-": return 0.0
    if isinstance(valor, str):
        valor = valor.replace('R$', '').replace('.', '').replace(',', '.').strip()
    try: return float(valor)
    except: return 0.0

@st.cache_data(ttl=10)
def carregar_dados():
    try:
        df = conn.read(worksheet=0, ttl=0)
        if df is None or df.empty: return pd.DataFrame(columns=COLUNAS_OFICIAIS)
        # Padroniza CPF e Data
        df['CPF'] = df['CPF'].apply(limpar_cpf)
        cols_num = ['Urbano', 'Boraali', 'app163', 'Outros_Receita', 'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos', 'KM_Inicial', 'KM_Final']
        for c in cols_num: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        return df
    except: return pd.DataFrame(columns=COLUNAS_OFICIAIS)

# --- 3. LOGIN ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False

params = st.query_params
q_nome, q_cpf = params.get("n", ""), limpar_cpf(params.get("c", ""))

if not st.session_state['autenticado']:
    if q_nome and len(q_cpf) == 11:
        st.session_state.update({'usuario': q_nome.lower(), 'cpf_usuario': q_cpf, 'autenticado': True})
        st.rerun()
    st.stop()

# --- 4. FILTRAGEM PRIVADA ---
CPF_LOGADO = st.session_state['cpf_usuario']
df_total = carregar_dados()
# Filtro Rigoroso: Só o dono do CPF vê os dados
df_user = df_total[(df_total['CPF'] == CPF_LOGADO) & (df_total['Status'] != 'Lixeira')].copy()

st.markdown(f"#### Olá, {st.session_state['usuario'].title()} 👤")

aba1, aba2 = st.tabs(["📝 LANÇAMENTOS", "📊 PERFORMANCE E EFICIÊNCIA"])

with aba1:
    # --- IMPORTAÇÃO DISCRETA ---
    with st.expander("⚙️ Opções de Importação (Excel)", expanded=False):
        arq = st.file_uploader("Suba sua planilha antiga", type=["xlsx"])
        if arq and st.button("🚀 Processar Excel"):
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
            df_db = conn.read(worksheet=0, ttl=0)
            conn.update(worksheet=0, data=pd.concat([df_db, pd.DataFrame(novas)], ignore_index=True))
            st.cache_data.clear()
            st.success("Importado!"); time.sleep(1); st.rerun()

    # --- LANÇAMENTO MANUAL ---
    if 'conf' not in st.session_state: st.session_state['conf'] = False
    if not st.session_state['conf']:
        col_r, col_c = st.columns(2)
        with col_r:
            st.markdown("**💰 Receitas (Ganhos)**")
            v_urb = st.number_input("99 / Uber", min_value=0.0); v_bora = st.number_input("BoraAli", min_value=0.0)
            v_163 = st.number_input("App 163", min_value=0.0); v_out_r = st.number_input("Particular", min_value=0.0)
        with col_c:
            st.markdown("**💸 Custos (Gastos)**")
            v_ene = st.number_input("Energia/Comb", min_value=0.0); v_man = st.number_input("Lavagem/Manut", min_value=0.0)
            v_seg = st.number_input("Seguro/Docs", min_value=0.0); v_ali = st.number_input("Alimentação", min_value=0.0)
        
        st.markdown("**🚗 Rodagem**")
        c_k1, c_k2 = st.columns(2)
        u_km = int(df_user['KM_Final'].max()) if not df_user.empty else 0
        k1 = c_k1.number_input("KM Inicial", value=u_km)
        k2 = c_k2.number_input("KM Final", value=u_km)
        obs = st.text_input("Observação:")
        
        if st.button("CONFERIR E SALVAR ➡️", type="primary"):
            st.session_state['tmp'] = {'Urbano':v_urb,'Boraali':v_bora,'app163':v_163,'Outros_Receita':v_out_r,'Energia':v_ene,'Manuten':v_man,'Seguro':v_seg,'Alimentacao':v_ali,'KM_Inicial':k1,'KM_Final':k2, 'Detalhes':obs}
            st.session_state['conf'] = True; st.rerun()
    else:
        d = st.session_state['tmp']
        st.warning("Confirmar dados acima?")
        if st.button("✅ SIM, SALVAR AGORA"):
            nova = {col: 0 for col in COLUNAS_OFICIAIS}; nova.update(d)
            nova.update({'ID_Unico': str(int(time.time())), 'Status': 'Ativo', 'Usuario': st.session_state['usuario'], 'CPF': CPF_LOGADO, 'Data': datetime.now(FUSO_BR).strftime("%Y-%m-%d")})
            df_db = conn.read(worksheet=0, ttl=0)
            conn.update(worksheet=0, data=pd.concat([df_db, pd.DataFrame([nova])], ignore_index=True))
            st.cache_data.clear(); st.session_state['conf'] = False; st.success("Salvo!"); time.sleep(1); st.rerun()

with aba2:
    if df_user.empty:
        st.info("Aguardando dados... Se você já importou, clique no botão de atualizar ou aguarde 10 segundos.")
    else:
        # --- PROCESSAMENTO BI ---
        df_res = df_user.copy().sort_values('Data')
        df_res['Rec_T'] = df_res[['Urbano','Boraali','app163','Outros_Receita']].sum(axis=1)
        df_res['Custo_T'] = df_res[['Energia','Manuten','Seguro','Alimentacao','Outros_Custos']].sum(axis=1)
        df_res['Lucro'] = df_res['Rec_T'] - df_res['Custo_T']
        df_res['KM_Rodado'] = (df_res['KM_Final'] - df_res['KM_Inicial']).clip(lower=0)
        
        # --- MÉTRICAS DE EFICIÊNCIA ---
        total_km = df_res['KM_Rodado'].sum()
        total_lucro = df_res['Lucro'].sum()
        total_receita = df_res['Rec_T'].sum()
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Lucro Líquido", f"R$ {total_lucro:,.2f}")
        m2.metric("KM Total", f"{total_km:,.0f} km")
        m3.metric("R$ por KM", f"R$ {total_receita/total_km:.2f}" if total_km > 0 else "R$ 0,00")
        m4.metric("Custo por KM", f"R$ {df_res['Custo_T'].sum()/total_km:.2f}" if total_km > 0 else "R$ 0,00")

        # --- GRÁFICOS ESTRATÉGICOS ---
        st.markdown("### 📈 Evolução Financeira")
        st.line_chart(df_res.set_index('Data')[['Rec_T', 'Lucro']])
        
        c_g1, c_g2 = st.columns(2)
        with c_g1:
            st.markdown("**🏆 Faturamento por Aplicativo**")
            faturamento_apps = df_res[['Urbano','Boraali','app163','Outros_Receita']].sum()
            st.bar_chart(faturamento_apps)
        
        with c_g2:
            st.markdown("**📉 Distribuição de Gastos**")
            gastos = df_res[['Energia','Manuten','Seguro','Alimentacao']].sum()
            st.bar_chart(gastos)

        st.markdown("### 📋 Histórico Detalhado")
        st.dataframe(df_res[['Data', 'Rec_T', 'Custo_T', 'Lucro', 'KM_Rodado']].sort_values('Data', ascending=False), use_container_width=True)

if st.button("Sair"):
    st.session_state['autenticado'] = False; st.rerun()
