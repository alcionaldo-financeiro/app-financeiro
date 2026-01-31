import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import PIL.Image as PILImage
import pytesseract
import re
from datetime import datetime
import plotly.express as px

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="BYD Pro - Gestão Inteligente", page_icon="💎", layout="wide")

# Definição das Colunas Oficiais (O DNA do Sistema)
# Adicionei 'Detalhes' para explicar o que caiu em 'Outros'
COLUNAS_OFICIAIS = [
    'Usuario', 'Data', 'Urbano', 'Boraali', 'app163', 'Outros_Receita', 
    'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Outros_Custos', 
    'KM_Final', 'Detalhes'
]

# Conexão
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO: AUTO-CONSTRUÇÃO DA PLANILHA ---
def garantir_estrutura_planilha():
    """
    Verifica se a planilha existe e tem cabeçalho. 
    Se não tiver, CRIA SOZINHO para o sócio não ter trabalho.
    """
    try:
        # Tenta ler a aba 'Lancamentos'
        df = conn.read(worksheet="Lancamentos", ttl="0")
        
        # Se estiver vazia ou faltando colunas vitais, recria o cabeçalho
        if df is None or df.empty or not set(COLUNAS_OFICIAIS).issubset(df.columns):
            st.toast("🔧 Detectei planilha nova/vazia. Criando cabeçalhos automáticos...", icon="🏗️")
            df_novo = pd.DataFrame(columns=COLUNAS_OFICIAIS)
            conn.update(worksheet="Lancamentos", data=df_novo)
            return df_novo
        return df
    except Exception:
        # Se a aba não existir ou der erro crítico, tenta criar do zero
        try:
            st.toast("⚠️ Criando aba 'Lancamentos' do zero...", icon="⚙️")
            df_novo = pd.DataFrame(columns=COLUNAS_OFICIAIS)
            conn.update(worksheet="Lancamentos", data=df_novo)
            return df_novo
        except Exception as e:
            st.error(f"Erro crítico ao acessar o Google Sheets: {e}")
            return pd.DataFrame(columns=COLUNAS_OFICIAIS)

# --- LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.title("💎 BYD Pro - Acesso Restrito")
    usuario = st.text_input("Motorista (Nome):").strip().lower()
    if st.button("Acessar Painel"):
        if usuario:
            st.session_state['usuario'] = usuario
            st.session_state['autenticado'] = True
            st.rerun()
    st.stop()

# --- CARREGAMENTO DE DADOS (COM AUTO-CONSTRUÇÃO) ---
NOME_USUARIO = st.session_state['usuario']
df_geral = garantir_estrutura_planilha()

# Filtra dados do usuário logado
try:
    # Garante que as colunas numéricas sejam tratadas como números (evita erro de soma)
    cols_numericas = ['Urbano', 'Boraali', 'app163', 'Outros_Receita', 'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Outros_Custos', 'KM_Final']
    for col in cols_numericas:
        if col in df_geral.columns:
            df_geral[col] = pd.to_numeric(df_geral[col], errors='coerce').fillna(0)
            
    df_usuario = df_geral[df_geral['Usuario'] == NOME_USUARIO].copy()
except:
    df_usuario = pd.DataFrame(columns=COLUNAS_OFICIAIS)

# --- CÉREBRO: PROCESSAMENTO DE TEXTO ---
def processar_texto_inteligente(frase):
    frase = frase.lower().replace(',', '.')
    res = {'Ganhos': {}, 'Gastos': {}, 'Detalhes': []}
    
    # Dicionário de Termos (O Robô aprende aqui)
    mapa = {
        'urbano': ('Ganhos', 'Urbano'), 'bora': ('Ganhos', 'Boraali'), '163': ('Ganhos', 'app163'),
        'particula': ('Ganhos', 'Outros_Receita'), 'viagem': ('Ganhos', 'Outros_Receita'),
        'energia': ('Gastos', 'Energia'), 'luz': ('Gastos', 'Energia'), 'kw': ('Gastos', 'Energia'),
        'gasolina': ('Gastos', 'Energia'), 'alcool': ('Gastos', 'Energia'),
        'manut': ('Gastos', 'Manuten'), 'oficina': ('Gastos', 'Manuten'), 'pneu': ('Gastos', 'Manuten'),
        'seguro': ('Gastos', 'Seguro'), 'app': ('Gastos', 'Aplicativo'),
        'marmita': ('Gastos', 'Outros_Custos'), 'almoco': ('Gastos', 'Outros_Custos'), 
        'lanche': ('Gastos', 'Outros_Custos'), 'agua': ('Gastos', 'Outros_Custos'),
        'lavagem': ('Gastos', 'Manuten')
    }
    
    # Regex para achar "coisa valor"
    pedacos = re.findall(r'([a-z1-9á-ú]+)\s*(\d+[\.]?\d*)', frase)
    
    for item, valor_str in pedacos:
        valor = float(valor_str)
        identificado = False
        
        for chave, (tipo, col) in mapa.items():
            if chave in item:
                res[tipo][col] = res[tipo].get(col, 0) + valor
                identificado = True
                break
        
        if not identificado:
            # Se não conhece (ex: "multa"), joga em Outros Custos e anota o nome
            # Lógica: Se parece ganho ou gasto? Por segurança, vamos assumir Custo se não for óbvio,
            # ou criar regra. Aqui vou jogar em Outros_Custos se não souber, para ser conservador.
            # (Ou você prefere Outros_Receita? Vou deixar Receita como padrão positivo)
            res['Ganhos']['Outros_Receita'] = res['Ganhos'].get('Outros_Receita', 0) + valor
            res['Detalhes'].append(f"{item} ({valor})")
        else:
            # Se for Outros (marmita, etc), também anota no detalhe pra saber o que foi
            if 'Outros' in col:
                res['Detalhes'].append(f"{item}")

    return res

# --- INTERFACE ---
st.sidebar.title(f"🚘 {NOME_USUARIO.capitalize()}")
if st.sidebar.button("Sair"):
    st.session_state['autenticado'] = False
    st.rerun()

aba1, aba2 = st.tabs(["📝 Novo Lançamento", "💰 Extrato"])

with aba1:
    st.markdown("### 🎙️ Digite ou fale o que rolou")
    texto = st.text_area("", placeholder="Ex: urbano 200, boraali 50, marmita 30, pneu 400")
    foto = st.file_uploader("📸 Foto do KM (Opcional)", type=['png', 'jpg', 'jpeg'])
    
    if st.button("GRAVAR NA NUVEM 🚀", use_container_width=True):
        if not texto and not foto:
            st.warning("Escreva algo para eu lançar!")
        else:
            with st.spinner("O Robô está trabalhando..."):
                dados = processar_texto_inteligente(texto)
                
                # Leitura de KM (OCR)
                km_lido = 0
                if foto:
                    try:
                        img = PILImage.open(foto)
                        txt_img = pytesseract.image_to_string(img)
                        # Tenta achar número grande (KM)
                        nums = [int(n) for n in re.findall(r'\d+', txt_img) if int(n) > 500]
                        if nums: km_lido = max(nums)
                    except: pass

                # Prepara a linha nova
                nova_linha = {col: 0 for col in COLUNAS_OFICIAIS}
                nova_linha.update({
                    'Usuario': NOME_USUARIO,
                    'Data': datetime.now().strftime("%Y-%m-%d"),
                    'Urbano': dados['Ganhos'].get('Urbano', 0),
                    'Boraali': dados['Ganhos'].get('Boraali', 0),
                    'app163': dados['Ganhos'].get('app163', 0),
                    'Outros_Receita': dados['Ganhos'].get('Outros_Receita', 0),
                    'Energia': dados['Gastos'].get('Energia', 0),
                    'Manuten': dados['Gastos'].get('Manuten', 0),
                    'Seguro': dados['Gastos'].get('Seguro', 0),
                    'Aplicativo': dados['Gastos'].get('Aplicativo', 0),
                    'Outros_Custos': dados['Gastos'].get('Outros_Custos', 0),
                    'KM_Final': km_lido,
                    'Detalhes': ", ".join(dados['Detalhes']) # Salva a anotação do que era "estranho"
                })
                
                # Salva
                try:
                    # Recarrega DF atualizado para não sobrescrever dados de outros
                    df_atual = conn.read(worksheet="Lancamentos", ttl="0")
                    df_final = pd.concat([df_atual, pd.DataFrame([nova_linha])], ignore_index=True)
                    conn.update(worksheet="Lancamentos", data=df_final)
                    st.success("✅ Lançamento Realizado com Sucesso!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

with aba2:
    if not df_usuario.empty:
        # Cálculos Rápidos
        ganhos = df_usuario[['Urbano', 'Boraali', 'app163', 'Outros_Receita']].sum().sum()
        custos = df_usuario[['Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Outros_Custos']].sum().sum()
        lucro = ganhos - custos
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Receita Total", f"R$ {ganhos:,.2f}")
        col2.metric("Custos", f"R$ {custos:,.2f}", delta_color="inverse")
        col3.metric("Lucro no Bolso", f"R$ {lucro:,.2f}")
        
        st.divider()
        st.subheader("📋 Histórico Recente")
        # Mostra colunas principais + Detalhes
        cols_view = ['Data', 'Urbano', 'Boraali', 'Energia', 'Outros_Custos', 'Detalhes', 'KM_Final']
        # Filtra colunas que existem no DF para não dar erro
        cols_view = [c for c in cols_view if c in df_usuario.columns]
        st.dataframe(df_usuario[cols_view].tail(10), use_container_width=True)
    else:
        st.info("Nenhum lançamento encontrado para você ainda.")
