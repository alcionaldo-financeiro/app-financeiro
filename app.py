import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime, timedelta
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
        .small-font { font-size:12px !important; }
        .stMetric { background-color: #f8f9fa; padding: 10px; border-radius: 10px; border: 1px solid #eee; }
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
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def limpar_cpf(t):
    texto = re.sub(r'\D', '', str(t).replace('.0', ''))
    return texto.zfill(11)

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
        df['CPF'] = df['CPF'].apply(limpar_cpf)
        cols_num = ['Urbano', 'Boraali', 'app163', 'Outros_Receita', 'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos', 'KM_Inicial', 'KM_Final']
        for c in cols_num: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
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

# --- 4. DADOS DO USUÁRIO ---
CPF_LOGADO = st.session_state['cpf_usuario']
df_total = carregar_dados()
df_user = df_total[(df_total['CPF'] == CPF_LOGADO) & (df_total['Status'] != 'Lixeira')].copy()

# --- TELA PRINCIPAL ---
st.markdown(f"**Motorista:** {st.session_state['usuario'].title()} | **CPF:** {CPF_LOGADO}")

aba1, aba2 = st.tabs(["📝 LANÇAR DADOS", "📊 PERFORMANCE & BI"])

with aba1:
    # Importação muito discreta
    with st.expander("⚙️", expanded=False):
        arq = st.file_uploader("Importar Planilha Excel", type=["xlsx"])
        if arq and st.button("Executar Importação"):
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
            st.cache_data.clear(); st.success("OK!"); time.sleep(1); st.rerun()

    # Formulário
    col_r, col_c = st.columns(2)
    with col_r:
        st.subheader("Ganhos")
        v_urb = st.number_input("99 / Uber (R$)", min_value=0.0, step=10.0)
        v_bora = st.number_input("BoraAli (R$)", min_value=0.0, step=10.0)
        v_163 = st.number_input("App 163 (R$)", min_value=0.0, step=10.0)
        v_out_r = st.number_input("Particular (R$)", min_value=0.0, step=10.0)
    with col_c:
        st.subheader("Custos")
        v_ene = st.number_input("Energia / Comb (R$)", min_value=0.0, step=5.0)
        v_man = st.number_input("Manutenção (R$)", min_value=0.0, step=5.0)
        v_seg = st.number_input("Seguro / Doc (R$)", min_value=0.0, step=5.0)
        v_ali = st.number_input("Alimentação (R$)", min_value=0.0, step=5.0)

    st.subheader("Rodagem")
    c_k1, c_k2 = st.columns(2)
    u_km = int(df_user['KM_Final'].max()) if not df_user.empty else 0
    k1 = c_k1.number_input("KM Inicial (Inalterável)", value=u_km, disabled=True)
    k2 = c_k2.number_input("KM Final (Digite o atual)", value=0)
    obs = st.text_input("Observação:")

    if st.button("CONFERIR E SALVAR LANÇAMENTO ➡️", type="primary"):
        if k2 <= k1 and k2 != 0: st.error("KM Final deve ser maior que Inicial.")
        else:
            nova = {col: 0 for col in COLUNAS_OFICIAIS}
            nova.update({'Urbano':v_urb,'Boraali':v_bora,'app163':v_163,'Outros_Receita':v_out_r,'Energia':v_ene,'Manuten':v_man,'Seguro':v_seg,'Alimentacao':v_ali,'KM_Inicial':k1,'KM_Final':k2 if k2 > 0 else k1,'ID_Unico': str(int(time.time())), 'Status': 'Ativo', 'Usuario': st.session_state['usuario'], 'CPF': CPF_LOGADO, 'Data': datetime.now(FUSO_BR).strftime("%Y-%m-%d"), 'Detalhes': obs})
            conn.update(worksheet=0, data=pd.concat([carregar_dados(), pd.DataFrame([nova])], ignore_index=True))
            st.cache_data.clear(); st.success("Salvo com sucesso!"); time.sleep(1); st.rerun()

with aba2:
    if df_user.empty: st.info("Sem dados disponíveis.")
    else:
        # --- PROCESSAMENTO DE DADOS ---
        df_bi = df_user.copy().sort_values('Data', ascending=False)
        df_bi['Rec_T'] = df_bi[['Urbano','Boraali','app163','Outros_Receita']].sum(axis=1)
        df_bi['Custo_T'] = df_bi[['Energia','Manuten','Seguro','Aplicativo','Alimentacao','Outros_Custos']].sum(axis=1)
        df_bi['Lucro'] = df_bi['Rec_T'] - df_bi['Custo_T']
        df_bi['KM_Rodado'] = (df_bi['KM_Final'] - df_bi['KM_Inicial']).clip(lower=0)
        
        # 1. TABELA COMPLETA (NO TOPO)
        st.subheader("📋 Histórico Completo")
        st.dataframe(df_bi, use_container_width=True, hide_index=True)

        # 2. FILTRO DE VISÃO
        st.divider()
        visao = st.radio("Filtrar gráficos por:", ["Dia", "Mês", "Ano"], horizontal=True)
        
        df_resumo = df_bi.copy()
        if visao == "Mês": df_resumo['Data_Ref'] = df_resumo['Data'].dt.to_period('M').astype(str)
        elif visao == "Ano": df_resumo['Data_Ref'] = df_resumo['Data'].dt.to_period('Y').astype(str)
        else: df_resumo['Data_Ref'] = df_resumo['Data'].dt.strftime('%d/%m/%Y')

        res_agrupado = df_resumo.groupby('Data_Ref').agg({
            'Rec_T':'sum', 'Custo_T':'sum', 'Lucro':'sum', 'KM_Rodado':'sum',
            'Urbano':'sum', 'Boraali':'sum', 'app163':'sum', 'Outros_Receita':'sum',
            'Energia':'sum', 'Manuten':'sum', 'Seguro':'sum', 'Alimentacao':'sum'
        }).reset_index().sort_values('Data_Ref')

        # 3. MÉTRICAS GERAIS
        m1, m2, m3, m4 = st.columns(4)
        total_km = res_agrupado['KM_Rodado'].sum()
        m1.metric("Faturamento Total", format_br(res_agrupado['Rec_T'].sum()))
        m2.metric("Lucro Líquido", format_br(res_agrupado['Lucro'].sum()))
        m3.metric("KM Total", f"{total_km:,.0f} km".replace(",", "."))
        m4.metric("Lucro por KM", format_br(res_agrupado['Lucro'].sum()/total_km if total_km > 0 else 0))

        # 4. GRÁFICOS DE PERFORMANCE
        c1, c2 = st.columns(2)
        with c1:
            st.write("**💰 Faturamento vs Custos**")
            fig_rec = px.bar(res_agrupado, x='Data_Ref', y=['Rec_T', 'Custo_T'], barmode='group', labels={'value':'Valor (R$)', 'Data_Ref': visao})
            st.plotly_chart(fig_rec, use_container_width=True)
            
            st.write("**🏆 Faturamento por Aplicativo**")
            fig_apps = px.bar(res_agrupado, x='Data_Ref', y=['Urbano','Boraali','app163','Outros_Receita'], labels={'value':'R$'})
            st.plotly_chart(fig_apps, use_container_width=True)

        with c2:
            st.write("**📉 Lucro por KM Rodado**")
            res_agrupado['L_KM'] = res_agrupado['Lucro'] / res_agrupado['KM_Rodado']
            fig_lkm = px.bar(res_agrupado, x='Data_Ref', y='L_KM', color_discrete_sequence=['#28a745'])
            st.plotly_chart(fig_lkm, use_container_width=True)

            st.write("**🍕 Impacto dos Custos**")
            custos_pie = df_bi[['Energia','Manuten','Seguro','Alimentacao']].sum()
            fig_pie = px.pie(values=custos_pie.values, names=custos_pie.index, hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)

        # 5. DIAS TRABALHADOS
        st.divider()
        dias_com_dados = df_bi['Data'].dt.date.nunique()
        data_min, data_max = df_bi['Data'].min(), df_bi['Data'].max()
        total_dias_periodo = (data_max - data_min).days + 1
        
        c_d1, c_d2, c_d3 = st.columns(3)
        c_d1.info(f"📅 Período Analisado: {total_dias_periodo} dias")
        c_d2.success(f"🚗 Dias Trabalhados: {dias_com_dados}")
        c_d3.error(f"🏠 Dias Parados: {max(0, total_dias_periodo - dias_com_dados)}")

if st.button("Sair"):
    st.session_state['autenticado'] = False; st.rerun()
