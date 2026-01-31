import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import PIL.Image as PILImage
import pytesseract
import re
from datetime import datetime
import time

# --- 1. CONFIGURAÇÃO VISUAL (DESIGN PRO) ---
st.set_page_config(page_title="BYD Pro", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

# CSS para esconder menus do Streamlit e deixar visual limpo (Modo App)
st.markdown("""
    <style>
    /* Esconde menu e rodapé */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Botões mais bonitos */
    div.stButton > button:first-child {
        border-radius: 12px;
        height: 3em;
        font-weight: bold;
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
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.title("💎 BYD Pro")
        st.write("### Acesso do Piloto")
        usuario = st.text_input("Seu Nome:", placeholder="Digite seu nome...").strip().lower()
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

# --- INTELIGÊNCIA ---
def processar_texto(frase):
    frase = frase.lower().replace(',', '.')
    res = {'Urbano': 0.0, 'Boraali': 0.0, 'app163': 0.0, 'Outros_Receita': 0.0,
           'Energia': 0.0, 'Manuten': 0.0, 'Seguro': 0.0, 'Aplicativo': 0.0, 'Outros_Custos': 0.0,
           'Detalhes': []}
    
    mapa = {
        'urbano': 'Urbano', 'bora': 'Boraali', '163': 'app163',
        'particula': 'Outros_Receita', 'viagem': 'Outros_Receita',
        'energia': 'Energia', 'luz': 'Energia', 'carreg': 'Energia', 
        'gasolina': 'Energia', 'alcool': 'Energia',
        'manut': 'Manuten', 'pneu': 'Manuten', 'oleo': 'Manuten', 
        'lavagem': 'Manuten', 'seguro': 'Seguro', 
        'app': 'Aplicativo', 'mensalidade': 'Aplicativo',
        'marmita': 'Outros_Custos', 'almoco': 'Outros_Custos',
        'almoço': 'Outros_Custos', 'lanche': 'Outros_Custos', 'agua': 'Outros_Custos'
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

# --- TELA PRINCIPAL ---
st.markdown(f"#### 🚘 Olá, {NOME_USUARIO.capitalize()}")

aba_lanc, aba_extrato = st.tabs(["📝 NOVO LANÇAMENTO", "📊 MEU EXTRATO"])

# === ABA 1: LANÇAMENTO ===
with aba_lanc:
    # Estado da Conferência
    if 'em_conferencia' not in st.session_state: st.session_state['em_conferencia'] = False
    if 'dados_temp' not in st.session_state: st.session_state['dados_temp'] = {}

    # TELA 1: ENTRADA
    if not st.session_state['em_conferencia']:
        st.markdown("##### O que rolou no plantão?")
        texto = st.text_area("", key="txt_entrada", placeholder="Ex: urbano 350, bora 100, almoço 20...", height=100)
        
        st.write("") # Espaço
        st.markdown("##### 📸 Foto do Painel (KM)")
        
        # Mudei para padrão "Galeria" no PC para não assustar com tela preta
        # No celular o usuário troca para Câmera fácil
        tipo_foto = st.radio("Fonte:", ["Galeria 📂", "Câmera 📷"], horizontal=True, label_visibility="collapsed")
        
        foto = None
        if tipo_foto == "Câmera 📷":
            # TRUQUE VISUAL: Coloca a câmera numa coluna central para não ficar GIGANTE
            col_esq, col_meio, col_dir = st.columns([1, 2, 1]) 
            with col_meio:
                foto = st.camera_input("Tirar Foto")
        else:
            foto = st.file_uploader("Carregar Foto", type=['png', 'jpg', 'jpeg'])
        
        st.write("") 
        if st.button("CONTINUAR ➡️", type="primary", use_container_width=True):
            if not texto and not foto:
                st.warning("⚠️ Escreva algo ou tire uma foto.")
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
        st.info("🔎 Confira se entendi tudo certo:")
        
        c_receita, c_despesa = st.columns(2)
        
        with c_receita:
            st.success("💰 **GANHOS**")
            val_urbano = st.number_input("Urbano", value=d['Urbano'])
            val_bora = st.number_input("BoraAli", value=d['Boraali'])
            val_outros_rec = st.number_input("Outros/Partic.", value=d['app163'] + d['Outros_Receita'])
            
        with c_despesa:
            st.error("💸 **GASTOS**")
            val_energia = st.number_input("Energia/Comb.", value=d['Energia'])
            val_manut = st.number_input("Manutenção/Outros", value=d['Manuten'] + d['Outros_Custos'])
            val_app = st.number_input("Apps/Mensal", value=d['Aplicativo'])
            
        st.warning("🚗 **KM Final**")
        val_km = st.number_input("Hodômetro:", value=int(d['KM_Final']), step=1)
        
        st.write("---")
        col_voltar, col_salvar = st.columns([1, 2])
        
        if col_voltar.button("↩️ Voltar"):
            st.session_state['em_conferencia'] = False
            st.rerun()
            
        if col_salvar.button("✅ CONFIRMAR LANÇAMENTO", type="primary", use_container_width=True):
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
                st.toast("✅ Salvo com sucesso!", icon="💾")
                time.sleep(1.5)
                st.session_state['em_conferencia'] = False
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")

# === ABA 2: EXTRATO ===
with aba_extrato:
    if not df_usuario.empty:
        g = df_usuario[['Urbano', 'Boraali', 'app163', 'Outros_Receita']].sum().sum()
        d = df_usuario[['Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Outros_Custos']].sum().sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Faturamento", f"R$ {g:,.2f}")
        c2.metric("Custos", f"R$ {d:,.2f}")
        c3.metric("Lucro", f"R$ {g-d:,.2f}")
        
        st.write("---")
        st.caption("📋 Histórico Recente")
        df_view = df_usuario.iloc[::-1]
        st.dataframe(
            df_view[['Data', 'Urbano', 'Boraali', 'Energia', 'KM_Final']].head(10),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Sem dados.")

if st.sidebar.button("Sair"): # Deixei escondido na sidebar pra não clicar sem querer
    st.session_state['autenticado'] = False
    st.rerun()
