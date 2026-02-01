import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime
import time
import pytz

# --- 1. CONFIGURAÇÃO E CSS ---
st.set_page_config(page_title="BYD Pro", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        #MainMenu, header, footer, .stDeployButton {display: none !important; visibility: hidden !important;}
        [data-testid="stToolbar"], [data-testid="stStatusWidget"], [data-testid="stDecoration"] {display: none !important;}
        .block-container {padding-top: 1rem !important;}
        div.stButton > button[kind="primary"] {
            background-color: #28a745 !important; color: white !important;
            border-radius: 12px; height: 3.5em; font-weight: bold; width: 100%;
        }
    </style>
    <meta name="google" content="notranslate">
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

def limpar_texto(t): return re.sub(r'\D', '', str(t))

def limpar_valor_monetario(valor):
    if pd.isna(valor) or valor == "" or valor == "-": return 0.0
    if isinstance(valor, str):
        valor = valor.replace('R$', '').replace('.', '').replace(',', '.').strip()
    try: return float(valor)
    except: return 0.0

@st.cache_data(ttl=60)
def carregar_dados_seguros():
    try:
        df = conn.read(worksheet=0, ttl=0)
        if df is None or df.empty: return pd.DataFrame(columns=COLUNAS_OFICIAIS)
        df['CPF'] = df['CPF'].apply(limpar_texto)
        cols_num = ['Urbano', 'Boraali', 'app163', 'Outros_Receita', 'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos', 'KM_Inicial', 'KM_Final']
        for c in cols_num: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        return df
    except: return pd.DataFrame(columns=COLUNAS_OFICIAIS)

# --- 3. LOGIN ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False

params = st.query_params
q_nome, q_cpf = params.get("n", ""), params.get("c", "")

if not st.session_state['autenticado']:
    st.title("💎 BYD Pro")
    n_in = st.text_input("Nome Completo:", value=q_nome)
    c_in = st.text_input("CPF (Apenas números):", value=q_cpf, max_chars=11)

    if st.button("ACESSAR SISTEMA 🚀", type="primary"):
        c_limpo = limpar_texto(c_in)
        if len(c_limpo) == 11 and n_in:
            st.session_state.update({'usuario': n_in.lower(), 'cpf_usuario': c_limpo, 'autenticado': True})
            st.rerun()
        else: st.error("⚠️ Verifique os dados.")
    st.stop()

# --- 4. SISTEMA LOGADO ---
CPF = st.session_state['cpf_usuario']
df_total = carregar_dados_seguros()
df_user = df_total[(df_total['CPF'] == CPF) & (df_total['Status'] != 'Lixeira')].copy()

st.markdown(f"#### Olá, {st.session_state['usuario'].title()} 👤")

aba1, aba2 = st.tabs(["📝 LANÇAR / IMPORTAR", "📊 DASHBOARD & RELATÓRIOS"])

with aba1:
    m_manual, m_auto = st.tabs(["Manual", "🚀 Importar Excel"])

    with m_manual:
        if 'conf' not in st.session_state: st.session_state['conf'] = False
        if not st.session_state['conf']:
            with st.expander("💰 FATURAMENTO", expanded=True):
                c1, c2 = st.columns(2); v_urb = c1.number_input("Urbano / 99", min_value=0.0); v_bora = c2.number_input("BoraAli", min_value=0.0)
                v_163 = c1.number_input("App 163", min_value=0.0); v_out_r = c2.number_input("Particular / Outros", min_value=0.0)
            with st.expander("💸 GASTOS", expanded=False):
                c3, c4 = st.columns(2); v_ene = c3.number_input("Energia", min_value=0.0); v_ali = c4.number_input("Alimentação", min_value=0.0)
                v_man = c3.number_input("Manutenção", min_value=0.0); v_seg = c4.number_input("Seguro/Documento", min_value=0.0)
                v_int = c3.number_input("Internet/Apps", min_value=0.0); v_out_c = c4.number_input("Outros Custos", min_value=0.0)
            u_km = int(df_user['KM_Final'].max()) if not df_user.empty else 0
            k1 = st.number_input("KM Inicial", value=u_km); k2 = st.number_input("KM Final", value=u_km); obs = st.text_input("Obs:")
            if st.button("CONFERIR ➡️", type="primary"):
                st.session_state['tmp'] = {'Urbano':v_urb,'Boraali':v_bora,'app163':v_163,'Outros_Receita':v_out_r,'Energia':v_ene,'Alimentacao':v_ali,'Manuten':v_man,'Seguro':v_seg,'Aplicativo':v_int,'Outros_Custos':v_out_c,'KM_Inicial':k1,'KM_Final':k2, 'Detalhes':obs}
                st.session_state['conf'] = True; st.rerun()
        else:
            d = st.session_state['tmp']
            st.subheader("Confirmar Lançamento?"); st.write(d)
            if st.button("✅ SALVAR AGORA"):
                nova = {col: 0 for col in COLUNAS_OFICIAIS}; nova.update(d)
                nova.update({'ID_Unico': str(int(time.time())), 'Status': 'Ativo', 'Usuario': st.session_state['usuario'], 'CPF': CPF, 'Data': datetime.now(FUSO_BR).strftime("%Y-%m-%d")})
                df_db = conn.read(worksheet=0, ttl=0); conn.update(worksheet=0, data=pd.concat([df_db, pd.DataFrame([nova])], ignore_index=True))
                st.success("Salvo!"); time.sleep(1); st.session_state['conf'] = False; st.rerun()

    with m_auto:
        st.subheader("Importação Automática de Planilha")
        st.write("Suba o arquivo exatamente como o da sua imagem.")
        arquivo = st.file_uploader("Selecione o arquivo Excel", type=["xlsx"])
        
        if arquivo:
            try:
                # Lendo o Excel (Ajustado para lidar com as duas colunas 'Outros')
                df_ex = pd.read_excel(arquivo)
                
                # O pandas renomeia colunas duplicadas. 'Outros' (receita) e 'Outros.1' (custo)
                # Vamos renomear para garantir o mapeamento
                cols_presentes = list(df_ex.columns)
                mapping = {
                    'Data': 'Data',
                    'Urbano': 'Urbano',
                    'Boraali': 'Boraali',
                    'app163': 'app163',
                    'Outros': 'Outros_Receita', # O primeiro Outros (Receita)
                    'Energia': 'Energia',
                    'Manuten': 'Manuten',
                    'Seguro': 'Seguro',
                    'Documento': 'Outros_Custos', # Mapeei Documento como Outros Custos
                    'Aplicativo': 'Aplicativo',
                    'KM Inicial': 'KM_Inicial',
                    'KM final': 'KM_Final'
                }
                
                if st.button("🚀 PROCESSAR E LANÇAR NO SISTEMA"):
                    with st.spinner("Lendo dados..."):
                        lista_novas_linhas = []
                        for i, row in df_ex.iterrows():
                            nova_linha = {col: 0 for col in COLUNAS_OFICIAIS}
                            
                            # Mapeamento Dinâmico
                            for excel_col, app_col in mapping.items():
                                if excel_col in row:
                                    valor = row[excel_col]
                                    if 'KM' in excel_col:
                                        nova_linha[app_col] = float(valor) if pd.notna(valor) else 0
                                    elif excel_col == 'Data':
                                        try: nova_linha[app_col] = pd.to_datetime(valor).strftime("%Y-%m-%d")
                                        except: nova_linha[app_col] = datetime.now(FUSO_BR).strftime("%Y-%m-%d")
                                    else:
                                        nova_linha[app_col] = limpar_valor_monetario(valor)
                            
                            # Metadados fixos solicitados
                            nova_linha.update({
                                'ID_Unico': str(int(time.time()) + i),
                                'Status': 'Ativo',
                                'Usuario': 'alcionaldo silva',
                                'CPF': '02111249319',
                                'Detalhes': 'Importado via Excel'
                            })
                            lista_novas_linhas.append(nova_linha)
                        
                        df_importacao = pd.DataFrame(lista_novas_linhas)
                        df_db_atual = conn.read(worksheet=0, ttl=0)
                        df_final = pd.concat([df_db_atual, df_importacao], ignore_index=True)
                        conn.update(worksheet=0, data=df_final)
                        
                        st.success(f"✅ {len(df_importacao)} linhas importadas para Alcionaldo Silva!")
                        time.sleep(2); st.rerun()
            except Exception as e:
                st.error(f"Erro ao processar: {e}")

with aba2:
    if df_user.empty: st.info("Sem dados para exibir.")
    else:
        df_res = df_user.copy()
        df_res['Receita_T'] = df_res[['Urbano','Boraali','app163','Outros_Receita']].sum(axis=1)
        df_res['Custo_T'] = df_res[['Energia','Manuten','Seguro','Aplicativo','Alimentacao','Outros_Custos']].sum(axis=1)
        df_res['Lucro'] = df_res['Receita_T'] - df_res['Custo_T']
        df_res['KM_R'] = (df_res['KM_Final'] - df_res['KM_Inicial']).clip(lower=0)
        
        m1, m2, m3, m4 = st.columns(4)
        tk = df_res['KM_R'].sum(); tl = df_res['Lucro'].sum()
        m1.metric("Lucro Total", f"R$ {tl:,.2f}"); m2.metric("KM Total", f"{tk:,.0f}")
        m3.metric("R$/KM", f"R$ {tl/tk:.2f}" if tk>0 else "0")
        m4.metric("Custo/KM", f"R$ {df_res['Custo_T'].sum()/tk:.2f}" if tk>0 else "0")
        
        st.area_chart(df_res.set_index('Data')[['Receita_T', 'Lucro']])
        st.dataframe(df_res[['Data', 'Receita_T', 'Custo_T', 'Lucro', 'KM_R']].sort_values('Data', ascending=False), use_container_width=True)

if st.button("Sair"):
    st.session_state['autenticado'] = False; st.rerun()
