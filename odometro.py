import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from database import conectar
from utils import obter_resumo_km_veiculo


LIMITE_MENSAL_PADRAO = 8000


def aplicar_estilo_odometro():
    st.markdown(
        """
    <style>
    .odo-card {
        background: linear-gradient(180deg, #111827 0%, #0b1220 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 18px;
        padding: 18px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.18);
        margin-bottom: 14px;
    }

    .odo-title {
        font-size: 1.08rem;
        font-weight: 800;
        color: #f8fafc;
        margin-bottom: 6px;
    }

    .odo-subtitle {
        font-size: 0.92rem;
        color: #94a3b8;
        margin-bottom: 0;
    }

    .odo-kpi {
        background: linear-gradient(180deg, #111827 0%, #0f172a 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
        padding: 14px;
        text-align: center;
        margin-bottom: 10px;
    }

    .odo-kpi-label {
        color: #94a3b8;
        font-size: 0.88rem;
        margin-bottom: 6px;
    }

    .odo-kpi-value {
        color: #f8fafc;
        font-size: 1.35rem;
        font-weight: 800;
        line-height: 1.1;
    }

    .odo-mini-info {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 14px;
        padding: 12px 14px;
        margin-top: 8px;
        margin-bottom: 12px;
    }

    .odo-alert-ok {
        background: rgba(34, 197, 94, 0.08);
        border: 1px solid rgba(34, 197, 94, 0.20);
        border-radius: 14px;
        padding: 12px 14px;
        color: #86efac;
        font-weight: 700;
        margin-bottom: 12px;
    }

    .odo-alert-warn {
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.22);
        border-radius: 14px;
        padding: 12px 14px;
        color: #fbbf24;
        font-weight: 700;
        margin-bottom: 12px;
    }

    .odo-alert-critical {
        background: rgba(251, 146, 60, 0.08);
        border: 1px solid rgba(251, 146, 60, 0.22);
        border-radius: 14px;
        padding: 12px 14px;
        color: #fdba74;
        font-weight: 700;
        margin-bottom: 12px;
    }

    .odo-alert-danger {
        background: rgba(239, 68, 68, 0.08);
        border: 1px solid rgba(239, 68, 68, 0.22);
        border-radius: 14px;
        padding: 12px 14px;
        color: #fca5a5;
        font-weight: 700;
        margin-bottom: 12px;
    }

    .odo-ranking-chip {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 999px;
        font-size: 0.80rem;
        font-weight: 700;
    }

    .odo-chip-ok { background: rgba(34, 197, 94, 0.12); color: #86efac; }
    .odo-chip-warn { background: rgba(245, 158, 11, 0.12); color: #fbbf24; }
    .odo-chip-critical { background: rgba(251, 146, 60, 0.12); color: #fdba74; }
    .odo-chip-danger { background: rgba(239, 68, 68, 0.12); color: #fca5a5; }
    </style>
    """,
        unsafe_allow_html=True,
    )


def formatar_km(valor):
    try:
        return f"{int(float(valor or 0)):,} km".replace(",", ".")
    except Exception:
        return "0 km"


def normalizar_percentual(resumo):
    percentual = resumo.get("percentual_uso")
    if percentual is None:
        percentual = resumo.get("percentual_mes", resumo.get("percentual", 0))

    try:
        percentual = float(percentual or 0)
    except Exception:
        percentual = 0.0

    if percentual <= 1.0:
        percentual *= 100

    return max(0.0, percentual)


def classificar_status_percentual(percentual):
    if percentual > 100:
        return "excedido", "Excedido"
    if percentual >= 90:
        return "critico", "Crítico"
    if percentual >= 70:
        return "atencao", "Atenção"
    return "normal", "Dentro do limite"


def metadados_status(status_raw):
    mapa = {
        "normal": {
            "label": "Dentro do limite",
            "icone": "✅",
            "classe": "odo-chip-ok",
            "alerta": "odo-alert-ok",
        },
        "atencao": {
            "label": "Atenção",
            "icone": "⚠️",
            "classe": "odo-chip-warn",
            "alerta": "odo-alert-warn",
        },
        "critico": {
            "label": "Crítico",
            "icone": "🟠",
            "classe": "odo-chip-critical",
            "alerta": "odo-alert-critical",
        },
        "excedido": {
            "label": "Excedido",
            "icone": "🚨",
            "classe": "odo-chip-danger",
            "alerta": "odo-alert-danger",
        },
    }
    return mapa.get(status_raw, mapa["normal"])


def carregar_base_odometro():
    conn = conectar()

    contratos_ativos = pd.read_sql_query(
        """
        SELECT
            c.id AS contrato_id,
            c.veiculo_id,
            c.status,
            c.data_inicio,
            c.data_fim,
            cl.nome AS cliente,
            v.modelo,
            v.placa
        FROM contratos c
        INNER JOIN clientes cl ON cl.id = c.cliente_id
        INNER JOIN veiculos v ON v.id = c.veiculo_id
        WHERE c.status = 'Ativo'
        ORDER BY c.id DESC
    """,
        conn,
    )

    vistorias = pd.read_sql_query(
        """
        SELECT
            v.id,
            v.veiculo_id,
            v.contrato_id,
            ve.modelo || ' - ' || ve.placa AS veiculo,
            ve.modelo,
            ve.placa,
            v.data_vistoria,
            v.odometro
        FROM vistorias v
        INNER JOIN veiculos ve ON ve.id = v.veiculo_id
        WHERE v.odometro IS NOT NULL
        ORDER BY date(v.data_vistoria) ASC, v.id ASC
    """,
        conn,
    )

    conn.close()
    return contratos_ativos, vistorias


def montar_df_resumo():
    conn = conectar()

    contratos_ativos = pd.read_sql_query(
        """
        SELECT
            c.id AS contrato_id,
            c.veiculo_id,
            c.data_inicio,
            c.data_fim,
            cl.nome AS cliente,
            v.modelo,
            v.placa
        FROM contratos c
        INNER JOIN clientes cl ON cl.id = c.cliente_id
        INNER JOIN veiculos v ON v.id = c.veiculo_id
        WHERE c.status = 'Ativo'
        ORDER BY v.modelo
    """,
        conn,
    )

    veiculos = pd.read_sql_query(
        """
        SELECT
            id,
            modelo,
            placa,
            status
        FROM veiculos
        ORDER BY modelo
    """,
        conn,
    )

    linhas = []

    for _, row in veiculos.iterrows():
        contrato_match = contratos_ativos[contratos_ativos["veiculo_id"] == row["id"]]

        contrato_id = None
        cliente = "-"
        data_inicio = "-"
        data_fim = "-"

        if not contrato_match.empty:
            contrato_row = contrato_match.iloc[0]
            contrato_id = int(contrato_row["contrato_id"])
            cliente = contrato_row["cliente"]
            data_inicio = contrato_row["data_inicio"]
            data_fim = contrato_row["data_fim"]

        resumo = obter_resumo_km_veiculo(
            conn=conn,
            veiculo_id=int(row["id"]),
            contrato_id=contrato_id,
            limite_mensal=LIMITE_MENSAL_PADRAO,
        )

        percentual_uso = normalizar_percentual(resumo)
        status_raw, status_visual = classificar_status_percentual(percentual_uso)

        linhas.append(
            {
                "veiculo_id": int(row["id"]),
                "veiculo": f"{row['modelo']} - {row['placa']}",
                "modelo": row["modelo"],
                "placa": row["placa"],
                "status_veiculo": row["status"],
                "contrato_id": contrato_id,
                "cliente": cliente,
                "data_inicio": data_inicio,
                "data_fim": data_fim,
                "ultimo_odometro": float(resumo.get("ultimo_odometro", 0) or 0),
                "km_semana": float(resumo.get("km_semana", 0) or 0),
                "km_mes": float(resumo.get("km_mes", 0) or 0),
                "km_contrato": float(resumo.get("km_contrato", 0) or 0),
                "limite_mensal": float(resumo.get("limite_mensal", LIMITE_MENSAL_PADRAO) or LIMITE_MENSAL_PADRAO),
                "percentual_uso": percentual_uso,
                "status_km": status_visual,
                "status_km_raw": status_raw,
            }
        )

    conn.close()

    df = pd.DataFrame(linhas)
    if df.empty:
        return df

    return df.sort_values(by=["percentual_uso", "ultimo_odometro"], ascending=[False, False])


def grafico_linha_odometro(df_vistorias, veiculo_id):
    df = df_vistorias[df_vistorias["veiculo_id"] == veiculo_id].copy()

    if df.empty or len(df) < 2:
        st.info("São necessárias ao menos 2 vistorias com KM para gerar o gráfico de evolução.")
        return

    df["data_vistoria"] = pd.to_datetime(df["data_vistoria"], errors="coerce")
    df["odometro"] = pd.to_numeric(df["odometro"], errors="coerce")
    df = df.dropna(subset=["data_vistoria", "odometro"])
    df = df.sort_values(by=["data_vistoria", "id"])

    if df.empty or len(df) < 2:
        st.info("São necessárias ao menos 2 vistorias válidas com KM para gerar o gráfico de evolução.")
        return

    df["data_label"] = df["data_vistoria"].dt.strftime("%d/%m")
    posicoes_x = list(range(len(df)))

    bg_color = "#0b1220"
    text_color = "#e5e7eb"
    grid_color = "#334155"
    line_color = "#60a5fa"

    plt.rcParams.update(
        {
            "figure.facecolor": bg_color,
            "axes.facecolor": bg_color,
            "savefig.facecolor": bg_color,
            "text.color": text_color,
            "axes.labelcolor": text_color,
            "xtick.color": text_color,
            "ytick.color": text_color,
            "axes.edgecolor": grid_color,
            "font.size": 10,
        }
    )

    fig, ax = plt.subplots(figsize=(9.0, 4.2))
    ax.plot(
        posicoes_x,
        df["odometro"],
        marker="o",
        linewidth=2.5,
        markersize=6,
        color=line_color,
    )

    ax.set_title("Evolução do odômetro", fontsize=12, pad=10)
    ax.set_xlabel("Data da vistoria")
    ax.set_ylabel("KM")
    ax.set_xticks(posicoes_x)
    ax.set_xticklabels(df["data_label"].tolist(), rotation=20)
    ax.grid(True, axis="y", linestyle="--", alpha=0.25)
    ax.grid(False, axis="x")
    ax.margins(x=0.05)
    fig.tight_layout()
    st.pyplot(fig, clear_figure=True)


def grafico_rosca_limite(km_mes, limite_mensal):
    usado = max(0.0, float(km_mes or 0))
    limite = max(1.0, float(limite_mensal or 1))
    percentual = (usado / limite) * 100 if limite > 0 else 0

    bg_color = "#0b1220"
    text_color = "#e5e7eb"

    plt.rcParams.update(
        {
            "figure.facecolor": bg_color,
            "axes.facecolor": bg_color,
            "savefig.facecolor": bg_color,
            "text.color": text_color,
        }
    )

    if usado <= limite:
        valores = [usado, max(0.0, limite - usado)]
        labels = ["Usado", "Disponível"]
        colors = ["#60a5fa", "#1f2937"]
    else:
        valores = [limite, max(0.0, usado - limite)]
        labels = ["Limite", "Excedente"]
        colors = ["#60a5fa", "#ef4444"]

    fig, ax = plt.subplots(figsize=(4.3, 4.3))
    ax.pie(
        valores,
        labels=labels,
        startangle=90,
        colors=colors,
        wedgeprops={"width": 0.34, "edgecolor": bg_color, "linewidth": 2},
        textprops={"color": text_color, "fontsize": 9},
    )

    ax.text(
        0,
        0,
        f"{int(usado):,}\nkm\n{percentual:.1f}%".replace(",", "."),
        ha="center",
        va="center",
        fontsize=11,
        color=text_color,
        fontweight="bold",
    )
    ax.set_title("Uso do limite mensal", fontsize=12, pad=10, color=text_color)
    ax.axis("equal")
    st.pyplot(fig, clear_figure=True)


def exibir_alerta_operacional(registro):
    percentual = float(registro["percentual_uso"])
    km_mes = float(registro["km_mes"])
    limite = float(registro["limite_mensal"])
    meta_atencao = limite * 0.7
    meta_critica = limite * 0.9

    status = registro["status_km_raw"]
    meta = metadados_status(status)

    if status == "excedido":
        excedente = max(0.0, km_mes - limite)
        texto = (
            f"{meta['icone']} Limite mensal excedido em {formatar_km(excedente)}. "
            f"Uso atual: {formatar_km(km_mes)} de {formatar_km(limite)}."
        )
    elif status == "critico":
        faltante = max(0.0, limite - km_mes)
        texto = (
            f"{meta['icone']} Veículo em faixa crítica. Restam apenas {formatar_km(faltante)} "
            f"para atingir o limite mensal."
        )
    elif status == "atencao":
        restante_critico = max(0.0, meta_critica - km_mes)
        texto = (
            f"{meta['icone']} Veículo em atenção. Faltam {formatar_km(restante_critico)} "
            f"para entrar na faixa crítica de uso."
        )
    else:
        margem = max(0.0, meta_atencao - km_mes)
        texto = (
            f"{meta['icone']} Dentro do limite. Ainda há uma margem confortável de "
            f"{formatar_km(margem)} até a faixa de atenção."
        )

    st.markdown(f'<div class="{meta["alerta"]}">{texto}</div>', unsafe_allow_html=True)


def montar_chip_status_html(status_raw):
    meta = metadados_status(status_raw)
    return (
        f'<span class="odo-ranking-chip {meta["classe"]}">{meta["icone"]} {meta["label"]}</span>'
    )


def tela_odometro():
    aplicar_estilo_odometro()
    st.subheader("Controle de Odômetro")

    st.markdown(
        """
        <div class="odo-card">
            <div class="odo-title">Painel operacional de quilometragem</div>
            <div class="odo-subtitle">
                Monitore o uso semanal, mensal e por contrato, com alerta de risco e ranking da frota.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_resumo = montar_df_resumo()
    _, df_vistorias = carregar_base_odometro()

    if df_resumo.empty:
        st.info("Cadastre veículos e vistorias para visualizar o painel de odômetro.")
        return

    total_veiculos = len(df_resumo)
    veiculos_atencao = int((df_resumo["status_km_raw"] == "atencao").sum())
    veiculos_criticos = int((df_resumo["status_km_raw"] == "critico").sum())
    veiculos_excedidos = int((df_resumo["status_km_raw"] == "excedido").sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Veículos monitorados", total_veiculos)
    c2.metric("Em atenção", veiculos_atencao)
    c3.metric("Críticos", veiculos_criticos)
    c4.metric("Excedidos", veiculos_excedidos)

    st.divider()

    veiculos_opcoes = {row["veiculo"]: row["veiculo_id"] for _, row in df_resumo.iterrows()}
    veiculo_escolhido = st.selectbox("Selecione o veículo", list(veiculos_opcoes.keys()))
    veiculo_id = veiculos_opcoes[veiculo_escolhido]
    registro = df_resumo[df_resumo["veiculo_id"] == veiculo_id].iloc[0]

    st.markdown(
        """
        <div class="odo-card">
            <div class="odo-title">Resumo do veículo</div>
            <div class="odo-subtitle">Indicadores consolidados de uso, leituras registradas e limite mensal.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.markdown(
            f"""
            <div class="odo-kpi">
                <div class="odo-kpi-label">Último odômetro</div>
                <div class="odo-kpi-value">{formatar_km(registro['ultimo_odometro'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k2:
        st.markdown(
            f"""
            <div class="odo-kpi">
                <div class="odo-kpi-label">KM semana</div>
                <div class="odo-kpi-value">{formatar_km(registro['km_semana'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k3:
        st.markdown(
            f"""
            <div class="odo-kpi">
                <div class="odo-kpi-label">KM mês</div>
                <div class="odo-kpi-value">{formatar_km(registro['km_mes'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k4:
        st.markdown(
            f"""
            <div class="odo-kpi">
                <div class="odo-kpi-label">KM contrato</div>
                <div class="odo-kpi-value">{formatar_km(registro['km_contrato'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div class="odo-mini-info">
            <strong>Cliente:</strong> {registro['cliente']} &nbsp;&nbsp;|&nbsp;&nbsp;
            <strong>Contrato:</strong> {registro['contrato_id'] if pd.notna(registro['contrato_id']) else '-'} &nbsp;&nbsp;|&nbsp;&nbsp;
            <strong>Status veículo:</strong> {registro['status_veiculo']}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write(
        f"**Uso mensal:** {formatar_km(registro['km_mes'])} de {formatar_km(registro['limite_mensal'])} "
        f"({float(registro['percentual_uso']):.1f}%)"
    )
    st.progress(min(float(registro["percentual_uso"]) / 100, 1.0))
    st.markdown(montar_chip_status_html(registro["status_km_raw"]), unsafe_allow_html=True)
    exibir_alerta_operacional(registro)

    g1, g2 = st.columns([1.5, 1])
    with g1:
        grafico_linha_odometro(df_vistorias, veiculo_id)
    with g2:
        grafico_rosca_limite(km_mes=registro["km_mes"], limite_mensal=registro["limite_mensal"])

    st.divider()
    st.markdown("### Ranking de uso mensal")

    ranking = df_resumo[
        [
            "veiculo",
            "cliente",
            "ultimo_odometro",
            "km_semana",
            "km_mes",
            "km_contrato",
            "percentual_uso",
            "status_km",
            "status_km_raw",
        ]
    ].copy()

    ranking["último odômetro"] = ranking["ultimo_odometro"].map(formatar_km)
    ranking["KM semana"] = ranking["km_semana"].map(formatar_km)
    ranking["KM mês"] = ranking["km_mes"].map(formatar_km)
    ranking["KM contrato"] = ranking["km_contrato"].map(formatar_km)
    ranking["% uso"] = ranking["percentual_uso"].map(lambda x: f"{float(x):.1f}%")
    ranking["status"] = ranking["status_km_raw"].map(lambda s: metadados_status(s)["label"])

    ranking_exibir = ranking[
        ["veiculo", "cliente", "último odômetro", "KM semana", "KM mês", "KM contrato", "% uso", "status"]
    ].rename(columns={"veiculo": "Veículo", "cliente": "Cliente"})

    st.dataframe(ranking_exibir, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("### Últimas leituras de odômetro")

    historico = df_vistorias[df_vistorias["veiculo_id"] == veiculo_id].copy()
    if historico.empty:
        st.info("Sem histórico de vistorias para este veículo.")
    else:
        historico["data_vistoria"] = pd.to_datetime(historico["data_vistoria"], errors="coerce")
        historico = historico.sort_values(by=["data_vistoria", "id"], ascending=[False, False])
        historico["data_vistoria"] = historico["data_vistoria"].dt.strftime("%d/%m/%Y")
        historico["odometro"] = pd.to_numeric(historico["odometro"], errors="coerce").fillna(0).map(formatar_km)
        st.dataframe(
            historico[["data_vistoria", "odometro", "contrato_id"]].rename(
                columns={
                    "data_vistoria": "Data da vistoria",
                    "odometro": "Odômetro",
                    "contrato_id": "Contrato",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
