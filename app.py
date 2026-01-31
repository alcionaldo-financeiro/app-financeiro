import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import PIL.Image as PILImage
import pytesseract
import re
from datetime import datetime
import plotly.express as px

# Configurações de Performance
st.set_page_config(page_title="BYD Pro - Gestão SaaS", page_icon="💎", layout="wide")

# Conexão com o Cofre (Google Sheets)
conn = st.connection("gsheets", type=GSheetsConnection)

# --- LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.title("💎 Bem-vindo ao Faturamento Pro")
    usuario = st.text_input("Seu Usuário (CPF ou Nome):").strip().lower()
    if st.button("Acessar Meu Painel"):
        if usuario:
            st.session_state['usuario'] = usuario
            st.session_state['autenticado'] = True
            st.rerun()
    st.stop()

# --- CARREGAR DADOS ---
NOME_USUARIO = st.session_state['usuario']
try:
    # Busca a aba 'Lancamentos' da sua Planilha Mestra
    df_geral = conn.read(worksheet="Lancamentos", ttl="0")
    df_user = df_geral[df_geral['Usuario'] == NOME_USUARIO].copy()
except:
    df_user = pd.DataFrame()

# --- CÉREBRO DE TRIAGEM ---
def triagem_inteligente(frase):
    frase = frase.lower().replace(',', '.')
    res = {'Rec': {}, 'Cus': {}}
    mapa = {
        'urbano': ('Rec', 'Urbano'), 'bora': ('Rec', 'Boraali'), '163': ('Rec', 'app163'),
        'particula': ('Rec', 'Outros_Receita'), 'energia': ('Cus', 'Energia'),
        'manut': ('Cus', 'Manuten'), 'seguro': ('Cus', 'Seguro'), 'marmita': ('Cus', 'Outros_Custos'),
        'pedagio': ('Cus', 'Outros_Custos'), 'almoço': ('Cus', 'Outros_Custos')
    }
    matches = re.findall(r'([a-z1-9]+)\s*(\d+[\.]?\d*)', frase)
    for item, val_str in matches:
        v = float(val_str)
        achou = False
        for chave, (tipo, col) in mapa.items():
            if chave in item: res[tipo][col] = v; achou = True; break
        if not achou: res['Rec']['Outros_Receita'] = v
    return res

# --- INTERFACE ---
st.sidebar.title(f"👤 {NOME_USUARIO.capitalize()}")
if st.sidebar.button("Sair"):
    st.session_state['autenticado'] = False
    st.rerun()

tab1, tab2 = st.tabs(["📥 Lançar", "📊 Dashboard Financeiro"])

with tab1:
    texto = st.text_area("O que faturamos hoje?", placeholder="Ex: Urbano 250, particular 100, marmita 30")
    foto = st.file_uploader("📷 Foto do Painel", type=['png', 'jpg', 'jpeg'])
    
    if st.button("🚀 Gravar Dados"):
        dados = triagem_inteligente(texto)
        km_lido = 0
        if foto:
            try:
                txt = pytesseract.image_to_string(PILImage.open(foto))
                kms = [int(n) for n in re.findall(r'\d+', txt) if int(n) > 100]
                if kms: km_lido = max(kms)
            except: pass
            
        nova_linha = {
            'Usuario': NOME_USUARIO, 'Data': datetime.now().strftime("%Y-%m-%d"),
            'Urbano': dados['Rec'].get('Urbano', 0), 'Boraali': dados['Rec'].get('Boraali', 0),
            'app163': dados['Rec'].get('app163', 0), 'Outros_Receita': dados['Rec'].get('Outros_Receita', 0),
            'Energia': dados['Cus'].get('Energia', 0), 'Manuten': dados['Cus'].get('Manuten', 0),
            'Seguro': dados['Cus'].get('Seguro', 0), 'Aplicativo': dados['Cus'].get('Aplicativo', 0),
            'Outros_Custos': dados['Cus'].get('Outros_Custos', 0), 'KM_Final': km_lido
        }
        
        # Envia para o Google Sheets
        df_atualizado = pd.concat([df_geral, pd.DataFrame([nova_linha])], ignore_index=True)
        conn.update(worksheet="Lancamentos", data=df_atualizado)
        st.success("✅ Faturamento salvo no Google Sheets!")

with tab2:
    if not df_user.empty:
        # Cálculos de Métricas (Igual ao seu Excel)
        total_rec = df_user[['Urbano', 'Boraali', 'app163', 'Outros_Receita']].sum().sum()
        total_cus = df_user[['Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Outros_Custos']].sum().sum()
        total_km = df_user['KM_Final'].max() - df_user['KM_Final'].min() if len(df_user) > 1 else 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Receita Total", f"R$ {total_rec:,.2f}")
        c2.metric("Lucro Líquido", f"R$ {total_rec - total_cus:,.2f}")
        c3.metric("Receita/KM", f"R$ {total_rec/total_km:.2f}" if total_km > 0 else "---")
        c4.metric("Custo/KM", f"R$ {total_cus/total_km:.2f}" if total_km > 0 else "---")
        
        st.plotly_chart(px.bar(df_user, x='Data', y=['Urbano', 'Boraali', 'app163'], title="Faturamento por Canal"))
        st.dataframe(df_user)
    else:
        st.warning("Aguardando seu primeiro lançamento.")
