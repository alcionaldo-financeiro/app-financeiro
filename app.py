import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
import re
from datetime import datetime
import os
import plotly.express as px

# Configurações do Fuso e Estilo
st.set_page_config(page_title="Gestão BYD Dolphin", page_icon="⚡", layout="wide")

# Banco de dados
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

# Fluxo Principal
df = inicializar_dados()
st.title("⚡ BYD Dolphin - Gestão Automática")
st.write(f"📍 Lucas do Rio Verde - MT | {datetime.now().strftime('%d/%m/%Y')}")

# Abas em Português
aba1, aba2 = st.tabs(["📥 Lançar Agora", "📈 Meus Relatórios"])

with aba1:
    st.info("💡 Exemplo: 'Fiz 239 no Urbano, 164 no Boraali e 106 no App'")
    entrada_texto = st.text_area("O que aconteceu hoje?", placeholder="Escreva aqui os ganhos e gastos...")
    foto_painel = st.file_uploader("📷 Foto do Painel (para pegar o KM)", type=['png', 'jpg', 'jpeg'])
    
    if st.button("🚀 Gravar Dados Agora"):
        dados_hoje = processar_texto_inteligente(entrada_texto)
        km_lido = 0
        if foto_painel:
            try:
                texto_img = pytesseract.image_to_string(Image.open(foto_painel))
                numeros = re.findall(r'\d+', texto_img)
                # Filtra números que parecem KM razoável
                kms = [int(n) for n in numeros if int(n) > 1000]
                if kms: km_lido = max(kms)
            except:
                st.warning("Não consegui ler o KM da foto automaticamente.")
        
        if dados_hoje or km_lido > 0:
            nova_linha = {col: 0 for col in df.columns}
            nova_linha['Data'] = datetime.now().strftime("%Y-%m-%d")
            for col, val in dados_hoje.items(): 
                nova_linha[col] = val
            
            if km_lido > 0:
                # Pega o último KM registrado para calcular a diferença
                ultimo_km = df['KM_Final'].iloc[-1] if not df.empty and not pd.isna(df['KM_Final'].iloc[-1]) else km_lido
                nova_linha['KM_Final'] = km_lido
                nova_linha['Km_rodados'] = km_lido - ultimo_km
            
            df = pd.concat([df, pd.DataFrame([nova_linha])], ignore_index=True)
            salvar(df)
            st.success("✅ Tudo gravado com sucesso!")
        else:
            st.error("Não encontrei valores no seu texto. Tente: 'Urbano 100'")

with aba2:
    if not df.empty:
        st.subheader("Resumo do Seu Desempenho")
        
        # Totais para os cartões
        ganho_total = df['Urbano'].sum() + df['Boraali'].sum() + df['app163'].sum()
        gasto_total = df['Energia'].sum() + df['Manuten'].sum() + df['Seguro'].sum() + df['Aplicativo'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Ganhos", f"R$ {ganho_total:,.2f}")
        c2.metric("Total Gastos", f"R$ {gasto_total:,.2f}")
        c3.metric("Lucro Líquido", f"R$ {ganho_total - gasto_total:,.2f}")
        
        # Gráfico de Ganhos Diários
        df_fig = df.copy()
        df_fig['Ganhos'] = df_fig['Urbano'] + df_fig['Boraali'] + df_fig['app163']
        st.plotly_chart(px.bar(df_fig, x='Data', y='Ganhos', title="Seus Ganhos por Dia"), use_container_width=True)
        
        st.write("📋 Histórico de Lançamentos")
        st.dataframe(df.tail(10))
    else:
        st.warning("Nenhum dado lançado ainda. Use a primeira aba!")
