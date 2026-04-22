import os
from datetime import date

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from database import (
    conectar,
    registrar_pagamento as registrar_pagamento_db,
    atualizar_pagamento_registrado,
    excluir_pagamento_registrado,
)

# =========================
# AÇÕES DE COBRANÇA
# =========================

def excluir_cobranca(cobranca_id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM pagamentos WHERE id = ?", (cobranca_id,))
    conn.commit()
    conn.close()


def atualizar_cobranca(cobranca_id, novo_valor):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE pagamentos
        SET valor_previsto = ?
        WHERE id = ?
    """, (novo_valor, cobranca_id))

    conn.commit()
    conn.close()

# ==========================================
# ESTILO
# ==========================================

def aplicar_estilo_financeiro():
    st.markdown("""
    <style>
    .fin-top-card {
        background: linear-gradient(180deg, #111827 0%, #0f172a 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 18px;
        padding: 18px;
        margin-bottom: 14px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.16);
    }

    .fin-top-title {
        color: #f8fafc;
        font-size: 1.08rem;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .fin-top-sub {
        color: #94a3b8;
        font-size: 0.92rem;
        margin-bottom: 0;
    }

    .fin-box {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 14px;
        padding: 12px 14px;
        margin-top: 8px;
        margin-bottom: 12px;
    }

    .fin-box-title {
        color: #e5e7eb;
        font-size: 0.96rem;
        font-weight: 800;
        margin-bottom: 5px;
    }

    .fin-box-sub {
        color: #94a3b8;
        font-size: 0.88rem;
        margin-bottom: 0;
    }

    .fin-alert-green {
        background: rgba(34, 197, 94, 0.08);
        border: 1px solid rgba(34, 197, 94, 0.22);
        border-radius: 14px;
        padding: 12px 14px;
        margin-top: 8px;
        margin-bottom: 12px;
        color: #86efac;
        font-weight: 700;
    }

    .fin-alert-yellow {
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.22);
        border-radius: 14px;
        padding: 12px 14px;
        margin-top: 8px;
        margin-bottom: 12px;
        color: #fbbf24;
        font-weight: 700;
    }

    .fin-alert-red {
        background: rgba(239, 68, 68, 0.08);
        border: 1px solid rgba(239, 68, 68, 0.22);
        border-radius: 14px;
        padding: 12px 14px;
        margin-top: 8px;
        margin-bottom: 12px;
        color: #fca5a5;
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
        font-size: 1.18rem !important;
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
            font-size: 1.05rem !important;
        }
    }

    @media (max-width: 1100px) {
        div[data-testid="stMetricValue"] {
            font-size: 0.96rem !important;
        }

        div[data-testid="stMetricLabel"] {
            font-size: 0.72rem !important;
        }
    }

    .fin-kpi-card {
        background: linear-gradient(180deg, rgba(15,23,42,0.95) 0%, rgba(2,6,23,0.96) 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
        padding: 14px;
        min-height: 112px;
        box-shadow: 0 10px 22px rgba(0,0,0,0.14);
        margin-bottom: 10px;
    }

    .fin-kpi-label {
        color: #94a3b8;
        font-size: 0.80rem;
        margin-bottom: 8px;
        font-weight: 700;
    }

    .fin-kpi-value {
        color: #f8fafc;
        font-size: 1.34rem;
        line-height: 1.05;
        font-weight: 800;
        margin-bottom: 6px;
    }

    .fin-kpi-sub {
        color: #cbd5e1;
        font-size: 0.82rem;
        line-height: 1.2;
    }

    .fin-mini-card {
        background: rgba(255,255,255,0.025);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 14px;
        padding: 12px;
        margin-bottom: 10px;
    }

    .fin-mini-title {
        color: #e5e7eb;
        font-weight: 800;
        font-size: 0.92rem;
        margin-bottom: 6px;
    }

    .fin-mini-line {
        color: #cbd5e1;
        font-size: 0.84rem;
        margin-bottom: 4px;
    }
    </style>
    """, unsafe_allow_html=True)


def card_abertura_financeiro():
    st.markdown("""
    <div class="fin-top-card">
        <div class="fin-top-title">Central financeira da locadora</div>
        <div class="fin-top-sub">
            Operação diária de cobrança, registro de pagamentos, histórico, inadimplência e visão consolidada por contrato e veículo.
        </div>
    </div>
    """, unsafe_allow_html=True)


# ==========================================
# HELPERS
# ==========================================

def formatar_moeda(valor):
    try:
        valor = float(valor or 0)
    except Exception:
        valor = 0.0
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_moeda_curta(valor):
    return formatar_moeda(valor)


def normalizar_data_coluna(df, coluna):
    if coluna in df.columns:
        df[coluna] = pd.to_datetime(df[coluna], errors="coerce")
    return df


def normalizar_valor_coluna(df, coluna):
    if coluna in df.columns:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce").fillna(0.0)
    return df


def classificar_resultado(valor):
    if valor > 0:
        return "Lucro"
    if valor < 0:
        return "Prejuízo"
    return "Empate"


def renderizar_kpi_card(titulo, valor, subtitulo=""):
    st.markdown(
        f'''
        <div class="fin-kpi-card">
            <div class="fin-kpi-label">{titulo}</div>
            <div class="fin-kpi-value">{valor}</div>
            <div class="fin-kpi-sub">{subtitulo}</div>
        </div>
        ''',
        unsafe_allow_html=True
    )


def montar_resumo_carteira(contratos, pagamentos):
    total_contratos = int(len(contratos)) if not contratos.empty else 0
    total_cobrancas = int(len(pagamentos)) if not pagamentos.empty else 0

    inadimplencia_valor = 0.0
    cobrancas_vencidas = 0
    if not pagamentos.empty:
        vencidas = pagamentos[pagamentos["status_real"] == "Vencido"].copy()
        cobrancas_vencidas = int(len(vencidas))
        inadimplencia_valor = float((vencidas["valor_previsto"] - vencidas["valor_pago"]).clip(lower=0).sum())

    taxa_recebimento = 0.0
    if not contratos.empty:
        total_contratado = float(contratos["valor_total_contrato"].sum())
        total_recebido = float(contratos["valor_pago_principal"].sum()) if "valor_pago_principal" in contratos.columns else float(contratos.get("valor_pago", pd.Series(dtype=float)).sum())
        if total_contratado > 0:
            taxa_recebimento = (total_recebido / total_contratado) * 100

    return {
        "total_contratos": total_contratos,
        "total_cobrancas": total_cobrancas,
        "cobrancas_vencidas": cobrancas_vencidas,
        "inadimplencia_valor": inadimplencia_valor,
        "taxa_recebimento": taxa_recebimento,
    }


def obter_top_inadimplentes(contratos_base, pagamentos_periodo, limite=5):
    if contratos_base.empty or pagamentos_periodo.empty:
        return pd.DataFrame(columns=["cliente", "veiculo", "placa", "valor_em_aberto", "qtd_vencida"])

    vencidas = pagamentos_periodo[pagamentos_periodo["status_real"] == "Vencido"].copy()
    if vencidas.empty:
        return pd.DataFrame(columns=["cliente", "veiculo", "placa", "valor_em_aberto", "qtd_vencida"])

    vencidas["valor_em_aberto"] = (vencidas["valor_previsto"] - vencidas["valor_pago"]).clip(lower=0)
    agrupado = vencidas.groupby("contrato_id", as_index=False).agg(
        valor_em_aberto=("valor_em_aberto", "sum"),
        qtd_vencida=("id", "count"),
    )

    base_cols = ["id", "cliente", "veiculo", "placa", "status_financeiro_real"]
    base = contratos_base[base_cols].drop_duplicates(subset=["id"]).copy()
    merged = agrupado.merge(base, left_on="contrato_id", right_on="id", how="left")
    merged = merged.sort_values(["valor_em_aberto", "qtd_vencida"], ascending=[False, False]).head(limite)

    return merged[["cliente", "veiculo", "placa", "valor_em_aberto", "qtd_vencida"]]


def classificar_status_pagamento_item(valor_previsto, valor_pago, data_vencimento=None):
    valor_previsto = float(valor_previsto or 0.0)
    valor_pago = float(valor_pago or 0.0)

    if valor_previsto > 0 and valor_pago >= valor_previsto:
        return "Pago"
    if valor_pago > 0:
        return "Parcial"

    if data_vencimento is not None and pd.notna(data_vencimento):
        hoje = pd.Timestamp.today().normalize()
        if pd.Timestamp(data_vencimento).normalize() < hoje:
            return "Vencido"

    return "Pendente"


def classificar_status_contrato_financeiro(valor_total, valor_pago, qtd_vencido=0):
    valor_total = float(valor_total or 0.0)
    valor_pago = float(valor_pago or 0.0)
    pendente = max(valor_total - valor_pago, 0.0)

    if qtd_vencido > 0 and pendente > 0:
        return "Vencido"
    if valor_total <= 0 and valor_pago <= 0:
        return "Sem valor"
    if pendente <= 0:
        return "Pago"
    if valor_pago > 0:
        return "Parcial"
    return "Pendente"


def filtrar_periodo(df, coluna_data, data_inicio=None, data_fim=None):
    if df.empty or coluna_data not in df.columns:
        return df.copy()

    filtrado = df.copy()
    filtrado = filtrado[filtrado[coluna_data].notna()]

    if data_inicio is not None:
        filtrado = filtrado[filtrado[coluna_data] >= pd.Timestamp(data_inicio)]

    if data_fim is not None:
        filtrado = filtrado[filtrado[coluna_data] <= pd.Timestamp(data_fim)]

    return filtrado


def salvar_comprovante_upload(arquivo, contrato_id):
    if arquivo is None:
        return ""

    pasta = "comprovantes_pagamento"
    os.makedirs(pasta, exist_ok=True)

    nome_original = arquivo.name or "comprovante"
    nome_base, extensao = os.path.splitext(nome_original)
    nome_limpo = "".join(ch for ch in nome_base if ch.isalnum() or ch in ("-", "_")) or "comprovante"
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    caminho = os.path.join(pasta, f"contrato_{contrato_id}_{timestamp}_{nome_limpo}{extensao}")

    with open(caminho, "wb") as f:
        f.write(arquivo.getbuffer())

    return caminho


def preparar_tabela_para_exibicao(df, colunas_data=None, colunas_moeda=None):
    tabela = df.copy()

    for col in colunas_data or []:
        if col in tabela.columns:
            tabela[col] = pd.to_datetime(tabela[col], errors="coerce").dt.strftime("%d/%m/%Y")
            tabela[col] = tabela[col].fillna("-")

    for col in colunas_moeda or []:
        if col in tabela.columns:
            tabela[col] = pd.to_numeric(tabela[col], errors="coerce").fillna(0.0).map(formatar_moeda)

    return tabela


# ==========================================
# CARGA DE DADOS
# ==========================================

def carregar_dados_financeiros(conn):
    contratos = pd.read_sql_query("""
        SELECT
            c.id,
            c.cliente_id,
            c.veiculo_id,
            cl.nome AS cliente,
            v.modelo || ' - ' || v.placa AS veiculo,
            v.modelo,
            v.placa,
            c.data_inicio,
            c.data_fim,
            c.valor_semanal,
            c.valor_total_contrato,
            c.caucao,
            c.valor_pago,
            c.status,
            c.status_pagamento,
            c.data_pagamento,
            c.comprovante_pagamento
        FROM contratos c
        INNER JOIN clientes cl ON c.cliente_id = cl.id
        INNER JOIN veiculos v ON c.veiculo_id = v.id
        ORDER BY c.id DESC
    """, conn)

    pagamentos = pd.read_sql_query("""
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
            c.veiculo_id,
            c.valor_total_contrato,
            c.status AS status_contrato,
            cl.nome AS cliente,
            v.modelo || ' - ' || v.placa AS veiculo,
            v.modelo,
            v.placa
        FROM pagamentos p
        INNER JOIN contratos c ON p.contrato_id = c.id
        INNER JOIN clientes cl ON c.cliente_id = cl.id
        INNER JOIN veiculos v ON c.veiculo_id = v.id
        ORDER BY p.id DESC
    """, conn)

    manutencoes = pd.read_sql_query("""
        SELECT
            m.id,
            m.veiculo_id,
            v.modelo || ' - ' || v.placa AS veiculo,
            v.modelo,
            v.placa,
            m.data_manutencao,
            m.tipo_servico,
            m.descricao,
            m.valor,
            m.oficina
        FROM manutencoes m
        INNER JOIN veiculos v ON m.veiculo_id = v.id
        ORDER BY m.id DESC
    """, conn)

    despesas = pd.read_sql_query("""
        SELECT
            d.id,
            d.veiculo_id,
            v.modelo || ' - ' || v.placa AS veiculo,
            v.modelo,
            v.placa,
            d.data_despesa,
            d.categoria,
            d.descricao,
            d.valor,
            d.observacoes
        FROM despesas_veiculo d
        INNER JOIN veiculos v ON d.veiculo_id = v.id
        ORDER BY d.id DESC
    """, conn)

    for coluna in ["data_inicio", "data_fim", "data_pagamento"]:
        contratos = normalizar_data_coluna(contratos, coluna)

    for coluna in ["valor_semanal", "valor_total_contrato", "caucao", "valor_pago"]:
        contratos = normalizar_valor_coluna(contratos, coluna)

    for coluna in ["data_vencimento", "data_pagamento"]:
        pagamentos = normalizar_data_coluna(pagamentos, coluna)

    for coluna in ["valor_previsto", "valor_pago", "valor_total_contrato"]:
        pagamentos = normalizar_valor_coluna(pagamentos, coluna)

    pagamentos["status_real"] = pagamentos.apply(
        lambda row: classificar_status_pagamento_item(
            row["valor_previsto"],
            row["valor_pago"],
            row["data_vencimento"]
        ),
        axis=1
    )

    manutencoes = normalizar_data_coluna(manutencoes, "data_manutencao")
    manutencoes = normalizar_valor_coluna(manutencoes, "valor")

    despesas = normalizar_data_coluna(despesas, "data_despesa")
    despesas = normalizar_valor_coluna(despesas, "valor")

    return contratos, pagamentos, manutencoes, despesas


# ==========================================
# PROCESSAMENTO
# ==========================================

def preparar_contratos_financeiros(contratos, pagamentos):
    df = contratos.copy()

    colunas_padrao = {
        "valor_total_contrato": 0.0,
        "valor_pago": 0.0,
        "valor_pendente": 0.0,
        "status_financeiro_real": "Pendente",
        "qtd_cobrancas": 0,
        "qtd_vencidos": 0,
        "qtd_pagos": 0,
        "qtd_parciais": 0,
        "qtd_pendentes": 0,
        "valor_previsto_pagamentos": 0.0,
        "valor_pago_pagamentos": 0.0,
        "valor_pago_principal": 0.0,
    }

    for coluna, valor_padrao in colunas_padrao.items():
        if coluna not in df.columns:
            df[coluna] = valor_padrao

    if df.empty:
        return df

    for col in ["valor_total_contrato", "valor_pago"]:
        if col not in df.columns:
            df[col] = 0

    df["valor_total_contrato"] = pd.to_numeric(df["valor_total_contrato"], errors="coerce").fillna(0.0)
    df["valor_pago"] = pd.to_numeric(df["valor_pago"], errors="coerce").fillna(0.0)

    df["valor_pendente"] = (df["valor_total_contrato"] - df["valor_pago"]).clip(lower=0)
    df["status_financeiro_real"] = df.apply(
        lambda row: classificar_status_contrato_financeiro(
            row["valor_total_contrato"],
            row["valor_pago"],
            0
        ),
        axis=1
    )

    colunas_resumo = [
        "qtd_cobrancas",
        "qtd_vencidos",
        "qtd_pagos",
        "qtd_parciais",
        "qtd_pendentes",
        "valor_previsto_pagamentos",
        "valor_pago_pagamentos",
        "contrato_id",
    ]
    df = df.drop(columns=[c for c in colunas_resumo if c in df.columns], errors="ignore")

    if not pagamentos.empty:
        pag = pagamentos.copy()

        for col in ["contrato_id", "id", "valor_previsto", "valor_pago", "status_real"]:
            if col not in pag.columns:
                pag[col] = 0.0 if col in ["valor_previsto", "valor_pago"] else None

        pag["valor_previsto"] = pd.to_numeric(pag["valor_previsto"], errors="coerce").fillna(0.0)
        pag["valor_pago"] = pd.to_numeric(pag["valor_pago"], errors="coerce").fillna(0.0)

        resumo_pag = pag.groupby("contrato_id", as_index=False).agg(
            qtd_cobrancas=("id", "count"),
            qtd_vencidos=("status_real", lambda s: int((s == "Vencido").sum())),
            qtd_pagos=("status_real", lambda s: int((s == "Pago").sum())),
            qtd_parciais=("status_real", lambda s: int((s == "Parcial").sum())),
            qtd_pendentes=("status_real", lambda s: int((s == "Pendente").sum())),
            valor_previsto_pagamentos=("valor_previsto", "sum"),
            valor_pago_pagamentos=("valor_pago", "sum"),
        )

        df = df.merge(resumo_pag, left_on="id", right_on="contrato_id", how="left")

        for col in ["qtd_cobrancas", "qtd_vencidos", "qtd_pagos", "qtd_parciais", "qtd_pendentes"]:
            if col not in df.columns:
                df[col] = 0
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

        for col in ["valor_previsto_pagamentos", "valor_pago_pagamentos"]:
            if col not in df.columns:
                df[col] = 0.0
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        df["valor_pago_principal"] = df["valor_pago_pagamentos"].where(df["qtd_cobrancas"] > 0, df["valor_pago"])
        df["valor_pendente"] = (df["valor_total_contrato"] - df["valor_pago_principal"]).clip(lower=0)
        df["status_financeiro_real"] = df.apply(
            lambda row: classificar_status_contrato_financeiro(
                row["valor_total_contrato"],
                row["valor_pago_principal"],
                row["qtd_vencidos"]
            ),
            axis=1
        )
    else:
        df["qtd_cobrancas"] = 0
        df["qtd_vencidos"] = 0
        df["qtd_pagos"] = 0
        df["qtd_parciais"] = 0
        df["qtd_pendentes"] = 0
        df["valor_previsto_pagamentos"] = 0.0
        df["valor_pago_pagamentos"] = 0.0
        df["valor_pago_principal"] = df["valor_pago"]

    return df


def consolidar_fluxo_mensal(contratos, pagamentos, manutencoes, despesas):
    receitas = pd.DataFrame(columns=["mes", "recebido"])
    manut = pd.DataFrame(columns=["mes", "manutencao"])
    desp = pd.DataFrame(columns=["mes", "despesa"])

    if not pagamentos.empty:
        df = pagamentos.copy()
        df = df[df["data_pagamento"].notna()].copy()
        if not df.empty:
            df["mes"] = df["data_pagamento"].dt.to_period("M").astype(str)
            receitas = df.groupby("mes", as_index=False)["valor_pago"].sum().rename(columns={"valor_pago": "recebido"})
    elif not contratos.empty:
        df = contratos.copy()
        df = df[df["data_pagamento"].notna()].copy()
        if not df.empty:
            df["mes"] = df["data_pagamento"].dt.to_period("M").astype(str)
            receitas = df.groupby("mes", as_index=False)["valor_pago"].sum().rename(columns={"valor_pago": "recebido"})

    if not manutencoes.empty:
        df = manutencoes.copy()
        df = df[df["data_manutencao"].notna()].copy()
        if not df.empty:
            df["mes"] = df["data_manutencao"].dt.to_period("M").astype(str)
            manut = df.groupby("mes", as_index=False)["valor"].sum().rename(columns={"valor": "manutencao"})

    if not despesas.empty:
        df = despesas.copy()
        df = df[df["data_despesa"].notna()].copy()
        if not df.empty:
            df["mes"] = df["data_despesa"].dt.to_period("M").astype(str)
            desp = df.groupby("mes", as_index=False)["valor"].sum().rename(columns={"valor": "despesa"})

    fluxo = receitas.merge(manut, on="mes", how="outer").merge(desp, on="mes", how="outer")

    if fluxo.empty:
        return pd.DataFrame(columns=["mes", "recebido", "manutencao", "despesa", "custo_total", "resultado"])

    fluxo["recebido"] = pd.to_numeric(fluxo["recebido"], errors="coerce").fillna(0)
    fluxo["manutencao"] = pd.to_numeric(fluxo["manutencao"], errors="coerce").fillna(0)
    fluxo["despesa"] = pd.to_numeric(fluxo["despesa"], errors="coerce").fillna(0)
    fluxo["custo_total"] = fluxo["manutencao"] + fluxo["despesa"]
    fluxo["resultado"] = fluxo["recebido"] - fluxo["custo_total"]
    fluxo = fluxo.sort_values("mes").reset_index(drop=True)
    return fluxo


def consolidar_resultado_por_veiculo(contratos, pagamentos, manutencoes, despesas):
    receita_recebida = pd.DataFrame(columns=["veiculo_id", "veiculo", "receita_recebida"])
    receita_contratada = pd.DataFrame(columns=["veiculo_id", "veiculo", "receita_contratada", "receita_pendente"])
    custo_manut = pd.DataFrame(columns=["veiculo_id", "manutencao"])
    custo_desp = pd.DataFrame(columns=["veiculo_id", "despesa"])

    if not pagamentos.empty:
        df = pagamentos.copy()
        receita_recebida = df.groupby(["veiculo_id", "veiculo"], as_index=False)["valor_pago"].sum().rename(columns={"valor_pago": "receita_recebida"})
    elif not contratos.empty:
        df = contratos.copy()
        receita_recebida = df.groupby(["veiculo_id", "veiculo"], as_index=False)["valor_pago_principal"].sum().rename(columns={"valor_pago_principal": "receita_recebida"})

    if not contratos.empty:
        df = contratos.copy()
        receita_contratada = df.groupby(["veiculo_id", "veiculo"], as_index=False).agg(
            receita_contratada=("valor_total_contrato", "sum"),
            receita_pendente=("valor_pendente", "sum")
        )

    if not manutencoes.empty:
        df = manutencoes.copy()
        custo_manut = df.groupby("veiculo_id", as_index=False)["valor"].sum().rename(columns={"valor": "manutencao"})

    if not despesas.empty:
        df = despesas.copy()
        custo_desp = df.groupby("veiculo_id", as_index=False)["valor"].sum().rename(columns={"valor": "despesa"})

    base = receita_contratada.merge(receita_recebida, on=["veiculo_id", "veiculo"], how="outer")
    base = base.merge(custo_manut, on="veiculo_id", how="outer").merge(custo_desp, on="veiculo_id", how="outer")

    if base.empty:
        return pd.DataFrame(columns=[
            "veiculo_id", "veiculo", "receita_contratada", "receita_recebida",
            "receita_pendente", "manutencao", "despesa", "custo_total",
            "resultado", "margem", "status_resultado"
        ])

    if "veiculo" not in base.columns:
        base["veiculo"] = "-"

    base["veiculo"] = base["veiculo"].fillna("-")
    base["receita_contratada"] = pd.to_numeric(base["receita_contratada"], errors="coerce").fillna(0.0)
    base["receita_recebida"] = pd.to_numeric(base["receita_recebida"], errors="coerce").fillna(0.0)
    base["receita_pendente"] = pd.to_numeric(base["receita_pendente"], errors="coerce").fillna(0.0)
    base["manutencao"] = pd.to_numeric(base["manutencao"], errors="coerce").fillna(0.0)
    base["despesa"] = pd.to_numeric(base["despesa"], errors="coerce").fillna(0.0)

    base["custo_total"] = base["manutencao"] + base["despesa"]
    base["resultado"] = base["receita_recebida"] - base["custo_total"]
    base["margem"] = base.apply(lambda row: (row["resultado"] / row["receita_recebida"] * 100) if row["receita_recebida"] > 0 else 0.0, axis=1)
    base["status_resultado"] = base["resultado"].apply(classificar_resultado)
    base = base.sort_values("resultado", ascending=False)
    return base


def consolidar_indicadores(contratos, pagamentos, manutencoes, despesas):
    total_contratado = float(contratos["valor_total_contrato"].sum()) if not contratos.empty else 0.0
    total_pendente = float(contratos["valor_pendente"].sum()) if not contratos.empty else 0.0
    total_recebido = float(pagamentos["valor_pago"].sum()) if not pagamentos.empty else (float(contratos["valor_pago_principal"].sum()) if not contratos.empty else 0.0)
    total_manutencao = float(manutencoes["valor"].sum()) if not manutencoes.empty else 0.0
    total_despesas = float(despesas["valor"].sum()) if not despesas.empty else 0.0
    custo_total = total_manutencao + total_despesas
    resultado_operacional = total_recebido - custo_total

    contratos_pagos = contratos_parciais = contratos_pendentes = contratos_vencidos = 0
    if not contratos.empty:
        contratos_pagos = int((contratos["status_financeiro_real"] == "Pago").sum())
        contratos_parciais = int((contratos["status_financeiro_real"] == "Parcial").sum())
        contratos_pendentes = int((contratos["status_financeiro_real"] == "Pendente").sum())
        contratos_vencidos = int((contratos["status_financeiro_real"] == "Vencido").sum())

    cobrancas_pagas = cobrancas_parciais = cobrancas_pendentes = cobrancas_vencidas = 0
    if not pagamentos.empty:
        cobrancas_pagas = int((pagamentos["status_real"] == "Pago").sum())
        cobrancas_parciais = int((pagamentos["status_real"] == "Parcial").sum())
        cobrancas_pendentes = int((pagamentos["status_real"] == "Pendente").sum())
        cobrancas_vencidas = int((pagamentos["status_real"] == "Vencido").sum())

    ticket_medio = (total_recebido / len(pagamentos)) if not pagamentos.empty else 0.0

    return {
        "total_contratado": total_contratado,
        "total_recebido": total_recebido,
        "total_pendente": total_pendente,
        "total_manutencao": total_manutencao,
        "total_despesas": total_despesas,
        "custo_total": custo_total,
        "resultado_operacional": resultado_operacional,
        "contratos_pagos": contratos_pagos,
        "contratos_parciais": contratos_parciais,
        "contratos_pendentes": contratos_pendentes,
        "contratos_vencidos": contratos_vencidos,
        "cobrancas_pagas": cobrancas_pagas,
        "cobrancas_parciais": cobrancas_parciais,
        "cobrancas_pendentes": cobrancas_pendentes,
        "cobrancas_vencidas": cobrancas_vencidas,
        "ticket_medio": ticket_medio,
    }


# ==========================================
# GRÁFICOS
# ==========================================

def abrir_card_grafico(titulo, subtitulo=""):
    st.markdown(f"""
    <div style="
        background: linear-gradient(180deg, #111827 0%, #0b1220 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 18px;
        padding: 14px;
        min-height: 400px;
        box-shadow: 0 8px 22px rgba(0,0,0,0.12);
        margin-bottom: 10px;">
        <div style="color:#e5e7eb;font-size:0.98rem;font-weight:800;margin-bottom:4px;">{titulo}</div>
        <div style="color:#94a3b8;font-size:0.84rem;margin-bottom:8px;">{subtitulo}</div>
    """, unsafe_allow_html=True)


def fechar_card_grafico():
    st.markdown("</div>", unsafe_allow_html=True)

def configurar_estilo_grafico():
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


def obter_config_grafico(modo_mobile=False, tipo="linha"):
    if modo_mobile:
        configs = {
            "linha": {"figsize": (5.4, 2.6), "titulo": 9, "label": 8, "tick": 7, "legend": 7},
            "barra": {"figsize": (5.4, 2.6), "titulo": 9, "label": 8, "tick": 7, "legend": 7},
            "pizza": {"figsize": (3.6, 3.6), "titulo": 9, "label": 7, "tick": 7, "legend": 7},
        }
    else:
        configs = {
            "linha": {"figsize": (6.2, 2.9), "titulo": 10, "label": 9, "tick": 8, "legend": 8},
            "barra": {"figsize": (6.2, 2.9), "titulo": 10, "label": 9, "tick": 8, "legend": 8},
            "pizza": {"figsize": (3.8, 3.8), "titulo": 10, "label": 8, "tick": 8, "legend": 8},
        }

    return configs.get(tipo, configs["linha"])


def grafico_fluxo_mensal(fluxo, modo_mobile=False):
    st.markdown("### Fluxo financeiro por mês")
    if fluxo.empty:
        st.info("Sem dados suficientes para exibir o fluxo financeiro.")
        return

    cfg = obter_config_grafico(modo_mobile, "linha")
    configurar_estilo_grafico()

    fig, ax = plt.subplots(figsize=cfg["figsize"])
    ax.plot(fluxo["mes"], fluxo["recebido"], marker="o", linewidth=1.8, label="Recebido")
    ax.plot(fluxo["mes"], fluxo["custo_total"], marker="o", linewidth=1.8, label="Custos")
    ax.plot(fluxo["mes"], fluxo["resultado"], marker="o", linewidth=1.8, label="Resultado")

    ax.set_title("Receitas, custos e resultado", fontsize=cfg["titulo"], pad=6)
    ax.set_xlabel("Mês", fontsize=cfg["label"])
    ax.set_ylabel("Valor (R$)", fontsize=cfg["label"])
    ax.grid(True, linestyle="--", alpha=0.25)
    ax.tick_params(axis="x", labelsize=cfg["tick"], rotation=18)
    ax.tick_params(axis="y", labelsize=cfg["tick"])
    ax.legend(fontsize=cfg["legend"])

    plt.tight_layout(pad=0.8)
    st.pyplot(fig, use_container_width=True)


def grafico_status_contratos(contratos, modo_mobile=False):
    st.markdown("### Distribuição financeira dos contratos")
    if contratos.empty:
        st.info("Sem contratos para exibir a distribuição.")
        return

    dist = contratos["status_financeiro_real"].value_counts().reindex(
        ["Pago", "Parcial", "Pendente", "Vencido"], fill_value=0
    )
    if dist.sum() == 0:
        st.info("Sem dados suficientes para o gráfico.")
        return

    cfg = obter_config_grafico(modo_mobile, "pizza")
    configurar_estilo_grafico()

    fig, ax = plt.subplots(figsize=cfg["figsize"])
    wedges, _ = ax.pie(
        dist.values,
        labels=None,
        startangle=90,
        wedgeprops={"width": 0.32, "edgecolor": "#0b1220", "linewidth": 2},
    )

    total = int(dist.sum())
    ax.text(
        0, 0,
        f"{total}\ncontrato(s)",
        ha="center",
        va="center",
        fontsize=7 if modo_mobile else 8,
        fontweight="bold"
    )
    ax.set_title("Status financeiro dos contratos", fontsize=cfg["titulo"], pad=8)
    ax.axis("equal")

    legend_labels = []
    for label, valor in zip(dist.index, dist.values):
        percentual = 0 if total == 0 else round((valor / total) * 100)
        legend_labels.append(f"{label}: {int(valor)} ({percentual}%)")

    ax.legend(
        wedges,
        legend_labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=2,
        frameon=False,
        fontsize=cfg["legend"]
    )

    fig.subplots_adjust(top=0.88, bottom=0.20)
    st.pyplot(fig, use_container_width=True)


def grafico_status_cobrancas(pagamentos, modo_mobile=False):
    st.markdown("### Distribuição das cobranças")
    if pagamentos.empty:
        st.info("Sem cobranças para exibir a distribuição.")
        return

    dist = pagamentos["status_real"].value_counts().reindex(
        ["Pago", "Parcial", "Pendente", "Vencido"], fill_value=0
    )
    if dist.sum() == 0:
        st.info("Sem dados suficientes para o gráfico.")
        return

    cfg = obter_config_grafico(modo_mobile, "pizza")
    configurar_estilo_grafico()

    fig, ax = plt.subplots(figsize=cfg["figsize"])
    wedges, _ = ax.pie(
        dist.values,
        labels=None,
        startangle=90,
        wedgeprops={"width": 0.32, "edgecolor": "#0b1220", "linewidth": 2},
    )

    total = int(dist.sum())
    ax.text(
        0, 0,
        f"{total}\ncobrança(s)",
        ha="center",
        va="center",
        fontsize=7 if modo_mobile else 8,
        fontweight="bold"
    )
    ax.set_title("Status das cobranças", fontsize=cfg["titulo"], pad=8)
    ax.axis("equal")

    legend_labels = []
    for label, valor in zip(dist.index, dist.values):
        percentual = 0 if total == 0 else round((valor / total) * 100)
        legend_labels.append(f"{label}: {int(valor)} ({percentual}%)")

    ax.legend(
        wedges,
        legend_labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=2,
        frameon=False,
        fontsize=cfg["legend"]
    )

    fig.subplots_adjust(top=0.88, bottom=0.20)
    st.pyplot(fig, use_container_width=True)


def grafico_despesas_categoria(despesas, modo_mobile=False):
    st.markdown("### Distribuição das despesas")
    if despesas.empty:
        st.info("Sem despesas para exibir no gráfico.")
        return

    df_cat = despesas.groupby("categoria", as_index=False)["valor"].sum()
    df_cat = df_cat[df_cat["valor"] > 0].sort_values("valor", ascending=False)
    if df_cat.empty:
        st.info("Sem valores de despesas para exibir.")
        return

    cfg = obter_config_grafico(modo_mobile, "barra")
    configurar_estilo_grafico()

    fig, ax = plt.subplots(figsize=cfg["figsize"])
    ax.bar(df_cat["categoria"], df_cat["valor"])
    ax.set_title("Despesas por categoria", fontsize=cfg["titulo"], pad=6)
    ax.set_xlabel("Categoria", fontsize=cfg["label"])
    ax.set_ylabel("Valor (R$)", fontsize=cfg["label"])
    ax.grid(True, axis="y", linestyle="--", alpha=0.25)
    ax.tick_params(axis="x", labelsize=cfg["tick"], rotation=20)
    ax.tick_params(axis="y", labelsize=cfg["tick"])

    plt.tight_layout(pad=0.8)
    st.pyplot(fig, use_container_width=True)


def grafico_resultado_por_veiculo(df_veiculos, modo_mobile=False):
    st.markdown("### Resultado por veículo")
    if df_veiculos.empty:
        st.info("Sem dados por veículo para exibir.")
        return

    top = df_veiculos.sort_values("resultado", ascending=False).head(8).copy()
    cfg = obter_config_grafico(modo_mobile, "barra")
    configurar_estilo_grafico()

    fig, ax = plt.subplots(figsize=cfg["figsize"])
    ax.bar(top["veiculo"], top["resultado"])
    ax.set_title("Top veículos por resultado", fontsize=cfg["titulo"], pad=6)
    ax.set_xlabel("Veículo", fontsize=cfg["label"])
    ax.set_ylabel("Resultado (R$)", fontsize=cfg["label"])
    ax.grid(True, axis="y", linestyle="--", alpha=0.25)
    ax.tick_params(axis="x", labelsize=cfg["tick"], rotation=25)
    ax.tick_params(axis="y", labelsize=cfg["tick"])

    plt.tight_layout(pad=0.8)
    st.pyplot(fig, use_container_width=True)


# ==========================================
# ABAS
# ==========================================

def renderizar_aba_painel(contratos_base, pagamentos_periodo, manut_base, despesas_base, modo_mobile=False):
    indicadores = consolidar_indicadores(contratos_base, pagamentos_periodo, manut_base, despesas_base)
    fluxo = consolidar_fluxo_mensal(contratos_base, pagamentos_periodo, manut_base, despesas_base)
    resultado_veiculos = consolidar_resultado_por_veiculo(contratos_base, pagamentos_periodo, manut_base, despesas_base)
    resumo_carteira = montar_resumo_carteira(contratos_base, pagamentos_periodo)
    top_inadimplentes = obter_top_inadimplentes(contratos_base, pagamentos_periodo, limite=5)

    st.markdown("""
    <div class="fin-box">
        <div class="fin-box-title">Painel executivo</div>
        <div class="fin-box-sub">
            Prioridade em caixa, inadimplência, margem e desempenho por veículo no período filtrado.
        </div>
    </div>
    """, unsafe_allow_html=True)

    linha1 = st.columns(4)
    with linha1[0]:
        renderizar_kpi_card(
            "Receita recebida",
            formatar_moeda(indicadores["total_recebido"]),
            f"Taxa de recebimento: {resumo_carteira['taxa_recebimento']:.1f}%"
        )
    with linha1[1]:
        renderizar_kpi_card(
            "Saldo pendente",
            formatar_moeda(indicadores["total_pendente"]),
            f"Cobranças vencidas: {resumo_carteira['cobrancas_vencidas']}"
        )
    with linha1[2]:
        renderizar_kpi_card(
            "Resultado operacional",
            formatar_moeda(indicadores["resultado_operacional"]),
            f"Custos totais: {formatar_moeda(indicadores['custo_total'])}"
        )
    with linha1[3]:
        renderizar_kpi_card(
            "Ticket médio",
            formatar_moeda(indicadores["ticket_medio"]),
            f"Contratos no período: {resumo_carteira['total_contratos']}"
        )

    linha2 = st.columns(4)
    with linha2[0]:
        st.metric("Receita contratada", formatar_moeda(indicadores["total_contratado"]))
    with linha2[1]:
        st.metric("Cobranças totais", resumo_carteira["total_cobrancas"])
    with linha2[2]:
        st.metric("Contratos vencidos", indicadores["contratos_vencidos"])
    with linha2[3]:
        st.metric("Cobranças vencidas", indicadores["cobrancas_vencidas"])

    if indicadores["resultado_operacional"] > 0:
        st.markdown(
            f'<div class="fin-alert-green">Operação positiva no período: resultado de {formatar_moeda(indicadores["resultado_operacional"])}.</div>',
            unsafe_allow_html=True
        )
    elif indicadores["resultado_operacional"] < 0:
        st.markdown(
            f'<div class="fin-alert-red">Operação negativa no período: resultado de {formatar_moeda(indicadores["resultado_operacional"])}. O foco deve ser cobrança e redução de custo.</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown('<div class="fin-alert-yellow">Resultado operacional zerado no período analisado.</div>', unsafe_allow_html=True)

    if resumo_carteira["inadimplencia_valor"] > 0:
        st.markdown(
            f'<div class="fin-alert-red">Inadimplência crítica do período: {formatar_moeda(resumo_carteira["inadimplencia_valor"])} em aberto nas cobranças vencidas.</div>',
            unsafe_allow_html=True
        )

    bloco1, bloco2 = st.columns([1, 1])
    with bloco1:
        abrir_card_grafico("Fluxo financeiro por mês", "Receitas, custos e resultado consolidados no período.")
        grafico_fluxo_mensal(fluxo, modo_mobile=modo_mobile)
        fechar_card_grafico()
    with bloco2:
        abrir_card_grafico("Status financeiro dos contratos", "Distribuição padronizada para comparação visual limpa.")
        grafico_status_contratos(contratos_base, modo_mobile=modo_mobile)
        fechar_card_grafico()

    bloco3, bloco4 = st.columns([1, 1])
    with bloco3:
        abrir_card_grafico("Resultado por veículo", "Desempenho econômico da frota com visual unificado.")
        grafico_resultado_por_veiculo(resultado_veiculos, modo_mobile=modo_mobile)
        fechar_card_grafico()
    with bloco4:
        abrir_card_grafico("Status das cobranças", "Distribuição padronizada das cobranças registradas.")
        grafico_status_cobrancas(pagamentos_periodo, modo_mobile=modo_mobile)
        fechar_card_grafico()

    st.divider()

    col_tabela, col_alertas = st.columns([1.45, 1])

    with col_tabela:
        st.markdown("""
        <div class="fin-box">
            <div class="fin-box-title">Lucratividade por veículo</div>
            <div class="fin-box-sub">
                Receita recebida menos manutenção e despesas. Use esta visão para decidir permanência e prioridade da frota.
            </div>
        </div>
        """, unsafe_allow_html=True)

        if resultado_veiculos.empty:
            st.info("Ainda não há dados suficientes para consolidar a lucratividade por veículo.")
        else:
            busca_veiculo = st.text_input(
                "Buscar veículo no resultado",
                placeholder="Digite modelo ou placa",
                key="busca_veic_resultado"
            )
            df_veiculos = resultado_veiculos.copy()
            if busca_veiculo:
                termo = busca_veiculo.strip().lower()
                df_veiculos = df_veiculos[
                    df_veiculos["veiculo"].astype(str).str.lower().str.contains(termo, na=False)
                ]

            tabela_veiculos = df_veiculos[[
                "veiculo", "receita_contratada", "receita_recebida", "receita_pendente",
                "manutencao", "despesa", "custo_total", "resultado", "margem", "status_resultado"
            ]].copy()
            tabela_veiculos["margem"] = pd.to_numeric(
                tabela_veiculos["margem"], errors="coerce"
            ).fillna(0.0).map(lambda x: f"{x:.1f}%")
            tabela_veiculos = preparar_tabela_para_exibicao(
                tabela_veiculos,
                colunas_moeda=[
                    "receita_contratada", "receita_recebida", "receita_pendente",
                    "manutencao", "despesa", "custo_total", "resultado"
                ]
            )
            st.dataframe(tabela_veiculos, use_container_width=True)

    with col_alertas:
        st.markdown("""
        <div class="fin-box">
            <div class="fin-box-title">Prioridades de cobrança</div>
            <div class="fin-box-sub">
                Lista curta para atacar primeiro onde o dinheiro travado é maior.
            </div>
        </div>
        """, unsafe_allow_html=True)

        if top_inadimplentes.empty:
            st.info("Sem inadimplentes relevantes no período filtrado.")
        else:
            for _, row in top_inadimplentes.iterrows():
                st.markdown(
                    f'''
                    <div class="fin-mini-card">
                        <div class="fin-mini-title">{row["cliente"]}</div>
                        <div class="fin-mini-line">{row["veiculo"]} • {row["placa"]}</div>
                        <div class="fin-mini-line">Em aberto: <strong>{formatar_moeda(row["valor_em_aberto"])}</strong></div>
                        <div class="fin-mini-line">Cobranças vencidas: {int(row["qtd_vencida"])}</div>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )

        st.markdown("""
        <div class="fin-box">
            <div class="fin-box-title">Composição de custos</div>
            <div class="fin-box-sub">
                Visual rápido para ver onde a operação está consumindo caixa.
            </div>
        </div>
        """, unsafe_allow_html=True)
        grafico_despesas_categoria(despesas_base, modo_mobile=modo_mobile)

def eh_imagem_preview(caminho_arquivo):
    if not caminho_arquivo:
        return False
    extensao = os.path.splitext(str(caminho_arquivo).lower())[1]
    return extensao in [".jpg", ".jpeg", ".png", ".webp"]

def renderizar_aba_cobrancas(contratos_base, pagamentos_periodo):
    st.markdown("""
    <div class="fin-box">
        <div class="fin-box-title">Cobranças</div>
        <div class="fin-box-sub">
            Gestão operacional completa por contrato: visualização, edição, exclusão e histórico.
        </div>
    </div>
    """, unsafe_allow_html=True)

    if contratos_base.empty:
        st.info("Nenhum contrato encontrado no período filtrado.")
        return

    contratos_exibir = contratos_base.copy().sort_values("id", ascending=False)

    busca_contrato = st.text_input(
        "Buscar contrato para gerenciar cobranças",
        placeholder="Digite cliente, veículo ou placa",
        key="fin_busca_contrato_cobranca"
    )

    if busca_contrato:
        termo = busca_contrato.strip().lower()
        contratos_exibir = contratos_exibir[
            contratos_exibir["cliente"].astype(str).str.lower().str.contains(termo, na=False) |
            contratos_exibir["veiculo"].astype(str).str.lower().str.contains(termo, na=False) |
            contratos_exibir["placa"].astype(str).str.lower().str.contains(termo, na=False)
        ]

    if contratos_exibir.empty:
        st.warning("Nenhum contrato encontrado com esse filtro.")
        return

    opcoes_contratos = {
        f"Contrato #{int(row['id'])} | {row['cliente']} | {row['veiculo']}": int(row["id"])
        for _, row in contratos_exibir.iterrows()
    }

    contrato_pagamento_select = st.selectbox(
        "Selecione o contrato para gerenciar cobranças",
        list(opcoes_contratos.keys()),
        key="fin_contrato_pagamento_select"
    )
    contrato_pagamento_id = opcoes_contratos[contrato_pagamento_select]

    registro_pagamento_contrato = contratos_exibir[
        contratos_exibir["id"] == contrato_pagamento_id
    ].iloc[0]

    if pagamentos_periodo.empty:
        pagamentos_contrato = pd.DataFrame(columns=[
            "id", "contrato_id", "data_vencimento", "data_pagamento",
            "valor_previsto", "valor_pago", "status", "status_real",
            "observacao", "comprovante_pagamento", "cliente", "veiculo", "placa"
        ])
    else:
        pagamentos_contrato = pagamentos_periodo[
            pagamentos_periodo["contrato_id"] == contrato_pagamento_id
        ].copy()

    st.markdown(
        f"""
        <div class="fin-box">
            <div class="fin-box-title">
                Contrato #{int(contrato_pagamento_id)} • {registro_pagamento_contrato['cliente']} • {registro_pagamento_contrato['veiculo']}
            </div>
            <div class="fin-box-sub">
                Pago: {formatar_moeda(registro_pagamento_contrato.get('valor_pago_principal', registro_pagamento_contrato.get('valor_pago', 0)))} |
                Pendente: {formatar_moeda(registro_pagamento_contrato.get('valor_pendente', 0))} |
                Cobranças: {int(registro_pagamento_contrato.get('qtd_cobrancas', 0))}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if pagamentos_contrato.empty:
        st.info("Este contrato ainda não possui cobranças cadastradas.")
    else:
        tabela_cobrancas = pagamentos_contrato[[
            "id", "data_vencimento", "data_pagamento", "valor_previsto",
            "valor_pago", "status_real", "observacao"
        ]].copy()

        tabela_cobrancas = preparar_tabela_para_exibicao(
            tabela_cobrancas,
            colunas_data=["data_vencimento", "data_pagamento"],
            colunas_moeda=["valor_previsto", "valor_pago"]
        )

        st.dataframe(tabela_cobrancas, use_container_width=True)

    subt1, subt2, subt3, subt4 = st.tabs([
        "Nova cobrança",
        "Editar cobrança",
        "Excluir cobrança",
        "Histórico do contrato"
    ])

    with subt1:
        with st.form(f"fin_form_novo_pagamento_{contrato_pagamento_id}"):
            colp1, colp2, colp3 = st.columns(3)
            with colp1:
                data_vencimento = st.date_input(
                    "Data de vencimento",
                    value=date.today(),
                    key=f"fin_data_venc_novo_{contrato_pagamento_id}"
                )
            with colp2:
                valor_previsto = st.number_input(
                    "Valor previsto",
                    min_value=0.0,
                    step=50.0,
                    value=float(registro_pagamento_contrato.get("valor_semanal", 0) or 0.0),
                    format="%.2f",
                    key=f"fin_val_prev_novo_{contrato_pagamento_id}"
                )
            with colp3:
                valor_pago = st.number_input(
                    "Valor pago inicial",
                    min_value=0.0,
                    step=50.0,
                    value=0.0,
                    format="%.2f",
                    key=f"fin_val_pago_novo_{contrato_pagamento_id}"
                )

            colp4, colp5 = st.columns(2)
            with colp4:
                marcar_como_pago = st.checkbox(
                    "Já registrar pagamento agora",
                    key=f"fin_marca_pago_{contrato_pagamento_id}"
                )
            with colp5:
                data_pagamento_novo = st.date_input(
                    "Data do pagamento",
                    value=date.today(),
                    key=f"fin_data_pagto_novo_{contrato_pagamento_id}"
                )

            observacao = st.text_input(
                "Observação da cobrança",
                key=f"fin_obs_novo_{contrato_pagamento_id}"
            )

            comprovante_novo = st.file_uploader(
                "Comprovante (opcional)",
                type=["jpg", "jpeg", "png", "pdf", "doc", "docx", "webp"],
                key=f"fin_novo_comprovante_{contrato_pagamento_id}"
            )

            salvar_novo_pagamento = st.form_submit_button("Salvar nova cobrança")

        if salvar_novo_pagamento:
            status_novo = "Pendente"
            data_pagto_salvar = None
            valor_pago_salvar = float(valor_pago or 0.0)

            if marcar_como_pago:
                data_pagto_salvar = str(data_pagamento_novo)
                status_novo = classificar_status_pagamento_item(
                    valor_previsto=float(valor_previsto or 0.0),
                    valor_pago=float(valor_pago_salvar or 0.0),
                    data_vencimento=pd.Timestamp(data_vencimento)
                )
                if status_novo == "Vencido":
                    status_novo = "Pendente"
            else:
                valor_pago_salvar = 0.0
                status_novo = classificar_status_pagamento_item(
                    valor_previsto=float(valor_previsto or 0.0),
                    valor_pago=0.0,
                    data_vencimento=pd.Timestamp(data_vencimento)
                )

            caminho_comp = salvar_comprovante_upload(comprovante_novo, contrato_pagamento_id)

            registrar_pagamento_db(
                contrato_id=int(contrato_pagamento_id),
                valor_previsto=float(valor_previsto or 0.0),
                data_vencimento=str(data_vencimento),
                valor_pago=float(valor_pago_salvar or 0.0),
                data_pagamento=data_pagto_salvar,
                status=status_novo,
                observacao=observacao,
                comprovante_pagamento=caminho_comp,
            )

            st.success("Cobrança registrada com sucesso.")
            st.rerun()

    with subt2:
        if pagamentos_contrato.empty:
            st.info("Esse contrato ainda não possui cobranças para editar.")
        else:
            opcoes_pag = {
                f"Cobrança #{int(row['id'])} - {row['observacao'] or 'Sem observação'} - {row['status_real']}": int(row["id"])
                for _, row in pagamentos_contrato.iterrows()
            }

            pagamento_escolhido = st.selectbox(
                "Selecione a cobrança",
                list(opcoes_pag.keys()),
                key=f"fin_editar_pagamento_select_{contrato_pagamento_id}"
            )

            pagamento_id_editar = opcoes_pag[pagamento_escolhido]
            registro_pagamento = pagamentos_contrato[
                pagamentos_contrato["id"] == pagamento_id_editar
            ].iloc[0]

            with st.form(f"fin_form_editar_pagamento_{pagamento_id_editar}"):
                colu1, colu2, colu3 = st.columns(3)
                with colu1:
                    venc_default = registro_pagamento["data_vencimento"]
                    venc_default = venc_default.date() if pd.notna(venc_default) else date.today()
                    data_vencimento_edit = st.date_input(
                        "Data de vencimento",
                        value=venc_default,
                        key=f"fin_venc_edit_{pagamento_id_editar}"
                    )
                with colu2:
                    valor_previsto_edit = st.number_input(
                        "Valor previsto",
                        min_value=0.0,
                        step=50.0,
                        value=float(registro_pagamento["valor_previsto"] or 0.0),
                        format="%.2f",
                        key=f"fin_prev_edit_{pagamento_id_editar}"
                    )
                with colu3:
                    valor_pago_edit = st.number_input(
                        "Valor pago",
                        min_value=0.0,
                        step=50.0,
                        value=float(registro_pagamento["valor_pago"] or 0.0),
                        format="%.2f",
                        key=f"fin_pago_edit_{pagamento_id_editar}"
                    )

                data_pagto_default = registro_pagamento["data_pagamento"]
                data_pagto_default = data_pagto_default.date() if pd.notna(data_pagto_default) else date.today()

                colu4, colu5 = st.columns(2)
                with colu4:
                    data_pagamento_edit = st.date_input(
                        "Data do pagamento",
                        value=data_pagto_default,
                        key=f"fin_data_pagto_edit_{pagamento_id_editar}"
                    )
                with colu5:
                    status_opcoes = ["Pendente", "Parcial", "Pago", "Vencido"]
                    status_atual = str(registro_pagamento["status_real"] or "Pendente")
                    if status_atual not in status_opcoes:
                        status_atual = "Pendente"

                    status_manual = st.selectbox(
                        "Status",
                        status_opcoes,
                        index=status_opcoes.index(status_atual),
                        key=f"fin_status_edit_{pagamento_id_editar}"
                    )

                observacao_edit = st.text_input(
                    "Observação",
                    value=registro_pagamento["observacao"] or "",
                    key=f"fin_obs_edit_{pagamento_id_editar}"
                )

                comprovante_edit = st.file_uploader(
                    "Novo comprovante (opcional)",
                    type=["jpg", "jpeg", "png", "pdf", "doc", "docx", "webp"],
                    key=f"fin_comprovante_edit_{pagamento_id_editar}"
                )

                salvar_edicao = st.form_submit_button("Salvar alterações da cobrança")

            if salvar_edicao:
                caminho_comp_edit = None
                if comprovante_edit is not None:
                    caminho_comp_edit = salvar_comprovante_upload(
                        comprovante_edit,
                        contrato_pagamento_id
                    )

                sucesso = atualizar_pagamento_registrado(
                    pagamento_id=int(pagamento_id_editar),
                    data_vencimento=str(data_vencimento_edit),
                    data_pagamento=str(data_pagamento_edit) if status_manual in ["Pago", "Parcial"] else None,
                    valor_previsto=float(valor_previsto_edit or 0.0),
                    valor_pago=float(valor_pago_edit or 0.0),
                    status=status_manual,
                    observacao=observacao_edit,
                    comprovante_pagamento=caminho_comp_edit
                )

                if sucesso:
                    st.success("Cobrança atualizada com sucesso.")
                    st.rerun()
                else:
                    st.warning("Não foi possível atualizar a cobrança.")

            caminho_comprovante = registro_pagamento["comprovante_pagamento"]
            st.write(f"**Comprovante atual:** {caminho_comprovante or 'Nenhum arquivo enviado'}")

            if caminho_comprovante and os.path.exists(caminho_comprovante):
                if eh_imagem_preview(caminho_comprovante):
                    st.image(caminho_comprovante, width=180, caption="Pré-visualização do comprovante")

                with open(caminho_comprovante, "rb") as f:
                    st.download_button(
                        "Baixar comprovante atual",
                        data=f,
                        file_name=os.path.basename(caminho_comprovante),
                        use_container_width=True,
                        key=f"fin_download_comprovante_{pagamento_id_editar}"
                    )

    with subt3:
        if pagamentos_contrato.empty:
            st.info("Esse contrato ainda não possui cobranças para excluir.")
        else:
            opcoes_excluir = {
                f"Cobrança #{int(row['id'])} - {row['observacao'] or 'Sem observação'} - {row['status_real']}": int(row["id"])
                for _, row in pagamentos_contrato.iterrows()
            }

            pagamento_excluir_nome = st.selectbox(
                "Selecione a cobrança para excluir",
                list(opcoes_excluir.keys()),
                key=f"fin_excluir_pagamento_select_{contrato_pagamento_id}"
            )
            pagamento_id_excluir = opcoes_excluir[pagamento_excluir_nome]

            registro_excluir = pagamentos_contrato[
                pagamentos_contrato["id"] == pagamento_id_excluir
            ].iloc[0]

            st.markdown("""
            <div class="fin-alert-red">
                Atenção: esta exclusão remove a cobrança de forma definitiva e recalcula o resumo financeiro do contrato.
            </div>
            """, unsafe_allow_html=True)

            st.write(f"**Cobrança selecionada:** #{int(registro_excluir['id'])}")
            st.write(f"**Observação:** {registro_excluir['observacao'] or '-'}")
            st.write(f"**Valor previsto:** {formatar_moeda(registro_excluir['valor_previsto'])}")
            st.write(f"**Valor pago:** {formatar_moeda(registro_excluir['valor_pago'])}")
            st.write(f"**Status:** {registro_excluir['status_real']}")

            confirmar_exclusao = st.checkbox(
                "Confirmo que desejo excluir esta cobrança",
                key=f"fin_confirmar_exclusao_{pagamento_id_excluir}"
            )

            if st.button(
                "Excluir cobrança selecionada",
                key=f"fin_btn_excluir_pag_{pagamento_id_excluir}"
            ):
                if not confirmar_exclusao:
                    st.warning("Marque a confirmação antes de excluir a cobrança.")
                else:
                    sucesso = excluir_pagamento_registrado(int(pagamento_id_excluir))
                    if sucesso:
                        st.success("Cobrança excluída com sucesso.")
                        st.rerun()
                    else:
                        st.warning("Não foi possível excluir a cobrança selecionada.")

    with subt4:
        st.markdown("#### Histórico financeiro do contrato")

        if pagamentos_contrato.empty:
            st.info("Esse contrato ainda não possui histórico de cobranças.")
        else:
            hist = pagamentos_contrato[[
                "id", "data_vencimento", "data_pagamento", "valor_previsto",
                "valor_pago", "status_real", "observacao", "comprovante_pagamento"
            ]].copy()

            hist = preparar_tabela_para_exibicao(
                hist,
                colunas_data=["data_vencimento", "data_pagamento"],
                colunas_moeda=["valor_previsto", "valor_pago"]
            )

            st.dataframe(hist, use_container_width=True)


def renderizar_aba_registrar_pagamento(contratos_disponiveis):
    st.markdown("""
    <div class="fin-box">
        <div class="fin-box-title">Registrar pagamento</div>
        <div class="fin-box-sub">
            Ação direta, sem depender da tela de contratos. Pode registrar pagamento total, parcial ou apenas criar cobrança pendente.
        </div>
    </div>
    """, unsafe_allow_html=True)

    if contratos_disponiveis.empty:
        st.info("Nenhum contrato disponível para registrar pagamento.")
        return

    contratos_form = contratos_disponiveis.copy().sort_values("id", ascending=False)
    mapa_contratos = {
        int(row["id"]): f"Contrato {int(row['id'])} | {row['cliente']} | {row['veiculo']}"
        for _, row in contratos_form.iterrows()
    }

    with st.form("form_registrar_pagamento_financeiro", clear_on_submit=False):
        contrato_id = st.selectbox(
            "Contrato",
            options=list(mapa_contratos.keys()),
            format_func=lambda x: mapa_contratos.get(x, f"Contrato {x}")
        )

        info = contratos_form[contratos_form["id"] == contrato_id].iloc[0]
        col1, col2, col3 = st.columns(3)
        col1.metric("Valor contratado", formatar_moeda(info.get("valor_total_contrato", 0)))
        col2.metric("Valor já recebido", formatar_moeda(info.get("valor_pago_principal", info.get("valor_pago", 0))))
        col3.metric("Saldo pendente", formatar_moeda(info.get("valor_pendente", 0)))

        c1, c2 = st.columns(2)
        with c1:
            data_vencimento = st.date_input("Data de vencimento", value=date.today(), key="fin_data_vencimento")
            valor_previsto = st.number_input("Valor previsto", min_value=0.0, value=float(info.get("valor_semanal", 0) or 0), step=50.0, format="%.2f")
            status = st.selectbox("Status do lançamento", ["Pendente", "Pago", "Parcial"], index=0)
        with c2:
            data_pagamento = st.date_input("Data do pagamento", value=date.today(), key="fin_data_pagamento")
            valor_pago = st.number_input("Valor pago", min_value=0.0, value=0.0, step=50.0, format="%.2f")
            observacao = st.text_input("Observação", placeholder="Ex.: pagamento via PIX, ajuste, cobrança da semana 3")

        comprovante = st.file_uploader("Comprovante (opcional)", type=["png", "jpg", "jpeg", "pdf"], key="fin_comprovante")
        enviar = st.form_submit_button("Registrar lançamento")

    if enviar:
        status_final = status
        if valor_pago > 0 and valor_previsto > 0:
            if valor_pago >= valor_previsto:
                status_final = "Pago"
            else:
                status_final = "Parcial"
        elif valor_pago > 0 and valor_previsto == 0:
            status_final = "Pago"
        elif valor_pago <= 0 and status == "Pago":
            status_final = "Pendente"

        caminho_comprovante = salvar_comprovante_upload(comprovante, contrato_id)
        registrar_pagamento_db(
            contrato_id=contrato_id,
            valor_previsto=valor_previsto,
            data_vencimento=str(data_vencimento),
            valor_pago=valor_pago,
            data_pagamento=str(data_pagamento) if valor_pago > 0 else None,
            status=status_final,
            observacao=observacao,
            comprovante_pagamento=caminho_comprovante,
        )
        st.success("Lançamento financeiro registrado com sucesso.")
        st.rerun()


def renderizar_aba_historico(pagamentos_periodo, fluxo, manut_base, despesas_base):
    st.markdown("""
    <div class="fin-box">
        <div class="fin-box-title">Histórico e auditoria</div>
        <div class="fin-box-sub">
            Consulta detalhada de pagamentos, fluxo mensal, manutenções e despesas operacionais.
        </div>
    </div>
    """, unsafe_allow_html=True)

    sub1, sub2, sub3, sub4 = st.tabs(["Pagamentos", "Fluxo mensal", "Manutenções", "Despesas"])

    with sub1:
        if pagamentos_periodo.empty:
            st.info("Nenhum pagamento encontrado no período.")
        else:
            busca_hist = st.text_input("Buscar no histórico", placeholder="Cliente, veículo, placa, observação ou status", key="busca_hist_pag")
            hist = pagamentos_periodo.copy()
            if busca_hist:
                termo = busca_hist.strip().lower()
                hist = hist[
                    hist["cliente"].astype(str).str.lower().str.contains(termo, na=False) |
                    hist["veiculo"].astype(str).str.lower().str.contains(termo, na=False) |
                    hist["placa"].astype(str).str.lower().str.contains(termo, na=False) |
                    hist["observacao"].astype(str).str.lower().str.contains(termo, na=False) |
                    hist["status_real"].astype(str).str.lower().str.contains(termo, na=False)
                ]
            tabela = hist[[
                "id", "contrato_id", "cliente", "veiculo", "data_vencimento", "data_pagamento",
                "valor_previsto", "valor_pago", "status_real", "observacao", "comprovante_pagamento"
            ]].copy()
            tabela = preparar_tabela_para_exibicao(
                tabela,
                colunas_data=["data_vencimento", "data_pagamento"],
                colunas_moeda=["valor_previsto", "valor_pago"]
            )
            st.dataframe(tabela, use_container_width=True)

    with sub2:
        if fluxo.empty:
            st.info("Sem fluxo mensal consolidado no período.")
        else:
            fluxo_tabela = preparar_tabela_para_exibicao(
                fluxo,
                colunas_moeda=["recebido", "manutencao", "despesa", "custo_total", "resultado"]
            )
            st.dataframe(fluxo_tabela, use_container_width=True)

    with sub3:
        if manut_base.empty:
            st.info("Nenhuma manutenção encontrada no período.")
        else:
            busca_manut = st.text_input("Buscar manutenção", placeholder="Veículo, placa, tipo ou oficina", key="busca_manut_fin")
            df_manut = manut_base.copy()
            if busca_manut:
                termo = busca_manut.strip().lower()
                df_manut = df_manut[
                    df_manut["veiculo"].astype(str).str.lower().str.contains(termo, na=False) |
                    df_manut["placa"].astype(str).str.lower().str.contains(termo, na=False) |
                    df_manut["tipo_servico"].astype(str).str.lower().str.contains(termo, na=False) |
                    df_manut["oficina"].astype(str).str.lower().str.contains(termo, na=False)
                ]
            tabela_manut = df_manut[["id", "veiculo", "data_manutencao", "tipo_servico", "descricao", "oficina", "valor"]].copy()
            tabela_manut = preparar_tabela_para_exibicao(tabela_manut, colunas_data=["data_manutencao"], colunas_moeda=["valor"])
            st.dataframe(tabela_manut, use_container_width=True)

    with sub4:
        if despesas_base.empty:
            st.info("Nenhuma despesa encontrada no período.")
        else:
            busca_desp = st.text_input("Buscar despesa", placeholder="Veículo, placa, categoria ou descrição", key="busca_desp_fin")
            df_desp = despesas_base.copy()
            if busca_desp:
                termo = busca_desp.strip().lower()
                df_desp = df_desp[
                    df_desp["veiculo"].astype(str).str.lower().str.contains(termo, na=False) |
                    df_desp["placa"].astype(str).str.lower().str.contains(termo, na=False) |
                    df_desp["categoria"].astype(str).str.lower().str.contains(termo, na=False) |
                    df_desp["descricao"].astype(str).str.lower().str.contains(termo, na=False)
                ]
            tabela_desp = df_desp[["id", "veiculo", "data_despesa", "categoria", "descricao", "valor"]].copy()
            tabela_desp = preparar_tabela_para_exibicao(tabela_desp, colunas_data=["data_despesa"], colunas_moeda=["valor"])
            st.dataframe(tabela_desp, use_container_width=True)


# ==========================================
# TELA
# ==========================================

def tela_financeiro():
    aplicar_estilo_financeiro()
    st.subheader("Financeiro")
    card_abertura_financeiro()

    conn = conectar()
    contratos, pagamentos, manutencoes, despesas = carregar_dados_financeiros(conn)
    conn.close()

    contratos = preparar_contratos_financeiros(contratos, pagamentos)

    todas_datas = []
    if not contratos.empty:
        todas_datas.extend(contratos["data_inicio"].dropna().tolist())
        todas_datas.extend(contratos["data_pagamento"].dropna().tolist())
    if not pagamentos.empty:
        todas_datas.extend(pagamentos["data_vencimento"].dropna().tolist())
        todas_datas.extend(pagamentos["data_pagamento"].dropna().tolist())
    if not manutencoes.empty:
        todas_datas.extend(manutencoes["data_manutencao"].dropna().tolist())
    if not despesas.empty:
        todas_datas.extend(despesas["data_despesa"].dropna().tolist())

    if todas_datas:
        data_min = min(todas_datas).date()
        data_max = max(todas_datas).date()
    else:
        hoje = pd.Timestamp.today().date()
        data_min = hoje
        data_max = hoje

    st.markdown("""
    <div class="fin-box">
        <div class="fin-box-title">Filtros gerenciais</div>
        <div class="fin-box-sub">
            Analise o financeiro por período, contratos e cobranças sem perder velocidade operacional.
        </div>
    </div>
    """, unsafe_allow_html=True)

    colf1, colf2, colf3, colf4 = st.columns([1, 1, 1.1, 1.1])
    with colf1:
        data_inicio = st.date_input("Data inicial", value=data_min, min_value=data_min, max_value=data_max)
    with colf2:
        data_fim = st.date_input("Data final", value=data_max, min_value=data_min, max_value=data_max)
    with colf3:
        filtro_status_contrato = st.multiselect(
            "Status dos contratos",
            ["Pago", "Parcial", "Pendente", "Vencido"],
            default=["Pago", "Parcial", "Pendente", "Vencido"]
        )
    with colf4:
        filtro_status_cobranca = st.multiselect(
            "Status das cobranças",
            ["Pago", "Parcial", "Pendente", "Vencido"],
            default=["Pago", "Parcial", "Pendente", "Vencido"]
        )

    if data_inicio > data_fim:
        st.error("A data inicial não pode ser maior que a data final.")
        return

    contratos_base = filtrar_periodo(contratos, "data_inicio", data_inicio, data_fim)
    manut_base = filtrar_periodo(manutencoes, "data_manutencao", data_inicio, data_fim)
    despesas_base = filtrar_periodo(despesas, "data_despesa", data_inicio, data_fim)

    contratos_base = preparar_contratos_financeiros(contratos_base, pagamentos)

    pagamentos_periodo = pagamentos.copy()
    if not pagamentos_periodo.empty:
        mask_venc = pagamentos_periodo["data_vencimento"].between(pd.Timestamp(data_inicio), pd.Timestamp(data_fim), inclusive="both")
        mask_pag = pagamentos_periodo["data_pagamento"].between(pd.Timestamp(data_inicio), pd.Timestamp(data_fim), inclusive="both")
        pagamentos_periodo = pagamentos_periodo[mask_venc | mask_pag]

    if filtro_status_contrato:
        contratos_base = contratos_base[contratos_base["status_financeiro_real"].isin(filtro_status_contrato)]

    if filtro_status_cobranca and not pagamentos_periodo.empty:
        pagamentos_periodo = pagamentos_periodo[pagamentos_periodo["status_real"].isin(filtro_status_cobranca)]

    if not pagamentos_periodo.empty and not contratos_base.empty:
        contratos_ids_validos = pagamentos_periodo["contrato_id"].dropna().unique().tolist()
        

    fluxo = consolidar_fluxo_mensal(contratos_base, pagamentos_periodo, manut_base, despesas_base)

    modo_mobile = st.toggle("Modo mobile", value=False)

    aba1, aba2, aba3, aba4 = st.tabs(["📊 Painel", "⚠️ Cobranças", "💵 Registrar pagamento", "📚 Histórico"])
    with aba1:
        renderizar_aba_painel(contratos_base, pagamentos_periodo, manut_base, despesas_base, modo_mobile=modo_mobile)
    with aba2:
        renderizar_aba_cobrancas(contratos_base, pagamentos_periodo)
    with aba3:
        renderizar_aba_registrar_pagamento(contratos)
    with aba4:
        renderizar_aba_historico(pagamentos_periodo, fluxo, manut_base, despesas_base)
