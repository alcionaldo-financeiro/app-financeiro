import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import PIL.Image as PILImage
import pytesseract
import re
from datetime import datetime
import time

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="BYD Pro", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

# --- CSS NUCLEAR ---
st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden; display: none !important;}
    [data-testid="stToolbar"] {visibility: hidden; display: none !important;}
    .stDeployButton {display: none; visibility: hidden;}
    .block-container {padding-top: 1rem !important; padding-bottom: 1rem !important;}
    div.stButton > button:first-child {
        border-radius: 12px; height: 3.5em; font-weight: bold; font-size: 18px !important;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
    }
    [data-testid="stMetricValue"] {font-size: 1.8rem !important;}
    div.stButton > button[kind="secondary"] {border: 1px solid #ff4b4b; color: #ff4b4b;}
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO ---
COLUNAS_OFICIAIS = [
    'ID_Unico', 'Status', 'Usuario', 'Data', 'Urbano', 'Boraali', 'app163', 'Outros_Receita', 
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
        
        if 'Status' not in df.columns:
            df['Status'] = 'Ativo'
            df['ID_Unico'] = range(1, len(df) + 1)
            conn.update(worksheet=0, data=df)
            
        return df, "Online"
    except:
        return pd.DataFrame(columns=COLUNAS_OFICIAIS), "Offline"

df_geral, STATUS = conectar_banco()

# --- LOGIN ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
if not st.session_state['autenticado']:
    st.markdown("<br>", unsafe_allow_html=True)
    st.title("💎 BYD Pro")
    usuario = st.text_input("Motorista:", placeholder="Seu nome...").strip().lower()
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
    # Garante que colunas numéricas sejam números
    numeric_cols = [c for c in COLUNAS_OFICIAIS if c not in ['Usuario', 'Data', 'Detalhes', 'Status']]
    if not df_geral.empty:
        for col in numeric_cols:
            if col in df_geral.columns:
                df_geral[col] = pd.to_numeric(df_geral[col], errors='coerce').fillna(0)
    
    if 'Usuario' in df_geral.columns and 'Status' in df_geral.columns:
        df_usuario = df_geral[
            (df_geral['Usuario'] == NOME_USUARIO) & 
            (df_geral['Status'] != 'Lixeira')
        ].copy()
    else:
        df_usuario = pd.DataFrame(columns=COLUNAS_OFICIAIS)
except:
    df_usuario = pd.DataFrame(columns=COLUNAS_OFICIAIS)

# --- CÉREBRO INTELIGENTE ---
def processar_texto(frase):
    frase = frase.lower().replace(',', '.')
    # Dicionário inicial zerado
    res = {col: 0.0 for col in COLUNAS_OFICIAIS if col not in ['ID_Unico', 'Status', 'Usuario', 'Data', 'Detalhes']}
    res['Detalhes'] = []
    
    # Mapa de Palavras-Chave (Agora com mais variações)
    mapa = {
        'urbano': 'Urbano', '99': 'Urbano', 'pop': 'Urbano', 'indrive': 'Urbano',
        'bora': 'Boraali', 'borali': 'Boraali', 'boraali': 'Boraali',
        '163': 'app163',
        'particula': 'Outros_Receita', 'viagem': 'Outros_Receita', 'gorjeta': 'Outros_Receita',
        'energia': 'Energia', 'luz': 'Energia', 'carreg': 'Energia', 'gasolina': 'Energia', 
        'combustivel': 'Energia', 'posto': 'Energia',
        'manut': 'Manuten', 'pneu': 'Manuten', 'oleo': 'Manuten', 'lavagem': 'Manuten', 'oficina': 'Manuten',
        'seguro': 'Seguro', 
        'app': 'Aplicativo', 'mensalidade': 'Aplicativo', 'internet': 'Aplicativo',
        'marmita': 'Outros_Custos', 'almoco': 'Outros_Custos', 'almoço': 'Outros_Custos', 
        'lanche': 'Outros_Custos', 'agua': 'Outros_Custos', 'cafe': 'Outros_Custos'
    }
    
    pedacos = re.findall(r'([a-z1-9á-úç]+)\s*(\d+[\.]?\d*)', frase)
    
    for item, valor_str in pedacos:
        valor = float(valor_str)
        achou = False
        
        # 1. Tenta achar no mapa conhecido
        for chave, col_destino in mapa.items():
            if chave in item:
                res[col_destino] += valor
                achou = True; break
        
        # 2. Se não achou, joga para Detalhes e pergunta depois (Lógica de segurança)
        if not achou:
            # Por padrão, assume que é Outra Receita se for valor alto (>100) ou Custo se baixo,
            # mas coloca no 'Detalhes' para o motorista validar.
            # Aqui simplificamos: Joga em Outros_Receita e adiciona o nome.
            # Na tela de conferência o motorista ajusta.
            res['Outros_Receita'] += valor 
            res['Detalhes'].append(f"{item} (?)")
        
    return res

# --- TELA ---
c_logo, c_nome = st.columns([1, 5])
with c_logo: st.markdown("## 🚘")
with c_nome: st.markdown(f"### Olá, {NOME_USUARIO.capitalize()}")

aba_lanc, aba_extrato = st.tabs(["📝 LANÇAR", "📊 EXTRATO & AJUSTES"])

# === ABA 1: LANÇAMENTO ===
with aba_lanc:
    if 'em_conferencia' not in st.session_state: st.session_state['em_conferencia'] = False
    if 'dados_temp' not in st.session_state: st.session_state['dados_temp'] = {}

    # TELA 1: DADOS
    if not st.session_state['em_conferencia']:
        st.write("Resumo do plantão:")
        texto = st.text_area("", key="txt_entrada", placeholder="Ex: urbano 350, borali 100, almoço 20...", height=100)
        
        st.write("📸 **Foto do KM**")
        # Inverti a ordem aqui: Galeria primeiro!
        tipo_foto = st.radio("Fonte:", ["Galeria 📂", "Câmera 📷"], horizontal=True, label_visibility="collapsed")
        
        foto = None
        if tipo_foto == "Câmera 📷":
            col_esq, col_meio, col_dir = st.columns([1, 4, 1])
            with col_meio:
                foto = st.camera_input("Tirar Foto")
        else:
            foto = st.file_uploader("Carregar Arquivo", type=['png', 'jpg', 'jpeg'])
        
        st.write("")
        if st.button("ANALISAR ➡️", type="primary", use_container_width=True):
            if not texto and not foto:
                st.warning("⚠️ Digite algo ou suba uma foto.")
            else:
                with st.spinner("O Robô está lendo..."):
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
        st.info("🔎 O Robô entendeu isso. Corrija se precisar:")
        
        # --- BLOCO INTELIGENTE DE CONFERÊNCIA ---
        c_receita, c_despesa = st.columns(2)
        with c_receita:
            st.success("💰 **GANHOS**")
            # Mostra campos apenas se tiverem valor ou se for os principais
            val_urbano = st.number_input("Urbano / 99 / InDrive", value=d['Urbano'])
            val_bora = st.number_input("BoraAli", value=d['Boraali'])
            val_163 = st.number_input("App 163", value=d['app163'])
            # Se o sistema não soube o que era, jogou aqui. O motorista ajusta.
            val_outros_rec = st.number_input("Outros / Particular", value=d['Outros_Receita'], help="Coisas que o robô não identificou caem aqui")
        
        with c_despesa:
            st.error("💸 **GASTOS**")
            val_energia = st.number_input("Energia / Combustível", value=d['Energia'])
            val_manut = st.number_input("Manutenção / Lavagem", value=d['Manuten'])
            val_custos = st.number_input("Alimentação / Diversos", value=d['Outros_Custos'])
            val_app = st.number_input("Mensalidades Apps", value=d['Aplicativo'])
            
        st.warning("🚗 **KM FINAL**")
        val_km = st.number_input("Hodômetro:", value=int(d['KM_Final']), step=1)
        
        # Campo para Detalhes (Opcional)
        detalhes_str = st.text_input("Observação (Opcional):", value=", ".join(d['Detalhes']))

        col_voltar, col_salvar = st.columns([1, 2])
        if col_voltar.button("↩️ Voltar"):
            st.session_state['em_conferencia'] = False
            st.rerun()
            
        if col_salvar.button("✅ CONFIRMAR", type="primary", use_container_width=True):
            id_novo = int(time.time())
            
            nova = {col: 0 for col in COLUNAS_OFICIAIS}
            nova.update({
                'ID_Unico': id_novo,
                'Status': 'Ativo',
                'Usuario': NOME_USUARIO, 'Data': datetime.now().strftime("%Y-%m-%d"),
                'Urbano': val_urbano, 'Boraali': val_bora, 'app163': val_163, 'Outros_Receita': val_outros_rec,
                'Energia': val_energia, 'Manuten': val_manut, 'Seguro': d.get('Seguro', 0.0), 'Aplicativo': val_app,
                'Outros_Custos': val_custos, 'KM_Final': val_km, 'Detalhes': detalhes_str
            })
            
            # --- BLINDAGEM ANTI-SOLUÇO ---
            sucesso = False
            my_bar = st.progress(0, text="Acordando banco de dados...")
            for tentativa in range(3):
                try:
                    df_atual = conn.read(worksheet=0, ttl="0")
                    df_final = pd.concat([df_atual, pd.DataFrame([nova])], ignore_index=True)
                    conn.update(worksheet=0, data=df_final)
                    sucesso = True
                    my_bar.progress(100, text="Salvo!")
                    break 
                except Exception as e:
                    time.sleep(1)
                    my_bar.progress(33*(tentativa+1), text=f"Reconectando... ({tentativa+1}/3)")
            my_bar.empty()
            
            if sucesso:
                st.balloons()
                st.toast("Lançamento Registrado!", icon="✅")
                time.sleep(1)
                st.session_state['em_conferencia'] = False
                st.rerun()
            else:
                st.error("Erro de conexão. Tente clicar em CONFIRMAR novamente.")

# === ABA 2: EXTRATO & AJUSTES ===
with aba_extrato:
    if not df_usuario.empty:
        # Métricas
        g = df_usuario[['Urbano', 'Boraali', 'app163', 'Outros_Receita']].sum().sum()
        d = df_usuario[['Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Outros_Custos']].sum().sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Ganhos", f"R$ {g:,.0f}")
        c2.metric("Gastos", f"R$ {d:,.0f}")
        c3.metric("Lucro", f"R$ {g-d:,.0f}")
        
        st.write("---")
        st.caption("📋 Histórico Completo (Itens Zerados são Ocultos)")
        
        # --- EXTRATO DINÂMICO (SOLUÇÃO DO PROBLEMA DO BORALI) ---
        # Filtra apenas colunas que tem algum valor > 0 em todo o histórico do usuário
        cols_para_mostrar = ['Data']
        # Pega todas as colunas numéricas
        cols_numericas = ['Urbano', 'Boraali', 'app163', 'Outros_Receita', 'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Outros_Custos', 'KM_Final']
        
        for col in cols_numericas:
            # Se a soma da coluna for diferente de zero, ela entra na tabela
            if df_usuario[col].sum() != 0:
                cols_para_mostrar.append(col)
        
        cols_para_mostrar.append('Detalhes') # Sempre mostra detalhes
        
        # Mostra a tabela dinâmica
        df_show = df_usuario[cols_para_mostrar].iloc[::-1].head(15)
        st.dataframe(df_show, use_container_width=True, hide_index=True)

        # --- ÁREA DE CORREÇÃO ---
        st.write("")
        with st.expander("🛠️ Correções / Lixeira"):
            lista_opcoes = df_usuario.iloc[::-1].head(10).to_dict('records')
            if lista_opcoes:
                opcoes_formatadas = {f"{row['Data']} | ID:{row['ID_Unico']}": row['ID_Unico'] for row in lista_opcoes}
                escolha = st.selectbox("Apagar item:", list(opcoes_formatadas.keys()))
                id_para_apagar = opcoes_formatadas[escolha]
                
                if st.button("🗑️ Apagar"):
                    st.session_state['confirmar_delete'] = True
                
                if st.session_state.get('confirmar_delete'):
                    st.error("Confirma exclusão?")
                    c_s, c_n = st.columns(2)
                    if c_s.button("Sim"):
                        try:
                            df_full = conn.read(worksheet=0, ttl="0")
                            mask = df_full['ID_Unico'] == id_para_apagar
                            if mask.any():
                                df_full.loc[mask, 'Status'] = 'Lixeira'
                                conn.update(worksheet=0, data=df_full)
                                st.success("Apagado!")
                                st.session_state['confirmar_delete'] = False
                                time.sleep(1)
                                st.rerun()
                        except: st.error("Erro ao apagar.")
                    if c_n.button("Não"):
                        st.session_state['confirmar_delete'] = False
                        st.rerun()
            else:
                st.info("Nada para apagar.")

    else:
        st.info("Sem dados.")
