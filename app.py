import os
import shutil

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from auth import tela_login, logout, verificar_login
from database import criar_tabelas, conectar
from clientes import tela_clientes
from veiculos import tela_veiculos
from contratos import tela_contratos
from vistorias import tela_vistorias
from odometro import tela_odometro
from manutencoes import tela_manutencoes
from despesas import tela_despesas
from financeiro import tela_financeiro
from locador import tela_locador


st.set_page_config(
    page_title="Locadora System Premium",
    page_icon="🚗",
    layout="wide"
)


# ==========================================
# ESTILO
# ==========================================

def aplicar_estilo_premium():
    st.markdown("""
    <style>
    .main > div {
        padding-top: 1rem;
    }

    .block-container {
        padding-top: 0.9rem;
        padding-bottom: 2rem;
    }

    [data-testid="stSidebar"] {
        background:
            radial-gradient(circle at top left, rgba(37, 99, 235, 0.18), transparent 32%),
            linear-gradient(180deg, #081120 0%, #0f172a 48%, #111827 100%);
        border-right: 1px solid rgba(255,255,255,0.05);
    }

    [data-testid="stSidebar"] * {
        color: #f8fafc;
    }

    [data-testid="stSidebar"] .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        padding-left: 0.8rem;
        padding-right: 0.8rem;
    }

    .sidebar-brand {
        padding: 8px 6px 16px 6px;
        border-bottom: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 14px;
    }

    .sidebar-brand-title {
        font-size: 1.22rem;
        font-weight: 900;
        color: #f8fafc;
        margin-bottom: 3px;
        letter-spacing: -0.02em;
    }

    .sidebar-brand-sub {
        font-size: 0.84rem;
        color: #cbd5e1;
    }

    .sidebar-user-pill {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 14px;
        padding: 10px 12px;
        margin-top: 12px;
        margin-bottom: 12px;
    }

    .sidebar-user-pill-label {
        font-size: 0.75rem;
        color: #94a3b8;
        margin-bottom: 2px;
    }

    .sidebar-user-pill-value {
        font-size: 0.92rem;
        font-weight: 800;
        color: #f8fafc;
    }

    .sidebar-dot {
        width: 10px;
        height: 10px;
        border-radius: 999px;
        background: #22c55e;
        box-shadow: 0 0 0 4px rgba(34,197,94,0.14);
        flex-shrink: 0;
    }

    .menu-status {
        background: linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.03) 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 14px;
        padding: 11px 12px;
        margin-top: 12px;
        margin-bottom: 14px;
    }

    .menu-status-label {
        color: #94a3b8;
        font-size: 0.76rem;
        margin-bottom: 3px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .menu-status-value {
        color: #f8fafc;
        font-size: 0.96rem;
        font-weight: 800;
    }

    .sidebar-group {
        margin-top: 14px;
        margin-bottom: 10px;
        padding: 10px;
        border-radius: 16px;
        background: rgba(255,255,255,0.025);
        border: 1px solid rgba(255,255,255,0.05);
    }

    .sidebar-section {
        margin-top: 0;
        margin-bottom: 10px;
        font-size: 0.76rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #94a3b8;
    }

    .sidebar-footer-note {
        color: #94a3b8;
        font-size: 0.78rem;
        text-align: center;
        margin-top: 8px;
    }

    .sidebar-admin-box {
        margin-top: 14px;
        padding: 12px;
        border-radius: 16px;
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.18);
    }

    [data-testid="stSidebar"] .stButton > button {
        min-height: 44px;
        border-radius: 12px;
        font-weight: 800;
        border: 1px solid rgba(255,255,255,0.08);
        background: linear-gradient(180deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.02) 100%);
        color: #f8fafc;
        transition: all 0.18s ease;
        box-shadow: none;
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        border-color: rgba(96, 165, 250, 0.55);
        background: linear-gradient(180deg, rgba(59,130,246,0.18) 0%, rgba(59,130,246,0.10) 100%);
        transform: translateY(-1px);
    }

    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        border-color: rgba(96, 165, 250, 0.65);
        background: linear-gradient(180deg, rgba(37, 99, 235, 0.34) 0%, rgba(29, 78, 216, 0.20) 100%);
        box-shadow: 0 8px 20px rgba(37, 99, 235, 0.18);
    }

    .premium-card {
        background: linear-gradient(180deg, #111827 0%, #0f172a 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 18px;
        padding: 18px 18px 14px 18px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.18);
        margin-bottom: 12px;
    }

    .premium-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #e5e7eb;
        margin-bottom: 6px;
    }

    .premium-subtitle {
        font-size: 0.92rem;
        color: #94a3b8;
        margin-bottom: 0;
    }

    .top-hero {
        background: linear-gradient(135deg, #0f172a 0%, #111827 55%, #172554 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 22px;
        padding: 22px 22px 18px 22px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.18);
        margin-bottom: 16px;
    }

    .top-hero-title {
        font-size: 1.35rem;
        font-weight: 800;
        color: #f8fafc;
        margin-bottom: 4px;
    }

    .top-hero-sub {
        font-size: 0.95rem;
        color: #cbd5e1;
        margin-bottom: 0;
    }

    .section-title {
        font-size: 1.06rem;
        font-weight: 800;
        margin-top: 0.4rem;
        margin-bottom: 0.8rem;
        color: #e5e7eb;
    }

    .small-note {
        color: #94a3b8;
        font-size: 0.88rem;
    }

    .menu-status {
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 14px;
        padding: 10px 12px;
        margin-top: 12px;
        margin-bottom: 12px;
    }

    .menu-status-label {
        color: #94a3b8;
        font-size: 0.8rem;
        margin-bottom: 2px;
    }

    .menu-status-value {
        color: #f8fafc;
        font-size: 0.95rem;
        font-weight: 700;
    }

    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, #111827 0%, #0b1220 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
        padding: 10px 12px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.12);
        min-height: 96px;
    }

    div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-size: 0.78rem !important;
        line-height: 1.15 !important;
    }

    div[data-testid="stMetricValue"] {
        color: #f8fafc !important;
        font-size: 1.12rem !important;
        font-weight: 800 !important;
        line-height: 1.1 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    div[data-testid="stMetricDelta"] {
        font-size: 0.72rem !important;
    }

    @media (max-width: 1400px) {
        div[data-testid="stMetricValue"] {
            font-size: 1.0rem !important;
        }
    }

    @media (max-width: 1100px) {
        div[data-testid="stMetricValue"] {
            font-size: 0.92rem !important;
        }
        div[data-testid="stMetricLabel"] {
            font-size: 0.72rem !important;
        }
    }

    .stButton > button {
        border-radius: 12px;
        font-weight: 700;
        border: 1px solid rgba(255,255,255,0.08);
        width: 100%;
    }

    .stDownloadButton > button {
        border-radius: 12px;
        font-weight: 700;
    }

    .menu-chip {
        display: inline-block;
        font-size: 0.8rem;
        font-weight: 700;
        color: #cbd5e1;
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 999px;
        padding: 6px 10px;
        margin-right: 6px;
        margin-bottom: 6px;
    }

    .chart-card {
        background: linear-gradient(180deg, #111827 0%, #0b1220 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 18px;
        padding: 14px;
        min-height: 330px;
        box-shadow: 0 8px 22px rgba(0,0,0,0.12);
        margin-bottom: 10px;
    }

    .chart-card-title {
        color: #e5e7eb;
        font-size: 0.96rem;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .chart-card-sub {
        color: #94a3b8;
        font-size: 0.82rem;
        margin-bottom: 8px;
    }

    .priority-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
        margin-bottom: 14px;
    }

    .priority-card {
        border-radius: 18px;
        padding: 14px 16px;
        border: 1px solid rgba(255,255,255,0.06);
        box-shadow: 0 8px 22px rgba(0,0,0,0.12);
        min-height: 118px;
    }

    .priority-card-red {
        background: linear-gradient(180deg, rgba(127, 29, 29, 0.75) 0%, rgba(69, 10, 10, 0.88) 100%);
        border-color: rgba(248, 113, 113, 0.25);
    }

    .priority-card-yellow {
        background: linear-gradient(180deg, rgba(120, 53, 15, 0.76) 0%, rgba(67, 20, 7, 0.88) 100%);
        border-color: rgba(251, 191, 36, 0.24);
    }

    .priority-card-blue {
        background: linear-gradient(180deg, rgba(30, 58, 138, 0.76) 0%, rgba(23, 37, 84, 0.88) 100%);
        border-color: rgba(96, 165, 250, 0.24);
    }

    .priority-label {
        color: rgba(255,255,255,0.78);
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 7px;
        font-weight: 800;
    }

    .priority-value {
        color: #f8fafc;
        font-size: 1.55rem;
        font-weight: 900;
        line-height: 1;
        margin-bottom: 8px;
    }

    .priority-desc {
        color: rgba(255,255,255,0.90);
        font-size: 0.86rem;
        line-height: 1.35;
    }

    @media (max-width: 900px) {
        .priority-grid {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """, unsafe_allow_html=True)


# ==========================================
# BOOTSTRAP
# ==========================================

criar_tabelas()
aplicar_estilo_premium()

if "logado" not in st.session_state:
    st.session_state["logado"] = False

if "usuario" not in st.session_state:
    st.session_state["usuario"] = ""

if "pagina_atual" not in st.session_state:
    st.session_state["pagina_atual"] = "Início"


# ==========================================
# HELPERS
# ==========================================

def formatar_moeda(valor):
    try:
        valor = float(valor or 0)
    except Exception:
        valor = 0.0
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def classificar_alerta(km_atual, km_limite):
    if km_limite is None or km_limite == 0:
        return None

    diferenca = km_limite - km_atual

    if diferenca < 0:
        return "Vencido"
    if diferenca <= 500:
        return "Urgente"
    if diferenca <= 1500:
        return "Próximo"
    return None


def classificar_status_pagamento_item(valor_previsto, valor_pago, data_vencimento):
    valor_previsto = float(valor_previsto or 0.0)
    valor_pago = float(valor_pago or 0.0)

    if valor_previsto > 0 and valor_pago >= valor_previsto:
        return "Pago"

    if valor_pago > 0:
        return "Parcial"

    data_venc = pd.to_datetime(data_vencimento, errors="coerce")
    hoje = pd.Timestamp.today().normalize()

    if pd.notna(data_venc) and data_venc.normalize() < hoje:
        return "Vencido"

    return "Pendente"


def renderizar_grafico_rosca(labels, valores, titulo, texto_centro, figsize=(3.1, 3.1)):
    bg_color = "#0b1220"
    text_color = "#e5e7eb"
    grid_color = "#334155"

    plt.rcParams.update({
        "figure.facecolor": bg_color,
        "axes.facecolor": bg_color,
        "savefig.facecolor": bg_color,
        "text.color": text_color,
        "axes.labelcolor": text_color,
        "xtick.color": text_color,
        "ytick.color": text_color,
        "axes.edgecolor": grid_color,
        "font.size": 10,
    })

    total = sum(valores)
    if total <= 0:
        st.markdown("""
        <div style="
            background: linear-gradient(180deg, #111827 0%, #0b1220 100%);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 18px;
            min-height: 250px;
            display:flex;
            align-items:center;
            justify-content:center;
            color:#94a3b8;
            text-align:center;
            padding:14px;">
            Sem dados suficientes para o gráfico.
        </div>
        """, unsafe_allow_html=True)
        return

    fig, ax = plt.subplots(figsize=figsize)
    wedges, _ = ax.pie(
        valores,
        labels=None,
        startangle=90,
        wedgeprops={"width": 0.32, "edgecolor": bg_color, "linewidth": 2}
    )

    ax.text(
        0, 0, texto_centro,
        ha="center", va="center",
        fontsize=9, color=text_color, fontweight="bold"
    )
    ax.set_title(titulo, fontsize=9, pad=8, color=text_color)
    ax.axis("equal")

    legend_labels = []
    for label, valor in zip(labels, valores):
        percentual = 0 if total == 0 else round((valor / total) * 100)
        legend_labels.append(f"{label}: {valor} ({percentual}%)")

    ax.legend(
        wedges,
        legend_labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.14),
        ncol=2,
        frameon=False,
        fontsize=7,
        labelcolor=text_color
    )

    fig.subplots_adjust(top=0.86, bottom=0.24)
    st.pyplot(fig, clear_figure=True, use_container_width=True)


def montar_alertas_manutencao(df_manut):
    alertas = []

    if df_manut.empty:
        return pd.DataFrame()

    itens = [
        ("Troca de óleo", "proxima_troca_oleo"),
        ("Revisão", "km_prox_revisao"),
        ("Pneus", "km_prox_pneu"),
        ("Freios", "km_prox_freio"),
        ("Bateria", "km_prox_bateria"),
    ]

    for _, row in df_manut.iterrows():
        veiculo = f"{row['modelo']} - {row['placa']}"
        km_atual = row["km_atual"]

        for nome_item, coluna in itens:
            km_limite = row[coluna]
            status = classificar_alerta(km_atual, km_limite)

            if status:
                alertas.append({
                    "Veículo": veiculo,
                    "Item": nome_item,
                    "KM atual": km_atual,
                    "Próximo KM": km_limite,
                    "Status": status
                })

    return pd.DataFrame(alertas)


# ==========================================
# INDICADORES DO DASHBOARD
# ==========================================

def carregar_indicadores():
    conn = conectar()

    total_clientes = pd.read_sql_query(
        "SELECT COUNT(*) AS total FROM clientes", conn
    ).iloc[0]["total"]

    total_veiculos = pd.read_sql_query(
        "SELECT COUNT(*) AS total FROM veiculos", conn
    ).iloc[0]["total"]

    veiculos_disponiveis = pd.read_sql_query(
        "SELECT COUNT(*) AS total FROM veiculos WHERE status = 'Disponível'", conn
    ).iloc[0]["total"]

    veiculos_alugados = pd.read_sql_query(
        "SELECT COUNT(*) AS total FROM veiculos WHERE status = 'Alugado'", conn
    ).iloc[0]["total"]

    contratos_ativos = pd.read_sql_query(
        "SELECT COUNT(*) AS total FROM contratos WHERE status = 'Ativo'", conn
    ).iloc[0]["total"]

    contratos_recentes = pd.read_sql_query(
        """
        SELECT
            c.id,
            cl.nome AS cliente,
            v.modelo || ' - ' || v.placa AS veiculo,
            c.data_inicio,
            c.data_fim,
            c.valor_total_contrato,
            c.valor_pago,
            c.status_pagamento,
            c.status
        FROM contratos c
        INNER JOIN clientes cl ON c.cliente_id = cl.id
        INNER JOIN veiculos v ON c.veiculo_id = v.id
        ORDER BY c.id DESC
        LIMIT 5
        """,
        conn
    )

    ultimas_manutencoes = pd.read_sql_query(
        """
        SELECT
            m.veiculo_id,
            m.km_atual,
            m.proxima_troca_oleo,
            m.km_prox_revisao,
            m.km_prox_pneu,
            m.km_prox_freio,
            m.km_prox_bateria,
            v.modelo,
            v.placa
        FROM manutencoes m
        INNER JOIN (
            SELECT veiculo_id, MAX(id) AS ultimo_id
            FROM manutencoes
            GROUP BY veiculo_id
        ) ult ON m.id = ult.ultimo_id
        INNER JOIN veiculos v ON m.veiculo_id = v.id
        ORDER BY v.modelo
        """,
        conn
    )

    total_contratado = pd.read_sql_query(
        """
        SELECT COALESCE(SUM(valor_total_contrato), 0) AS total
        FROM contratos
        WHERE status = 'Ativo'
        """,
        conn
    ).iloc[0]["total"]

    gasto_manutencao = pd.read_sql_query(
        """
        SELECT COALESCE(SUM(valor), 0) AS total
        FROM manutencoes
        """,
        conn
    ).iloc[0]["total"]

    outras_despesas = pd.read_sql_query(
        """
        SELECT COALESCE(SUM(valor), 0) AS total
        FROM despesas_veiculo
        """,
        conn
    ).iloc[0]["total"]

    pagamentos = pd.read_sql_query(
        """
        SELECT
            p.id,
            p.contrato_id,
            p.data_vencimento,
            p.data_pagamento,
            p.valor_previsto,
            p.valor_pago,
            p.status,
            p.observacao,
            p.comprovante_pagamento,
            c.status AS status_contrato,
            cl.nome AS cliente,
            v.modelo || ' - ' || v.placa AS veiculo,
            v.placa
        FROM pagamentos p
        INNER JOIN contratos c ON p.contrato_id = c.id
        INNER JOIN clientes cl ON c.cliente_id = cl.id
        INNER JOIN veiculos v ON c.veiculo_id = v.id
        ORDER BY p.id DESC
        """,
        conn
    )

    if not pagamentos.empty:
        pagamentos["data_vencimento"] = pd.to_datetime(pagamentos["data_vencimento"], errors="coerce")
        pagamentos["data_pagamento"] = pd.to_datetime(pagamentos["data_pagamento"], errors="coerce")
        pagamentos["valor_previsto"] = pd.to_numeric(pagamentos["valor_previsto"], errors="coerce").fillna(0.0)
        pagamentos["valor_pago"] = pd.to_numeric(pagamentos["valor_pago"], errors="coerce").fillna(0.0)
        pagamentos["status_real"] = pagamentos.apply(
            lambda row: classificar_status_pagamento_item(
                row["valor_previsto"],
                row["valor_pago"],
                row["data_vencimento"]
            ),
            axis=1
        )
        receita_recebida = float(pagamentos["valor_pago"].sum())
    else:
        receita_recebida = pd.read_sql_query(
            """
            SELECT COALESCE(SUM(valor_pago), 0) AS total
            FROM contratos
            WHERE status = 'Ativo'
            """,
            conn
        ).iloc[0]["total"]

    pagamentos_resumo = pd.DataFrame()
    if not pagamentos.empty:
        pagamentos_resumo = (
            pagamentos.groupby("status_real", as_index=False)
            .size()
            .rename(columns={"size": "quantidade", "status_real": "status_pagamento"})
        )

    contratos_sem_comprovante = pd.DataFrame()
    if not pagamentos.empty:
        contratos_sem_comprovante = pagamentos[
            (pagamentos["status_real"].isin(["Pago", "Parcial"])) &
            (
                pagamentos["comprovante_pagamento"].isna() |
                (pagamentos["comprovante_pagamento"] == "")
            )
        ][[
            "id", "contrato_id", "cliente", "veiculo",
            "valor_previsto", "valor_pago", "status_real",
            "data_vencimento", "data_pagamento"
        ]].copy()

    conn.close()

    return {
        "total_clientes": int(total_clientes),
        "total_veiculos": int(total_veiculos),
        "veiculos_disponiveis": int(veiculos_disponiveis),
        "veiculos_alugados": int(veiculos_alugados),
        "contratos_ativos": int(contratos_ativos),
        "receita_recebida": float(receita_recebida or 0.0),
        "total_contratado": float(total_contratado or 0.0),
        "gasto_manutencao": float(gasto_manutencao or 0.0),
        "outras_despesas": float(outras_despesas or 0.0),
        "contratos_recentes": contratos_recentes,
        "ultimas_manutencoes": ultimas_manutencoes,
        "pagamentos_resumo": pagamentos_resumo,
        "contratos_sem_comprovante": contratos_sem_comprovante,
        "pagamentos_df": pagamentos,
    }


# ==========================================
# TELA INICIAL
# ==========================================

def tela_inicio():
    indicadores = carregar_indicadores()
    gasto_total = indicadores["gasto_manutencao"] + indicadores["outras_despesas"]
    saldo_operacional = indicadores["receita_recebida"] - gasto_total

    st.markdown("""
    <div class="top-hero">
        <div class="top-hero-title">Painel executivo da locadora</div>
        <div class="top-hero-sub">
            Visão geral da operação, contratos, manutenção, pagamentos parcelados e indicadores principais.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        """
        <span class="menu-chip">Visão geral</span>
        <span class="menu-chip">Indicadores principais</span>
        <span class="menu-chip">Pagamentos parcelados</span>
        <span class="menu-chip">Alertas operacionais</span>
        """,
        unsafe_allow_html=True
    )

    renderizar_painel_prioridades()

    st.markdown('<div class="section-title">Indicadores principais</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Clientes", indicadores["total_clientes"])
    col2.metric("Veículos", indicadores["total_veiculos"])
    col3.metric("Disponíveis", indicadores["veiculos_disponiveis"])
    col4.metric("Alugados", indicadores["veiculos_alugados"])

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Contratos ativos", indicadores["contratos_ativos"])
    col6.metric("Recebido", formatar_moeda(indicadores["receita_recebida"]))
    col7.metric("Contratado", formatar_moeda(indicadores["total_contratado"]))
    col8.metric("Gasto total", formatar_moeda(gasto_total))

    col9, col10 = st.columns(2)
    col9.metric("Saldo operacional", formatar_moeda(saldo_operacional))
    col10.metric("Margem bruta", f"{((saldo_operacional / indicadores['receita_recebida']) * 100):.1f}%" if indicadores["receita_recebida"] > 0 else "0,0%")

    st.markdown('<div class="section-title">Últimos contratos</div>', unsafe_allow_html=True)
    if indicadores["contratos_recentes"].empty:
        st.info("Nenhum contrato cadastrado ainda.")
    else:
        contratos_exibir = indicadores["contratos_recentes"].copy()
        st.dataframe(contratos_exibir, use_container_width=True)

    st.markdown('<div class="section-title">Alertas de manutenção</div>', unsafe_allow_html=True)
    df_alertas = montar_alertas_manutencao(indicadores["ultimas_manutencoes"])

    if df_alertas.empty:
        st.success("Nenhum alerta de manutenção no momento.")
    else:
        df_vencidos = df_alertas[df_alertas["Status"] == "Vencido"]
        df_urgentes = df_alertas[df_alertas["Status"] == "Urgente"]
        df_proximos = df_alertas[df_alertas["Status"] == "Próximo"]

        a1, a2, a3 = st.columns(3)
        a1.metric("Vencidos", len(df_vencidos))
        a2.metric("Urgentes", len(df_urgentes))
        a3.metric("Próximos", len(df_proximos))

        if not df_vencidos.empty:
            st.error("Existem itens de manutenção vencidos.")
            st.dataframe(df_vencidos, use_container_width=True)

        if not df_urgentes.empty:
            st.warning("Existem itens em estado urgente.")
            st.dataframe(df_urgentes, use_container_width=True)

        if not df_proximos.empty:
            st.info("Existem itens próximos do limite.")
            st.dataframe(df_proximos, use_container_width=True)

    st.markdown('<div class="section-title">Pagamentos e comprovantes</div>', unsafe_allow_html=True)

    pagamentos = indicadores["pagamentos_resumo"]
    pagamentos_df = indicadores["pagamentos_df"]
    contratos_sem = indicadores["contratos_sem_comprovante"]

    resumo_pagamentos = {}
    if not pagamentos.empty:
        resumo_pagamentos = {
            row["status_pagamento"]: row["quantidade"]
            for _, row in pagamentos.iterrows()
        }

    pendentes = int(resumo_pagamentos.get("Pendente", 0))
    parciais = int(resumo_pagamentos.get("Parcial", 0))
    pagos = int(resumo_pagamentos.get("Pago", 0))
    vencidos = int(resumo_pagamentos.get("Vencido", 0))

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Pendentes", pendentes)
    p2.metric("Parciais", parciais)
    p3.metric("Pagos", pagos)
    p4.metric("Vencidos", vencidos)

    if contratos_sem.empty:
        st.success("Nenhum pagamento liquidado sem comprovante no momento.")
    else:
        st.warning("Existem pagamentos pagos/parciais sem comprovante anexado.")
        st.dataframe(contratos_sem, use_container_width=True)

    st.markdown('<div class="section-title">Resumo visual</div>', unsafe_allow_html=True)

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("""
        <div class="chart-card">
            <div class="chart-card-title">Frota</div>
            <div class="chart-card-sub">Distribuição atual entre veículos disponíveis e alugados.</div>
        """, unsafe_allow_html=True)
        renderizar_grafico_rosca(
            labels=["Disponíveis", "Alugados"],
            valores=[
                indicadores["veiculos_disponiveis"],
                indicadores["veiculos_alugados"]
            ],
            titulo="Frota",
            texto_centro=f"{indicadores['total_veiculos']}\nveículos",
            figsize=(3.1, 3.1)
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_g2:
        st.markdown("""
        <div class="chart-card">
            <div class="chart-card-title">Parcelas</div>
            <div class="chart-card-sub">Composição do status financeiro das cobranças registradas.</div>
        """, unsafe_allow_html=True)
        renderizar_grafico_rosca(
            labels=["Pendentes", "Parciais", "Pagos", "Vencidos"],
            valores=[pendentes, parciais, pagos, vencidos],
            titulo="Parcelas",
            texto_centro=f"{pendentes + parciais + pagos + vencidos}\nparcelas",
            figsize=(3.1, 3.1)
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class="premium-card">
        <div class="premium-title">Direção recomendada</div>
        <div class="premium-subtitle">
            Use o Painel para visão geral, Contratos para operação comercial, Financeiro para análise de recebimentos,
            Odômetro para quilometragem e Vistorias para operação de campo.
        </div>
    </div>
    """, unsafe_allow_html=True)


def executar_reset_total():
    conn = conectar()
    cursor = conn.cursor()

    tabelas = [
        "pagamentos",
        "documentos_cliente",
        "documentos_veiculo",
        "vistorias",
        "manutencoes",
        "despesas_veiculo",
        "contratos",
        "veiculos",
        "clientes",
        "logs_acoes",
    ]

    try:
        cursor.execute("PRAGMA foreign_keys = OFF")
        for tabela in tabelas:
            try:
                cursor.execute(f"DELETE FROM {tabela}")
            except Exception:
                pass
        try:
            cursor.execute("DELETE FROM sqlite_sequence")
        except Exception:
            pass
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        try:
            cursor.execute("PRAGMA foreign_keys = ON")
        except Exception:
            pass
        conn.close()

    pastas = [
        "contratos_gerados",
        "vistorias",
        "assinaturas",
        "uploads",
        "comprovantes",
        "documentos_veiculo",
        "documentos_cliente",
    ]
    for pasta in pastas:
        if os.path.exists(pasta):
            shutil.rmtree(pasta, ignore_errors=True)
        os.makedirs(pasta, exist_ok=True)


def renderizar_botao_menu(rotulo, pagina, key, icone="", primary=False):
    label = rotulo if not icone else f"{icone} {rotulo}".strip()
    tipo = "primary" if st.session_state.get("pagina_atual") == pagina or primary else "secondary"
    if st.button(label, key=key, use_container_width=True, type=tipo):
        ir_para(pagina)


def renderizar_reset_admin_sidebar():
    usuario_logado = st.session_state.get("usuario", "")
    if usuario_logado != "admin":
        return

    st.markdown('<div class="sidebar-admin-box">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section">Administração</div>', unsafe_allow_html=True)

    senha_admin = st.text_input("Senha do admin", type="password", key="reset_admin_senha")
    confirmacao_reset = st.text_input("Digite ZERAR para confirmar", key="reset_admin_confirmacao")
    confirmar_checkbox = st.checkbox(
        "Confirmo que desejo apagar TODOS os dados do sistema.",
        key="reset_admin_checkbox"
    )

    if st.button("Executar reset total", use_container_width=True, key="btn_reset_admin"):
        if not verificar_login(usuario_logado, senha_admin):
            st.error("Senha incorreta.")
        elif confirmacao_reset != "ZERAR":
            st.error("Digite exatamente ZERAR para confirmar.")
        elif not confirmar_checkbox:
            st.error("Marque a confirmação final.")
        else:
            try:
                executar_reset_total()
                st.session_state["pagina_atual"] = "Início"
                st.success("Sistema zerado com sucesso.")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao resetar o sistema: {e}")

    st.markdown('</div>', unsafe_allow_html=True)



def obter_notificacoes_menu():
    notificacoes = {
        "financeiro": 0,
        "contratos": 0,
        "manutencoes": 0,
    }

    try:
        conn = conectar()

        try:
            df_fin = pd.read_sql_query("""
                SELECT COUNT(*) AS total
                FROM pagamentos
                WHERE LOWER(COALESCE(status, '')) = 'vencido'
                   OR LOWER(COALESCE(status_real, '')) = 'vencido'
            """, conn)
            notificacoes["financeiro"] = int(df_fin["total"].iloc[0]) if not df_fin.empty else 0
        except Exception:
            notificacoes["financeiro"] = 0

        try:
            df_contratos = pd.read_sql_query("""
                SELECT COUNT(*) AS total
                FROM contratos
                WHERE COALESCE(status, '') IN ('Ativo', 'ativo')
                  AND date(COALESCE(data_fim, '')) <= date('now', '+3 day')
                  AND date(COALESCE(data_fim, '')) >= date('now')
            """, conn)
            notificacoes["contratos"] = int(df_contratos["total"].iloc[0]) if not df_contratos.empty else 0
        except Exception:
            notificacoes["contratos"] = 0

        try:
            df_manut = pd.read_sql_query("""
                SELECT COUNT(*) AS total
                FROM manutencoes
                WHERE date(COALESCE(proxima_manutencao, '')) <= date('now', '+7 day')
                  AND date(COALESCE(proxima_manutencao, '')) >= date('now')
            """, conn)
            notificacoes["manutencoes"] = int(df_manut["total"].iloc[0]) if not df_manut.empty else 0
        except Exception:
            notificacoes["manutencoes"] = 0

        conn.close()
    except Exception:
        pass

    return notificacoes


def montar_rotulo_menu(base, quantidade):
    return f"{base} ({quantidade})" if int(quantidade or 0) > 0 else base


def obter_prioridades_dashboard():
    prioridades = {
        "cobrancas_vencidas": 0,
        "contratos_vencendo": 0,
        "manutencoes_pendentes": 0,
    }

    try:
        conn = conectar()

        try:
            df_cobrancas = pd.read_sql_query("""
                SELECT COUNT(*) AS total
                FROM pagamentos
                WHERE LOWER(COALESCE(status, '')) = 'vencido'
                   OR LOWER(COALESCE(status_real, '')) = 'vencido'
            """, conn)
            prioridades["cobrancas_vencidas"] = int(df_cobrancas["total"].iloc[0]) if not df_cobrancas.empty else 0
        except Exception:
            prioridades["cobrancas_vencidas"] = 0

        try:
            df_contratos = pd.read_sql_query("""
                SELECT COUNT(*) AS total
                FROM contratos
                WHERE COALESCE(status, '') IN ('Ativo', 'ativo')
                  AND date(COALESCE(data_fim, '')) <= date('now', '+3 day')
                  AND date(COALESCE(data_fim, '')) >= date('now')
            """, conn)
            prioridades["contratos_vencendo"] = int(df_contratos["total"].iloc[0]) if not df_contratos.empty else 0
        except Exception:
            prioridades["contratos_vencendo"] = 0

        try:
            df_manut = pd.read_sql_query("""
                SELECT COUNT(*) AS total
                FROM manutencoes
                WHERE date(COALESCE(proxima_manutencao, '')) <= date('now', '+7 day')
                  AND date(COALESCE(proxima_manutencao, '')) >= date('now')
            """, conn)
            prioridades["manutencoes_pendentes"] = int(df_manut["total"].iloc[0]) if not df_manut.empty else 0
        except Exception:
            prioridades["manutencoes_pendentes"] = 0

        conn.close()
    except Exception:
        pass

    return prioridades


def renderizar_painel_prioridades():
    prioridades = obter_prioridades_dashboard()

    st.markdown('<div class="section-title">Painel de prioridades</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class="priority-card priority-card-red">
            <div class="priority-label">Cobranças vencidas</div>
            <div class="priority-value">{prioridades['cobrancas_vencidas']}</div>
            <div class="priority-desc">Acompanhe clientes com parcelas vencidas e priorize a cobrança imediata.</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Ir para Financeiro", key="prioridade_financeiro", use_container_width=True):
            ir_para("Financeiro")
            st.rerun()

    with col2:
        st.markdown(f"""
        <div class="priority-card priority-card-yellow">
            <div class="priority-label">Contratos vencendo</div>
            <div class="priority-value">{prioridades['contratos_vencendo']}</div>
            <div class="priority-desc">Contratos ativos com vencimento em até 3 dias para agir antes do atraso.</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Ir para Contratos", key="prioridade_contratos", use_container_width=True):
            ir_para("Contratos")
            st.rerun()

    with col3:
        st.markdown(f"""
        <div class="priority-card priority-card-blue">
            <div class="priority-label">Manutenções próximas</div>
            <div class="priority-value">{prioridades['manutencoes_pendentes']}</div>
            <div class="priority-desc">Itens programados para até 7 dias que merecem atenção operacional.</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Ir para Manutenções", key="prioridade_manutencoes", use_container_width=True):
            ir_para("Manutenções")
            st.rerun()


# ==========================================
# NAVEGAÇÃO
# ==========================================

def ir_para(nome_pagina):
    st.session_state["pagina_atual"] = nome_pagina


def montar_menu_sidebar():
    notificacoes = obter_notificacoes_menu()

    with st.sidebar:
        st.markdown("""
        <div class="sidebar-brand">
            <div class="sidebar-brand-title">🚗 Locadora System</div>
            <div class="sidebar-brand-sub">Gestão profissional • Operação, controle e financeiro</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="sidebar-user-pill">
            <div>
                <div class="sidebar-user-pill-label">Usuário logado</div>
                <div class="sidebar-user-pill-value">{st.session_state['usuario']}</div>
            </div>
            <div class="sidebar-dot"></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="menu-status">
            <div class="menu-status-label">Área atual</div>
            <div class="menu-status-value">{}</div>
        </div>
        """.format(st.session_state["pagina_atual"]), unsafe_allow_html=True)

        st.markdown('<div class="sidebar-group">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-section">Painel</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            renderizar_botao_menu("Início", "Início", "btn_inicio", "🏠")
        with col2:
            renderizar_botao_menu("Odômetro", "Odômetro", "btn_odometro", "📏")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="sidebar-group">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-section">Cadastros</div>', unsafe_allow_html=True)
        col3, col4, col4b = st.columns(3)
        with col3:
            renderizar_botao_menu("Locador", "Locador", "btn_locador", "🏢")
        with col4:
            renderizar_botao_menu("Clientes", "Clientes", "btn_clientes", "👤")
        with col4b:
            renderizar_botao_menu("Veículos", "Veículos", "btn_veiculos", "🚘")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="sidebar-group">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-section">Operações</div>', unsafe_allow_html=True)
        col5, col6 = st.columns(2)
        with col5:
            renderizar_botao_menu(montar_rotulo_menu("📄 Contratos", notificacoes["contratos"]), "Contratos", "btn_contratos")
        with col6:
            renderizar_botao_menu("Vistorias", "Vistorias", "btn_vistorias", "🛠️")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="sidebar-group">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-section">Controle</div>', unsafe_allow_html=True)
        col7, col8 = st.columns(2)
        with col7:
            renderizar_botao_menu(montar_rotulo_menu("🔧 Manutenções", notificacoes["manutencoes"]), "Manutenções", "btn_manutencoes")
        with col8:
            renderizar_botao_menu("Despesas", "Despesas", "btn_despesas", "💸")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="sidebar-group">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-section">Financeiro</div>', unsafe_allow_html=True)
        renderizar_botao_menu(montar_rotulo_menu("📊 Financeiro", notificacoes["financeiro"]), "Financeiro", "btn_financeiro")
        st.markdown('</div>', unsafe_allow_html=True)

        renderizar_reset_admin_sidebar()

        st.markdown("---")
        if st.button("Sair do sistema", use_container_width=True, key="btn_logout_sidebar"):
            logout()

        st.markdown('<div class="sidebar-footer-note">Menu lateral reorganizado para navegação mais rápida e limpa.</div>', unsafe_allow_html=True)

    return st.session_state["pagina_atual"]


# ==========================================
# RENDER
# ==========================================

def renderizar_pagina(menu):
    st.markdown("""
    <div class="top-hero">
        <div class="top-hero-title">Locadora System Premium</div>
        <div class="top-hero-sub">
            Sistema de gestão profissional para contratos, vistorias, odômetro, manutenção e financeiro.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.caption(f"Área atual: {menu}")

    if menu == "Início":
        tela_inicio()
    elif menu == "Clientes":
        tela_clientes()
    elif menu == "Veículos":
        tela_veiculos()
    elif menu == "Locador":
        tela_locador()
    elif menu == "Contratos":
        tela_contratos()
    elif menu == "Vistorias":
        tela_vistorias()
    elif menu == "Odômetro":
        tela_odometro()
    elif menu == "Manutenções":
        tela_manutencoes()
    elif menu == "Despesas":
        tela_despesas()
    elif menu == "Financeiro":
        tela_financeiro()
    else:
        st.warning("Página não encontrada.")


if not st.session_state["logado"]:
    tela_login()
else:
    menu = montar_menu_sidebar()
    renderizar_pagina(menu)