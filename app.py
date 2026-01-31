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

# --- SISTEMA DE ACESSO ---
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

# --- CARREGAR DADOS COM SEGURANÇA ---
NOME_USUARIO = st.session_state['usuario']
try:
    # Busca a aba 'Lancamentos' da sua Planilha Mestra
    df_geral = conn.read(worksheet="Lancamentos", ttl="0")
    if df_geral is None:
        df_geral = pd.DataFrame(columns=['Usuario', 'Data', 'Urbano', 'Boraali', 'app163', 'Outros_Receita', 'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Outros_Custos', 'KM_Final'])
    df_usuario = df_geral[df_geral['Usuario'] == NOME_USUARIO].copy()
except Exception as e:
    st.error(f"Erro ao conectar com o Google: {e}")
    df_geral = pd.DataFrame()
    df_usuario = pd.DataFrame()

# --- CÉREBRO DE TRIAGEM ---
def triagem_inteligente(frase):
    frase = frase.lower().replace(',', '.')
    res = {'Ganhos': {}, 'Gastos': {}}
    mapa = {
        'urbano': ('Ganhos', 'Urbano'), 'bora': ('Ganhos', 'Boraali'), '163': ('Ganhos', 'app163'),
        'particula': ('Ganhos', 'Outros_Receita'), 'arroz': ('Ganhos', 'Outros_Receita'), 
        'energia': ('Gastos', 'Energia'), 'combust': ('Gastos', 'Energia'), 'gasolina': ('Gastos', 'Energia'),
        'manut': ('Gastos', 'Manuten'), 'seguro': ('Gastos', 'Seguro'), 'marmita': ('Gastos', 'Outros_Custos'),
        'pedagio': ('Gastos', 'Outros_Custos'), 'almoço': ('Gastos', 'Outros_Custos')
    }
    matches = re.findall(r'([a-z1-9]+)\s*(\d+[\.]?\d*)', frase)
    for item, val_str in matches:
        v = float(val_str)
        achou = False
        for chave, (tipo, col) in mapa.items():
            if chave in item: res[tipo][col] = v; achou = True; break
        if not achou: res['Ganhos']['Outros_Receita'] = v
    return res

# --- INTERFACE ---
st.sidebar.title(f"👤 {NOME_USUARIO.capitalize()}")
if st.sidebar.button("Sair"):
    st.session_state['autenticado'] = False
    st.rerun()

aba1, aba2 = st.tabs(["📥 Lançar", "📊 Meu Financeiro"])

with aba1:
    texto = st.text_area("O que faturamos hoje?", placeholder="Ex: Urbano 250, Particular 100, Marmita 30")
    foto = st.file_uploader("📷 Foto do Painel", type=['png', 'jpg', 'jpeg'])
    
    if st.button("🚀 Gravar Dados"):
        dados_processados = triagem_inteligente(texto)
        km_lido = 0
        if foto:
            try:
                txt = pytesseract.image_to_string(PILImage.open(foto))
                kms = [int(n) for n in re.findall(r'\d+', txt) if int(n) > 100]
                if kms: km_lido = max(kms)
            except: pass
            
        nova_linha = {
            'Usuario': NOME_USUARIO, 'Data': datetime.now().strftime("%Y-%m-%d"),
            'Urbano': dados_processados['Ganhos'].get('Urbano', 0), 
            'Boraali': dados_processados['Ganhos'].get('Boraali', 0),
            'app163': dados_processados['Ganhos'].get('app163', 0), 
            'Outros_Receita': dados_processados['Ganhos'].get('Outros_Receita', 0),
            'Energia': dados_processados['Gastos'].get('Energia', 0), 
            'Manuten': dados_processados['Gastos'].get('Manuten', 0),
            'Seguro': dados_processados['Gastos'].get('Seguro', 0), 
            'Aplicativo': dados_processados['Gastos'].get('Aplicativo', 0),
            'Outros_Custos': dados_processados['Gastos'].get('Outros_Custos', 0), 
            'KM_Final': km_lido
        }
        
        # Envia para o Google Sheets
        df_atualizado = pd.concat([df_geral, pd.DataFrame([nova_linha])], ignore_index=True)
        conn.update(worksheet="Lancamentos", data=df_atualizado)
        st.success("✅ Faturamento salvo no Google Sheets!")
        st.rerun()

with aba2:
    if not df_usuario.empty:
        total_ganhos = df_usuario[['Urbano', 'Boraali', 'app163', 'Outros_Receita']].sum().sum()
        total_gastos = df_usuario[['Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Outros_Custos']].sum().sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ganhos Totais", f"R$ {total_ganhos:,.2f}")
        c2.metric("Despesas Totais", f"R$ {total_gastos:,.2f}")
        c3.metric("Lucro Líquido", f"R$ {total_ganhos - total_gastos:,.2f}")
        
        st.write("📋 Seus Últimos Registros")
        st.dataframe(df_usuario.tail(10))
    else:
        st.warning("Aguardando seu primeiro lançamento para gerar os relatórios.")
