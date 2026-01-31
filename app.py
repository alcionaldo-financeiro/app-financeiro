import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import PIL.Image as PILImage
import pytesseract
import re
from datetime import datetime
import time

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="BYD Pro - Gestão Inteligente", page_icon="💎", layout="wide")

# Colunas Oficiais
COLUNAS_OFICIAIS = [
    'Usuario', 'Data', 'Urbano', 'Boraali', 'app163', 'Outros_Receita', 
    'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Outros_Custos', 
    'KM_Final', 'Detalhes'
]

conn = st.connection("gsheets", type=GSheetsConnection)

# --- CONEXÃO INTELIGENTE ---
def conectar_banco():
    try:
        # Lê a PRIMEIRA aba (Index 0)
        df = conn.read(worksheet=0, ttl="0")
        if df is None or df.empty or len(df.columns) < 2:
            df_novo = pd.DataFrame(columns=COLUNAS_OFICIAIS)
            conn.update(worksheet=0, data=df_novo)
            return df_novo, "Primeira Aba (Auto)"
        return df, "Conectado!"
    except Exception as e:
        return pd.DataFrame(columns=COLUNAS_OFICIAIS), f"Erro: {e}"

df_geral, STATUS_CONEXAO = conectar_banco()

# --- LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.markdown("# 💎 BYD Pro")
    usuario = st.text_input("Motorista:").strip().lower()
    if st.button("Acessar Painel 🚀"):
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

# --- CÉREBRO (Texto) ---
def processar_texto(frase):
    frase = frase.lower().replace(',', '.')
    res = {'Ganhos': {}, 'Gastos': {}, 'Detalhes': []}
    
    mapa = {
        'urbano': ('Ganhos', 'Urbano'), 'bora': ('Ganhos', 'Boraali'), '163': ('Ganhos', 'app163'),
        'particula': ('Ganhos', 'Outros_Receita'), 'viagem': ('Ganhos', 'Outros_Receita'),
        'energia': ('Gastos', 'Energia'), 'luz': ('Gastos', 'Energia'), 
        'carreg': ('Gastos', 'Energia'), 'gasolina': ('Gastos', 'Energia'),
        'manut': ('Gastos', 'Manuten'), 'pneu': ('Gastos', 'Manuten'), 
        'oleo': ('Gastos', 'Manuten'), 'lavagem': ('Gastos', 'Manuten'),
        'seguro': ('Gastos', 'Seguro'), 'app': ('Gastos', 'Aplicativo'), 
        'mensalidade': ('Gastos', 'Aplicativo'),
        'marmita': ('Gastos', 'Outros_Custos'), 'almoco': ('Gastos', 'Outros_Custos'),
        'almoço': ('Gastos', 'Outros_Custos'), 'lanche': ('Gastos', 'Outros_Custos'),
        'agua': ('Gastos', 'Outros_Custos')
    }
    
    pedacos = re.findall(r'([a-z1-9á-úç]+)\s*(\d+[\.]?\d*)', frase)
    
    for item, valor_str in pedacos:
        valor = float(valor_str)
        achou = False
        for chave, (tipo, col) in mapa.items():
            if chave in item:
                res[tipo][col] = res[tipo].get(col, 0) + valor
                achou = True; break
        if not achou:
            res['Ganhos']['Outros_Receita'] = res['Ganhos'].get('Outros_Receita', 0) + valor
            res['Detalhes'].append(f"{item}")
            
    return res

# --- TELA ---
st.sidebar.markdown(f"## 🚘 {NOME_USUARIO.capitalize()}")
if st.sidebar.button("Sair"):
    st.session_state['autenticado'] = False
    st.rerun()

aba1, aba2 = st.tabs(["📝 Lançar", "💰 Extrato"])

with aba1:
    if "Erro" in STATUS_CONEXAO:
        st.error(f"🚨 {STATUS_CONEXAO}")
    else:
        st.success(f"✅ {STATUS_CONEXAO}")

    # --- CAMPO DE TEXTO ---
    texto = st.text_area("Digite aqui:", key="txt_entrada", placeholder="Ex: urbano 350, almoço 20")
    
    # --- NOVO SISTEMA DE FOTO (CÂMERA OU ARQUIVO) ---
    st.write("📸 **Registro do KM (Hodômetro)**")
    tipo_foto = st.radio("Escolha:", ["Câmera 📷", "Galeria 📂"], horizontal=True, label_visibility="collapsed")
    
    foto = None
    if tipo_foto == "Câmera 📷":
        foto = st.camera_input("Tire uma foto do painel", key="cam_input")
    else:
        foto = st.file_uploader("Escolha a foto", key="file_input", type=['png', 'jpg', 'jpeg'])
    
    if st.button("GRAVAR 🚀", use_container_width=True):
        if not texto and not foto:
            st.warning("Opa, escreva algo primeiro!")
        else:
            dados = processar_texto(texto)
            km_lido = 0
            
            # --- TENTATIVA DE LER O KM (OCR MELHORADO) ---
            if foto:
                try:
                    img = PILImage.open(foto)
                    txt_img = pytesseract.image_to_string(img)
                    # Limpa pontos (ex: 10.000 vira 10000) e procura numeros
                    nums_limpos = re.findall(r'\d+', txt_img.replace('.', '').replace(',', ''))
                    # Filtra numeros provaveis de KM (maior que 500 e menor que 500.000)
                    nums_validos = [int(n) for n in nums_limpos if 500 < int(n) < 500000]
                    if nums_validos: 
                        km_lido = max(nums_validos) # Pega o maior numero achado
                        st.toast(f"👁️ Li na foto: {km_lido} KM")
                    else:
                        st.toast("⚠️ Não consegui ler o KM na foto (tente aproximar mais).")
                except:
                    pass

            nova = {col: 0 for col in COLUNAS_OFICIAIS}
            nova.update({
                'Usuario': NOME_USUARIO, 'Data': datetime.now().strftime("%Y-%m-%d"),
                'Urbano': dados['Ganhos'].get('Urbano', 0), 'Boraali': dados['Ganhos'].get('Boraali', 0),
                'app163': dados['Ganhos'].get('app163', 0), 'Outros_Receita': dados['Ganhos'].get('Outros_Receita', 0),
                'Energia': dados['Gastos'].get('Energia', 0), 'Manuten': dados['Gastos'].get('Manuten', 0),
                'Seguro': dados['Gastos'].get('Seguro', 0), 'Aplicativo': dados['Gastos'].get('Aplicativo', 0),
                'Outros_Custos': dados['Gastos'].get('Outros_Custos', 0), 'KM_Final': km_lido,
                'Detalhes': ", ".join(dados['Detalhes'])
            })
            
            try:
                df_atual = conn.read(worksheet=0, ttl="0")
                df_final = pd.concat([df_atual, pd.DataFrame([nova])], ignore_index=True)
                conn.update(worksheet=0, data=df_final)
                
                st.balloons()
                st.success(f"✅ Salvo! KM registrado: {km_lido}")
                
                time.sleep(2)
                st.session_state['txt_entrada'] = "" 
                st.rerun()
                
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

with aba2:
    if not df_usuario.empty:
        g = df_usuario[['Urbano', 'Boraali', 'app163', 'Outros_Receita']].sum().sum()
        d = df_usuario[['Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Outros_Custos']].sum().sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Faturamento", f"R$ {g:,.2f}")
        c2.metric("Despesas", f"R$ {d:,.2f}", delta_color="inverse")
        c3.metric("Lucro Líquido", f"R$ {g-d:,.2f}")
        
        st.divider()
        st.subheader("📋 Últimos Lançamentos")
        
        df_view = df_usuario.iloc[::-1]
        visivel = ['Data', 'Urbano', 'Boraali', 'Energia', 'Outros_Custos', 'KM_Final', 'Detalhes']
        st.dataframe(df_view[[c for c in visivel if c in df_usuario.columns]].head(15), use_container_width=True)
    else:
        st.info("Aguardando lançamentos...")

