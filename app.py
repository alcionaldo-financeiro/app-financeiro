import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import PIL.Image as PILImage
import pytesseract
import re
from datetime import datetime
import time

# --- 1. CONFIGURAÇÃO VISUAL (MODO APP NATIVO) ---
st.set_page_config(page_title="BYD Pro", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

# --- CSS NUCLEAR (VISUAL APP + CÂMERA COMPACTA) ---
st.markdown("""
    <style>
    /* 1. Mata o Menu e Rodapé */
    #MainMenu, footer, header {visibility: hidden; display: none !important;}
    [data-testid="stToolbar"] {visibility: hidden; display: none !important;}
    .stDeployButton {display: none; visibility: hidden;}
    
    /* 2. Ajuste Mobile */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* 3. Botões Estilosos */
    div.stButton > button:first-child {
        border-radius: 12px;
        height: 3.5em;
        font-weight: bold;
        font-size: 18px !important;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
    }
    
    /* 4. Métricas Grandes */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO ---
COLUNAS_OFICIAIS = [
    'Usuario', 'Data', 'Urbano', 'Boraali', 'app163', 'Outros_Receita', 
    'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Outros_Custos', 
    'KM_Final', 'Detalhes'
]
conn = st.connection("gsheets", type=GSheetsConnection)

def conectar_banco():
    try:
        df = conn.read(worksheet=0, ttl="0")
        if df is None or df.empty or len(df.columns) < 2:
            df_novo = pd.DataFrame(columns=COLUNAS_OFICIAIS)
            conn.update(worksheet=0, data=df_novo)
            return df_novo, "Online"
        return df, "Online"
    except:
        return pd.DataFrame(columns=COLUNAS_OFICIAIS), "Offline"

df_geral, STATUS = conectar_banco()

# --- LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.markdown("<br>", unsafe_allow_html=True)
    st.title("💎 BYD Pro")
    usuario = st.text_input("Piloto:", placeholder="Seu nome...").strip().lower()
    st.write("")
    if st.button("ENTRAR 🚀", type="primary", use_container_width=True):
        if usuario:
            st.session_state['usuario'] = usuario
            st.session_state['autenticado'] = True
            st.rerun()
    st.stop()

# --- DADOS ---
NOME_USUARIO = st.session_state['usuario']
try:
    cols_num = ['Urbano', 'Boraali', 'app163', 'Outros_Receita', 'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Outros_Custos', 'KM_Final']
    if not df_geral.empty:
        for col in cols_num:
            if col in df_geral.columns:
                df_geral[col] = pd.to_numeric(df_geral[col], errors='coerce').fillna(0)
    if 'Usuario' in df_geral.columns:
        df_usuario = df_geral[df_geral['Usuario'] == NOME_USUARIO].copy()
    else:
        df_usuario = pd.DataFrame(columns=COLUNAS_OFICIAIS)
except:
    df_usuario = pd.DataFrame(columns=COLUNAS_OFICIAIS)

# --- CÉREBRO ---
def processar_texto(frase):
    frase = frase.lower().replace(',', '.')
    res = {'Urbano': 0.0, 'Boraali': 0.0, 'app163': 0.0, 'Outros_Receita': 0.0,
           'Energia': 0.0, 'Manuten': 0.0, 'Seguro': 0.0, 'Aplicativo': 0.0, 'Outros_Custos': 0.0,
           'Detalhes': []}
    mapa = {
        'urbano': 'Urbano', 'bora': 'Boraali', '163': 'app163',
        'particula': 'Outros_Receita', 'viagem': 'Outros_Receita',
        'energia': 'Energia', 'luz': 'Energia', 'carreg': 'Energia', 'gasolina': 'Energia',
        'manut': 'Manuten', 'pneu': 'Manuten', 'oleo': 'Manuten', 'lavagem': 'Manuten',
        'seguro': 'Seguro', 'app': 'Aplicativo', 'mensalidade': 'Aplicativo',
        'marmita': 'Outros_Custos', 'almoco': 'Outros_Custos', 'almoço': 'Outros_Custos', 
        'lanche': 'Outros_Custos', 'agua': 'Outros_Custos'
    }
    pedacos = re.findall(r'([a-z1-9á-úç]+)\s*(\d+[\.]?\d*)', frase)
    for item, valor_str in pedacos:
        valor = float(valor_str)
        achou = False
        for chave, col_destino in mapa.items():
            if chave in item:
                res[col_destino] += valor
                achou = True; break
        if not achou:
            res['Outros_Receita'] += valor
            res['Detalhes'].append(f"{item}")
    return res

# --- TELA ---
c_logo, c_nome = st.columns([1, 5])
with c_logo: st.markdown("## 🚘")
with c_nome: st.markdown(f"### Olá, {NOME_USUARIO.capitalize()}")

aba_lanc, aba_extrato = st.tabs(["📝 LANÇAR", "📊 EXTRATO"])

with aba_lanc:
    if 'em_conferencia' not in st.session_state: st.session_state['em_conferencia'] = False
    if 'dados_temp' not in st.session_state: st.session_state['dados_temp'] = {}

    # TELA 1: DADOS
    if not st.session_state['em_conferencia']:
        st.write("Resumo do dia:")
        texto = st.text_area("", key="txt_entrada", placeholder="Ex: urbano 350, bora 100, almoço 20...", height=100)
        
        st.write("📸 **Foto KM**")
        tipo_foto = st.radio("Fonte:", ["Câmera", "Galeria"], horizontal=True, label_visibility="collapsed")
        
        foto = None
        if tipo_foto == "Câmera":
            # --- TRUQUE PARA CÂMERA NÃO FICAR GIGANTE ---
            # Cria 3 colunas: [Vazio] [Câmera] [Vazio]
            # No celular, a coluna do meio ocupa quase tudo. No PC, ela fica centralizada e menor.
            col_esq, col_meio, col_dir = st.columns([1, 4, 1])
            with col_meio:
                foto = st.camera_input("Tirar Foto")
        else:
            foto = st.file_uploader("Carregar Foto", type=['png', 'jpg', 'jpeg'])
        
        st.write("")
        if st.button("ANALISAR ➡️", type="primary", use_container_width=True):
            if not texto and not foto:
                st.warning("⚠️ Digite algo ou tire uma foto.")
            else:
                with st.spinner("Processando..."):
                    dados_lidos = processar_texto(texto)
                    km_lido = 0
                    if foto:
                        try:
                            img = PILImage.open(foto)
                            txt_img = pytesseract.image_to_string(img)
                            nums = re.findall(r'\d+', txt_img.replace('.', '').replace(',', ''))
                            validos = [int(n) for n in nums if 500 < int(n) < 500000]
                            if validos: km_lido = max(validos)
                        except: pass
                    
                    st.session_state['dados_temp'] = dados_lidos
                    st.session_state['dados_temp']['KM_Final'] = km_lido
                    st.session_state['em_conferencia'] = True
                    st.rerun()

    # TELA 2: CONFERÊNCIA
    else:
        d = st.session_state['dados_temp']
        st.info("🔎 Confira os valores:")
        
        c_receita, c_despesa = st.columns(2)
        with c_receita:
            st.success("💰 **ENTROU**")
            val_urbano = st.number_input("Urbano", value=d['Urbano'])
            val_bora = st.number_input("BoraAli", value=d['Boraali'])
            val_outros_rec = st.number_input("Outros", value=d['app163'] + d['Outros_Receita'])
        with c_despesa:
            st.error("💸 **SAIU**")
            val_energia = st.number_input("Energia", value=d['Energia'])
            val_manut = st.number_input("Manut/Outros", value=d['Manuten'] + d['Outros_Custos'])
            val_app = st.number_input("Apps", value=d['Aplicativo'])
            
        st.warning("🚗 **KM FINAL**")
        val_km = st.number_input("Hodômetro:", value=int(d['KM_Final']), step=1)
        
        col_voltar, col_salvar = st.columns([1, 2])
        if col_voltar.button("↩️ Voltar"):
            st.session_state['em_conferencia'] = False
            st.rerun()
            
        if col_salvar.button("✅ CONFIRMAR", type="primary", use_container_width=True):
            nova = {col: 0 for col in COLUNAS_OFICIAIS}
            nova.update({
                'Usuario': NOME_USUARIO, 'Data': datetime.now().strftime("%Y-%m-%d"),
                'Urbano': val_urbano, 'Boraali': val_bora, 'app163': 0, 'Outros_Receita': val_outros_rec,
                'Energia': val_energia, 'Manuten': val_manut, 'Seguro': d['Seguro'], 'Aplicativo': val_app,
                'Outros_Custos': 0, 'KM_Final': val_km, 'Detalhes': ", ".join(d['Detalhes'])
            })
            try:
                df_atual = conn.read(worksheet=0, ttl="0")
                df_final = pd.concat([df_atual, pd.DataFrame([nova])], ignore_index=True)
                conn.update(worksheet=0, data=df_final)
                st.balloons()
                st.toast("Salvo!", icon="✅")
                time.sleep(1)
                st.session_state['em_conferencia'] = False
                st.rerun()
            except:
                st.error("Erro de conexão.")

with aba_extrato:
    if not df_usuario.empty:
        g = df_usuario[['Urbano', 'Boraali', 'app163', 'Outros_Receita']].sum().sum()
        d = df_usuario[['Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Outros_Custos']].sum().sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Ganhos", f"R$ {g:,.0f}")
        c2.metric("Gastos", f"R$ {d:,.0f}")
        c3.metric("Lucro", f"R$ {g-d:,.0f}")
        st.write("---")
        st.dataframe(df_usuario[['Data', 'Urbano', 'Energia', 'KM_Final']].iloc[::-1].head(10), use_container_width=True, hide_index=True)
    else:
        st.info("Sem dados.")
