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

def limpar_texto(t):
    if pd.isna(t): return ""
    # Remove .0 que o Excel coloca em números e pega só dígitos
    texto = str(t).replace('.0', '')
    return re.sub(r'\D', '', texto)

def limpar_valor_monetario(valor):
    if pd.isna(valor) or valor == "" or valor == "-": return 0.0
    if isinstance(valor, str):
        valor = valor.replace('R$', '').replace('.', '').replace(',', '.').strip()
    try: return float(valor)
    except: return 0.0

@st.cache_data(ttl=60)
def carregar_dados_seguros():
    try:
        # Forçamos a leitura sem cache para garantir que pegamos o que acabou de ser postado
        df = conn.read(worksheet=0, ttl=0)
        if df is None or df.empty: return pd.DataFrame(columns=COLUNAS_OFICIAIS)
        
        # Garante que CPF seja string limpa
        df['CPF'] = df['CPF'].astype(str).apply(limpar_texto)
        
        # Converter colunas numéricas
        cols_num = ['Urbano', 'Boraali', 'app163', 'Outros_Receita', 'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos', 'KM_Inicial', 'KM_Final']
        for c in cols_num: 
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        
        # Converter Data
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Erro ao carregar banco: {e}")
        return pd.DataFrame(columns=COLUNAS_OFICIAIS)

# --- 3. LOGIN ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False

params = st.query_params
# Prioriza o CPF que vem da URL para o login automático
q_nome = params.get("n", "")
q_cpf = limpar_texto(params.get("c", ""))

if not st.session_state['autenticado']:
    if q_nome and len(q_cpf) == 11:
        st.session_state.update({'usuario': q_nome.lower(), 'cpf_usuario': q_cpf, 'autenticado': True})
        st.rerun()
    
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
CPF_LOGADO = st.session_state['cpf_usuario']
df_total = carregar_dados_seguros()

# Filtragem rigorosa para o usuário logado
df_user = df_total[df_total['CPF'].str.contains(CPF_LOGADO, na=False)].copy()
df_user = df_user[df_user['Status'] != 'Lixeira']

st.markdown(f"#### Olá, {st.session_state['usuario'].title()} 👤")

aba1, aba2 = st.tabs(["📝 LANÇAR / IMPORTAR", "📊 DASHBOARD & RELATÓRIOS"])

with aba1:
    m_manual, m_auto = st.tabs(["Manual", "🚀 Importar Excel"])

    with m_manual:
        # (Código de lançamento manual omitido aqui para brevidade, mas mantido igual ao anterior no seu arquivo final)
        if 'conf' not in st.session_state: st.session_state['conf'] = False
        if not st.session_state['conf']:
            with st.expander("💰 FATURAMENTO", expanded=True):
                c1, c2 = st.columns(2)
                v_urb = c1.number_input("Urbano / 99", min_value=0.0)
                v_bora = c2.number_input("BoraAli", min_value=0.0)
                v_163 = c1.number_input("App 163", min_value=0.0)
                v_out_r = c2.number_input("Particular / Outros", min_value=0.0)
            with st.expander("💸 GASTOS", expanded=False):
                c3, c4 = st.columns(2)
                v_ene = c3.number_input("Energia", min_value=0.0)
                v_ali = c4.number_input("Alimentação", min_value=0.0)
                v_man = c3.number_input("Manutenção", min_value=0.0)
                v_seg = c4.number_input("Seguro/Documento", min_value=0.0)
                v_int = c3.number_input("Internet/Apps", min_value=0.0)
                v_out_c = c4.number_input("Outros Custos", min_value=0.0)
            u_km = int(df_user['KM_Final'].max()) if not df_user.empty else 0
            k1 = st.number_input("KM Inicial", value=u_km)
            k2 = st.number_input("KM Final", value=u_km)
            obs = st.text_input("Obs:")
            if st.button("CONFERIR ➡️", type="primary"):
                st.session_state['tmp'] = {'Urbano':v_urb,'Boraali':v_bora,'app163':v_163,'Outros_Receita':v_out_r,'Energia':v_ene,'Alimentacao':v_ali,'Manuten':v_man,'Seguro':v_seg,'Aplicativo':v_int,'Outros_Custos':v_out_c,'KM_Inicial':k1,'KM_Final':k2, 'Detalhes':obs}
                st.session_state['conf'] = True; st.rerun()
        else:
            d = st.session_state['tmp']
            if st.button("✅ CONFIRMAR E SALVAR"):
                nova = {col: 0 for col in COLUNAS_OFICIAIS}; nova.update(d)
                nova.update({'ID_Unico': str(int(time.time())), 'Status': 'Ativo', 'Usuario': st.session_state['usuario'], 'CPF': CPF_LOGADO, 'Data': datetime.now(FUSO_BR).strftime("%Y-%m-%d")})
                df_db = conn.read(worksheet=0, ttl=0)
                conn.update(worksheet=0, data=pd.concat([df_db, pd.DataFrame([nova])], ignore_index=True))
                st.cache_data.clear() # LIMPA O CACHE AQUI
                st.success("Salvo!"); time.sleep(1); st.session_state['conf'] = False; st.rerun()

    with m_auto:
        st.subheader("Importação Automática")
        arquivo = st.file_uploader("Selecione o arquivo Excel", type=["xlsx"])
        
        if arquivo:
            try:
                df_ex = pd.read_excel(arquivo)
                # Mapeamento de colunas conforme sua imagem
                mapping = {
                    'Data': 'Data', 'Urbano': 'Urbano', 'Boraali': 'Boraali', 'app163': 'app163',
                    'Outros': 'Outros_Receita', 'Energia': 'Energia', 'Manuten': 'Manuten',
                    'Seguro': 'Seguro', 'Documento': 'Outros_Custos', 'Aplicativo': 'Aplicativo',
                    'KM Inicial': 'KM_Inicial', 'KM final': 'KM_Final'
                }
                
                if st.button("🚀 PROCESSAR E LANÇAR TUDO"):
                    with st.spinner("Enviando para o Google Sheets..."):
                        lista_novas = []
                        timestamp_base = int(time.time())
                        for i, row in df_ex.iterrows():
                            nova = {col: 0 for col in COLUNAS_OFICIAIS}
                            for ex_col, app_col in mapping.items():
                                if ex_col in row:
                                    if 'Data' in ex_col:
                                        try: nova[app_col] = pd.to_datetime(row[ex_col]).strftime("%Y-%m-%d")
                                        except: nova[app_col] = datetime.now(FUSO_BR).strftime("%Y-%m-%d")
                                    elif 'KM' in ex_col:
                                        nova[app_col] = float(row[ex_col]) if pd.notna(row[ex_col]) else 0
                                    else:
                                        nova[app_col] = limpar_valor_monetario(row[ex_col])
                            
                            nova.update({
                                'ID_Unico': str(timestamp_base + i), 'Status': 'Ativo',
                                'Usuario': st.session_state['usuario'], 'CPF': CPF_LOGADO,
                                'Detalhes': 'Importação Excel'
                            })
                            lista_novas.append(nova)
                        
                        df_import = pd.DataFrame(lista_novas)
                        df_db_atual = conn.read(worksheet=0, ttl=0)
                        conn.update(worksheet=0, data=pd.concat([df_db_atual, df_import], ignore_index=True))
                        
                        st.cache_data.clear() # LIMPA O CACHE PARA O DASHBOARD ATUALIZAR
                        st.success(f"✅ {len(df_import)} linhas importadas!")
                        time.sleep(2)
                        st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")

with aba2:
    if df_user.empty:
        st.info("Sem dados para exibir. Verifique se o CPF na planilha importada é o mesmo do seu login.")
        # Debug para você ver o que tem no banco (apenas para teste)
        with st.expander("Visualizar Banco Bruto (Debug)"):
            st.write("Seu CPF Logado:", CPF_LOGADO)
            st.dataframe(df_total.head())
    else:
        # --- CÁLCULOS ---
        df_res = df_user.copy()
        df_res['Receita_T'] = df_res[['Urbano','Boraali','app163','Outros_Receita']].sum(axis=1)
        df_res['Custo_T'] = df_res[['Energia','Manuten','Seguro','Aplicativo','Alimentacao','Outros_Custos']].sum(axis=1)
        df_res['Lucro'] = df_res['Receita_T'] - df_res['Custo_T']
        df_res['KM_R'] = (df_res['KM_Final'] - df_res['KM_Inicial']).clip(lower=0)
        
        m1, m2, m3, m4 = st.columns(4)
        tk = df_res['KM_R'].sum(); tl = df_res['Lucro'].sum()
        m1.metric("Lucro Total", f"R$ {tl:,.2f}")
        m2.metric("KM Total", f"{tk:,.0f}")
        m3.metric("R$/KM", f"R$ {tl/tk:.2f}" if tk>0 else "0")
        m4.metric("Custo/KM", f"R$ {df_res['Custo_T'].sum()/tk:.2f}" if tk>0 else "0")
        
        st.markdown("### Histórico de Lançamentos")
        st.dataframe(df_res[['Data', 'Receita_T', 'Custo_T', 'Lucro', 'KM_R']].sort_values('Data', ascending=False), use_container_width=True)

if st.button("Sair"):
    st.session_state['autenticado'] = False; st.rerun()
