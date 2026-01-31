import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
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
    
    div.stButton > button:first-child {
        border-radius: 12px; height: 3.5em; font-weight: bold; font-size: 18px !important;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
    }
    .stNumberInput input {font-size: 18px; font-weight: bold; text-align: center; padding: 10px;}
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
        if df is None or df.empty or len(df.columns) < 2:
            df_novo = pd.DataFrame(columns=COLUNAS_OFICIAIS)
            conn.update(worksheet=0, data=df_novo)
            return df_novo, "Online"
        
        mudou = False
        for col in COLUNAS_OFICIAIS:
            if col not in df.columns:
                df[col] = 0 if col not in ['Usuario', 'Data', 'Detalhes', 'Status'] else ''
                mudou = True
        
        df['ID_Unico'] = df['ID_Unico'].astype(str)
        if mudou: conn.update(worksheet=0, data=df)
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
    numeric_cols = [c for c in COLUNAS_OFICIAIS if c not in ['ID_Unico', 'Usuario', 'Data', 'Detalhes', 'Status']]
    if not df_geral.empty:
        df_geral['ID_Unico'] = df_geral['ID_Unico'].astype(str)
        for col in numeric_cols:
            if col in df_geral.columns:
                df_geral[col] = pd.to_numeric(df_geral[col], errors='coerce').fillna(0)
    
    if 'Usuario' in df_geral.columns and 'Status' in df_geral.columns:
        df_usuario = df_geral[
            (df_geral['Usuario'] == NOME_USUARIO) & 
            (df_geral['Status'] != 'Lixeira')
        ].copy()
        df_usuario['Data'] = pd.to_datetime(df_usuario['Data'], errors='coerce')
    else:
        df_usuario = pd.DataFrame(columns=COLUNAS_OFICIAIS)
except:
    df_usuario = pd.DataFrame(columns=COLUNAS_OFICIAIS)

# --- TELA PRINCIPAL ---
c_logo, c_nome = st.columns([1, 5])
with c_logo: st.markdown("## 🚘")
with c_nome: st.markdown(f"### Olá, {NOME_USUARIO.capitalize()}")

aba_lanc, aba_extrato = st.tabs(["📝 LANÇAR", "📊 RELATÓRIOS"])

# === ABA 1: LANÇAMENTO ===
with aba_lanc:
    if 'em_conferencia' not in st.session_state: st.session_state['em_conferencia'] = False
    
    # --- TELA 1: INPUT ---
    if not st.session_state['em_conferencia']:
        st.info("Preencha apenas o que teve no dia:")
        
        # AGORA VEM FECHADO (expanded=False)
        with st.expander("💰 RECEITAS (GANHOS)", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                v_urbano = st.number_input("Urbano / 99", min_value=0.0, step=10.0, key="in_urbano")
                v_bora = st.number_input("BoraAli", min_value=0.0, step=10.0, key="in_bora")
            with c2:
                v_163 = st.number_input("App 163", min_value=0.0, step=10.0, key="in_163")
                v_outros = st.number_input("Particular / Outros", min_value=0.0, step=10.0, key="in_outros")

        # AGORA VEM FECHADO (expanded=False)
        with st.expander("💸 DESPESAS (GASTOS)", expanded=False):
            c3, c4 = st.columns(2)
            with c3:
                v_energia = st.number_input("Energia / Combustível", min_value=0.0, step=10.0, key="in_energia")
                v_alimentacao = st.number_input("Alimentação / Lanche", min_value=0.0, step=10.0, key="in_alime")
                v_manut = st.number_input("Manutenção / Lavagem", min_value=0.0, step=10.0, key="in_manut")
            with c4:
                v_app = st.number_input("Apps / Internet", min_value=0.0, step=10.0, key="in_app")
                v_seguro = st.number_input("Seguro", min_value=0.0, step=10.0, key="in_seguro")
                v_custos = st.number_input("Outros Custos", min_value=0.0, step=10.0, key="in_custos")

        # KM Manual
        st.write("🚗 **Hodômetro**")
        v_km_manual = st.number_input("KM Final do Painel:", min_value=0, step=1, format="%d", key="in_km")
        obs = st.text_input("Observação (Opcional):", placeholder="Ex: Pneu furou...")

        # CÁLCULO DE LUCRO EM TEMPO REAL
        t_receita = v_urbano + v_bora + v_163 + v_outros
        t_despesa = v_energia + v_alimentacao + v_manut + v_app + v_custos + v_seguro
        t_lucro = t_receita - t_despesa
        
        st.divider()
        col_l1, col_l2, col_l3 = st.columns(3)
        col_l1.metric("Receita Hoje", f"R$ {t_receita:.2f}")
        col_l2.metric("Despesa Hoje", f"R$ {t_despesa:.2f}")
        col_l3.metric("Lucro Líquido", f"R$ {t_lucro:.2f}", delta_color="normal")

        st.write("")
        if st.button("AVANÇAR PARA CONFERÊNCIA ➡️", type="primary", use_container_width=True):
            if t_receita == 0 and t_despesa == 0 and v_km_manual == 0:
                st.warning("⚠️ Tudo zerado? Preencha algo.")
            else:
                st.session_state['dados_temp'] = {
                    'Urbano': v_urbano, 'Boraali': v_bora, 'app163': v_163, 'Outros_Receita': v_outros,
                    'Energia': v_energia, 'Alimentacao': v_alimentacao, 'Manuten': v_manut,
                    'Aplicativo': v_app, 'Outros_Custos': v_custos, 'Seguro': v_seguro,
                    'KM_Final': v_km_manual, 'Detalhes': obs
                }
                st.session_state['em_conferencia'] = True
                st.rerun()

    # --- TELA 2: CONFERÊNCIA ---
    else:
        d = st.session_state['dados_temp']
        st.markdown("### 📝 Confirmar Lançamento?")
        
        c_res1, c_res2 = st.columns(2)
        total_ganhos = d['Urbano'] + d['Boraali'] + d['app163'] + d['Outros_Receita']
        total_gastos = d['Energia'] + d['Alimentacao'] + d['Manuten'] + d['Aplicativo'] + d['Outros_Custos'] + d['Seguro']
        
        with c_res1: st.success(f"💰 Receita: R$ {total_ganhos:,.2f}")
        with c_res2: st.error(f"💸 Despesa: R$ {total_gastos:,.2f}")
            
        st.metric("LUCRO FINAL", f"R$ {total_ganhos - total_gastos:,.2f}")
        
        col_voltar, col_salvar = st.columns([1, 2])
        if col_voltar.button("✏️ Editar"):
            st.session_state['em_conferencia'] = False
            st.rerun()
            
        if col_salvar.button("✅ CONFIRMAR AGORA", type="primary", use_container_width=True):
            id_novo = str(int(time.time()))
            
            nova = {col: 0 for col in COLUNAS_OFICIAIS}
            nova.update({
                'ID_Unico': id_novo, 'Status': 'Ativo',
                'Usuario': NOME_USUARIO, 'Data': datetime.now().strftime("%Y-%m-%d"),
                'Urbano': d['Urbano'], 'Boraali': d['Boraali'], 'app163': d['app163'], 'Outros_Receita': d['Outros_Receita'],
                'Energia': d['Energia'], 'Manuten': d['Manuten'], 'Seguro': d['Seguro'], 'Aplicativo': d['Aplicativo'],
                'Alimentacao': d['Alimentacao'], 'Outros_Custos': d['Outros_Custos'], 
                'KM_Final': d['KM_Final'], 'Detalhes': d['Detalhes']
            })
            
            sucesso = False
            my_bar = st.progress(0, text="Salvando...")
            for i in range(3):
                try:
                    df_atual = conn.read(worksheet=0, ttl="0")
                    df_final = pd.concat([df_atual, pd.DataFrame([nova])], ignore_index=True)
                    conn.update(worksheet=0, data=df_final)
                    sucesso = True; break
                except: time.sleep(1)
            my_bar.empty()
            
            if sucesso:
                st.balloons()
                st.toast("Sucesso!", icon="✅")
                time.sleep(1)
                st.session_state['em_conferencia'] = False
                st.rerun()
            else: st.error("Erro ao salvar. Tente de novo.")

# === ABA 2: RELATÓRIOS ===
with aba_extrato:
    if not df_usuario.empty:
        tipo_visao = st.radio("Visualizar:", ["📅 Dia a Dia (Detalhado)", "🗓️ Mensal (Gestão)", "📆 Anual"], horizontal=True)
        
        df_show = df_usuario.copy()
        df_show['Receita_Total'] = df_show['Urbano'] + df_show['Boraali'] + df_show['app163'] + df_show['Outros_Receita']
        df_show['Custo_Total'] = df_show['Energia'] + df_show['Manuten'] + df_show['Seguro'] + df_show['Aplicativo'] + df_show['Alimentacao'] + df_show['Outros_Custos']
        df_show['Lucro'] = df_show['Receita_Total'] - df_show['Custo_Total']
        
        if "Dia a Dia" in tipo_visao:
            st.caption("Lista de lançamentos recentes.")
            cols = ['Data', 'Receita_Total', 'Custo_Total', 'Lucro', 'Energia', 'Alimentacao', 'KM_Final', 'Detalhes']
            st.dataframe(df_show[cols].sort_values('Data', ascending=False), use_container_width=True, hide_index=True)
            
            st.divider()
            with st.expander("🗑️ Excluir Lançamento"):
                lista = df_show.sort_values('Data', ascending=False).head(20).to_dict('records')
                if lista:
                    opts = {f"{r['Data'].strftime('%d/%m')} | R$ {r['Receita_Total']:.0f} (ID {r['ID_Unico']})": str(r['ID_Unico']) for r in lista}
                    sel = st.selectbox("Selecione o item:", list(opts.keys()))
                    
                    if st.button("🗑️ Apagar Item"):
                        try:
                            df_full = conn.read(worksheet=0, ttl="0")
                            df_full['ID_Unico'] = df_full['ID_Unico'].astype(str)
                            id_alvo = opts[sel]
                            
                            if id_alvo in df_full['ID_Unico'].values:
                                df_full.loc[df_full['ID_Unico'] == id_alvo, 'Status'] = 'Lixeira'
                                conn.update(worksheet=0, data=df_full)
                                st.success("Apagado com sucesso!")
                                time.sleep(1)
                                st.rerun()
                            else: st.error("Erro: ID não encontrado.")
                        except Exception as e: st.error(f"Erro: {e}")
                else: st.info("Sem dados recentes.")

        else:
            if "Mensal" in tipo_visao: df_show['Periodo'] = df_show['Data'].dt.to_period('M').astype(str)
            else: df_show['Periodo'] = df_show['Data'].dt.to_period('Y').astype(str)
            
            resumo = df_show.groupby('Periodo')[['Receita_Total', 'Custo_Total', 'Lucro', 'KM_Final', 'Energia']].sum().reset_index()
            resumo['R$/KM'] = resumo.apply(lambda x: x['Receita_Total'] / x['KM_Final'] if x['KM_Final'] > 0 else 0, axis=1)
            resumo['Custo/KM'] = resumo.apply(lambda x: x['Custo_Total'] / x['KM_Final'] if x['KM_Final'] > 0 else 0, axis=1)
            resumo['Lucro/KM'] = resumo.apply(lambda x: x['Lucro'] / x['KM_Final'] if x['KM_Final'] > 0 else 0, axis=1)
            
            st.markdown(f"### 📊 Relatório {tipo_visao}")
            st.dataframe(
                resumo.sort_values('Periodo', ascending=False),
                column_config={
                    "Receita_Total": st.column_config.NumberColumn("Receita", format="R$ %.2f"),
                    "Custo_Total": st.column_config.NumberColumn("Custos", format="R$ %.2f"),
                    "Lucro": st.column_config.NumberColumn("Lucro Líquido", format="R$ %.2f"),
                    "R$/KM": st.column_config.NumberColumn("R$/KM", format="R$ %.2f"),
                    "Lucro/KM": st.column_config.NumberColumn("Lucro/KM", format="R$ %.2f"),
                },
                use_container_width=True, hide_index=True
            )
            st.bar_chart(resumo.set_index('Periodo')[['Receita_Total', 'Lucro']])
    else: st.info("Sem dados para exibir.")
