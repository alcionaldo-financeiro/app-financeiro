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
        /* Esconder menus desnecessários */
        #MainMenu, header, footer, .stDeployButton {display: none !important;}
        [data-testid="stToolbar"], [data-testid="stDecoration"] {display: none !important;}
        
        /* Ajuste de margens para Celular */
        .block-container {padding-top: 1rem !important; padding-bottom: 5rem !important;}
        
        /* Botões grandes para o polegar */
        div.stButton > button {
            width: 100% !important;
            height: 3.5rem !important;
            border-radius: 12px !important;
            font-weight: bold !important;
            font-size: 1.1rem !important;
        }
        
        /* Estilo dos Cards de métricas */
        [data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #e1e4e8;
            padding: 10px;
            border-radius: 10px;
            box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
        }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNÇÕES ESSENCIAIS ---
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
    # Remove qualquer coisa que não seja número e força 11 dígitos
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
        # Converter números
        cols_num = ['Urbano', 'Boraali', 'app163', 'Outros_Receita', 'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos', 'KM_Inicial', 'KM_Final']
        for c in cols_num: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        # Converter Data
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        # Anti-duplicidade
        df = df.drop_duplicates(subset=['Data', 'Urbano', 'KM_Final', 'CPF'], keep='last')
        return df
    except: return pd.DataFrame(columns=COLUNAS_OFICIAIS)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. LOGIN AUTOMÁTICO ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
p = st.query_params
q_nome, q_cpf = p.get("n", ""), limpar_cpf(p.get("c", ""))

if not st.session_state['autenticado']:
    if q_nome and len(q_cpf) == 11:
        st.session_state.update({'usuario': q_nome.lower(), 'cpf_usuario': q_cpf, 'autenticado': True})
        st.rerun()
    st.stop()

# --- 4. FILTRAGEM POR USUÁRIO ---
CPF_LOGADO = st.session_state['cpf_usuario']
df_total = carregar_dados()
df_user = df_total[(df_total['CPF'] == CPF_LOGADO) & (df_total['Status'] != 'Lixeira')].copy()

# --- 5. NAVEGAÇÃO ---
aba_lancar, aba_ver = st.tabs(["📝 LANÇAR", "📊 RELATÓRIOS"])

# --- ABA 1: LANÇAMENTOS (OTIMIZADA PARA POLEGAR) ---
with aba_lancar:
    # Importação escondidinha
    with st.expander("⚙️ Importar Excel"):
        arq = st.file_uploader("Suba o arquivo", type=["xlsx"])
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

    st.subheader("Ganhos do Dia")
    v_99 = st.number_input("99 / Uber", min_value=0.0, step=10.0, format="%.2f")
    v_ba = st.number_input("BoraAli", min_value=0.0, step=10.0, format="%.2f")
    v_163 = st.number_input("App 163", min_value=0.0, step=10.0, format="%.2f")
    v_out_r = st.number_input("Outros / Particular", min_value=0.0, step=10.0, format="%.2f")
    
    st.subheader("Custos")
    v_comb = st.number_input("Energia / Combustível", min_value=0.0, step=5.0, format="%.2f")
    v_gastos = st.number_input("Manutenção / Outros", min_value=0.0, step=5.0, format="%.2f")

    st.subheader("KM do Veículo")
    u_km = int(df_user['KM_Final'].max()) if not df_user.empty else 0
    st.info(f"KM Inicial: {u_km}")
    k_fim = st.number_input("KM Final Atual", min_value=0, step=1)
    
    if st.button("SALVAR AGORA ✅", type="primary"):
        if k_fim > 0 and k_fim <= u_km:
            st.error("O KM Final deve ser maior que o inicial!")
        else:
            nova = {col: 0 for col in COLUNAS_OFICIAIS}
            nova.update({
                'Urbano':v_99, 'Boraali':v_ba, 'app163':v_163, 'Outros_Receita':v_out_r,
                'Energia':v_comb, 'Outros_Custos':v_gastos, 'KM_Inicial':u_km, 'KM_Final':k_fim if k_fim > 0 else u_km,
                'ID_Unico': str(int(time.time())), 'Status': 'Ativo', 'Usuario': st.session_state['usuario'], 
                'CPF': CPF_LOGADO, 'Data': datetime.now(FUSO_BR).strftime("%Y-%m-%d")
            })
            df_db = carregar_dados()
            conn.update(worksheet=0, data=pd.concat([df_db, pd.DataFrame([nova])], ignore_index=True))
            st.cache_data.clear(); st.success("Salvo com sucesso!"); time.sleep(1); st.rerun()

# --- ABA 2: PERFORMANCE (CELULAR) ---
with aba_ver:
    if df_user.empty:
        st.info("Nenhum dado encontrado.")
    else:
        # Cálculos
        df_bi = df_user.copy().sort_values('Data', ascending=False)
        df_bi['Rec'] = df_bi[['Urbano','Boraali','app163','Outros_Receita']].sum(axis=1)
        df_bi['Cus'] = df_bi[['Energia','Manuten','Seguro','Aplicativo','Alimentacao','Outros_Custos']].sum(axis=1)
        df_bi['Lucro'] = df_bi['Rec'] - df_bi['Cus']
        df_bi['KMR'] = (df_bi['KM_Final'] - df_bi['KM_Inicial']).clip(lower=0)
        
        # Filtros simplificados para Celular
        st.subheader("🔍 Filtros")
        # Correção do Erro do Ano: Converter para string sem o .0
        lista_anos = ["Todos"] + sorted([str(int(y)) for y in df_bi['Data'].dt.year.dropna().unique()], reverse=True)
        ano_sel = st.selectbox("Escolha o Ano", lista_anos)
        
        meses = ["Todos", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        mes_sel = st.selectbox("Escolha o Mês", meses)
        
        df_f = df_bi.copy()
        if ano_sel != "Todos": df_f = df_f[df_f['Data'].dt.year == int(ano_sel)]
        if mes_sel != "Todos": df_f = df_f[df_f['Data'].dt.month == meses.index(mes_sel)]

        # Métricas em Colunas (No celular elas empilham)
        t_rec, t_luc, t_km = df_f['Rec'].sum(), df_f['Lucro'].sum(), df_f['KMR'].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("Faturamento", format_br(t_rec))
        c1.metric("KM Rodado", f"{t_km:,.0f} km")
        c2.metric("Lucro Líquido", format_br(t_luc))
        c2.metric("Lucro/KM", format_br(t_luc/t_km if t_km > 0 else 0))

        # Tabela dentro de um Expander (para não ocupar a tela toda do celular)
        with st.expander("📋 Ver Tabela de Dados"):
            st.dataframe(df_f, use_container_width=True)

        # Gráficos Verticais
        st.divider()
        st.subheader("📊 Gráficos")
        
        df_f['Data_Txt'] = df_f['Data'].dt.strftime('%d/%m')
        
        st.write("**Ganhos vs Custos por Dia**")
        fig1 = px.bar(df_f, x='Data_Txt', y=['Rec', 'Cus'], barmode='group', color_discrete_map={'Rec':'#28a745', 'Cus':'#dc3545'})
        fig1.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig1, use_container_width=True)

        st.write("**Faturamento por App**")
        app_sums = df_f[['Urbano','Boraali','app163','Outros_Receita']].sum()
        fig2 = px.bar(x=app_sums.index, y=app_sums.values, color_discrete_sequence=['#28a745'])
        st.plotly_chart(fig2, use_container_width=True)

        st.write("**Onde está seu custo?**")
        custos_sums = df_f[['Energia','Manuten','Seguro','Alimentacao','Outros_Custos']].sum()
        fig3 = px.pie(names=custos_sums.index, values=custos_sums.values, hole=0.3)
        st.plotly_chart(fig3, use_container_width=True)

if st.button("Sair / Trocar Usuário"):
    st.session_state['autenticado'] = False
    st.rerun()
