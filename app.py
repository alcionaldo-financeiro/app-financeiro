import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime
import time
import pytz  # Para fuso horário de Brasília

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="BYD Pro", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

# --- CSS NUCLEAR ---
st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden; display: none !important;}
    [data-testid="stToolbar"] {visibility: hidden; display: none !important;}
    .stDeployButton {display: none; visibility: hidden;}
    .block-container {padding-top: 1rem !important; padding-bottom: 1rem !important;}
    
    div.stButton > button[kind="primary"] {
        background-color: #28a745 !important; 
        border-color: #28a745 !important;
        color: white !important;
        border-radius: 12px; height: 3.5em; font-weight: bold; font-size: 18px !important;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.2);
    }
    
    details div.stButton > button {
        background-color: #dc3545 !important;
        border-color: #dc3545 !important;
        color: white !important;
        font-weight: bold;
        border-radius: 8px;
    }

    .stNumberInput input {
        font-size: 20px !important; 
        font-weight: bold; 
        text-align: center; 
        padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURAÇÕES DE DADOS ---
COLUNAS_OFICIAIS = [
    'ID_Unico', 'Status', 'Usuario', 'CPF', 'Data', 
    'Urbano', 'Boraali', 'app163', 'Outros_Receita', 
    'Energia', 'Manuten', 'Seguro', 'Aplicativo', 'Alimentacao', 'Outros_Custos', 
    'KM_Inicial', 'KM_Final', 'Detalhes'
]
FUSO_BR = pytz.timezone('America/Sao_Paulo')

conn = st.connection("gsheets", type=GSheetsConnection)

def limpar_cpf(texto):
    return re.sub(r'\D', '', str(texto))

def conectar_banco():
    try:
        # ttl="0" garante que leremos sempre o dado mais recente na conferência
        df = conn.read(worksheet=0, ttl="0")
        
        if df is None or df.empty:
            return pd.DataFrame(columns=COLUNAS_OFICIAIS), "Online"
        
        # Garante que todas as colunas oficiais existam
        for col in COLUNAS_OFICIAIS:
            if col not in df.columns:
                df[col] = 0 if col not in ['Usuario', 'CPF', 'Data', 'Detalhes', 'Status'] else ''
        
        # Padronização de Tipos de Dados Críticos
        df['CPF'] = df['CPF'].apply(limpar_cpf)
        df['ID_Unico'] = df['ID_Unico'].astype(str)
        df['Usuario'] = df['Usuario'].astype(str).str.lower().str.strip()
        
        return df, "Online"
    except Exception as e:
        return pd.DataFrame(columns=COLUNAS_OFICIAIS), f"Offline: {e}"

# Carregamento Global
df_geral, STATUS_CONEXAO = conectar_banco()

# --- HELPER ---
def safe_val(val): return float(val) if val is not None else 0.0

# --- TELA DE LOGIN ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.markdown("<br>", unsafe_allow_html=True)
    st.title("💎 BYD Pro")
    st.write("### Identificação do Piloto")
    
    c_login1, c_login2 = st.columns(2)
    with c_login1:
        usuario_input = st.text_input("Nome Completo:", placeholder="Ex: João Silva").strip()
    with c_login2:
        cpf_input = st.text_input("CPF (Apenas números):", max_chars=14, placeholder="000.000.000-00")

    if st.button("ACESSAR SISTEMA 🚀", type="primary", use_container_width=True):
        cpf_limpo = limpar_cpf(cpf_input)
        nome_limpo = usuario_input.lower().strip()
        
        if not nome_limpo or len(cpf_limpo) != 11:
            st.warning("⚠️ Verifique se o nome foi preenchido e o CPF tem 11 dígitos.")
        else:
            # AUDITORIA: Verifica se este CPF já pertence a outro nome
            conflito = False
            if not df_geral.empty:
                # Busca qualquer registro com esse CPF
                registro_existente = df_geral[df_geral['CPF'] == cpf_limpo]
                if not registro_existente.empty:
                    nome_na_base = registro_existente.iloc[0]['Usuario']
                    if nome_na_base != nome_limpo:
                        st.error(f"⛔ SEGURANÇA: Este CPF está vinculado ao motorista {nome_na_base.upper()}.")
                        st.info("Se você mudou de nome ou houve erro, contate o administrador.")
                        conflito = True
            
            if not conflito:
                st.session_state['usuario'] = nome_limpo
                st.session_state['cpf_usuario'] = cpf_limpo
                st.session_state['autenticado'] = True
                st.rerun()
    st.stop()

# --- VARIAVEIS DE SESSÃO ---
NOME_USUARIO = st.session_state['usuario']
CPF_USUARIO = st.session_state['cpf_usuario']

# Filtragem de dados específica do usuário logado (usando CPF por segurança)
df_usuario = df_geral[
    (df_geral['CPF'] == CPF_USUARIO) & 
    (df_geral['Status'] != 'Lixeira')
].copy()

# --- TELA PRINCIPAL ---
c_logo, c_nome = st.columns([1, 5])
with c_logo: st.markdown("## 🚘")
with c_nome: st.markdown(f"### Olá, {NOME_USUARIO.title()}")

aba_lanc, aba_extrato = st.tabs(["📝 LANÇAR", "📊 RELATÓRIOS"])

# === ABA 1: LANÇAMENTO ===
with aba_lanc:
    if 'em_conferencia' not in st.session_state: st.session_state['em_conferencia'] = False
    
    if not st.session_state['em_conferencia']:
        st.info("Preencha apenas o que teve no dia:")
        
        with st.expander("💰 RECEITAS (GANHOS)", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                v_urbano = st.number_input("Urbano / 99", min_value=0.0, step=5.0, value=None, placeholder="0,00", key="in_urbano")
                v_bora = st.number_input("BoraAli", min_value=0.0, step=5.0, value=None, placeholder="0,00", key="in_bora")
            with c2:
                v_163 = st.number_input("App 163", min_value=0.0, step=5.0, value=None, placeholder="0,00", key="in_163")
                v_outros = st.number_input("Particular / Outros", min_value=0.0, step=5.0, value=None, placeholder="0,00", key="in_outros")

        with st.expander("💸 DESPESAS (GASTOS)", expanded=False):
            c3, c4 = st.columns(2)
            with c3:
                v_energia = st.number_input("Energia / Combustível", min_value=0.0, step=5.0, value=None, placeholder="0,00", key="in_energia")
                v_alimentacao = st.number_input("Alimentação / Lanche", min_value=0.0, step=5.0, value=None, placeholder="0,00", key="in_alime")
                v_manut = st.number_input("Manutenção / Lavagem", min_value=0.0, step=5.0, value=None, placeholder="0,00", key="in_manut")
            with c4:
                v_app = st.number_input("Apps / Internet", min_value=0.0, step=5.0, value=None, placeholder="0,00", key="in_app")
                v_seguro = st.number_input("Seguro", min_value=0.0, step=5.0, value=None, placeholder="0,00", key="in_seguro")
                v_custos = st.number_input("Outros Custos", min_value=0.0, step=5.0, value=None, placeholder="0,00", key="in_custos")

        st.write("🚗 **Hodômetro**")
        # Busca o último KM real deste usuário específico
        ultimo_km = 0
        if not df_usuario.empty:
            try: ultimo_km = int(pd.to_numeric(df_usuario['KM_Final']).max())
            except: ultimo_km = 0

        c_km1, c_km2 = st.columns(2)
        with c_km1:
            v_km_ini = st.number_input("KM Inicial", min_value=0, step=1, value=ultimo_km, format="%d", key="in_km_ini")
        with c_km2:
            v_km_fim = st.number_input("KM Final", min_value=0, step=1, value=None, placeholder=str(ultimo_km), format="%d", key="in_km_fim")
        
        obs = st.text_input("Observação (Opcional):", placeholder="Ex: Pneu furou...")

        # Cálculos Prévios
        t_receita = safe_val(v_urbano) + safe_val(v_bora) + safe_val(v_163) + safe_val(v_outros)
        t_despesa = safe_val(v_energia) + safe_val(v_alimentacao) + safe_val(v_manut) + safe_val(v_app) + safe_val(v_custos) + safe_val(v_seguro)
        
        st.divider()
        if st.button("AVANÇAR PARA CONFERÊNCIA ➡️", type="primary", use_container_width=True):
            if t_receita == 0 and t_despesa == 0 and not v_km_fim:
                st.warning("⚠️ Preencha pelo menos um valor ou o KM Final.")
            elif v_km_fim and v_km_fim < v_km_ini:
                st.error("⚠️ KM Final não pode ser menor que o Inicial.")
            else:
                st.session_state['dados_temp'] = {
                    'Urbano': safe_val(v_urbano), 'Boraali': safe_val(v_bora), 
                    'app163': safe_val(v_163), 'Outros_Receita': safe_val(v_outros),
                    'Energia': safe_val(v_energia), 'Alimentacao': safe_val(v_alimentacao), 
                    'Manuten': safe_val(v_manut), 'Aplicativo': safe_val(v_app), 
                    'Outros_Custos': safe_val(v_custos), 'Seguro': safe_val(v_seguro),
                    'KM_Inicial': v_km_ini, 'KM_Final': v_km_fim if v_km_fim else v_km_ini, 
                    'Detalhes': obs
                }
                st.session_state['em_conferencia'] = True
                st.rerun()

    # --- TELA 2: CONFERÊNCIA ---
    else:
        d = st.session_state['dados_temp']
        st.markdown("### 📝 Confirmar Dados")
        
        c_res1, c_res2 = st.columns(2)
        total_ganhos = d['Urbano'] + d['Boraali'] + d['app163'] + d['Outros_Receita']
        total_gastos = d['Energia'] + d['Alimentacao'] + d['Manuten'] + d['Aplicativo'] + d['Outros_Custos'] + d['Seguro']
        
        with c_res1: st.metric("💰 RECEITA", f"R$ {total_ganhos:,.2f}")
        with c_res2: st.metric("💸 DESPESA", f"R$ {total_gastos:,.2f}", delta=f"-{total_gastos:,.2f}", delta_color="inverse")
            
        st.subheader(f"LUCRO LÍQUIDO: R$ {total_ganhos - total_gastos:,.2f}")
        
        col_voltar, col_salvar = st.columns([1, 2])
        if col_voltar.button("✏️ Editar"):
            st.session_state['em_conferencia'] = False
            st.rerun()
            
        if col_salvar.button("✅ CONFIRMAR E SALVAR", type="primary", use_container_width=True):
            with st.spinner("Salvando no banco de dados..."):
                # Geração de ID e Data com Fuso Brasil
                id_novo = str(int(time.time()))
                data_hoje = datetime.now(FUSO_BR).strftime("%Y-%m-%d")
                
                nova_linha = {
                    'ID_Unico': id_novo, 'Status': 'Ativo',
                    'Usuario': NOME_USUARIO, 'CPF': CPF_USUARIO, 'Data': data_hoje,
                    'Urbano': d['Urbano'], 'Boraali': d['Boraali'], 'app163': d['app163'], 'Outros_Receita': d['Outros_Receita'],
                    'Energia': d['Energia'], 'Manuten': d['Manuten'], 'Seguro': d['Seguro'], 'Aplicativo': d['Aplicativo'],
                    'Alimentacao': d['Alimentacao'], 'Outros_Custos': d['Outros_Custos'], 
                    'KM_Inicial': d['KM_Inicial'], 'KM_Final': d['KM_Final'], 'Detalhes': d['Detalhes']
                }
                
                try:
                    df_atual = conn.read(worksheet=0, ttl="0")
                    df_final = pd.concat([df_atual, pd.DataFrame([nova_linha])], ignore_index=True)
                    conn.update(worksheet=0, data=df_final)
                    
                    st.balloons()
                    st.toast("Dados salvos com sucesso!", icon="✅")
                    time.sleep(2)
                    st.session_state['em_conferencia'] = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao conectar com Google Sheets: {e}")

# === ABA 2: RELATÓRIOS ===
with aba_extrato:
    if not df_usuario.empty:
        # Preparação dos dados para exibição
        df_show = df_usuario.copy()
        df_show['Data'] = pd.to_datetime(df_show['Data'])
        df_show['Receita'] = df_show['Urbano'] + df_show['Boraali'] + df_show['app163'] + df_show['Outros_Receita']
        df_show['Custo'] = df_show['Energia'] + df_show['Manuten'] + df_show['Seguro'] + df_show['Aplicativo'] + df_show['Alimentacao'] + df_show['Outros_Custos']
        df_show['Lucro'] = df_show['Receita'] - df_show['Custo']
        df_show['KM_Rodado'] = df_show['KM_Final'] - df_show['KM_Inicial']
        df_show['KM_Rodado'] = df_show['KM_Rodado'].clip(lower=0)

        tipo_visao = st.radio("Filtro:", ["Detalhado", "Mensal"], horizontal=True)

        if tipo_visao == "Detalhado":
            st.dataframe(
                df_show[['Data', 'Receita', 'Custo', 'Lucro', 'KM_Rodado', 'Detalhes']].sort_values('Data', ascending=False),
                column_config={
                    "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    "Receita": st.column_config.NumberColumn("Receita", format="R$ %.2f"),
                    "Custo": st.column_config.NumberColumn("Custo", format="R$ %.2f"),
                    "Lucro": st.column_config.NumberColumn("Lucro", format="R$ %.2f")
                },
                use_container_width=True, hide_index=True
            )
        else:
            df_show['Mês'] = df_show['Data'].dt.to_period('M').astype(str)
            resumo = df_show.groupby('Mês')[['Receita', 'Custo', 'Lucro', 'KM_Rodado']].sum().reset_index()
            st.dataframe(resumo.sort_values('Mês', ascending=False), use_container_width=True, hide_index=True)
            st.bar_chart(resumo.set_index('Mês')[['Receita', 'Lucro']])

        # Lixeira com ID
        with st.expander("🗑️ Excluir lançamento"):
            id_para_deletar = st.selectbox("Escolha o ID para remover:", df_show['ID_Unico'].tolist())
            if st.button("Confirmar Exclusão"):
                with st.spinner("Removendo..."):
                    df_full = conn.read(worksheet=0, ttl="0")
                    df_full['ID_Unico'] = df_full['ID_Unico'].astype(str)
                    df_full.loc[df_full['ID_Unico'] == id_para_deletar, 'Status'] = 'Lixeira'
                    conn.update(worksheet=0, data=df_full)
                    st.success("Removido com sucesso!")
                    time.sleep(1)
                    st.rerun()
    else:
        st.info("Nenhum dado encontrado para o seu CPF.")
