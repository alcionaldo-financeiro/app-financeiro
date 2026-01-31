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

# --- CSS NUCLEAR (Visual Limpo) ---
st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden; display: none !important;}
    [data-testid="stToolbar"] {visibility: hidden; display: none !important;}
    .stDeployButton {display: none; visibility: hidden;}
    .block-container {padding-top: 1rem !important; padding-bottom: 1rem !important;}
    
    /* Botões Grandes e Estilosos */
    div.stButton > button:first-child {
        border-radius: 12px; height: 3.5em; font-weight: bold; font-size: 18px !important;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Ajuste dos Inputs Numéricos para Mobile */
    .stNumberInput input {
        font-size: 18px;
        font-weight: bold;
        text-align: center; 
        padding: 10px;
    }
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
    usuario = st.text_input("Nome do Motorista:", placeholder="Digite aqui...").strip().lower()
    st.write("")
    if st.button("ACESSAR SISTEMA 🚀", type="primary", use_container_width=True):
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

# --- TELA PRINCIPAL ---
c_logo, c_nome = st.columns([1, 5])
with c_logo: st.markdown("## 🚘")
with c_nome: st.markdown(f"### Olá, {NOME_USUARIO.capitalize()}")

aba_lanc, aba_extrato = st.tabs(["📝 LANÇAR", "📊 EXTRATO"])

# === ABA 1: LANÇAMENTO (FORMATO NOVO - PAINEL DE CONTROLE) ===
with aba_lanc:
    if 'em_conferencia' not in st.session_state: st.session_state['em_conferencia'] = False
    
    # --- TELA 1: PREENCHIMENTO RÁPIDO ---
    if not st.session_state['em_conferencia']:
        st.info("Preencha apenas o que teve no dia:")
        
        # GRUPO 1: GANHOS (Expandido por padrão)
        with st.expander("💰 RECEITAS (GANHOS)", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                v_urbano = st.number_input("Urbano / 99 / InDrive", min_value=0.0, step=10.0, key="in_urbano")
                v_bora = st.number_input("BoraAli", min_value=0.0, step=10.0, key="in_bora")
            with c2:
                v_163 = st.number_input("App 163", min_value=0.0, step=10.0, key="in_163")
                v_outros = st.number_input("Particular / Outros", min_value=0.0, step=10.0, key="in_outros")

        # GRUPO 2: DESPESAS (Recolhido para limpar a tela)
        with st.expander("💸 DESPESAS (GASTOS)", expanded=False):
            c3, c4 = st.columns(2)
            with c3:
                v_energia = st.number_input("Energia / Combustível", min_value=0.0, step=10.0, key="in_energia")
                v_alimentacao = st.number_input("Alimentação / Lanche", min_value=0.0, step=10.0, key="in_alime")
                v_manut = st.number_input("Manutenção / Lavagem", min_value=0.0, step=10.0, key="in_manut")
            with c4:
                v_app = st.number_input("Mensalidades (Apps/Net)", min_value=0.0, step=10.0, key="in_app")
                v_custos = st.number_input("Outros Custos", min_value=0.0, step=10.0, key="in_custos")
                v_seguro = st.number_input("Seguro", min_value=0.0, step=10.0, key="in_seguro")

        # GRUPO 3: KM e OBS
        with st.expander("🚗 HODÔMETRO & FOTO", expanded=True):
            st.write("Dica: Digite o KM ou tire a foto para eu tentar ler.")
            v_km_manual = st.number_input("KM Final (Painel)", min_value=0, step=1, format="%d", key="in_km")
            
            tipo_foto = st.radio("Foto (Opcional):", ["Galeria 📂", "Câmera 📷"], horizontal=True, label_visibility="collapsed")
            foto = None
            if tipo_foto == "Câmera 📷":
                col_esq, col_meio, col_dir = st.columns([1, 4, 1])
                with col_meio: foto = st.camera_input("Tirar Foto")
            else:
                foto = st.file_uploader("Carregar Arquivo", type=['png', 'jpg', 'jpeg'])
                
            obs = st.text_input("Observação (Opcional):", placeholder="Ex: Pneu furou, Gorjeta...")

        st.write("")
        # Botão Grande
        if st.button("AVANÇAR PARA CONFERÊNCIA ➡️", type="primary", use_container_width=True):
            # Validação básica: Tem que ter pelo menos um valor ou foto
            soma_tudo = v_urbano + v_bora + v_163 + v_outros + v_energia + v_alimentacao + v_manut + v_app + v_custos + v_seguro
            
            if soma_tudo == 0 and v_km_manual == 0 and foto is None:
                st.warning("⚠️ Você não preencheu nada!")
            else:
                # Se tiver foto e o KM for 0, tenta ler o OCR
                km_final_processado = v_km_manual
                if foto and km_final_processado == 0:
                    with st.spinner("Lendo foto..."):
                        try:
                            img = PILImage.open(foto)
                            txt_img = pytesseract.image_to_string(img)
                            nums = re.findall(r'\d+', txt_img.replace('.', '').replace(',', ''))
                            # Filtro inteligente
                            validos = [int(n) for n in nums if 500 < int(n) < 500000]
                            if validos: 
                                km_final_processado = max(validos)
                                st.toast(f"Li na foto: {km_final_processado} KM")
                        except: pass

                # Salva no estado temporário
                st.session_state['dados_temp'] = {
                    'Urbano': v_urbano, 'Boraali': v_bora, 'app163': v_163, 'Outros_Receita': v_outros,
                    'Energia': v_energia, 'Alimentacao': v_alimentacao, 'Manuten': v_manut,
                    'Aplicativo': v_app, 'Outros_Custos': v_custos, 'Seguro': v_seguro,
                    'KM_Final': km_final_processado,
                    'Detalhes': obs
                }
                st.session_state['em_conferencia'] = True
                st.rerun()

    # --- TELA 2: CONFERÊNCIA FINAL ---
    else:
        d = st.session_state['dados_temp']
        st.markdown("### 📝 Resumo do Lançamento")
        st.caption("Confira os valores antes de salvar.")
        
        # Mostra de forma bonita e resumida
        c_res1, c_res2 = st.columns(2)
        
        # Calcula totais para mostrar
        total_ganhos = d['Urbano'] + d['Boraali'] + d['app163'] + d['Outros_Receita']
        total_gastos = d['Energia'] + d['Alimentacao'] + d['Manuten'] + d['Aplicativo'] + d['Outros_Custos'] + d['Seguro']
        
        with c_res1:
            st.metric("Total Ganhos", f"R$ {total_ganhos:,.2f}")
            if d['Urbano'] > 0: st.write(f"• Urbano: {d['Urbano']}")
            if d['Boraali'] > 0: st.write(f"• BoraAli: {d['Boraali']}")
            if d['app163'] > 0: st.write(f"• 163: {d['app163']}")
            if d['Outros_Receita'] > 0: st.write(f"• Outros: {d['Outros_Receita']}")
            
        with c_res2:
            st.metric("Total Gastos", f"R$ {total_gastos:,.2f}")
            if d['Energia'] > 0: st.write(f"• Energia: {d['Energia']}")
            if d['Alimentacao'] > 0: st.write(f"• Comida: {d['Alimentacao']}")
            if d['Manuten'] > 0: st.write(f"• Manut: {d['Manuten']}")
            if (d['Aplicativo'] + d['Outros_Custos'] + d['Seguro']) > 0: st.write(f"• Div: {d['Aplicativo'] + d['Outros_Custos'] + d['Seguro']}")

        st.divider()
        st.write(f"🚗 **KM Final:** {d['KM_Final']}")
        if d['Detalhes']: st.write(f"📝 **Obs:** {d['Detalhes']}")
        
        col_voltar, col_salvar = st.columns([1, 2])
        
        if col_voltar.button("✏️ Editar"):
            st.session_state['em_conferencia'] = False
            st.rerun()
            
        if col_salvar.button("✅ CONFIRMAR LANÇAMENTO", type="primary", use_container_width=True):
            id_novo = int(time.time())
            
            nova = {col: 0 for col in COLUNAS_OFICIAIS}
            nova.update({
                'ID_Unico': id_novo, 'Status': 'Ativo',
                'Usuario': NOME_USUARIO, 'Data': datetime.now().strftime("%Y-%m-%d"),
                # Mapeia direto do dicionário temporário
                'Urbano': d['Urbano'], 'Boraali': d['Boraali'], 'app163': d['app163'], 'Outros_Receita': d['Outros_Receita'],
                'Energia': d['Energia'], 'Manuten': d['Manuten'], 'Seguro': d['Seguro'], 'Aplicativo': d['Aplicativo'],
                'Alimentacao': d['Alimentacao'], 'Outros_Custos': d['Outros_Custos'], 
                'KM_Final': d['KM_Final'], 'Detalhes': d['Detalhes']
            })
            
            # Retry system
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
                st.toast("Sucesso!", icon="✅")
                time.sleep(1)
                st.session_state['em_conferencia'] = False
                # Limpa os campos forçando rerun
                st.rerun()
            else:
                st.error("Erro ao salvar. Tente novamente.")

# === ABA 2: EXTRATO ===
with aba_extrato:
    if not df_usuario.empty:
        g = df_usuario[['Urbano', 'Boraali', 'app163', 'Outros_Receita']].sum().sum()
        d = df_usuario[['Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos']].sum().sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Ganhos", f"R$ {g:,.0f}")
        c2.metric("Gastos", f"R$ {d:,.0f}")
        c3.metric("Lucro", f"R$ {g-d:,.0f}")
        
        st.write("---")
        st.caption("📋 Extrato Simplificado")
        
        # Filtra colunas com valores
        cols_ver = ['Data', 'Urbano', 'Boraali', 'Energia', 'Alimentacao', 'Manuten', 'KM_Final']
        # Adiciona colunas extras se tiverem valor
        for extra in ['app163', 'Outros_Receita', 'Aplicativo', 'Outros_Custos', 'Seguro']:
             if df_usuario[extra].sum() > 0: cols_ver.append(extra)
        
        cols_finais = [c for c in cols_ver if c in df_usuario.columns]
        st.dataframe(df_usuario[cols_finais].iloc[::-1].head(15), use_container_width=True, hide_index=True)

        # Lixeira
        st.write("")
        with st.expander("🗑️ Lixeira / Correção"):
            lista = df_usuario.iloc[::-1].head(10).to_dict('records')
            if lista:
                opts = {f"{r['Data']} - R$ {r['Urbano']} (ID {r['ID_Unico']})": r['ID_Unico'] for r in lista}
                sel = st.selectbox("Apagar:", list(opts.keys()))
                if st.button("Confirmar Exclusão"):
                    try:
                        df_full = conn.read(worksheet=0, ttl="0")
                        df_full.loc[df_full['ID_Unico'] == opts[sel], 'Status'] = 'Lixeira'
                        conn.update(worksheet=0, data=df_full)
                        st.success("Apagado!")
                        time.sleep(1)
                        st.rerun()
                    except: st.error("Erro.")
    else:
        st.info("Sem dados.")
