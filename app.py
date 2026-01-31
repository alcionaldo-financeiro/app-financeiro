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

# --- CONEXÃO E COLUNAS ---
COLUNAS_OFICIAIS = [
    'ID_Unico', 'Status', 'Usuario', 'Data', 
    'Urbano', 'Boraali', 'app163', 'Outros_Receita', 
    'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos', 
    'KM_Final', 'Detalhes'
]
conn = st.connection("gsheets", type=GSheetsConnection)

def conectar_banco():
    try:
        df = conn.read(worksheet=0, ttl="0")
        
        # Cria planilha se vazia
        if df is None or df.empty or len(df.columns) < 2:
            df_novo = pd.DataFrame(columns=COLUNAS_OFICIAIS)
            conn.update(worksheet=0, data=df_novo)
            return df_novo, "Online"
        
        # Cria colunas novas se faltar
        mudou_algo = False
        for col in COLUNAS_OFICIAIS:
            if col not in df.columns:
                df[col] = 0 if col not in ['Usuario', 'Data', 'Detalhes', 'Status'] else ''
                if col == 'Status': df['Status'] = 'Ativo'
                if col == 'ID_Unico': df['ID_Unico'] = range(1, len(df) + 1)
                mudou_algo = True
        
        if mudou_algo:
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

# --- CÉREBRO EINSTEIN (SUPER INTELIGENTE) ---
def processar_texto(frase):
    frase = frase.lower().replace(',', '.')
    res = {col: 0.0 for col in COLUNAS_OFICIAIS if col not in ['ID_Unico', 'Status', 'Usuario', 'Data', 'Detalhes']}
    res['Detalhes'] = []
    
    # Dicionário expandido - O Robô aprendeu tudo isso aqui:
    mapa = {
        # --- GANHOS ---
        'Urbano': ['urbano', '99', 'pop', 'indrive', 'uber', 'black', 'comfort', 'x'],
        'Boraali': ['bora', 'borali', 'boraali'],
        'app163': ['163', 'app163'],
        'Outros_Receita': ['particula', 'viagem', 'gorjeta', 'corrida', 'passageiro', 'extra'],
        
        # --- DESPESAS: ENERGIA ---
        'Energia': ['energia', 'luz', 'carreg', 'kwh', 'posto', 'eletrico', 
                   'gasolina', 'combustivel', 'diesel', 'etanol', 'alcool', 'abastec'],
                   
        # --- DESPESAS: MANUTENÇÃO ---
        'Manuten': ['manut', 'pneu', 'oleo', 'filtro', 'lavagem', 'limpeza', 'oficina', 
                   'peca', 'freio', 'pastilha', 'revisao', 'alinhamento', 'balanceamento', 'lampada'],
                   
        # --- DESPESAS: ALIMENTAÇÃO (VÁRIAS PALAVRAS) ---
        'Alimentacao': ['marmita', 'almoco', 'almoço', 'janta', 'lanche', 'cafe', 'café', 
                       'mercado', 'comida', 'feijao', 'feijão', 'arroz', 'carne', 'restaurante', 
                       'padaria', 'coxinha', 'salgado', 'suco', 'refri', 'refrigerante', 'agua', 'água', 'acai', 'açaí'],
                       
        # --- DESPESAS: APPS ---
        'Aplicativo': ['app', 'mensalidade', 'internet', 'plano', 'vivo', 'claro', 'tim', 
                      'sem parar', 'conectcar', 'tag', 'assinatura', 'recarga'],
                      
        # --- DESPESAS: OUTROS ---
        'Seguro': ['seguro', 'franquia', 'sinistro'],
        'Outros_Custos': ['multa', 'ipva', 'licenciamento', 'doc', 'detran', 'pedagio']
    }
    
    # Lógica de Varredura
    pedacos = re.findall(r'([a-z1-9á-úçãõ]+)\s*(\d+[\.]?\d*)', frase)
    
    for item, valor_str in pedacos:
        valor = float(valor_str)
        achou = False
        
        # Varre o dicionário inteligente
        for coluna_destino, lista_palavras in mapa.items():
            # Verifica se alguma das palavras está no item digitado
            if any(palavra in item for palavra in lista_palavras):
                res[coluna_destino] += valor
                achou = True
                break # Para de procurar se achou
        
        # Se não achou NADA, aí sim pergunta
        if not achou:
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
        texto = st.text_area("", key="txt_entrada", placeholder="Ex: urbano 350, feijão 20, mensalidade 50...", height=100)
        
        st.write("📸 **Foto do KM**")
        tipo_foto = st.radio("Fonte:", ["Galeria 📂", "Câmera 📷"], horizontal=True, label_visibility="collapsed")
        
        foto = None
        if tipo_foto == "Câmera 📷":
            col_esq, col_meio, col_dir = st.columns([1, 4, 1])
            with col_meio: foto = st.camera_input("Tirar Foto")
        else:
            foto = st.file_uploader("Carregar Arquivo", type=['png', 'jpg', 'jpeg'])
        
        st.write("")
        if st.button("ANALISAR ➡️", type="primary", use_container_width=True):
            if not texto and not foto:
                st.warning("⚠️ Digite algo ou suba uma foto.")
            else:
                with st.spinner("Lendo..."):
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

    # TELA 2: CONFERÊNCIA AUTOMÁTICA
    else:
        d = st.session_state['dados_temp']
        st.info("🔎 Confira se entendi certo:")
        
        c_receita, c_despesa = st.columns(2)
        with c_receita:
            st.success("💰 **GANHOS**")
            val_urbano = st.number_input("Urbano / 99", value=d['Urbano'])
            val_bora = st.number_input("BoraAli", value=d['Boraali'])
            val_163 = st.number_input("App 163", value=d['app163'])
            val_outros_rec = st.number_input("Outros", value=d['Outros_Receita'], help="Ganhos não identificados")
        
        with c_despesa:
            st.error("💸 **GASTOS**")
            val_energia = st.number_input("Energia / Combustível", value=d['Energia'])
            val_manut = st.number_input("Manutenção", value=d['Manuten'])
            val_alimentacao = st.number_input("Alimentação", value=d['Alimentacao']) 
            val_app = st.number_input("Mensalidades Apps", value=d['Aplicativo'])
            val_seguro = st.number_input("Seguro", value=d.get('Seguro', 0.0))
            val_custos = st.number_input("Outros Custos", value=d['Outros_Custos'])
            
        st.warning("🚗 **KM FINAL**")
        val_km = st.number_input("Hodômetro:", value=int(d['KM_Final']), step=1)
        detalhes_str = st.text_input("Obs:", value=", ".join(d['Detalhes']))

        col_voltar, col_salvar = st.columns([1, 2])
        if col_voltar.button("↩️ Voltar"):
            st.session_state['em_conferencia'] = False
            st.rerun()
            
        if col_salvar.button("✅ CONFIRMAR", type="primary", use_container_width=True):
            id_novo = int(time.time())
            
            nova = {col: 0 for col in COLUNAS_OFICIAIS}
            nova.update({
                'ID_Unico': id_novo, 'Status': 'Ativo',
                'Usuario': NOME_USUARIO, 'Data': datetime.now().strftime("%Y-%m-%d"),
                'Urbano': val_urbano, 'Boraali': val_bora, 'app163': val_163, 'Outros_Receita': val_outros_rec,
                'Energia': val_energia, 'Manuten': val_manut, 'Seguro': val_seguro, 'Aplicativo': val_app,
                'Alimentacao': val_alimentacao, 'Outros_Custos': val_custos, 
                'KM_Final': val_km, 'Detalhes': detalhes_str
            })
            
            sucesso = False
            my_bar = st.progress(0, text="Salvando...")
            for tentativa in range(3):
                try:
                    df_atual = conn.read(worksheet=0, ttl="0")
                    df_final = pd.concat([df_atual, pd.DataFrame([nova])], ignore_index=True)
                    conn.update(worksheet=0, data=df_final)
                    sucesso = True
                    my_bar.progress(100, text="Salvo!")
                    break 
                except:
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
                st.error("Erro de conexão. Tente novamente.")

# === ABA 2: EXTRATO ===
with aba_extrato:
    if not df_usuario.empty:
        # Métricas
        g = df_usuario[['Urbano', 'Boraali', 'app163', 'Outros_Receita']].sum().sum()
        d = df_usuario[['Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos']].sum().sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Ganhos", f"R$ {g:,.0f}")
        c2.metric("Gastos", f"R$ {d:,.0f}")
        c3.metric("Lucro", f"R$ {g-d:,.0f}")
        
        st.write("---")
        st.caption("📋 Histórico")
        
        cols_para_mostrar = ['Data']
        numeric_cols_check = [
            'Urbano', 'Boraali', 'app163', 'Outros_Receita', 
            'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos', 
            'KM_Final'
        ]
        
        for col in numeric_cols_check:
            if col in df_usuario.columns and df_usuario[col].sum() != 0:
                cols_para_mostrar.append(col)
        
        cols_para_mostrar.append('Detalhes')
        cols_finais = [c for c in cols_para_mostrar if c in df_usuario.columns]
        
        st.dataframe(df_usuario[cols_finais].iloc[::-1].head(15), use_container_width=True, hide_index=True)

        st.write("")
        with st.expander("🛠️ Correções / Lixeira"):
            lista = df_usuario.iloc[::-1].head(10).to_dict('records')
            if lista:
                opts = {f"{r['Data']} | ID:{r['ID_Unico']}": r['ID_Unico'] for r in lista}
                sel = st.selectbox("Apagar item:", list(opts.keys()))
                id_del = opts[sel]
                
                if st.button("🗑️ Apagar"): st.session_state['confirm_del'] = True
                
                if st.session_state.get('confirm_del'):
                    st.error("Confirma?")
                    if st.button("Sim"):
                        try:
                            df_full = conn.read(worksheet=0, ttl="0")
                            mask = df_full['ID_Unico'] == id_del
                            if mask.any():
                                df_full.loc[mask, 'Status'] = 'Lixeira'
                                conn.update(worksheet=0, data=df_full)
                                st.success("Feito!")
                                st.session_state['confirm_del'] = False
                                time.sleep(1)
                                st.rerun()
                        except: st.error("Erro.")
            else: st.info("Vazio.")
    else:
        st.info("Sem dados.")
