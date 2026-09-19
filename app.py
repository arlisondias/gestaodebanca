import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA E DESIGN BLACK MODE
# ---------------------------------------------------------
st.set_page_config(
    page_title="Gestão de Banca Pro",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilização CSS Customizada (Modern Dark / Black Theme)
st.markdown("""
    <style>
    /* Fundo Geral e Cores Globais */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    
    /* Estilização dos Cards de Métricas (KPIs) */
    div[data-testid="stMetric"] {
        background-color: #161B22;
        border: 1px solid #30363D;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    
    /* Abas Customizadas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #161B22;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        color: #8B949E;
        border: 1px solid #30363D;
    }
    .stTabs [aria-selected="true"] {
        background-color: #21262D !important;
        color: #00FF7F !important; /* Verde Neon */
        border-bottom: 2px solid #00FF7F !important;
    }
    
    /* Botões */
    .stButton>button {
        background-color: #238636;
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #2EA043;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# BANCO DE DADOS (SQLite)
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect('banca_futebol.db')
    c = conn.cursor()
    
    # Tabelas Auxiliares (Cadastros)
    c.execute('''CREATE TABLE IF NOT EXISTS bancas (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS estrategias (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE)''')
    
    # Tabelas Financeiras
    c.execute('''
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data DATE,
            casa TEXT,
            tipo TEXT,
            valor REAL
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS apostas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data DATE,
            casa TEXT,
            evento TEXT,
            estrategia TEXT,
            stake REAL,
            odd REAL,
            resultado TEXT,
            cash REAL,
            lucro REAL
        )
    ''')
    
    # Inserir bancas padrão se estiver vazio
    c.execute("INSERT OR IGNORE INTO bancas (nome) VALUES ('Bet365'), ('Betano')")
    # Inserir estratégia padrão se estiver vazio
    c.execute("INSERT OR IGNORE INTO estrategias (nome) VALUES ('Over Gols'), ('Handicap'), ('Ambas Marcam')")
    
    conn.commit()
    conn.close()

init_db()

def get_connection():
    return sqlite3.connect('banca_futebol.db')

# ---------------------------------------------------------
# INTERFACE PRINCIPAL
# ---------------------------------------------------------
st.title("⚽ Gestão de Banca & Analytics Pro")

aba1, aba2, aba3, aba4, aba5 = st.tabs([
    "📊 Dashboard", 
    "➕ Nova Aposta", 
    "📋 Histórico", 
    "💰 Depósitos / Saques", 
    "⚙️ Cadastros"
])

# ==========================================
# ABA 1: DASHBOARD & METRICAS
# ==========================================
with aba1:
    conn = get_connection()
    df_apostas = pd.read_sql_query("SELECT * FROM apostas", conn)
    df_mov = pd.read_sql_query("SELECT * FROM movimentacoes", conn)
    conn.close()

    if not df_apostas.empty:
        df_apostas['data'] = pd.to_datetime(df_apostas['data'])

        # Filtros Globais
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            casas_list = ["Todas"] + list(df_apostas['casa'].unique())
            casa_sel = st.selectbox("Filtrar por Banca/Casa", casas_list)
        with col_f2:
            est_list = ["Todas"] + list(df_apostas['estrategia'].unique())
            est_sel = st.selectbox("Filtrar por Estratégia", est_list)

        # Aplicar Filtros
        df_filtered = df_apostas.copy()
        if casa_sel != "Todas":
            df_filtered = df_filtered[df_filtered['casa'] == casa_sel]
        if est_sel != "Todas":
            df_filtered = df_filtered[df_filtered['estrategia'] == est_sel]

        # Separação de Concluídas x Pendentes
        df_concluidas = df_filtered[df_filtered['resultado'] != 'pendente']
        df_pendentes = df_filtered[df_filtered['resultado'] == 'pendente']

        # Cálculos das Métricas
        total_investido = df_concluidas['stake'].sum()
        lucro_total = df_concluidas['lucro'].sum()
        roi = (lucro_total / total_investido * 100) if total_investido > 0 else 0
        
        total_concluidas = len(df_concluidas)
        greens = len(df_concluidas[df_concluidas['resultado'] == 'green'])
        win_rate = (greens / total_concluidas * 100) if total_concluidas > 0 else 0

        dep = df_mov[df_mov['tipo'] == 'Depósito']['valor'].sum() if not df_mov.empty else 0
        saq = df_mov[df_mov['tipo'] == 'Saque']['valor'].sum() if not df_mov.empty else 0
        saldo_banca = dep - saq + df_apostas['lucro'].sum()

        # Display KPIs
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Saldo da Banca", f"R$ {saldo_banca:.2f}")
        k2.metric("Lucro Líquido", f"R$ {lucro_total:.2f}", delta=f"{lucro_total:.2f}")
        k3.metric("ROI (%)", f"{roi:.2f}%")
        k4.metric("Win Rate (%)", f"{win_rate:.1f}%")
        k5.metric("Apostas Pendentes", f"{len(df_pendentes)}")

        st.markdown("<br>", unsafe_allow_html=True)

        # Gráficos em Modo Dark
        if not df_concluidas.empty:
            df_concluidas = df_concluidas.sort_values('data')
            df_concluidas['lucro_acumulado'] = df_concluidas['lucro'].cumsum()
            
            fig_curva = px.line(
                df_concluidas, 
                x='data', 
                y='lucro_acumulado', 
                title="📈 Curva de Crescimento da Banca",
                markers=True,
                template="plotly_dark"
            )
            fig_curva.update_traces(line_color="#00FF7F")
            st.plotly_chart(fig_curva, use_container_width=True)

            cg1, cg2 = st.columns(2)
            with cg1:
                df_est = df_concluidas.groupby('estrategia')['lucro'].sum().reset_index()
                fig_est = px.bar(
                    df_est, 
                    x='estrategia', 
                    y='lucro', 
                    title="🎯 Lucro por Estratégia",
                    color='lucro',
                    template="plotly_dark"
                )
                st.plotly_chart(fig_est, use_container_width=True)

            with cg2:
                df_res = df_filtered['resultado'].value_counts().reset_index()
                df_res.columns = ['resultado', 'quantidade']
                fig_pie = px.pie(
                    df_res, 
                    names='resultado', 
                    values='quantidade', 
                    title="📊 Distribuição dos Status/Resultados",
                    hole=0.4,
                    template="plotly_dark"
                )
                st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Nenhuma aposta cadastrada no sistema.")

# ==========================================
# ABA 2: REGISTRO DE NOVA APOSTA
# ==========================================
with aba2:
    st.subheader("Registrar Nova Entrada")
    
    conn = get_connection()
    bancas_df = pd.read_sql_query("SELECT nome FROM bancas", conn)
    est_df = pd.read_sql_query("SELECT nome FROM estrategias", conn)
    conn.close()

    if bancas_df.empty or est_df.empty:
        st.warning("Cadastre ao menos uma banca e uma estratégia na aba '⚙️ Cadastros' antes de apostar.")
    else:
        with st.form("form_aposta", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                data_aposta = st.date_input("Data da Aposta", datetime.today())
                casa = st.selectbox("Banca / Casa", bancas_df['nome'].tolist())
                evento = st.text_input("Evento / Jogo", placeholder="Ex: Real Madrid vs Barcelona")
                estrategia = st.selectbox("Estratégia", est_df['nome'].tolist())
            
            with col2:
                stake = st.number_input("Valor Apostado (Stake R$)", min_value=0.01, step=5.0)
                odd = st.number_input("Odd Cotada", min_value=1.01, step=0.05)
                resultado = st.selectbox("Resultado / Status", ["pendente", "green", "red", "push", "cashout"])
                cash = st.number_input("Valor Retornado (Se foi Cashout)", min_value=0.0, step=1.0)

            submit = st.form_submit_button("Salvar Aposta")

            if submit:
                # Cálculo de Lucro conforme o status
                if resultado == "green":
                    lucro = (stake * odd) - stake
                elif resultado == "red":
                    lucro = -stake
                elif resultado in ["push", "pendente"]:
                    lucro = 0.0
                elif resultado == "cashout":
                    lucro = cash - stake

                conn = get_connection()
                c = conn.cursor()
                c.execute('''
                    INSERT INTO apostas (data, casa, evento, estrategia, stake, odd, resultado, cash, lucro)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (data_aposta, casa, evento, estrategia, stake, odd, resultado, cash if resultado == 'cashout' else None, lucro))
                conn.commit()
                conn.close()
                st.success("Aposta registrada com sucesso!")
                st.rerun()

# ==========================================
# ABA 3: HISTÓRICO E EDIÇÃO
# ==========================================
with aba3:
    st.subheader("Histórico de Apostas")
    conn = get_connection()
    df_hist = pd.read_sql_query("SELECT * FROM apostas ORDER BY data DESC", conn)
    conn.close()

    if not df_hist.empty:
        # Tabela editável diretamente pelo Streamlit
        df_edited = st.data_editor(
            df_hist, 
            num_rows="dynamic",
            column_config={
                "resultado": st.column_config.SelectboxColumn(
                    "Resultado",
                    options=["pendente", "green", "red", "push", "cashout"],
                    required=True
                )
            },
            use_container_width=True
        )
        
        if st.button("Salvar Alterações do Histórico"):
            # Recalcular lucros para itens atualizados na tabela
            for idx, row in df_edited.iterrows():
                res = row['resultado']
                stk = row['stake']
                od = row['odd']
                csh = row['cash'] if pd.notnull(row['cash']) else 0.0
                
                if res == "green":
                    lucro_calc = (stk * od) - stk
                elif res == "red":
                    lucro_calc = -stk
                elif res in ["push", "pendente"]:
                    lucro_calc = 0.0
                elif res == "cashout":
                    lucro_calc = csh - stk
                else:
                    lucro_calc = 0.0

                df_edited.at[idx, 'lucro'] = lucro_calc

            conn = get_connection()
            c = conn.cursor()
            c.execute("DELETE FROM apostas")
            for _, row in df_edited.iterrows():
                c.execute('''
                    INSERT INTO apostas (id, data, casa, evento, estrategia, stake, odd, resultado, cash, lucro)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (row['id'], row['data'], row['casa'], row['evento'], row['estrategia'], row['stake'], row['odd'], row['resultado'], row['cash'], row['lucro']))
            conn.commit()
            conn.close()
            st.success("Histórico atualizado com sucesso!")
            st.rerun()
    else:
        st.info("Nenhum registro encontrado.")

# ==========================================
# ABA 4: DEPÓSITOS E SAQUES
# ==========================================
with aba4:
    st.subheader("Gestão de Movimentações Financeiras")
    conn = get_connection()
    bancas_df = pd.read_sql_query("SELECT nome FROM bancas", conn)
    conn.close()

    if not bancas_df.empty:
        with st.form("form_mov", clear_on_submit=True):
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                data_mov = st.date_input("Data", datetime.today())
                casa_mov = st.selectbox("Banca / Casa", bancas_df['nome'].tolist())
            with col_m2:
                tipo_mov = st.selectbox("Tipo de Operação", ["Depósito", "Saque"])
                valor_mov = st.number_input("Valor (R$)", min_value=1.0, step=10.0)

            submit_mov = st.form_submit_button("Registrar Operação")
            if submit_mov:
                conn = get_connection()
                c = conn.cursor()
                c.execute('''
                    INSERT INTO movimentacoes (data, casa, tipo, valor)
                    VALUES (?, ?, ?, ?)
                ''', (data_mov, casa_mov, tipo_mov, valor_mov))
                conn.commit()
                conn.close()
                st.success(f"{tipo_mov} registrado com sucesso!")
                st.rerun()

# ==========================================
# ABA 5: CADASTROS (BANCAS E ESTRATÉGIAS)
# ==========================================
with aba5:
    st.subheader("Configuração de Bancas & Estratégias")
    
    col_cad1, col_cad2 = st.columns(2)
    
    # Gerenciar Bancas
    with col_cad1:
        st.markdown("### 🏦 Bancas / Casas de Aposta")
        nova_banca = st.text_input("Nome da Nova Banca")
        if st.button("Cadastrar Banca"):
            if nova_banca.strip():
                try:
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO bancas (nome) VALUES (?)", (nova_banca.strip(),))
                    conn.commit()
                    conn.close()
                    st.success(f"Banca '{nova_banca}' adicionada!")
                    st.rerun()
                except:
                    st.error("Esta banca já está cadastrada.")
        
        conn = get_connection()
        bancas_atual = pd.read_sql_query("SELECT * FROM bancas", conn)
        conn.close()
        st.dataframe(bancas_atual[['nome']], use_container_width=True)

    # Gerenciar Estratégias
    with col_cad2:
        st.markdown("### 🎯 Estratégias")
        nova_est = st.text_input("Nome da Nova Estratégia")
        if st.button("Cadastrar Estratégia"):
            if nova_est.strip():
                try:
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO estrategias (nome) VALUES (?)", (nova_est.strip(),))
                    conn.commit()
                    conn.close()
                    st.success(f"Estratégia '{nova_est}' adicionada!")
                    st.rerun()
                except:
                    st.error("Esta estratégia já está cadastrada.")
                    
        conn = get_connection()
        est_atual = pd.read_sql_query("SELECT * FROM estrategias", conn)
        conn.close()
        st.dataframe(est_atual[['nome']], use_container_width=True)
