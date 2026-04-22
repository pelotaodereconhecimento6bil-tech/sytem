
import os
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from database import conectar


PASTA_FOTOS_MANUTENCOES = "fotos_manutencoes"
INTERVALO_PADRAO_RECOMPLETAMENTO_OLEO = 2600


def aplicar_estilo_manutencoes():
    st.markdown("""
    <style>
    .manut-top-card {
        background: linear-gradient(180deg, #111827 0%, #0f172a 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 18px;
        padding: 18px;
        margin-bottom: 14px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.16);
    }

    .manut-top-title {
        color: #f8fafc;
        font-size: 1.08rem;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .manut-top-sub {
        color: #94a3b8;
        font-size: 0.92rem;
        margin-bottom: 0;
    }

    .manut-box {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 14px;
        padding: 12px 14px;
        margin-top: 8px;
        margin-bottom: 12px;
    }

    .manut-box-title {
        color: #e5e7eb;
        font-size: 0.96rem;
        font-weight: 800;
        margin-bottom: 5px;
    }

    .manut-box-sub {
        color: #94a3b8;
        font-size: 0.88rem;
        margin-bottom: 0;
    }

    .manut-warning-box {
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.22);
        border-radius: 14px;
        padding: 12px 14px;
        margin-top: 10px;
        margin-bottom: 12px;
        color: #fbbf24;
        font-weight: 600;
    }

    .manut-alert-ok {
        background: rgba(34, 197, 94, 0.08);
        border: 1px solid rgba(34, 197, 94, 0.20);
        border-radius: 12px;
        padding: 10px 12px;
        margin-bottom: 10px;
        color: #86efac;
        font-weight: 700;
    }

    .manut-alert-info {
        background: rgba(59, 130, 246, 0.08);
        border: 1px solid rgba(59, 130, 246, 0.20);
        border-radius: 12px;
        padding: 10px 12px;
        margin-bottom: 10px;
        color: #93c5fd;
        font-weight: 700;
    }

    .manut-alert-warn {
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.20);
        border-radius: 12px;
        padding: 10px 12px;
        margin-bottom: 10px;
        color: #fbbf24;
        font-weight: 700;
    }

    .manut-alert-error {
        background: rgba(239, 68, 68, 0.08);
        border: 1px solid rgba(239, 68, 68, 0.20);
        border-radius: 12px;
        padding: 10px 12px;
        margin-bottom: 10px;
        color: #fca5a5;
        font-weight: 700;
    }

    .manut-kpi {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 14px;
        padding: 12px 14px;
        margin-bottom: 12px;
    }

    .manut-kpi-title {
        color: #94a3b8;
        font-size: 0.82rem;
        margin-bottom: 3px;
    }

    .manut-kpi-value {
        color: #f8fafc;
        font-size: 1.2rem;
        font-weight: 800;
        margin-bottom: 0;
    }

    .manut-chart-box {
        background: linear-gradient(180deg, rgba(255,255,255,0.035) 0%, rgba(255,255,255,0.02) 100%);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 16px;
        padding: 10px 10px 8px 10px;
        margin-bottom: 12px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.10);
    }

    .manut-chart-title {
        color: #f8fafc;
        font-size: 0.88rem;
        font-weight: 800;
        margin-bottom: 6px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)


def card_abertura_manutencoes():
    st.markdown("""
    <div class="manut-top-card">
        <div class="manut-top-title">Gestão de manutenções</div>
        <div class="manut-top-sub">
            Controle corretivo e preventivo da frota com histórico, custos, fotos e alertas por quilometragem.
        </div>
    </div>
    """, unsafe_allow_html=True)


def salvar_foto_manutencao(foto, veiculo_texto):
    if foto is None:
        return ""

    os.makedirs(PASTA_FOTOS_MANUTENCOES, exist_ok=True)

    nome_base = veiculo_texto.replace(" ", "_").replace("-", "_").replace("/", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    extensao = os.path.splitext(foto.name)[1].lower()

    if not extensao:
        extensao = ".jpg"

    nome_arquivo = f"manutencao_{nome_base}_{timestamp}{extensao}"
    caminho_arquivo = os.path.join(PASTA_FOTOS_MANUTENCOES, nome_arquivo)

    with open(caminho_arquivo, "wb") as f:
        f.write(foto.getbuffer())

    return caminho_arquivo


def formatar_moeda(valor):
    try:
        valor_float = float(valor or 0)
    except Exception:
        valor_float = 0.0
    return f"R$ {valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def classificar_alerta(km_atual, km_limite):
    if not km_limite or km_limite <= 0:
        return None

    diferenca = float(km_limite) - float(km_atual or 0)

    if diferenca < 0:
        return "vencido"
    if diferenca <= 500:
        return "urgente"
    if diferenca <= 1500:
        return "proximo"
    return None


def classificar_alerta_recompletamento(km_atual, km_ultimo_recompletamento, intervalo=INTERVALO_PADRAO_RECOMPLETAMENTO_OLEO):
    if not intervalo or intervalo <= 0:
        intervalo = INTERVALO_PADRAO_RECOMPLETAMENTO_OLEO
    if km_ultimo_recompletamento is None or int(km_ultimo_recompletamento or 0) <= 0:
        return None
    km_limite = int(km_ultimo_recompletamento or 0) + int(intervalo or INTERVALO_PADRAO_RECOMPLETAMENTO_OLEO)
    return classificar_alerta(km_atual, km_limite)


def calcular_limite_recompletamento(km_ultimo_recompletamento, intervalo):
    if km_ultimo_recompletamento is None or int(km_ultimo_recompletamento or 0) <= 0:
        return 0
    return int(km_ultimo_recompletamento or 0) + int(intervalo or INTERVALO_PADRAO_RECOMPLETAMENTO_OLEO)


def calcular_percentual_uso(km_atual, km_limite, km_base=0):
    try:
        km_atual = float(km_atual or 0)
        km_limite = float(km_limite or 0)
        km_base = float(km_base or 0)
    except Exception:
        return 0.0
    alcance = km_limite - km_base
    if alcance <= 0:
        return 0.0
    usado = km_atual - km_base
    return max(0.0, min((usado / alcance) * 100.0, 100.0))


def mostrar_alerta_item(nome, km_atual, km_limite):
    status = classificar_alerta(km_atual, km_limite)

    if status == "vencido":
        st.markdown(
            f'<div class="manut-alert-error">{nome}: vencido. Atual: {int(km_atual or 0)} km | Limite: {int(km_limite or 0)} km</div>',
            unsafe_allow_html=True,
        )
    elif status == "urgente":
        st.markdown(
            f'<div class="manut-alert-warn">{nome}: atenção. Atual: {int(km_atual or 0)} km | Limite: {int(km_limite or 0)} km</div>',
            unsafe_allow_html=True,
        )
    elif status == "proximo":
        st.markdown(
            f'<div class="manut-alert-info">{nome}: se aproximando. Atual: {int(km_atual or 0)} km | Limite: {int(km_limite or 0)} km</div>',
            unsafe_allow_html=True,
        )


def mostrar_alerta_recompletamento(km_atual, km_ultimo_recompletamento, intervalo):
    status = classificar_alerta_recompletamento(km_atual, km_ultimo_recompletamento, intervalo)
    if not status:
        return

    km_limite = calcular_limite_recompletamento(km_ultimo_recompletamento, intervalo)
    texto_base = (
        f"Recompletamento de óleo: Atual: {int(km_atual or 0)} km | "
        f"Último recompletamento: {int(km_ultimo_recompletamento or 0)} km | "
        f"Limite: {int(km_limite or 0)} km"
    )

    if status == "vencido":
        st.markdown(
            f'<div class="manut-alert-error">{texto_base} | vencido</div>',
            unsafe_allow_html=True,
        )
    elif status == "urgente":
        st.markdown(
            f'<div class="manut-alert-warn">{texto_base} | atenção</div>',
            unsafe_allow_html=True,
        )
    elif status == "proximo":
        st.markdown(
            f'<div class="manut-alert-info">{texto_base} | se aproximando</div>',
            unsafe_allow_html=True,
        )


def status_visual(status):
    if status == "vencido":
        return "Vencido"
    if status == "urgente":
        return "Urgente"
    if status == "proximo":
        return "Próximo"
    return "OK"


def carregar_manutencoes(conn):
    return pd.read_sql_query(
        """
        SELECT
            manutencoes.id,
            manutencoes.veiculo_id,
            veiculos.modelo || ' - ' || veiculos.placa AS veiculo,
            manutencoes.data_manutencao,
            manutencoes.tipo_servico,
            manutencoes.descricao,
            manutencoes.valor,
            manutencoes.oficina,
            manutencoes.km_atual,
            manutencoes.proxima_troca_oleo,
            manutencoes.km_ultimo_recompletamento_oleo,
            manutencoes.intervalo_recompletamento_oleo,
            manutencoes.km_prox_revisao,
            manutencoes.km_prox_pneu,
            manutencoes.km_prox_freio,
            manutencoes.km_prox_bateria,
            manutencoes.observacoes,
            manutencoes.foto_path
        FROM manutencoes
        INNER JOIN veiculos ON manutencoes.veiculo_id = veiculos.id
        ORDER BY manutencoes.id DESC
        """,
        conn,
    )


def obter_ultimos_controles(df):
    if df.empty:
        return pd.DataFrame()
    return df.sort_values("id", ascending=False).groupby("veiculo_id", as_index=False).first()


def obter_ultimo_controle_por_veiculo(df, veiculo_id):
    if df.empty:
        return {}
    base = df[df["veiculo_id"] == veiculo_id].sort_values("id", ascending=False)
    if base.empty:
        return {}
    return base.iloc[0].to_dict()


def gerar_registros_painel(ultimas):
    registros = []
    if ultimas.empty:
        return pd.DataFrame()

    for _, row in ultimas.iterrows():
        km_atual = int(row.get("km_atual") or 0)
        itens = [
            ("Troca de óleo", classificar_alerta(km_atual, row.get("proxima_troca_oleo")), row.get("proxima_troca_oleo"), None),
            (
                "Recompletamento de óleo",
                classificar_alerta_recompletamento(
                    km_atual,
                    row.get("km_ultimo_recompletamento_oleo"),
                    row.get("intervalo_recompletamento_oleo") or INTERVALO_PADRAO_RECOMPLETAMENTO_OLEO,
                ),
                calcular_limite_recompletamento(
                    row.get("km_ultimo_recompletamento_oleo"),
                    row.get("intervalo_recompletamento_oleo") or INTERVALO_PADRAO_RECOMPLETAMENTO_OLEO,
                ),
                row.get("km_ultimo_recompletamento_oleo"),
            ),
            ("Revisão", classificar_alerta(km_atual, row.get("km_prox_revisao")), row.get("km_prox_revisao"), None),
            ("Pneus", classificar_alerta(km_atual, row.get("km_prox_pneu")), row.get("km_prox_pneu"), None),
            ("Freios", classificar_alerta(km_atual, row.get("km_prox_freio")), row.get("km_prox_freio"), None),
            ("Bateria", classificar_alerta(km_atual, row.get("km_prox_bateria")), row.get("km_prox_bateria"), None),
        ]

        for categoria, status, km_limite, km_base in itens:
            status_label = status_visual(status)
            if km_limite and int(km_limite or 0) > 0:
                km_restante = int(km_limite or 0) - km_atual
            else:
                km_restante = None
            registros.append(
                {
                    "veiculo_id": row["veiculo_id"],
                    "veiculo": row["veiculo"],
                    "categoria": categoria,
                    "status": status_label,
                    "km_atual": km_atual,
                    "km_limite": int(km_limite or 0) if km_limite else 0,
                    "km_restante": km_restante,
                    "km_base": int(km_base or 0) if km_base else 0,
                }
            )

    return pd.DataFrame(registros)


def contagem_status_categoria(df_painel, categoria):
    base = df_painel[df_painel["categoria"] == categoria].copy()
    contagem = {"OK": 0, "Próximo": 0, "Urgente": 0, "Vencido": 0}
    if base.empty:
        return contagem
    for chave in contagem.keys():
        contagem[chave] = int((base["status"] == chave).sum())
    return contagem


def plotar_donut_status(titulo, contagem):
    valores = list(contagem.values())
    labels = list(contagem.keys())
    total = sum(valores)

    fig, ax = plt.subplots(figsize=(2.7, 2.7))
    if total <= 0:
        ax.text(0, 0, "Sem\ndados", ha="center", va="center", fontsize=10, fontweight="bold")
        ax.axis("off")
        return fig

    def _fmt(pct):
        valor = int(round((pct / 100.0) * total))
        return f"{valor}" if valor > 0 else ""

    wedges, _, _ = ax.pie(
        valores,
        labels=None,
        autopct=_fmt,
        startangle=90,
        wedgeprops={"width": 0.38, "edgecolor": "white", "linewidth": 1.0},
        pctdistance=0.76,
        textprops={"fontsize": 8, "fontweight": "bold"},
    )
    ax.text(0, 0, f"{titulo}\n{total}", ha="center", va="center", fontsize=9, fontweight="bold")
    ax.axis("equal")
    ax.legend(
        wedges,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.14),
        ncol=2,
        fontsize=7,
        frameon=False,
        handlelength=1.1,
        columnspacing=1.0,
    )
    return fig


def plotar_donut_progresso(titulo, km_atual, km_limite, km_base=0):
    try:
        km_atual = float(km_atual or 0)
        km_limite = float(km_limite or 0)
        km_base = float(km_base or 0)
    except Exception:
        km_atual, km_limite, km_base = 0.0, 0.0, 0.0

    total = max(km_limite - km_base, 0.0)
    usado = max(km_atual - km_base, 0.0)

    if total <= 0:
        fig, ax = plt.subplots(figsize=(2.7, 2.7))
        ax.text(0, 0, f"{titulo}\nSem dados", ha="center", va="center", fontsize=9, fontweight="bold")
        ax.axis("off")
        return fig

    usado_plot = min(usado, total)
    restante = max(total - usado_plot, 0.0)
    valores = [usado_plot, restante]
    labels = ["Usado", "Restante"]

    fig, ax = plt.subplots(figsize=(2.7, 2.7))
    wedges, _, _ = ax.pie(
        valores,
        labels=None,
        startangle=90,
        autopct=lambda p: f"{int(round((p/100.0) * total))} km" if p > 0 and total <= 20000 else "",
        wedgeprops={"width": 0.38, "edgecolor": "white", "linewidth": 1.0},
        pctdistance=0.76,
        textprops={"fontsize": 7, "fontweight": "bold"},
    )

    percentual = int(round((usado / total) * 100)) if total > 0 else 0
    percentual = max(0, min(percentual, 999))

    ax.text(
        0,
        0,
        f"{titulo}\n{percentual}%",
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold",
    )
    ax.axis("equal")
    ax.legend(
        wedges,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.14),
        ncol=2,
        fontsize=7,
        frameon=False,
        handlelength=1.1,
        columnspacing=1.0,
    )
    return fig


def exibir_kpi(titulo, valor):
    st.markdown(
        f"""
        <div class="manut-kpi">
            <div class="manut-kpi-title">{titulo}</div>
            <div class="manut-kpi-value">{valor}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def exibir_barra_item(categoria, status, km_atual, km_limite, km_base=0):
    percentual = calcular_percentual_uso(km_atual, km_limite, km_base)
    restante = int(km_limite or 0) - int(km_atual or 0) if km_limite else 0
    st.markdown(f"**{categoria}** — {status}")
    st.progress(min(max(percentual / 100.0, 0.0), 1.0), text=f"Atual: {int(km_atual or 0)} km | Limite: {int(km_limite or 0)} km | Restante: {restante} km")


def tela_manutencoes():
    aplicar_estilo_manutencoes()
    st.subheader("Manutenções")
    card_abertura_manutencoes()

    conn = conectar()
    veiculos = pd.read_sql_query("SELECT id, modelo, placa FROM veiculos ORDER BY modelo", conn)

    if veiculos.empty:
        st.info("Cadastre veículos antes de registrar manutenções.")
        conn.close()
        return

    df = carregar_manutencoes(conn)

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["Nova manutenção", "Histórico", "Checklist preventivo", "Painel visual", "Editar", "Excluir"]
    )

    with tab1:
        st.markdown(
            """
        <div class="manut-box">
            <div class="manut-box-title">Novo registro de manutenção</div>
            <div class="manut-box-sub">
                Registre serviço, custo, quilometragem atual, próximos controles e foto da manutenção.
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        opcoes = {f"{row['modelo']} - {row['placa']}": row["id"] for _, row in veiculos.iterrows()}
        veiculo_escolhido = st.selectbox(
            "Veículo para novo registro",
            list(opcoes.keys()),
            key="novo_registro_manutencao_veiculo"
        )
        veiculo_id_preselecionado = opcoes[veiculo_escolhido]

        ultimo_registro = obter_ultimo_controle_por_veiculo(df, veiculo_id_preselecionado)

        km_atual_padrao = int(ultimo_registro.get("km_atual") or 0) if ultimo_registro else 0
        proxima_troca_oleo_padrao = int(ultimo_registro.get("proxima_troca_oleo") or 0) if ultimo_registro else 0
        km_prox_revisao_padrao = int(ultimo_registro.get("km_prox_revisao") or 0) if ultimo_registro else 0
        km_prox_pneu_padrao = int(ultimo_registro.get("km_prox_pneu") or 0) if ultimo_registro else 0
        km_prox_freio_padrao = int(ultimo_registro.get("km_prox_freio") or 0) if ultimo_registro else 0
        km_prox_bateria_padrao = int(ultimo_registro.get("km_prox_bateria") or 0) if ultimo_registro else 0
        km_ultimo_recompletamento_padrao = int(ultimo_registro.get("km_ultimo_recompletamento_oleo") or 0) if ultimo_registro else 0
        intervalo_recompletamento_padrao = (
            int(ultimo_registro.get("intervalo_recompletamento_oleo") or INTERVALO_PADRAO_RECOMPLETAMENTO_OLEO)
            if ultimo_registro else INTERVALO_PADRAO_RECOMPLETAMENTO_OLEO
        )

        if ultimo_registro:
            st.markdown(
                f"""
                <div class="manut-alert-info">
                    Dados preventivos e KM atual pré-preenchidos a partir do último registro deste veículo.
                    KM atual carregado: {km_atual_padrao} km.
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="manut-alert-warn">
                    Este veículo ainda não possui histórico de manutenção. Os campos preventivos iniciarão vazios.
                </div>
                """,
                unsafe_allow_html=True,
            )

        with st.form("form_manutencao"):
            data_manutencao = st.date_input("Data da manutenção")

            col1, col2 = st.columns(2)
            with col1:
                tipo_servico = st.text_input("Tipo de serviço")
                descricao = st.text_area("Descrição")
                valor = st.number_input("Valor", min_value=0.0, step=50.0, format="%.2f")
            with col2:
                oficina = st.text_input("Oficina ou responsável")
                km_atual = st.number_input("KM atual", min_value=0, step=1, value=km_atual_padrao)
                observacoes = st.text_area("Observações adicionais")

            st.markdown("### Próximos controles preventivos")
            c1, c2 = st.columns(2)
            with c1:
                proxima_troca_oleo = st.number_input(
                    "Próxima troca de óleo (KM)",
                    min_value=0,
                    step=500,
                    value=proxima_troca_oleo_padrao,
                )
                km_prox_revisao = st.number_input(
                    "Próxima revisão (KM)",
                    min_value=0,
                    step=500,
                    value=km_prox_revisao_padrao,
                )
                km_ultimo_recompletamento_oleo = st.number_input(
                    "KM do último recompletamento de óleo",
                    min_value=0,
                    step=100,
                    value=km_ultimo_recompletamento_padrao,
                )
            with c2:
                km_prox_pneu = st.number_input(
                    "Próxima troca de pneus (KM)",
                    min_value=0,
                    step=500,
                    value=km_prox_pneu_padrao,
                )
                km_prox_freio = st.number_input(
                    "Próxima revisão de freio (KM)",
                    min_value=0,
                    step=500,
                    value=km_prox_freio_padrao,
                )
                intervalo_recompletamento_oleo = st.number_input(
                    "Intervalo para recompletamento de óleo (KM)",
                    min_value=0,
                    step=100,
                    value=intervalo_recompletamento_padrao,
                )

            km_prox_bateria = st.number_input(
                "Próxima troca de bateria (KM)",
                min_value=0,
                step=500,
                value=km_prox_bateria_padrao,
            )
            foto = st.file_uploader("Foto da manutenção/peça/serviço", type=["jpg", "jpeg", "png", "webp"])

            salvar = st.form_submit_button("Salvar manutenção")

            if salvar:
                if not tipo_servico:
                    st.error("Informe o tipo de serviço.")
                else:
                    veiculo_id = veiculo_id_preselecionado
                    foto_path = salvar_foto_manutencao(foto, veiculo_escolhido)

                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO manutencoes (
                            veiculo_id, data_manutencao, tipo_servico, descricao,
                            valor, oficina, km_atual, proxima_troca_oleo,
                            observacoes, foto_path, km_prox_revisao,
                            km_prox_pneu, km_prox_freio, km_prox_bateria,
                            km_ultimo_recompletamento_oleo, intervalo_recompletamento_oleo
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            veiculo_id,
                            str(data_manutencao),
                            tipo_servico,
                            descricao,
                            valor,
                            oficina,
                            km_atual,
                            proxima_troca_oleo,
                            observacoes,
                            foto_path,
                            km_prox_revisao,
                            km_prox_pneu,
                            km_prox_freio,
                            km_prox_bateria,
                            km_ultimo_recompletamento_oleo,
                            intervalo_recompletamento_oleo or INTERVALO_PADRAO_RECOMPLETAMENTO_OLEO,
                        ),
                    )
                    conn.commit()
                    st.success("Manutenção registrada com sucesso.")
                    st.rerun()

    with tab2:
        st.markdown(
            """
        <div class="manut-box">
            <div class="manut-box-title">Histórico de manutenções</div>
            <div class="manut-box-sub">
                Consulte os serviços realizados, custos, quilometragem e fotos vinculadas ao veículo.
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if df.empty:
            st.info("Nenhuma manutenção cadastrada ainda.")
        else:
            busca = st.text_input("Buscar manutenção", placeholder="Digite veículo, tipo de serviço ou oficina")
            df_hist = df.copy()

            if busca:
                busca_lower = busca.strip().lower()
                df_hist = df_hist[
                    df_hist["veiculo"].str.lower().str.contains(busca_lower, na=False)
                    | df_hist["tipo_servico"].str.lower().str.contains(busca_lower, na=False)
                    | df_hist["oficina"].str.lower().str.contains(busca_lower, na=False)
                ]

            exibicao_hist = df_hist[["id", "veiculo", "data_manutencao", "tipo_servico", "valor", "oficina", "km_atual"]].copy()
            exibicao_hist["valor"] = exibicao_hist["valor"].apply(formatar_moeda)
            st.dataframe(exibicao_hist, use_container_width=True)

            opcoes_hist = {f"#{row['id']} - {row['veiculo']} - {row['tipo_servico']}": row["id"] for _, row in df_hist.iterrows()}

            if opcoes_hist:
                manut_escolhida = st.selectbox("Selecionar manutenção", list(opcoes_hist.keys()))
                manut_id = opcoes_hist[manut_escolhida]
                registro = df_hist[df_hist["id"] == manut_id].iloc[0]

                st.write(f"**Veículo:** {registro['veiculo']}")
                st.write(f"**Data:** {registro['data_manutencao']}")
                st.write(f"**Tipo de serviço:** {registro['tipo_servico']}")
                st.write(f"**Descrição:** {registro['descricao'] or '-'}")
                st.write(f"**Valor:** {formatar_moeda(registro['valor'])}")
                st.write(f"**Oficina/Responsável:** {registro['oficina'] or '-'}")
                st.write(f"**KM atual:** {int(registro['km_atual'] or 0)} km")
                st.write(f"**Último recompletamento de óleo:** {int(registro['km_ultimo_recompletamento_oleo'] or 0)} km")
                st.write(
                    f"**Intervalo recompletamento de óleo:** {int(registro['intervalo_recompletamento_oleo'] or INTERVALO_PADRAO_RECOMPLETAMENTO_OLEO)} km"
                )
                st.write(f"**Observações:** {registro['observacoes'] or '-'}")

                if registro["foto_path"] and os.path.exists(registro["foto_path"]):
                    st.image(registro["foto_path"], caption="Foto da manutenção", use_container_width=True)

    with tab3:
        st.markdown(
            """
        <div class="manut-box">
            <div class="manut-box-title">Checklist preventivo</div>
            <div class="manut-box-sub">
                Veja rapidamente os próximos itens de revisão e os alertas por quilometragem da frota.
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if df.empty:
            st.info("Nenhuma manutenção cadastrada ainda.")
        else:
            ultimas = obter_ultimos_controles(df)

            if ultimas.empty:
                st.info("Nenhum dado disponível.")
            else:
                for _, row in ultimas.iterrows():
                    st.markdown(f"### Veículo • {row['veiculo']}")
                    st.caption(f"KM atual registrado: {int(row['km_atual'] or 0)} km")

                    mostrar_alerta_item("Troca de óleo", row["km_atual"], row["proxima_troca_oleo"])
                    mostrar_alerta_recompletamento(
                        row["km_atual"],
                        row["km_ultimo_recompletamento_oleo"],
                        row["intervalo_recompletamento_oleo"] or INTERVALO_PADRAO_RECOMPLETAMENTO_OLEO,
                    )
                    mostrar_alerta_item("Revisão", row["km_atual"], row["km_prox_revisao"])
                    mostrar_alerta_item("Pneus", row["km_atual"], row["km_prox_pneu"])
                    mostrar_alerta_item("Freios", row["km_atual"], row["km_prox_freio"])
                    mostrar_alerta_item("Bateria", row["km_atual"], row["km_prox_bateria"])

                    if not any(
                        [
                            classificar_alerta(row["km_atual"], row["proxima_troca_oleo"]),
                            classificar_alerta_recompletamento(
                                row["km_atual"],
                                row["km_ultimo_recompletamento_oleo"],
                                row["intervalo_recompletamento_oleo"] or INTERVALO_PADRAO_RECOMPLETAMENTO_OLEO,
                            ),
                            classificar_alerta(row["km_atual"], row["km_prox_revisao"]),
                            classificar_alerta(row["km_atual"], row["km_prox_pneu"]),
                            classificar_alerta(row["km_atual"], row["km_prox_freio"]),
                            classificar_alerta(row["km_atual"], row["km_prox_bateria"]),
                        ]
                    ):
                        st.markdown(
                            '<div class="manut-alert-ok">Nenhum item crítico no momento para este veículo.</div>',
                            unsafe_allow_html=True,
                        )

                    st.divider()

    with tab4:
        st.markdown(
            """
        <div class="manut-box">
            <div class="manut-box-title">Painel visual preventivo</div>
            <div class="manut-box-sub">
                Visão gerencial dos controles preventivos com leitura rápida por status e prioridade da frota.
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if df.empty:
            st.info("Nenhuma manutenção cadastrada ainda.")
        else:
            ultimas = obter_ultimos_controles(df)
            df_painel = gerar_registros_painel(ultimas)

            if df_painel.empty:
                st.info("Nenhum dado preventivo disponível.")
            else:
                opcoes_filtro = {"Todos os veículos": 0}
                for _, row in ultimas.sort_values("veiculo").iterrows():
                    opcoes_filtro[row["veiculo"]] = int(row["veiculo_id"])

                veiculo_visual = st.selectbox("Visualizar dados de", list(opcoes_filtro.keys()), key="painel_visual_veiculo")
                filtro_id = opcoes_filtro[veiculo_visual]

                if filtro_id:
                    df_painel_filtrado = df_painel[df_painel["veiculo_id"] == filtro_id].copy()
                    ultimas_filtradas = ultimas[ultimas["veiculo_id"] == filtro_id].copy()
                else:
                    df_painel_filtrado = df_painel.copy()
                    ultimas_filtradas = ultimas.copy()

                total_veiculos = int(df_painel_filtrado["veiculo_id"].nunique())
                total_vencidos = int((df_painel_filtrado["status"] == "Vencido").sum())
                total_urgentes = int((df_painel_filtrado["status"] == "Urgente").sum())
                total_proximos = int((df_painel_filtrado["status"] == "Próximo").sum())

                k1, k2, k3, k4 = st.columns(4)
                with k1:
                    exibir_kpi("Veículos monitorados", total_veiculos)
                with k2:
                    exibir_kpi("Itens vencidos", total_vencidos)
                with k3:
                    exibir_kpi("Itens urgentes", total_urgentes)
                with k4:
                    exibir_kpi("Itens próximos", total_proximos)

                categorias = [
                    "Troca de óleo",
                    "Recompletamento de óleo",
                    "Revisão",
                    "Pneus",
                    "Freios",
                    "Bateria",
                ]

                if filtro_id:
                    st.markdown(f"### Painel individual — {veiculo_visual}")
                    veiculos_para_exibir = ultimas_filtradas.sort_values("veiculo").copy()
                else:
                    st.markdown("### Painel preventivo por veículo")
                    veiculos_para_exibir = ultimas_filtradas.sort_values("veiculo").copy()

                for _, veiculo_info in veiculos_para_exibir.iterrows():
                    veiculo_id_atual = int(veiculo_info["veiculo_id"])
                    veiculo_nome_atual = veiculo_info["veiculo"]
                    detalhe = df_painel[df_painel["veiculo_id"] == veiculo_id_atual].sort_values(["categoria"]).copy()

                    st.markdown(f"#### {veiculo_nome_atual}")

                    for i in range(0, len(categorias), 3):
                        cols = st.columns(3)
                        for col, categoria in zip(cols, categorias[i:i + 3]):
                            with col:
                                item = detalhe[detalhe["categoria"] == categoria]
                                st.markdown(
                                    f'<div class="manut-chart-box"><div class="manut-chart-title">{categoria}</div>',
                                    unsafe_allow_html=True,
                                )

                                if item.empty:
                                    fig = plotar_donut_status(categoria, {"OK": 0, "Próximo": 0, "Urgente": 0, "Vencido": 0})
                                else:
                                    linha = item.iloc[0]
                                    fig = plotar_donut_progresso(
                                        categoria,
                                        linha["km_atual"],
                                        linha["km_limite"],
                                        linha["km_base"],
                                    )

                                st.pyplot(fig, use_container_width=True)
                                plt.close(fig)
                                st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown("### Resumo técnico do veículo")
                    exibir_detalhe = detalhe[["categoria", "status", "km_atual", "km_limite", "km_restante"]].copy()
                    exibir_detalhe.rename(
                        columns={
                            "categoria": "Item",
                            "status": "Status",
                            "km_atual": "KM atual",
                            "km_limite": "KM limite",
                            "km_restante": "KM restantes",
                        },
                        inplace=True,
                    )
                    st.dataframe(exibir_detalhe, use_container_width=True, hide_index=True)

                    if len(veiculos_para_exibir) > 1:
                        st.divider()

                st.markdown("### Prioridades preventivas")
                criticos = df_painel_filtrado[df_painel_filtrado["status"].isin(["Vencido", "Urgente", "Próximo"])].copy()
                ordem_status = {"Vencido": 0, "Urgente": 1, "Próximo": 2, "OK": 3}
                criticos["ordem_status"] = criticos["status"].map(ordem_status)
                criticos["km_restante_ordenacao"] = criticos["km_restante"].fillna(999999)
                criticos = criticos.sort_values(["ordem_status", "km_restante_ordenacao", "veiculo"]).drop(columns=["ordem_status", "km_restante_ordenacao"])

                if criticos.empty:
                    st.markdown(
                        '<div class="manut-alert-ok">Nenhum item crítico ou próximo no momento.</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    exibir_criticos = criticos[["veiculo", "categoria", "status", "km_atual", "km_limite", "km_restante"]].copy()
                    exibir_criticos.rename(
                        columns={
                            "veiculo": "Veículo",
                            "categoria": "Item",
                            "status": "Status",
                            "km_atual": "KM atual",
                            "km_limite": "KM limite",
                            "km_restante": "KM restantes",
                        },
                        inplace=True,
                    )
                    st.dataframe(exibir_criticos, use_container_width=True, hide_index=True)

    with tab5:
        st.markdown(
            """
        <div class="manut-box">
            <div class="manut-box-title">Editar manutenção</div>
            <div class="manut-box-sub">
                Atualize valores, descrição, quilometragem ou próximos controles preventivos.
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if df.empty:
            st.info("Nenhuma manutenção cadastrada ainda.")
        else:
            opcoes_editar = {f"#{row['id']} - {row['veiculo']} - {row['tipo_servico']}": row["id"] for _, row in df.iterrows()}

            manut_editar = st.selectbox("Selecione a manutenção para editar", list(opcoes_editar.keys()), key="editar_manutencao")
            manut_id = opcoes_editar[manut_editar]
            registro = df[df["id"] == manut_id].iloc[0]

            opcoes_veic = {f"{row['modelo']} - {row['placa']}": row["id"] for _, row in veiculos.iterrows()}
            veiculo_label_atual = next(
                (label for label, vid in opcoes_veic.items() if vid == registro["veiculo_id"]),
                list(opcoes_veic.keys())[0],
            )

            with st.form("form_editar_manutencao"):
                veiculo_escolhido = st.selectbox(
                    "Veículo",
                    list(opcoes_veic.keys()),
                    index=list(opcoes_veic.keys()).index(veiculo_label_atual),
                )
                data_manutencao = st.date_input("Data da manutenção", value=pd.to_datetime(registro["data_manutencao"]).date())
                tipo_servico = st.text_input("Tipo de serviço", value=registro["tipo_servico"] or "")
                descricao = st.text_area("Descrição", value=registro["descricao"] or "")
                valor = st.number_input("Valor", min_value=0.0, step=50.0, value=float(registro["valor"] or 0), format="%.2f")
                oficina = st.text_input("Oficina ou responsável", value=registro["oficina"] or "")
                km_atual = st.number_input("KM atual", min_value=0, step=1, value=int(registro["km_atual"] or 0))

                proxima_troca_oleo = st.number_input(
                    "Próxima troca de óleo (KM)",
                    min_value=0,
                    step=500,
                    value=int(registro["proxima_troca_oleo"] or 0),
                )
                km_ultimo_recompletamento_oleo = st.number_input(
                    "KM do último recompletamento de óleo",
                    min_value=0,
                    step=100,
                    value=int(registro["km_ultimo_recompletamento_oleo"] or 0),
                )
                intervalo_recompletamento_oleo = st.number_input(
                    "Intervalo para recompletamento de óleo (KM)",
                    min_value=0,
                    step=100,
                    value=int(registro["intervalo_recompletamento_oleo"] or INTERVALO_PADRAO_RECOMPLETAMENTO_OLEO),
                )
                km_prox_revisao = st.number_input(
                    "Próxima revisão (KM)",
                    min_value=0,
                    step=500,
                    value=int(registro["km_prox_revisao"] or 0),
                )
                km_prox_pneu = st.number_input(
                    "Próxima troca de pneus (KM)",
                    min_value=0,
                    step=500,
                    value=int(registro["km_prox_pneu"] or 0),
                )
                km_prox_freio = st.number_input(
                    "Próxima revisão de freio (KM)",
                    min_value=0,
                    step=500,
                    value=int(registro["km_prox_freio"] or 0),
                )
                km_prox_bateria = st.number_input(
                    "Próxima troca de bateria (KM)",
                    min_value=0,
                    step=500,
                    value=int(registro["km_prox_bateria"] or 0),
                )

                observacoes = st.text_area("Observações adicionais", value=registro["observacoes"] or "")
                foto = st.file_uploader("Nova foto da manutenção (opcional)", type=["jpg", "jpeg", "png", "webp"], key=f"foto_edit_{manut_id}")

                atualizar = st.form_submit_button("Atualizar manutenção")

                if atualizar:
                    if not tipo_servico:
                        st.error("Informe o tipo de serviço.")
                    else:
                        veiculo_id = opcoes_veic[veiculo_escolhido]
                        foto_path = registro["foto_path"]

                        if foto is not None:
                            foto_path = salvar_foto_manutencao(foto, veiculo_escolhido)

                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            UPDATE manutencoes
                            SET veiculo_id = ?, data_manutencao = ?, tipo_servico = ?, descricao = ?,
                                valor = ?, oficina = ?, km_atual = ?, proxima_troca_oleo = ?,
                                observacoes = ?, foto_path = ?, km_prox_revisao = ?,
                                km_prox_pneu = ?, km_prox_freio = ?, km_prox_bateria = ?,
                                km_ultimo_recompletamento_oleo = ?, intervalo_recompletamento_oleo = ?
                            WHERE id = ?
                            """,
                            (
                                veiculo_id,
                                str(data_manutencao),
                                tipo_servico,
                                descricao,
                                valor,
                                oficina,
                                km_atual,
                                proxima_troca_oleo,
                                observacoes,
                                foto_path,
                                km_prox_revisao,
                                km_prox_pneu,
                                km_prox_freio,
                                km_prox_bateria,
                                km_ultimo_recompletamento_oleo,
                                intervalo_recompletamento_oleo or INTERVALO_PADRAO_RECOMPLETAMENTO_OLEO,
                                manut_id,
                            ),
                        )
                        conn.commit()
                        st.success("Manutenção atualizada com sucesso.")
                        st.rerun()

    with tab6:
        st.markdown(
            """
        <div class="manut-box">
            <div class="manut-box-title">Excluir manutenção</div>
            <div class="manut-box-sub">
                Remova registros incorretos com cuidado para não comprometer o histórico da frota.
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if df.empty:
            st.info("Nenhuma manutenção cadastrada ainda.")
        else:
            opcoes_excluir = {f"#{row['id']} - {row['veiculo']} - {row['tipo_servico']}": row["id"] for _, row in df.iterrows()}

            manut_excluir = st.selectbox("Selecione a manutenção para excluir", list(opcoes_excluir.keys()), key="excluir_manutencao")
            manut_id = opcoes_excluir[manut_excluir]
            registro = df[df["id"] == manut_id].iloc[0]

            st.markdown(
                f"""
                <div class="manut-warning-box">
                    Você está prestes a excluir a manutenção <strong>{registro['tipo_servico']}</strong> do veículo
                    <strong>{registro['veiculo']}</strong>.
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.write(f"**Data:** {registro['data_manutencao']}")
            st.write(f"**Valor:** {formatar_moeda(registro['valor'])}")
            st.write(f"**KM atual:** {int(registro['km_atual'] or 0)} km")

            confirmar = st.checkbox("Confirmo que desejo excluir esta manutenção permanentemente.")

            if st.button("Excluir manutenção selecionada", type="primary", use_container_width=True):
                if not confirmar:
                    st.warning("Confirme a exclusão antes de continuar.")
                else:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM manutencoes WHERE id = ?", (manut_id,))
                    conn.commit()
                    st.success("Manutenção excluída com sucesso.")
                    st.rerun()

    conn.close()
