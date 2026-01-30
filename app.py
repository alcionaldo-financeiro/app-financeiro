import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os
from PIL import Image
import re

# Tenta importar o leitor de imagens (OCR)
try:
    import pytesseract
    # SE PRECISAR, AJUSTE O CAMINHO ONDE INSTALOU O TESSERACT NO WINDOWS:
    # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    OCR_DISPONIVEL = True
except ImportError:
    OCR_DISPONIVEL = False

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão Motorista - BYD Dolphin", layout="centered", page_icon="🚗")

# --- CONEXÃO COM BANCO DE DADOS ---
CAMINHO_DO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
NOME_BANCO = os.path.join(CAMINHO_DO_SCRIPT, "banco_financeiro.db")

def conectar_banco():
    return sqlite3.connect(NOME_BANCO)

def criar_tabelas():
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS financas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            receita_total REAL,
            custos_total REAL,
            km_rodados REAL,
            lucro_liquido REAL,
            lucro_por_km REAL,
            urbano REAL,
            boraali REAL,
            app163 REAL,
            outros_rec REAL,
            energia REAL,
            manutencao REAL,
            seguro REAL,
            km_inicial REAL,
            km_final REAL
        )
    ''')
    conn.commit()
    conn.close()

# Garante que a tabela existe
criar_tabelas()

# --- FUNÇÃO DE INTELIGÊNCIA (LER IMAGEM) ---
def ler_imagem(imagem):
    if not OCR_DISPONIVEL:
        return "Erro: Biblioteca pytesseract não instalada.", 0.0
    
    try:
        texto = pytesseract.image_to_string(imagem)
        # Limpa o texto para achar números
        # Procura padrões de dinheiro (Ex: R$ 20,50 ou 20.50)
        padrao_dinheiro = r'R\$\s?(\d+[.,]?\d*)'
        numeros = re.findall(padrao_dinheiro, texto.replace(',', '.'))
        
        # Se achar números, tenta pegar o maior (geralmente é o total)
        maior_valor = 0.0
        if numeros:
            valores = [float(n.replace('R$', '').strip()) for n in numeros]
            maior_valor = max(valores)
            
        return texto, maior_valor
    except Exception as e:
        return f"Erro na leitura: {e}", 0.0

# --- TELA PRINCIPAL ---
st.title("🚗 Gestão Financeira - BYD Dolphin")
st.markdown("### Controle Diário de Ganhos e Custos")

# Abas para separar Manual de Automático
aba_manual, aba_auto, aba_dados = st.tabs(["📝 Lançamento Manual", "📸 Leitura Automática (BETA)", "📊 Relatórios"])

# --- VARIÁVEIS DE ESTADO ---
if 'valor_lido_ocr' not in st.session_state:
    st.session_state['valor_lido_ocr'] = 0.0
if 'km_lido_ocr' not in st.session_state:
    st.session_state['km_lido_ocr'] = 0.0

with aba_auto:
    st.header("📸 Leitura de Prints")
    if not OCR_DISPONIVEL:
        st.warning("⚠️ Para usar essa função, você precisa instalar o 'Tesseract' e a biblioteca 'pytesseract'.")
        st.code("pip install pytesseract Pillow")
    else:
        uploaded_file = st.file_uploader("Solte o Print do App ou Painel aqui", type=['png', 'jpg', 'jpeg'])
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption='Imagem Carregada', use_column_width=True)
            
            if st.button("🔍 Ler Imagem Agora"):
                texto_extraido, valor = ler_imagem(image)
                st.success(f"Valor Identificado: R$ {valor:.2f}")
                st.text_area("Texto Bruto Lido (Para conferência)", texto_extraido, height=100)
                
                # Botões para jogar o valor para o campo certo
                col1, col2, col3 = st.columns(3)
                if col1.button("É Uber/99?"):
                    st.session_state['valor_lido_ocr'] = valor
                    st.toast(f"Valor R$ {valor} enviado para Receita!")
                if col2.button("É KM Final?"):
                    st.session_state['km_lido_ocr'] = valor
                    st.toast(f"KM {valor} enviado para KM Final!")

with aba_manual:
    with st.form("form_lancamento"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("💰 Receitas (Ganhos)")
            urbano = st.number_input("Urbano Norte (R$)", min_value=0.0, step=0.10)
            boraali = st.number_input("Bora Ali (R$)", min_value=0.0, step=0.10)
            app163 = st.number_input("APP 163 / 99 / Uber (R$)", min_value=0.0, value=st.session_state['valor_lido_ocr'], step=0.10)
            outros_rec = st.number_input("Particulares / Outros (R$)", min_value=0.0, step=0.10)
            
        with col2:
            st.subheader("💸 Custos & KM")
            energia = st.number_input("Energia (KWh/R$)", min_value=0.0, step=0.10)
            manuten = st.number_input("Manutenção/Lava Jato", min_value=0.0, step=0.10)
            
            st.markdown("---")
            # Tenta pegar o último KM salvo para facilitar
            ultimo_km = 0.0
            try:
                conn = conectar_banco()
                ultimo = pd.read_sql_query("SELECT km_final FROM financas ORDER BY id DESC LIMIT 1", conn)
                conn.close()
                if not ultimo.empty:
                    ultimo_km = ultimo['km_final'].iloc[0]
            except:
                pass

            km_inicial = st.number_input("KM Inicial do Dia", min_value=0.0, value=float(ultimo_km), format="%.1f")
            km_final = st.number_input("KM Final do Dia", min_value=0.0, value=float(st.session_state['km_lido_ocr']), format="%.1f")
        
        # Cálculos Automáticos
        receita_total = urbano + boraali + app163 + outros_rec
        custos_total = energia + manuten
        km_rodados = km_final - km_inicial
        
        st.markdown(f"### 💵 Total Receita: :green[R$ {receita_total:.2f}]")
        st.markdown(f"### 🛣️ KM Rodados: {km_rodados:.1f} km")
        
        enviar = st.form_submit_button("💾 SALVAR NO SISTEMA")
        
        if enviar:
            if km_rodados < 0:
                st.error("⚠️ Erro: KM Final menor que Inicial!")
            else:
                lucro = receita_total - custos_total
                lucro_km = (lucro / km_rodados) if km_rodados > 0 else 0
                data_hoje = datetime.now().strftime("%Y-%m-%d")
                
                conn = conectar_banco()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO financas (data, receita_total, custos_total, km_rodados, lucro_liquido, lucro_por_km, 
                    urbano, boraali, app163, outros_rec, energia, manutencao, seguro, km_inicial, km_final)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                ''', (data_hoje, receita_total, custos_total, km_rodados, lucro, lucro_km, 
                      urbano, boraali, app163, outros_rec, energia, manuten, km_inicial, km_final))
                conn.commit()
                conn.close()
                st.success("✅ Lançamento salvo com sucesso!")
                # Limpa os estados
                st.session_state['valor_lido_ocr'] = 0.0
                st.session_state['km_lido_ocr'] = 0.0
                st.rerun()

with aba_dados:
    st.subheader("📊 Histórico de Corridas")
    conn = conectar_banco()
    try:
        df = pd.read_sql_query("SELECT * FROM financas ORDER BY id DESC", conn)
        st.dataframe(df)
        
        if not df.empty:
            total_mes = df['receita_total'].sum()
            meta = 15000.00
            falta = meta - total_mes
            st.metric("Faturamento Total", f"R$ {total_mes:.2f}")
            st.progress(min(total_mes / meta, 1.0))
            st.caption(f"Meta: R$ 15.000 | Falta: R$ {falta:.2f}")
    except:
        st.info("Nenhum dado lançado ainda.")
    conn.close()