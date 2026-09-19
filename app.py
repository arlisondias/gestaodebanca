import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime

# Configuração da página para Mobile e Desktop
st.set_page_config(
    page_title="Gestão de Banca - Futebol",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- BANCO DE DADOS (SQLite) ---
def init_db():
    conn = sqlite3.connect('banca_futebol.db')
    c = conn.cursor()
    # Tabela de Movimentações (Depósitos e Saques)
    c.execute('''
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data DATE,
            casa TEXT,
            tipo TEXT,
            valor REAL
        )
    ''')
    # Tabela de Apostas (Baseada no modelo da sua planilha)
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
    conn.commit()
    conn.close()

init_db()

def get_connection():
    return sqlite3.connect('banca_futebol.db')

# --- TITULO ---
st.title("⚽ Gestão de Banca & Analytics")

# --- NAVEGAÇÃO SUPERIOR ---
aba1, aba2, aba3, aba4 = st.tabs(["📊 Dashboard & Analytics", "➕ Nova Aposta", "💰 Depósito / Saque", "📋 Histórico"])

# ==========================================
# ABA 1: DASHBOARD & METRICAS DE ANALISTA
# ==========================================
with aba1:
    conn = get_connection()
    df_apostas = pd.read_sql_query("SELECT * FROM apostas", conn)
    df_mov = pd.read_sql_query("SELECT * FROM movimentacoes", conn)
    conn.close()

    if not df_apostas.empty:
        df_apostas['data'] = pd.to_datetime(df_apostas['data'])

        # Sidebar de Filtros
        st.sidebar.header("🔍 Filtros de Análise")
        casas = ["Todas"] + list(df_apostas['casa'].unique())
        casa_sel = st.sidebar.selectbox("Casa de Aposta", casas)
        
        estrategias = ["Todas"] + list(df_apostas['estrategia'].unique())
        est_sel = st.sidebar.selectbox("Estratégia", estrategias)

        # Aplicando Filtros
        df_filtered = df_apostas.copy()
        if casa_sel != "Todas":
            df_filtered = df_filtered[df_filtered['casa'] == casa_sel]
        if est_sel != "Todas":
            df_filtered = df_filtered[df_filtered['estrategia'] == est_sel]

        # Cálculos de Métricas
        total_investido = df_filtered['stake'].sum()
        lucro_total = df_filtered['lucro'].sum()
        roi = (lucro_total / total_investido * 100) if total_investido > 0 else 0
        total_apostas = len(df_filtered)
        greens = len(df_filtered[df_filtered['resultado'] == 'green'])
        win_rate = (greens / total_apostas * 100) if total_apostas > 0 else 0
        odd_media = df_filtered['odd'].mean() if total_apostas > 0 else 0

        # Totais de Depósitos e Saques
        dep = df_mov[df_mov['tipo'] == 'Depósito']['valor'].sum() if not df_mov.empty else 0
        saq = df_mov[df_mov['tipo'] == 'Saque']['valor'].sum() if not df_mov.empty else 0
        saldo_banca = dep - saq + df_apostas['lucro'].sum()

        # Display KPIs
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Saldo da Banca", f"R$ {saldo_banca:.2f}")
        kpi2.metric("Lucro Líquido", f"R$ {lucro_total:.2f}", delta=f"{lucro_total:.2f}")
        kpi3.metric("ROI (%)", f"{roi:.2f}%")
        kpi4.metric("Win Rate (%)", f"{win_rate:.1f}%")

        st.markdown("---")

        # Gráfico 1: Evolução do Patrimônio (Curva de Lucro acumulado)
        df_filtered = df_filtered.sort_values('data')
        df_filtered['lucro_acumulado'] = df_filtered['lucro'].cumsum()
        
        fig_curva = px.line(
            df_filtered, 
            x='data', 
            y='lucro_acumulado', 
            title="📈 Curva de Crescimento da Banca (Lucro Acumulado)",
            labels={'data': 'Data', 'lucro_acumulado': 'Lucro (R$)'},
            markers=True
        )
        st.plotly_chart(fig_curva, use_container_width=True)

        col_g1, col_g2 = st.columns(2)
        
        # Gráfico 2: Desempenho por Estratégia
        with col_g1:
            df_est = df_filtered.groupby('estrategia')['lucro'].sum().reset_index()
            fig_est = px.bar(
                df_est, 
                x='estrategia', 
                y='lucro', 
                color='lucro',
                title="🎯 Lucro/Prejuízo por Estratégia",
                labels={'estrategia': 'Estratégia', 'lucro': 'Lucro (R$)'}
            )
            st.plotly_chart(fig_est, use_container_width=True)

        # Gráfico 3: Distribuição dos Resultados
        with col_g2:
            df_res = df_filtered['resultado'].value_counts().reset_index()
            df_res.columns = ['resultado', 'quantidade']
            fig_pie = px.pie(
                df_res, 
                names='resultado', 
                values='quantidade', 
                title="📊 Distribuição dos Resultados",
                hole=0.4
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    else:
        st.info("Nenhuma aposta cadastrada ainda. Utilize a aba 'Nova Aposta' para registrar suas entradas.")

# ==========================================
# ABA 2: CADASTRO DE NOVAS APOSTAS
# ==========================================
with aba2:
    st.subheader("Registrar Movimento no Mercado")
    with st.form("form_aposta", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data_aposta = st.date_input("Data da Aposta", datetime.today())
            casa = st.selectbox("Casa de Aposta", ["Bet365", "Betano", "Outra"])
            evento = st.text_input("Evento / Jogo", placeholder="Ex: Flamengo vs Palmeiras")
            estrategia = st.text_input("Estratégia", placeholder="Ex: Over 2.5, Handicap +0.5, Cantos")
        
        with col2:
            stake = st.number_input("Valor Apostado (Stake R$)", min_value=0.01, step=1.0)
            odd = st.number_input("Odd Cotada", min_value=1.01, step=0.01)
            resultado = st.selectbox("Resultado", ["green", "red", "push", "cashout"])
            cash = st.number_input("Valor Retornado (Se foi Cashout)", min_value=0.0, step=1.0)

        submit = st.form_submit_button("Salvar Aposta")

        if submit:
            # Cálculo de Lucro seguindo a lógica da sua planilha
            if resultado == "green":
                lucro = (stake * odd) - stake
            elif resultado == "red":
                lucro = -stake
            elif resultado == "push":
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
# ABA 3: DEPÓSITOS E SAQUES
# ==========================================
with aba3:
    st.subheader("Gerenciar Entradas e Saídas da Banca")
    with st.form("form_mov"):
        data_mov = st.date_input("Data", datetime.today())
        casa_mov = st.selectbox("Casa de Aposta", ["Bet365", "Betano", "Outra"])
        tipo_mov = st.selectbox("Tipo de Operação", ["Depósito", "Saque"])
        valor_mov = st.number_input("Valor (R$)", min_value=0.01, step=10.0)
        
        submit_mov = st.form_submit_button("Registrar Movimentação")
        if submit_mov:
            conn = get_connection()
            c = conn.cursor()
            c.execute('''
                INSERT INTO movimentacoes (data, casa, tipo, valor)
                VALUES (?, ?, ?, ?)
            ''', (data_mov, casa_mov, tipo_mov, valor_mov))
            conn.commit()
            conn.close()
            st.success(f"{tipo_mov} de R$ {valor_mov:.2f} em {casa_mov} registrado!")
            st.rerun()

# ==========================================
# ABA 4: HISTÓRICO & EDICÃO
# ==========================================
with aba4:
    st.subheader("Histórico Completo de Apostas")
    conn = get_connection()
    df_hist = pd.read_sql_query("SELECT * FROM apostas ORDER BY data DESC", conn)
    conn.close()
    
    if not df_hist.empty:
        st.dataframe(df_hist, use_container_width=True)
    else:
        st.write("Nenhum registro encontrado.")