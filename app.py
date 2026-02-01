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

# CSS para garantir Botões Verdes e visual limpo
st.markdown("""
    <style>
        #MainMenu, header, footer, .stDeployButton {display: none !important;}
        [data-testid="stToolbar"], [data-testid="stDecoration"] {display: none !important;}
        .block-container {padding-top: 1rem !important;}
        
        /* Botão Salvar em Verde */
        div.stButton > button[kind="primary"] {
            background-color: #28a745 !important;
            color: white !important;
            border: none !important;
            width: 100% !important;
            height: 3.5rem !important;
            font-weight: bold !important;
        }
        /* Cards de Métricas */
        [data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #e1e4e8;
            padding: 10px;
            border-radius: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNÇÕES DE FORMATAÇÃO E DADOS ---
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
        for c in cols_num: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        df = df.drop_duplicates(subset=['Data', 'Urbano', 'KM_Final', 'CPF'], keep='last')
        return df
    except: return pd.DataFrame(columns=COLUNAS_OFICIAIS)

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

# --- 4. NAVEGAÇÃO ---
aba_lancar, aba_relatorio = st.tabs(["📝 LANÇAR DADOS", "📊 PERFORMANCE E BI"])

with aba_lancar:
    with st.expander("⚙️ Importar Excel Antigo"):
        arq = st.file_uploader("Arquivo .xlsx", type=["xlsx"])
        if arq and st.button("Processar Importação"):
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
            conn = st.connection("gsheets", type=GSheetsConnection)
            conn.update(worksheet=0, data=pd.concat([carregar_dados(), pd.DataFrame(novas)], ignore_index=True))
            st.cache_data.clear(); st.success("Sucesso!"); time.sleep(1); st.rerun()

    # FORMULÁRIO DE LANÇAMENTO
    st.markdown("### 💰 Receitas")
    c1, c2 = st.columns(2)
    v_urb = c1.number_input("99 / Uber", min_value=0.0, format="%.2f")
    v_bora = c2.number_input("BoraAli", min_value=0.0, format="%.2f")
    v_163 = c1.number_input("App 163", min_value=0.0, format="%.2f")
    v_part = c2.number_input("Particular / Outros", min_value=0.0, format="%.2f")

    st.markdown("### 💸 Custos")
    c3, c4 = st.columns(2)
    v_ene = c3.number_input("Energia / Combustível", min_value=0.0, format="%.2f")
    v_man = c4.number_input("Manutenção / Lavagem", min_value=0.0, format="%.2f")
    v_seg = c3.number_input("Seguro / Documentos", min_value=0.0, format="%.2f")
    v_ali = c4.number_input("Alimentação", min_value=0.0, format="%.2f")
    v_app = c3.number_input("Internet / Apps", min_value=0.0, format="%.2f")
    v_out_c = c4.number_input("Outros Custos", min_value=0.0, format="%.2f")

    st.markdown("### 🚗 Rodagem")
    u_km = int(df_user['KM_Final'].max()) if not df_user.empty else 0
    k_ini = st.number_input("KM Inicial", value=u_km) # AGORA EDITÁVEL
    k_fim = st.number_input("KM Final Atual", min_value=0)
    obs = st.text_input("Observação")

    if st.button("SALVAR LANÇAMENTO ✅", type="primary"):
        if k_fim > 0 and k_fim < k_ini:
            st.error("Erro: KM Final não pode ser menor que o Inicial.")
        else:
            nova = {col: 0 for col in COLUNAS_OFICIAIS}
            nova.update({
                'Urbano':v_urb, 'Boraali':v_bora, 'app163':v_163, 'Outros_Receita':v_part,
                'Energia':v_ene, 'Manuten':v_man, 'Seguro':v_seg, 'Alimentacao':v_ali, 'Aplicativo':v_app, 'Outros_Custos':v_out_c,
                'KM_Inicial':k_ini, 'KM_Final':k_fim if k_fim > 0 else k_ini,
                'ID_Unico': str(int(time.time())), 'Status': 'Ativo', 'Usuario': st.session_state['usuario'], 
                'CPF': CPF_LOGADO, 'Data': datetime.now(FUSO_BR).strftime("%Y-%m-%d"), 'Detalhes': obs
            })
            conn = st.connection("gsheets", type=GSheetsConnection)
            conn.update(worksheet=0, data=pd.concat([carregar_dados(), pd.DataFrame([nova])], ignore_index=True))
            st.cache_data.clear(); st.success("Dados Salvos!"); time.sleep(1); st.rerun()

with aba_relatorio:
    if df_user.empty: st.info("Sem dados.")
    else:
        df_bi = df_user.copy().sort_values('Data', ascending=False)
        df_bi['Rec'] = df_bi[['Urbano','Boraali','app163','Outros_Receita']].sum(axis=1)
        df_bi['Cus'] = df_bi[['Energia','Manuten','Seguro','Aplicativo','Alimentacao','Outros_Custos']].sum(axis=1)
        df_bi['Lucro'] = df_bi['Rec'] - df_bi['Cus']
        df_bi['KMR'] = (df_bi['KM_Final'] - df_bi['KM_Inicial']).clip(lower=0)
        
        # FILTROS
        st.subheader("🔍 Filtros")
        f1, f2, f3 = st.columns(3)
        anos = ["Todos"] + sorted([str(int(y)) for y in df_bi['Data'].dt.year.unique()], reverse=True)
        ano_s = f1.selectbox("Ano", anos)
        meses = ["Todos", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        mes_s = f2.selectbox("Mês", meses)
        dia_s = f3.date_input("Dia Específico", value=None)

        df_f = df_bi.copy()
        if ano_s != "Todos": df_f = df_f[df_f['Data'].dt.year == int(ano_s)]
        if mes_s != "Todos": df_f = df_f[df_f['Data'].dt.month == meses.index(mes_s)]
        if dia_s: df_f = df_f[df_f['Data'].dt.date == dia_s]

        # KPIs NO TOPO
        tr, tc, tl, tk = df_f['Rec'].sum(), df_f['Cus'].sum(), df_f['Lucro'].sum(), df_f['KMR'].sum()
        
        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.metric("Faturamento", format_br(tr))
        c_m2.metric("Lucro Líquido", format_br(tl))
        c_m3.metric("KM Rodado", f"{tk:,.0f} km".replace(",", "."))
        
        # NOVOS INDICADORES DE EFICIÊNCIA
        c_e1, c_e2, c_e3 = st.columns(3)
        c_e1.metric("Faturamento / KM", format_br(tr/tk if tk > 0 else 0))
        c_e2.metric("Custo / KM", format_br(tc/tk if tk > 0 else 0))
        c_e3.metric("Lucro / KM", format_br(tl/tk if tk > 0 else 0))

        with st.expander("📋 Ver Tabela Detalhada"):
            st.dataframe(df_f, use_container_width=True)

        # GRÁFICOS
        st.divider()
        df_f['Data_Txt'] = df_f['Data'].dt.strftime('%d/%m/%Y')
        df_g = df_f.groupby('Data_Txt').agg({'Rec':'sum','Cus':'sum','KMR':'sum'}).reset_index()

        st.write("### 💰 Ganhos vs Custos por Dia")
        fig1 = px.bar(df_g, x='Data_Txt', y=['Rec', 'Cus'], barmode='group', 
                      color_discrete_map={'Rec':'#28a745','Cus':'#dc3545'}, text_auto='.2s')
        fig1.update_layout(xaxis_title="Data", yaxis_title="Reais (R$)", legend_title="Legenda")
        st.plotly_chart(fig1, use_container_width=True)

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.write("### 🏆 Top Apps")
            app_sum = df_f[['Urbano','Boraali','app163','Outros_Receita']].sum()
            fig2 = px.bar(x=app_sum.index, y=app_sum.values, text_auto='.2s', color_discrete_sequence=['#28a745'])
            st.plotly_chart(fig2, use_container_width=True)

        with col_g2:
            st.write("### 🍕 Onde está o Custo?")
            custo_sum = df_f[['Energia','Manuten','Seguro','Aplicativo','Alimentacao','Outros_Custos']].sum()
            fig3 = px.pie(names=custo_sum.index, values=custo_sum.values, hole=0.4)
            st.plotly_chart(fig3, use_container_width=True)

        st.write("### 🚗 KM Rodados por Dia")
        fig4 = px.bar(df_g, x='Data_Txt', y='KMR', text_auto='.0f', color_discrete_sequence=['#007bff'])
        st.plotly_chart(fig4, use_container_width=True)

if st.button("Sair / Trocar Usuário"):
    st.session_state['autenticado'] = False
    st.rerun()
