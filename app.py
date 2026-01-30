import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
import re
from datetime import datetime
import os
import plotly.express as px

# Configurações do Fuso e Estilo
st.set_page_config(page_title="BYD Dolphin - Gestão Inteligente", page_icon="⚡", layout="wide")

# Banco de dados (CSV que simula sua planilha Base)
ARQUIVO_BASE = "base_motorista.csv"

def inicializar_dados():
    if not os.path.exists(ARQUIVO_BASE):
        colunas = ['Data', 'Urbano', 'Boraali', 'app163', 'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'KM_Final', 'Km_rodados']
        df = pd.DataFrame(columns=colunas)
        df.to_csv(ARQUIVO_BASE, index=False)
    return pd.read_csv(ARQUIVO_BASE)

def salvar(df):
    df.to_csv(ARQUIVO_BASE, index=False)

def processar_texto_inteligente(frase):
    frase = frase.lower()
    resultados = {}
    categorias = {
        'urbano': 'Urbano', 'bora': 'Boraali', 'ali': 'Boraali', '163': 'app163',
        'uber': 'app163', '99': 'app163', 'energia': 'Energia', 'luz': 'Energia',
        'carga': 'Energia', 'combust': 'Energia', 'manut': 'Manuten', 'lava': 'Manuten',
        'seguro': 'Seguro', 'mensal': 'Aplicativo', 'app': 'Aplicativo'
    }
    for chave, coluna in categorias.items():
        if chave in frase:
            match = re.search(rf'{chave}.*?(\d+[\.,]?\d*)', frase)
            if match:
                valor = float(match.group(1).replace(',', '.'))
                resultados[coluna] = valor
    return resultados

df = inicializar_dados()
st.title("⚡ BYD Dolphin - Gestão Automática")
st.write(f"📍 Lucas do Rio Verde - MT | {datetime.now().strftime('%d/%m/%Y')}")

tab1, tab2 = st.tabs(["📥 Lançar Agora", "📈 Meus Relatórios"])

with tab1:
    st.info("💡 Digite: 'Urbano 239. Boraali 164. App 106'")
    entrada_texto = st.text_area("O que aconteceu hoje?", placeholder="Ex: Fiz 300 no urbano...")
    foto_painel = st.file_uploader("📷 Foto do Painel (KM)", type=['png', 'jpg', 'jpeg'])
    
    if st.button("🚀 Processar e Salvar Tudo"):
        dados_hoje = processar_texto_inteligente(entrada_texto)
        km_lido = 0
        if foto_painel:
            texto_img = pytesseract.image_to_string(Image.open(foto_painel))
            numeros = re.findall(r'\d+', texto_img)
            kms = [int(n) for n in numeros if int(n) > 1000]
            if kms: km_lido = max(kms)
        
        if dados_hoje or km_lido > 0:
            nova_linha = {col: 0 for col in df.columns}
            nova_linha['Data'] = datetime.now().strftime("%Y-%m-%d")
            for col, val in dados_hoje.items(): nova_linha[col] = val
            if km_lido > 0:
                ultimo_km = df['KM_Final'].iloc[-1] if not df.empty and not pd.isna(df['KM_Final'].iloc[-1]) else km_lido
                nova_linha['KM_Final'] = km_lido
                nova_linha['Km_rodados'] = km_lido - ultimo_km
            df = pd.concat([df, pd.DataFrame([nova_linha])], ignore_index=True)
            salvar(df)
            st.success("✅ Salvo com sucesso!")
        else:
            st.error("Não entendi os valores.")

with tab2:
    if not df.empty:
        st.subheader("Resumo de Desempenho")
        receita_total = df['Urbano'].sum() + df['Boraali'].sum() + df['app163'].sum()
        custo_total = df['Energia'].sum() + df['Manuten'].sum() + df['Seguro'].sum() + df['Aplicativo'].sum()
        km_total = df['Km_rodados'].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Faturamento", f"R$ {receita_total:,.2f}")
        c2.metric("Custos", f"R$ {custo_total:,.2f}")
        c3.metric("Lucro Líquido", f"R$ {receita_total - custo_total:,.2f}")
        df_grafico = df.copy()
        df_grafico['Ganhos'] = df_grafico['Urbano'] + df_grafico['Boraali'] + df_grafico['app163']
        st.plotly_chart(px.bar(df_grafico, x='Data', y='Ganhos', title="Ganhos Diários"), use_container_width=True)
        st.dataframe(df.tail(10))
    else:
        st.warning("Sem dados ainda.")
