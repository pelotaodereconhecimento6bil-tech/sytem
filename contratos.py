import os
import re
import urllib.parse
from datetime import datetime

import pandas as pd
import streamlit as st
from services.contrato_service import (
    calcular_status_pagamento_item as service_calcular_status_pagamento_item,
    carregar_contratos as service_carregar_contratos,
    carregar_pagamentos as service_carregar_pagamentos,
    criar_contrato_completo,
    excluir_contrato_completo as service_excluir_contrato_completo,
    finalizar_contrato as service_finalizar_contrato,
    gerar_contrato_docx as service_gerar_contrato_docx,
    gerar_cobrancas_semanais as service_gerar_cobrancas_semanais,
    calcular_semanas_cobradas as service_calcular_semanas_cobradas,
    normalizar_status_pagamento_visual as service_normalizar_status_pagamento_visual,
    atualizar_resumo_todos_contratos as service_atualizar_resumo_todos_contratos,
)

from database import (
    conectar,
    registrar_pagamento,
    atualizar_pagamento_registrado,
    excluir_pagamento_registrado,
    atualizar_resumo_pagamento_contrato,
    obter_documentos_cliente,
    listar_locadores,
    obter_locador_por_id,
)
from utils import (
    buscar_cep,
    formatar_moeda,
    formatar_telefone,
    formatar_nome,
    formatar_cpf,
    formatar_rg,
    formatar_cep,
    valor_por_extenso,
    data_por_extenso,
    duracao_texto,
    obter_resumo_km_contrato,
    obter_ultimo_odometro,
)

TEMPLATE_PATH = "templates/contrato_template.docx"
OUTPUT_DIR = "contratos_gerados"
COMPROVANTES_DIR = "comprovantes_pagamento"
LIMITE_MENSAL_PADRAO = 8000


# ==========================================
# ESTILO
# ==========================================

def aplicar_estilo_contratos():
    st.markdown(
        """
    <style>
    .contrato-top-card {
        background: linear-gradient(180deg, #111827 0%, #0f172a 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 18px;
        padding: 18px;
        margin-bottom: 14px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.16);
    }

    .contrato-top-title {
        color: #f8fafc;
        font-size: 1.08rem;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .contrato-top-sub {
        color: #94a3b8;
        font-size: 0.92rem;
        margin-bottom: 0;
    }

    .contrato-box {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 14px;
        padding: 12px 14px;
        margin-top: 8px;
        margin-bottom: 12px;
    }

    .contrato-box-title {
        color: #e5e7eb;
        font-size: 0.96rem;
        font-weight: 800;
        margin-bottom: 5px;
    }

    .contrato-box-sub {
        color: #94a3b8;
        font-size: 0.88rem;
        margin-bottom: 0;
    }

    .contrato-warning-box {
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.22);
        border-radius: 14px;
        padding: 12px 14px;
        margin-top: 10px;
        margin-bottom: 12px;
        color: #fbbf24;
        font-weight: 600;
    }

    .contrato-danger-box {
        background: rgba(239, 68, 68, 0.08);
        border: 1px solid rgba(239, 68, 68, 0.22);
        border-radius: 14px;
        padding: 12px 14px;
        margin-top: 10px;
        margin-bottom: 12px;
        color: #fca5a5;
        font-weight: 600;
    }

    .contrato-highlight {
        background: linear-gradient(180deg, #172554 0%, #1e293b 100%);
        border: 1px solid rgba(96,165,250,0.22);
        border-radius: 16px;
        padding: 14px 16px;
        margin-bottom: 14px;
    }

    .contrato-highlight-title {
        color: #dbeafe;
        font-size: 1rem;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .contrato-highlight-sub {
        color: #bfdbfe;
        font-size: 0.9rem;
        margin-bottom: 0;
    }

    .contrato-success-box {
        background: rgba(34, 197, 94, 0.08);
        border: 1px solid rgba(34, 197, 94, 0.22);
        border-radius: 14px;
        padding: 12px 14px;
        margin-top: 10px;
        margin-bottom: 12px;
        color: #86efac;
        font-weight: 600;
    }

    .contrato-info-box {
        background: rgba(59, 130, 246, 0.08);
        border: 1px solid rgba(59, 130, 246, 0.22);
        border-radius: 14px;
        padding: 12px 14px;
        margin-top: 10px;
        margin-bottom: 12px;
        color: #93c5fd;
        font-weight: 600;
    }

    .contrato-whatsapp-box {
        background: rgba(34, 197, 94, 0.08);
        border: 1px solid rgba(34, 197, 94, 0.22);
        border-radius: 14px;
        padding: 12px 14px;
        margin-top: 10px;
        margin-bottom: 12px;
        color: #86efac;
        font-weight: 600;
    }

    .contrato-link-box {
        background: rgba(255,255,255,0.03);
        border: 1px dashed rgba(255,255,255,0.14);
        border-radius: 12px;
        padding: 10px 12px;
        margin-top: 8px;
        margin-bottom: 10px;
    }

    .contrato-download-wrap {
        background: rgba(34, 197, 94, 0.08);
        border: 1px solid rgba(34, 197, 94, 0.24);
        border-radius: 16px;
        padding: 14px;
        margin-top: 12px;
        margin-bottom: 12px;
    }

    .contrato-download-title {
        color: #dcfce7;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .contrato-download-sub {
        color: #bbf7d0;
        font-size: 0.92rem;
        margin-bottom: 10px;
    }

    div[data-testid="stDownloadButton"] > button {
        background: linear-gradient(180deg, #22c55e 0%, #16a34a 100%);
        color: white !important;
        border: 1px solid rgba(21, 128, 61, 0.85);
        font-weight: 700;
        border-radius: 12px;
        min-height: 46px;
        box-shadow: 0 8px 18px rgba(34, 197, 94, 0.18);
    }

    div[data-testid="stDownloadButton"] > button:hover {
        border-color: rgba(21, 128, 61, 1);
        box-shadow: 0 10px 22px rgba(34, 197, 94, 0.22);
    }

    .contrato-numero-box {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 12px 14px;
        margin-bottom: 12px;
    }

    .contrato-numero-label {
        color: #94a3b8;
        font-size: 0.82rem;
        margin-bottom: 2px;
    }

    .contrato-numero-valor {
        color: #f8fafc;
        font-size: 1.15rem;
        font-weight: 800;
        margin-bottom: 0;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


def card_abertura_contratos():
    st.markdown(
        """
    <div class="contrato-top-card">
        <div class="contrato-top-title">Gestão de contratos</div>
        <div class="contrato-top-sub">
            Central comercial da locadora: geração de contratos, cobrança semanal automática, WhatsApp, comprovantes e controle de quilometragem.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


# ==========================================
# HELPERS
# ==========================================

def montar_endereco_completo(endereco, numero="", complemento=""):
    partes = []

    if endereco:
        partes.append(str(endereco).strip())

    if numero:
        partes.append(f"nº {str(numero).strip()}")

    endereco_completo = ", ".join(partes) if partes else ""

    if complemento:
        comp = str(complemento).strip()
        if endereco_completo:
            endereco_completo += f" - {comp}"
        else:
            endereco_completo = comp

    return endereco_completo


def exibir_bloco_resumo(titulo, linhas, tipo="info"):
    classe = {
        "info": "contrato-info-box",
        "warn": "contrato-warning-box",
        "danger": "contrato-danger-box",
        "success": "contrato-success-box",
    }.get(tipo, "contrato-info-box")

    conteudo = "<br/>".join(str(linha) for linha in linhas if str(linha).strip())
    st.markdown(
        f"""
        <div class="{classe}">
            <strong>{titulo}</strong><br/>{conteudo}
        </div>
        """,
        unsafe_allow_html=True,
    )


def exibir_box_numero_contrato(numero_contrato):
    st.markdown(
        f"""
        <div class="contrato-numero-box">
            <div class="contrato-numero-label">Número do contrato</div>
            <div class="contrato-numero-valor">Contrato n° {numero_contrato}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def preparar_dados_locador_contrato(locador_cfg):
    endereco_completo = montar_endereco_completo(
        locador_cfg.get("endereco", ""),
        locador_cfg.get("numero", ""),
        locador_cfg.get("complemento", ""),
    )

    return {
        "locador_nome": formatar_nome(locador_cfg.get("nome", "")),
        "locador_cpf": formatar_cpf(locador_cfg.get("cpf", "")),
        "locador_telefone": formatar_telefone(locador_cfg.get("telefone", "")),
        "locador_estado_civil": str(locador_cfg.get("estado_civil", "") or "").strip(),
        "estado_civil": str(locador_cfg.get("estado_civil", "") or "").strip(),
        "profissao": str(locador_cfg.get("profissao", "") or "").strip(),
        "locador_cidade": str(locador_cfg.get("cidade", "") or "").strip(),
        "locador_estado": str(locador_cfg.get("estado", "") or "").strip().upper(),
        "locador_cep": formatar_cep(locador_cfg.get("cep", "") or ""),
        "locador_endereco": endereco_completo,
        "locador_endereco_referencia": str(locador_cfg.get("endereco_referencia", "") or "").strip(),
        "locador_observacoes": str(locador_cfg.get("observacoes", "") or "").strip(),
    }


def preparar_dados_cliente_contrato(cliente):
    endereco_completo = montar_endereco_completo(
        cliente.get("endereco", ""),
        cliente.get("numero", ""),
        cliente.get("complemento", ""),
    )

    return {
        "locatario_nome": formatar_nome(cliente.get("nome", "")),
        "locatario_cpf": formatar_cpf(cliente.get("cpf", "")),
        "locatario_rg": formatar_rg(cliente.get("rg", "")),
        "locatario_telefone": formatar_telefone(cliente.get("telefone", "")),
        "locatario_endereco": endereco_completo,
        "locatario_cidade": formatar_nome(cliente.get("cidade", "")),
        "locatario_estado": str(cliente.get("estado", "") or "").strip().upper(),
        "locatario_cep": formatar_cep(cliente.get("cep", "") or ""),
    }


def preparar_dados_veiculo_contrato(veiculo, km_atual):
    return {
        "veiculo_modelo": veiculo.get("modelo") or "",
        "veiculo_marca": veiculo.get("marca") or "",
        "veiculo_ano": veiculo.get("ano") or "",
        "veiculo_placa": veiculo.get("placa") or "",
        "veiculo_cor": veiculo.get("cor") or "",
        "renavam": str(veiculo.get("renavam") or ""),
        "km_atual": f"{int(km_atual):,} km".replace(",", ".") if int(km_atual or 0) > 0 else "Não informado",
    }


def gerar_contrato_docx(dados):
    return service_gerar_contrato_docx(dados)


def salvar_comprovante_pagamento(contrato_id, pagamento_id, arquivo):
    if arquivo is None:
        return ""

    os.makedirs(COMPROVANTES_DIR, exist_ok=True)

    extensao = os.path.splitext(arquivo.name)[1].lower()
    if not extensao:
        extensao = ".bin"

    nome_arquivo = f"comprovante_contrato_{contrato_id}_pagamento_{pagamento_id}{extensao}"
    caminho = os.path.join(COMPROVANTES_DIR, nome_arquivo)

    with open(caminho, "wb") as f:
        f.write(arquivo.getbuffer())

    return caminho


def eh_imagem_preview(caminho_arquivo):
    if not caminho_arquivo:
        return False

    extensao = os.path.splitext(str(caminho_arquivo))[1].lower()
    return extensao in [".jpg", ".jpeg", ".png", ".webp"]


def excluir_contrato_completo(contrato_id):
    conn = conectar()
    try:
        return service_excluir_contrato_completo(conn, contrato_id)
    finally:
        conn.close()


def exibir_documentos_contrato(cliente_id, contrato_id):
    st.markdown("### 📂 Documentos do locatário")

    docs = obter_documentos_cliente(cliente_id=cliente_id, contrato_id=contrato_id)

    if docs.empty:
        st.info("Nenhum documento anexado a este contrato.")
        return

    colunas = st.columns(2)
    for idx, (_, doc) in enumerate(docs.iterrows()):
        with colunas[idx % 2]:
            st.markdown(f"**{str(doc['tipo_documento']).replace('_', ' ')}**")
            caminho = str(doc.get("caminho_arquivo") or "")
            nome = str(doc.get("nome_arquivo") or os.path.basename(caminho) or "documento")
            data_upload = doc.get("data_upload")

            if pd.notna(data_upload):
                data_upload_fmt = pd.to_datetime(data_upload, errors="coerce")
                if pd.notna(data_upload_fmt):
                    st.caption(f"Enviado em {data_upload_fmt.strftime('%d/%m/%Y %H:%M')}")

            if caminho and os.path.exists(caminho):
                if eh_imagem_preview(caminho):
                    st.image(caminho, width=140)
                else:
                    st.caption("Prévia disponível apenas para imagem.")

                with open(caminho, "rb") as f:
                    st.download_button(
                        "Baixar documento",
                        data=f,
                        file_name=nome,
                        key=f"download_doc_{doc['id']}",
                        use_container_width=True,
                    )
            else:
                st.warning("Arquivo não encontrado no armazenamento.")

            st.divider()


def calcular_semanas_cobradas(data_inicio, data_fim):
    return service_calcular_semanas_cobradas(data_inicio, data_fim)


def gerar_cobrancas_semanais(data_inicio, data_fim, valor_semanal):
    return service_gerar_cobrancas_semanais(data_inicio, data_fim, valor_semanal)


def calcular_status_pagamento_item(valor_previsto, valor_pago, data_vencimento=None):
    return service_calcular_status_pagamento_item(valor_previsto, valor_pago, data_vencimento)


def normalizar_status_pagamento_visual(status):
    return service_normalizar_status_pagamento_visual(status)


def limpar_numero_whatsapp(telefone):
    telefone = re.sub(r"\D", "", str(telefone or ""))

    if not telefone:
        return ""

    if telefone.startswith("55"):
        return telefone

    if len(telefone) in [10, 11]:
        return f"55{telefone}"

    return telefone


def telefone_whatsapp_valido(telefone):
    numero = limpar_numero_whatsapp(telefone)
    return len(numero) >= 12


def montar_mensagem_cobranca_parcela(cliente_nome, veiculo, contrato_id, parcela_id, valor_previsto, valor_pago, data_vencimento, status, observacao=""):
    venc_str = "-"
    if pd.notna(pd.to_datetime(data_vencimento, errors="coerce")):
        venc_str = pd.to_datetime(data_vencimento).strftime("%d/%m/%Y")

    saldo = max(float(valor_previsto or 0.0) - float(valor_pago or 0.0), 0.0)
    detalhe = f"\nReferência: {observacao}" if observacao else ""

    mensagem = (
        f"Olá, {cliente_nome}. Tudo bem?\n\n"
        f"Estamos entrando em contato sobre o contrato #{contrato_id} referente ao veículo {veiculo}.\n\n"
        f"Cobrança #{parcela_id}{detalhe}\n"
        f"Vencimento: {venc_str}\n"
        f"Valor previsto: {formatar_moeda(valor_previsto)}\n"
        f"Valor já pago: {formatar_moeda(valor_pago)}\n"
        f"Saldo em aberto: {formatar_moeda(saldo)}\n"
        f"Status atual: {status}\n\n"
        f"Pedimos, por gentileza, a regularização do pagamento. "
        f"Caso já tenha efetuado, envie o comprovante para atualização no sistema.\n\n"
        f"Obrigado."
    )
    return mensagem


def montar_mensagem_cobranca_resumo(cliente_nome, veiculo, contrato_id, total_aberto, qtd_itens, primeira_data_vencimento):
    venc_str = "-"
    if pd.notna(pd.to_datetime(primeira_data_vencimento, errors="coerce")):
        venc_str = pd.to_datetime(primeira_data_vencimento).strftime("%d/%m/%Y")

    mensagem = (
        f"Olá, {cliente_nome}. Tudo bem?\n\n"
        f"Identificamos pendência(s) financeira(s) no contrato #{contrato_id} referente ao veículo {veiculo}.\n\n"
        f"Cobranças em aberto: {int(qtd_itens)}\n"
        f"Primeiro vencimento em aberto: {venc_str}\n"
        f"Total em aberto: {formatar_moeda(total_aberto)}\n\n"
        f"Pedimos, por gentileza, a regularização. "
        f"Caso o pagamento já tenha sido realizado, envie o comprovante para atualização no sistema.\n\n"
        f"Obrigado."
    )
    return mensagem


def gerar_link_whatsapp(telefone, mensagem):
    numero = limpar_numero_whatsapp(telefone)
    if not numero:
        return ""
    texto = urllib.parse.quote(mensagem)
    return f"https://wa.me/{numero}?text={texto}"


def finalizar_contrato(contrato_id):
    conn = conectar()
    try:
        return service_finalizar_contrato(conn, contrato_id)
    finally:
        conn.close()


def carregar_contratos(conn):
    return service_carregar_contratos(conn)


def carregar_pagamentos(conn):
    return service_carregar_pagamentos(conn)


def atualizar_resumo_todos_contratos(conn):
    return service_atualizar_resumo_todos_contratos(conn)


def exibir_card_km_contrato(resumo_km):
    if not resumo_km:
        st.info("Sem dados de quilometragem para este contrato.")
        return

    ultimo_odometro = float(resumo_km.get("ultimo_odometro", 0) or 0)
    km_total = float(resumo_km.get("km_total", 0) or 0)
    km_mes = float(resumo_km.get("km_mes", 0) or 0)
    limite_mensal = float(resumo_km.get("limite_mensal", LIMITE_MENSAL_PADRAO) or LIMITE_MENSAL_PADRAO)
    percentual_mes = float(resumo_km.get("percentual_mes", 0) or 0)
    status_km = str(resumo_km.get("status_km", "Dentro do limite") or "Dentro do limite")

    st.markdown(
        """
    <div class="contrato-box">
        <div class="contrato-box-title">Quilometragem do contrato</div>
        <div class="contrato-box-sub">
            Acompanhe o uso do veículo ao longo do contrato e o consumo frente ao limite mensal definido.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Último odômetro", f"{ultimo_odometro:,.0f} km".replace(",", "."))
    c2.metric("KM no contrato", f"{km_total:,.0f} km".replace(",", "."))
    c3.metric("KM no mês", f"{km_mes:,.0f} km".replace(",", "."))
    c4.metric("Limite mensal", f"{limite_mensal:,.0f} km".replace(",", "."))

    progresso = 0.0
    if limite_mensal > 0:
        progresso = max(0.0, min(percentual_mes / 100.0, 1.0))

    st.progress(progresso, text=f"Uso do limite mensal: {percentual_mes:.1f}%")

    if percentual_mes >= 100:
        st.markdown(
            f'<div class="contrato-danger-box">Limite mensal atingido ou ultrapassado. Status: {status_km}.</div>',
            unsafe_allow_html=True,
        )
    elif percentual_mes >= 80:
        st.markdown(
            f'<div class="contrato-warning-box">Atenção: consumo de {percentual_mes:.1f}% do limite mensal. Status: {status_km}.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="contrato-success-box">Quilometragem sob controle. Status: {status_km}.</div>',
            unsafe_allow_html=True,
        )


# ==========================================
# TELA
# ==========================================

def preparar_df_contratos_para_tela(df, pagamentos_df):
    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "id",
                "cliente_id",
                "veiculo_id",
                "cliente",
                "cliente_telefone",
                "veiculo",
                "placa",
                "data_inicio",
                "data_fim",
                "valor_total_contrato",
                "valor_pago",
                "valor_pendente",
                "status",
                "status_pagamento",
            ]
        )

    df = df.copy()

    colunas_padrao = {
        "cliente_id": None,
        "veiculo_id": None,
        "cliente": "",
        "cliente_telefone": "",
        "veiculo": "",
        "placa": "",
        "data_inicio": "",
        "data_fim": "",
        "valor_total_contrato": 0.0,
        "valor_pago": 0.0,
        "valor_pendente": 0.0,
        "status": "Ativo",
        "status_pagamento": "Pendente",
    }

    for coluna, valor_padrao in colunas_padrao.items():
        if coluna not in df.columns:
            df[coluna] = valor_padrao

    for coluna in ["valor_total_contrato", "valor_pago", "valor_pendente"]:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce").fillna(0.0)

    if pagamentos_df is not None and not pagamentos_df.empty:
        pag = pagamentos_df.copy()

        for coluna, padrao in {
            "contrato_id": None,
            "valor_pago": 0.0,
            "valor_previsto": 0.0,
        }.items():
            if coluna not in pag.columns:
                pag[coluna] = padrao

        pag = pag[pag["contrato_id"].notna()].copy()
        if not pag.empty:
            pag["contrato_id"] = pd.to_numeric(pag["contrato_id"], errors="coerce")
            pag = pag[pag["contrato_id"].notna()].copy()
            pag["contrato_id"] = pag["contrato_id"].astype(int)
            pag["valor_pago"] = pd.to_numeric(pag["valor_pago"], errors="coerce").fillna(0.0)

            resumo_pag = pag.groupby("contrato_id", as_index=False).agg(valor_pago_pagamentos=("valor_pago", "sum"))

            df = df.merge(resumo_pag, left_on="id", right_on="contrato_id", how="left")

            df["valor_pago_pagamentos"] = pd.to_numeric(df.get("valor_pago_pagamentos", 0.0), errors="coerce").fillna(0.0)

            df["valor_pago"] = df["valor_pago_pagamentos"].where(df["valor_pago_pagamentos"] > 0, df["valor_pago"])

    df["valor_pendente"] = (
        pd.to_numeric(df["valor_total_contrato"], errors="coerce").fillna(0.0)
        - pd.to_numeric(df["valor_pago"], errors="coerce").fillna(0.0)
    ).clip(lower=0)

    if "contrato_id" in df.columns:
        df = df.drop(columns=["contrato_id"])

    return df


def preparar_df_pagamentos_para_tela(pagamentos_df, df_contratos):
    colunas_base = [
        "id",
        "contrato_id",
        "data_vencimento",
        "data_pagamento",
        "valor_previsto",
        "valor_pago",
        "status",
        "status_real",
        "observacao",
        "comprovante_pagamento",
        "cliente",
        "cliente_telefone",
        "veiculo",
        "placa",
    ]

    if pagamentos_df is None or pagamentos_df.empty:
        return pd.DataFrame(columns=colunas_base)

    pag = pagamentos_df.copy()

    padroes = {
        "id": None,
        "contrato_id": None,
        "data_vencimento": pd.NaT,
        "data_pagamento": pd.NaT,
        "valor_previsto": 0.0,
        "valor_pago": 0.0,
        "status": "Pendente",
        "status_real": "Pendente",
        "observacao": "",
        "comprovante_pagamento": "",
        "cliente": "",
        "cliente_telefone": "",
        "veiculo": "",
        "placa": "",
    }

    for coluna, valor_padrao in padroes.items():
        if coluna not in pag.columns:
            pag[coluna] = valor_padrao

    for coluna in ["valor_previsto", "valor_pago"]:
        pag[coluna] = pd.to_numeric(pag[coluna], errors="coerce").fillna(0.0)

    for coluna in ["data_vencimento", "data_pagamento"]:
        pag[coluna] = pd.to_datetime(pag[coluna], errors="coerce")

    if "status_real" not in pag.columns or pag["status_real"].isna().all():
        pag["status_real"] = pag["status"]
    pag["status_real"] = pag["status_real"].fillna(pag["status"]).fillna("Pendente")

    if df_contratos is not None and not df_contratos.empty:
        base_contratos = df_contratos.copy()
        for coluna, valor_padrao in {
            "id": None,
            "cliente": "",
            "cliente_telefone": "",
            "veiculo": "",
            "placa": "",
        }.items():
            if coluna not in base_contratos.columns:
                base_contratos[coluna] = valor_padrao

        base_contratos = base_contratos[["id", "cliente", "cliente_telefone", "veiculo", "placa"]].drop_duplicates(subset=["id"])

        pag["contrato_id"] = pd.to_numeric(pag["contrato_id"], errors="coerce")
        base_contratos["id"] = pd.to_numeric(base_contratos["id"], errors="coerce")

        pag = pag.merge(
            base_contratos,
            left_on="contrato_id",
            right_on="id",
            how="left",
            suffixes=("", "_contrato"),
        )

        for coluna in ["cliente", "cliente_telefone", "veiculo", "placa"]:
            origem = f"{coluna}_contrato"
            if origem in pag.columns:
                pag[coluna] = pag[coluna].fillna("")
                pag[coluna] = pag[coluna].where(pag[coluna].astype(str).str.strip() != "", pag[origem].fillna(""))

        colunas_descartar = [
            c
            for c in ["id_contrato", "cliente_contrato", "cliente_telefone_contrato", "veiculo_contrato", "placa_contrato"]
            if c in pag.columns
        ]
        if colunas_descartar:
            pag = pag.drop(columns=colunas_descartar)

    for coluna in ["cliente", "cliente_telefone", "veiculo", "placa", "observacao", "comprovante_pagamento"]:
        pag[coluna] = pag[coluna].fillna("")

    return pag


def tela_contratos():
    aplicar_estilo_contratos()
    st.subheader("Gestão de Contratos")
    card_abertura_contratos()

    conn = conectar()
    df_locadores = listar_locadores(conn)

    clientes = pd.read_sql_query("SELECT * FROM clientes ORDER BY nome", conn)
    veiculos = pd.read_sql_query(
        """
        SELECT id, modelo, marca, ano, placa, cor, status, km_inicial, data_entrada_frota, observacao_entrada, renavam
        FROM veiculos
        ORDER BY modelo
        """,
        conn,
    )

    atualizar_resumo_todos_contratos(conn)
    df = carregar_contratos(conn)
    pagamentos_df = carregar_pagamentos(conn)
    df = preparar_df_contratos_para_tela(df, pagamentos_df)
    pagamentos_df = preparar_df_pagamentos_para_tela(pagamentos_df, df)

    if "arquivo_contrato_gerado" not in st.session_state:
        st.session_state.arquivo_contrato_gerado = None

    if "nome_arquivo_contrato_gerado" not in st.session_state:
        st.session_state.nome_arquivo_contrato_gerado = None

    if "toast_contrato_gerado" not in st.session_state:
        st.session_state.toast_contrato_gerado = False

    if st.session_state.toast_contrato_gerado:
        st.toast("Contrato gerado com sucesso. Download liberado.", icon="✅")
        st.session_state.toast_contrato_gerado = False

    tab1, tab2, tab3 = st.tabs(["Novo contrato", "Lista de contratos", "Excluir contrato"])

    with tab1:
        st.markdown(
            """
        <div class="contrato-box">
            <div class="contrato-box-title">Novo contrato</div>
            <div class="contrato-box-sub">
                Gere um contrato com dados do cliente, veículo, período, valor semanal e cobrança automática por semana.
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if clientes.empty:
            st.warning("Cadastre clientes primeiro.")
            conn.close()
            return
        if veiculos.empty:
            st.warning("Cadastre veículos primeiro.")
            conn.close()
            return
        if df_locadores.empty:
            st.warning("Cadastre pelo menos um locador primeiro em Cadastros > Locador.")
            conn.close()
            return

        veiculos_disponiveis = veiculos[veiculos["status"] == "Disponível"]

        if veiculos_disponiveis.empty:
            st.info("Sem veículos disponíveis.")
        else:
            proximo_numero_contrato = 1 if df.empty else int(pd.to_numeric(df["id"], errors="coerce").max()) + 1
            ano_atual = datetime.now().year
            numero_contrato_formatado = f"{proximo_numero_contrato}/{ano_atual}"

            locador_opcoes = {f"{row['nome']} - CPF: {row['cpf']}": int(row["id"]) for _, row in df_locadores.iterrows()}
            locador_nome_escolhido = st.selectbox("Locador", list(locador_opcoes.keys()))
            locador_id = locador_opcoes[locador_nome_escolhido]
            locador_cfg = obter_locador_por_id(conn, locador_id)

            cliente_opcoes = {f"{row['nome']}": row["id"] for _, row in clientes.iterrows()}
            cliente_nome_escolhido = st.selectbox("Cliente", list(cliente_opcoes.keys()))
            cliente_id = cliente_opcoes[cliente_nome_escolhido]
            cliente = clientes[clientes["id"] == cliente_id].iloc[0]

            dados_locador = preparar_dados_locador_contrato(locador_cfg)
            dados_cliente_base = preparar_dados_cliente_contrato(cliente)

            st.markdown("### Dados-base do contrato")
            exibir_box_numero_contrato(numero_contrato_formatado)

            locador_incompleto = not str(dados_locador.get("locador_nome", "")).strip() or not str(dados_locador.get("locador_cpf", "")).strip()
            cliente_incompleto = not str(dados_cliente_base.get("locatario_nome", "")).strip() or not str(dados_cliente_base.get("locatario_cpf", "")).strip()
            cliente_endereco_incompleto = not str(dados_cliente_base.get("locatario_endereco", "")).strip() or not str(dados_cliente_base.get("locatario_cidade", "")).strip()

            col_base_1, col_base_2 = st.columns(2)
            with col_base_1:
                exibir_bloco_resumo(
                    "Locador (cadastro fixo)",
                    [
                        f"Nome: {dados_locador.get('locador_nome') or '-'}",
                        f"CPF: {dados_locador.get('locador_cpf') or '-'}",
                        f"Estado civil: {dados_locador.get('estado_civil') or '-'}",
                        f"Profissão: {dados_locador.get('profissao') or '-'}",
                        f"WhatsApp: {dados_locador.get('locador_telefone') or '-'}",
                        f"Cidade/UF: {(dados_locador.get('locador_cidade') or '-')} / {(dados_locador.get('locador_estado') or '-')}",
                        f"Endereço: {dados_locador.get('locador_endereco') or '-'}",
                        f"CEP: {dados_locador.get('locador_cep') or '-'}",
                    ],
                    tipo="warn" if locador_incompleto else "info",
                )
            with col_base_2:
                exibir_bloco_resumo(
                    "Locatário (cadastro do cliente)",
                    [
                        f"Nome: {dados_cliente_base.get('locatario_nome') or '-'}",
                        f"CPF: {dados_cliente_base.get('locatario_cpf') or '-'}",
                        f"RG: {dados_cliente_base.get('locatario_rg') or '-'}",
                        f"Telefone: {dados_cliente_base.get('locatario_telefone') or '-'}",
                        f"Endereço: {dados_cliente_base.get('locatario_endereco') or '-'}",
                        f"Cidade/UF: {(dados_cliente_base.get('locatario_cidade') or '-')} / {(dados_cliente_base.get('locatario_estado') or '-')}",
                        f"CEP: {dados_cliente_base.get('locatario_cep') or '-'}",
                    ],
                    tipo="warn" if (cliente_incompleto or cliente_endereco_incompleto) else "info",
                )

            veiculo_opcoes = {f"{row['modelo']} - {row['placa']}": row["id"] for _, row in veiculos_disponiveis.iterrows()}
            veiculo_nome_escolhido = st.selectbox(
                "Veículo do contrato",
                list(veiculo_opcoes.keys()),
                key="contrato_veiculo_select"
            )
            veiculo_id = veiculo_opcoes[veiculo_nome_escolhido]
            veiculo = veiculos_disponiveis[veiculos_disponiveis["id"] == veiculo_id].iloc[0]

            km_inicial_cadastro = int(pd.to_numeric(veiculo.get("km_inicial", 0), errors="coerce") or 0)
            ultimo_odometro_vistoria = int(obter_ultimo_odometro(conn, int(veiculo_id)) or 0)
            odometro_documento = ultimo_odometro_vistoria if ultimo_odometro_vistoria > 0 else km_inicial_cadastro
            data_entrada_frota = veiculo.get("data_entrada_frota") or "-"
            dados_veiculo_resumo = preparar_dados_veiculo_contrato(veiculo, odometro_documento)

            with st.form("form_contrato"):
                st.markdown("### Cliente selecionado")
                st.info(f"Cliente: {cliente['nome']}")

                exibir_bloco_resumo(
                    "Veículo do contrato",
                    [
                        f"Modelo: {dados_veiculo_resumo.get('veiculo_modelo') or '-'}",
                        f"Marca: {dados_veiculo_resumo.get('veiculo_marca') or '-'}",
                        f"Ano: {dados_veiculo_resumo.get('veiculo_ano') or '-'}",
                        f"Placa: {dados_veiculo_resumo.get('veiculo_placa') or '-'}",
                        f"Cor: {dados_veiculo_resumo.get('veiculo_cor') or '-'}",
                        f"RENAVAM: {dados_veiculo_resumo.get('renavam') or '-'}",
                        f"KM de referência: {dados_veiculo_resumo.get('km_atual') or '-'}",
                    ],
                    tipo="warn" if not str(dados_veiculo_resumo.get("renavam", "")).strip() else "info",
                )

                st.markdown("### Referência de quilometragem do veículo")
                q1, q2, q3 = st.columns(3)
                q1.metric("KM inicial cadastrado", f"{km_inicial_cadastro:,.0f} km".replace(",", "."))
                q2.metric("Último odômetro de vistoria", f"{ultimo_odometro_vistoria:,.0f} km".replace(",", "."))
                q3.metric("KM usado no documento", f"{odometro_documento:,.0f} km".replace(",", "."))
                st.caption(f"Entrada na frota: {data_entrada_frota}")

                col1, col2, col3 = st.columns(3)
                with col1:
                    data_inicio = st.date_input("Data de início")
                with col2:
                    data_fim = st.date_input("Data de fim")
                with col3:
                    valor_semanal = st.number_input("Valor semanal (R$)", min_value=0.0, step=50.0, format="%.2f")

                col4, col5 = st.columns(2)
                with col4:
                    caucao = st.number_input("Caução (R$)", min_value=0.0, step=50.0, format="%.2f")
                with col5:
                    observacoes_iniciais = st.text_area("Observações iniciais")

                st.markdown("### Dados contratuais complementares")
                dia_semana_padrao = data_inicio.strftime("%A") if hasattr(data_inicio, "strftime") else ""
                mapa_dias = {
                    "Monday": "segunda-feira",
                    "Tuesday": "terça-feira",
                    "Wednesday": "quarta-feira",
                    "Thursday": "quinta-feira",
                    "Friday": "sexta-feira",
                    "Saturday": "sábado",
                    "Sunday": "domingo",
                }
                dia_semana_default = mapa_dias.get(dia_semana_padrao, "segunda-feira")
                dias_opcoes = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
                idx_dia = dias_opcoes.index(dia_semana_default) if dia_semana_default in dias_opcoes else 0

                cx1, cx2, cx3, cx4 = st.columns(4)
                with cx1:
                    prazo_minimo = st.number_input("Prazo mínimo (dias)", min_value=0, value=90, step=1)
                with cx2:
                    hora_limite = st.text_input("Hora limite pagamento", value="18:00")
                with cx3:
                    multa_atraso = st.number_input("Multa atraso por dia (R$)", min_value=0.0, value=50.0, step=10.0, format="%.2f")
                with cx4:
                    valor_franquia = st.number_input("Franquia (R$)", min_value=0.0, value=0.0, step=100.0, format="%.2f")

                dia_semana = st.selectbox("Dia fixo do pagamento", dias_opcoes, index=idx_dia)
                exibir_bloco_resumo(
                    "Contato de cobrança do locador",
                    [f"WhatsApp utilizado no contrato: {dados_locador.get('locador_telefone') or '-'}"],
                    tipo="warn" if not str(dados_locador.get("locador_telefone", "")).strip() else "success",
                )

                st.markdown("### Informações do termo/laudo")
                lx1, lx2 = st.columns(2)
                with lx1:
                    acessorios = st.text_area("Acessórios", value="Chave, documento, estepe, macaco, triângulo")
                    estado_conservacao = st.text_area("Estado de conservação", value="Veículo em bom estado geral de conservação.")
                with lx2:
                    pintura = st.text_area("Pintura", value="Sem avarias relevantes aparentes, salvo apontamentos da vistoria.")
                    tipo_combustivel = st.selectbox("Tipo de combustível", ["Gasolina", "Etanol"], index=0)
                    nivel_combustivel = st.selectbox("Tanque entregue em", ["1/4", "2/4", "3/4", "4/4"], index=0)

                st.markdown("### 📎 Documentos do locatário (opcional)")

                col_doc1, col_doc2 = st.columns(2)
                with col_doc1:
                    doc_cnh = st.file_uploader("CNH", type=["jpg", "jpeg", "png", "pdf", "doc", "docx", "webp"], key="doc_cnh")
                    doc_comprovante = st.file_uploader(
                        "Comprovante de endereço",
                        type=["jpg", "jpeg", "png", "pdf", "doc", "docx", "webp"],
                        key="doc_comprovante",
                    )

                with col_doc2:
                    doc_rg = st.file_uploader("RG (opcional)", type=["jpg", "jpeg", "png", "pdf", "doc", "docx", "webp"], key="doc_rg")
                    doc_adicional = st.file_uploader(
                        "Documento adicional",
                        type=["jpg", "jpeg", "png", "pdf", "doc", "docx", "webp"],
                        key="doc_adicional",
                    )

                salvar_contrato = st.form_submit_button("Gerar e salvar contrato")

                if salvar_contrato:
                    if data_fim < data_inicio:
                        st.error("A data final não pode ser menor que a data inicial.")
                    else:
                        semanas = calcular_semanas_cobradas(data_inicio, data_fim)
                        valor_total_contrato = round(semanas * float(valor_semanal or 0.0), 2)
                        cobrancas_semanais = gerar_cobrancas_semanais(data_inicio, data_fim, valor_semanal)

                        odometro_atual_veiculo = int(obter_ultimo_odometro(conn, int(veiculo_id)) or 0)
                        if odometro_atual_veiculo <= 0:
                            odometro_atual_veiculo = int(pd.to_numeric(veiculo.get("km_inicial", 0), errors="coerce") or 0)

                        dados_locador = preparar_dados_locador_contrato(locador_cfg)
                        dados_cliente_base = preparar_dados_cliente_contrato(cliente)
                        dados_veiculo_base = preparar_dados_veiculo_contrato(veiculo, odometro_atual_veiculo)

                        dados_template = {
                            **dados_locador,
                            **dados_cliente_base,
                            **dados_veiculo_base,
                            "numero_contrato": f"Contrato n° {numero_contrato_formatado}",
                            "data_inicio": data_inicio.strftime("%d/%m/%Y"),
                            "data_fim": data_fim.strftime("%d/%m/%Y"),
                            "data_inicio_extenso": data_por_extenso(data_inicio),
                            "data_fim_extenso": data_por_extenso(data_fim),
                            "duracao": duracao_texto(data_inicio, data_fim),
                            "valor": formatar_moeda(float(valor_semanal or 0.0)),
                            "valor_extenso": valor_por_extenso(float(valor_semanal or 0.0)) if float(valor_semanal or 0.0) > 0 else "ZERO REAIS",
                            "valor_semanal": formatar_moeda(float(valor_semanal or 0.0)),
                            "valor_total_contrato": formatar_moeda(valor_total_contrato),
                            "valor_total_extenso": valor_por_extenso(valor_total_contrato),
                            "valor_caucao": formatar_moeda(float(caucao or 0.0)),
                            "valor_caucao_extenso": valor_por_extenso(float(caucao or 0.0)) if float(caucao or 0.0) > 0 else "ZERO REAIS",
                            "caucao": formatar_moeda(float(caucao or 0.0)),
                            "caucao_extenso": valor_por_extenso(float(caucao or 0.0)) if float(caucao or 0.0) > 0 else "",
                            "valor_franquia": formatar_moeda(float(valor_franquia or 0.0)),
                            "valor_franquia_extenso": valor_por_extenso(float(valor_franquia or 0.0)) if float(valor_franquia or 0.0) > 0 else "ZERO REAIS",
                            "prazo_minimo": int(prazo_minimo or 0),
                            "prazo_minimo_dias": int(prazo_minimo or 0),
                            "hora_limite": str(hora_limite or "").strip(),
                            "multa_atraso": formatar_moeda(float(multa_atraso or 0.0)),
                            "multa_atraso_float": float(multa_atraso or 0.0),
                            "valor_franquia_float": float(valor_franquia or 0.0),
                            "dia_semana": dia_semana,
                            "telefone": dados_locador.get("locador_telefone", ""),
                            "cidade": dados_locador.get("locador_cidade", "") or dados_cliente_base.get("locatario_cidade", ""),
                            "data_assinatura_extenso": data_por_extenso(datetime.now().date()),
                            "acessorios": acessorios or "",
                            "estado_conservacao": estado_conservacao or "",
                            "pintura": pintura or "",
                            "tipo_combustivel": tipo_combustivel or "",
                            "nivel_combustivel": nivel_combustivel or "",
                            "observacoes_iniciais": observacoes_iniciais or "",
                        }

                        if not str(dados_locador.get("locador_nome", "")).strip() or not str(dados_locador.get("locador_cpf", "")).strip():
                            st.error("Cadastre os dados do locador em Cadastros > Locador antes de gerar o contrato.")
                        elif not str(dados_cliente_base.get("locatario_endereco", "")).strip() or not str(dados_cliente_base.get("locatario_cidade", "")).strip():
                            st.error("Complete o endereço do cliente em Cadastros > Clientes antes de gerar o contrato.")
                        elif not str(veiculo.get("renavam") or "").strip():
                            st.error("O veículo selecionado está sem RENAVAM cadastrado.")
                        else:
                            try:
                                resultado = criar_contrato_completo(
                                    conn,
                                    cliente_id=int(cliente_id),
                                    veiculo_id=int(veiculo_id),
                                    data_inicio=data_inicio,
                                    data_fim=data_fim,
                                    valor_semanal=float(valor_semanal or 0.0),
                                    caucao=float(caucao or 0.0),
                                    dados_template=dados_template,
                                    documentos={
                                        "CNH": doc_cnh,
                                        "Comprovante_Endereco": doc_comprovante,
                                        "RG": doc_rg,
                                        "Documento_Adicional": doc_adicional,
                                    },
                                    locador_id=int(locador_id),
                                )
                            except Exception as e:
                                st.error(f"Erro ao salvar contrato: {e}")
                            else:
                                st.session_state.arquivo_contrato_gerado = resultado["caminho_arquivo"]
                                st.session_state.nome_arquivo_contrato_gerado = os.path.basename(resultado["caminho_arquivo"])
                                st.session_state.toast_contrato_gerado = True
                                st.success("Contrato salvo com sucesso.")
                                st.markdown(
                                    f"""
                                    <div class="contrato-success-box">
                                        Contrato gerado com sucesso. Número estimado exibido: #{proximo_numero_contrato} •
                                        Valor total: {formatar_moeda(resultado['valor_total_contrato'])} •
                                        Cobranças semanais criadas: {len(resultado['cobrancas'])}
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )
                                st.rerun()

            if st.session_state.arquivo_contrato_gerado and os.path.exists(st.session_state.arquivo_contrato_gerado):
                st.markdown(
                    """
                    <div class="contrato-download-wrap">
                        <div class="contrato-download-title">Contrato pronto para download</div>
                        <div class="contrato-download-sub">Arquivo gerado com sucesso. Use o botão abaixo para baixar a versão mais recente.</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                with open(st.session_state.arquivo_contrato_gerado, "rb") as f:
                    st.download_button(
                        "✅ Baixar último contrato gerado",
                        data=f,
                        file_name=st.session_state.nome_arquivo_contrato_gerado,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                    )

    with tab2:
        st.markdown(
            """
        <div class="contrato-box">
            <div class="contrato-box-title">Lista de contratos</div>
            <div class="contrato-box-sub">
                Pesquise contratos, acompanhe cobranças semanais, faça cobrança por WhatsApp, gerencie comprovantes, quilometragem e finalize operações.
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if df.empty:
            st.info("Nenhum contrato cadastrado ainda.")
        else:
            colf1, colf2, colf3 = st.columns([1.6, 1, 1])

            with colf1:
                busca = st.text_input("Buscar contrato", placeholder="Digite cliente, veículo, placa ou status")

            with colf2:
                status_contrato_filtro = st.selectbox("Status do contrato", ["Todos", "Ativo", "Finalizado"])

            with colf3:
                status_pag_filtro = st.selectbox("Status do pagamento", ["Todos", "Pendente", "Parcial", "Pago", "Vencido"])

            df_filtrado = df.copy()

            if busca:
                termo = busca.strip().lower()
                df_filtrado = df_filtrado[
                    df_filtrado["cliente"].astype(str).str.lower().str.contains(termo, na=False)
                    | df_filtrado["veiculo"].astype(str).str.lower().str.contains(termo, na=False)
                    | df_filtrado["placa"].astype(str).str.lower().str.contains(termo, na=False)
                    | df_filtrado["status"].astype(str).str.lower().str.contains(termo, na=False)
                    | df_filtrado["status_pagamento"].astype(str).str.lower().str.contains(termo, na=False)
                ]

            if status_contrato_filtro != "Todos":
                df_filtrado = df_filtrado[df_filtrado["status"] == status_contrato_filtro]

            if status_pag_filtro != "Todos":
                df_filtrado = df_filtrado[df_filtrado["status_pagamento"] == status_pag_filtro]

            df_exibicao = df_filtrado[[
                "id",
                "cliente",
                "veiculo",
                "data_inicio",
                "data_fim",
                "valor_total_contrato",
                "valor_pago",
                "valor_pendente",
                "status",
                "status_pagamento",
            ]].copy()

            for coluna in ["valor_total_contrato", "valor_pago", "valor_pendente"]:
                df_exibicao[coluna] = df_exibicao[coluna].apply(formatar_moeda)

            st.dataframe(df_exibicao, use_container_width=True)

            st.divider()
            st.markdown("### Resumo visual do contrato")

            opcoes_contratos = {f"Contrato #{row['id']} - {row['cliente']} - {row['veiculo']}": row["id"] for _, row in df_filtrado.iterrows()}

            if opcoes_contratos:
                contrato_visual = st.selectbox("Selecione o contrato para detalhar", list(opcoes_contratos.keys()), key="contrato_visual_select")
                contrato_id_visual = opcoes_contratos[contrato_visual]
                registro_visual = df[df["id"] == contrato_id_visual].iloc[0]

                st.markdown(
                    """
                <div class="contrato-highlight">
                    <div class="contrato-highlight-title">Resumo comercial</div>
                    <div class="contrato-highlight-sub">
                        Visão consolidada do contrato, valores, pagamento e quilometragem.
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                a1, a2, a3, a4 = st.columns(4)
                a1.metric("Cliente", registro_visual["cliente"])
                a2.metric("Veículo", registro_visual["placa"])
                a3.metric("Contrato", f"#{int(registro_visual['id'])}")
                a4.metric("Status", registro_visual["status"])

                b1, b2, b3, b4 = st.columns(4)
                b1.metric("Total contrato", formatar_moeda(registro_visual["valor_total_contrato"]))
                b2.metric("Total pago", formatar_moeda(registro_visual["valor_pago"]))
                b3.metric("Saldo pendente", formatar_moeda(registro_visual["valor_pendente"]))
                b4.metric("Pagamento", str(registro_visual["status_pagamento"]))

                resumo_km = obter_resumo_km_contrato(conn=conn, contrato_id=int(contrato_id_visual), limite_mensal=LIMITE_MENSAL_PADRAO)
                exibir_card_km_contrato(resumo_km)

                exibir_documentos_contrato(cliente_id=int(registro_visual["cliente_id"]), contrato_id=int(contrato_id_visual))

            st.divider()
            st.markdown("### Cobranças semanais")

            if not opcoes_contratos:
                st.info("Nenhum contrato disponível para gerenciar pagamentos.")
            else:
                contrato_pagamento_select = st.selectbox(
                    "Selecione o contrato para gerenciar cobranças",
                    list(opcoes_contratos.keys()),
                    key="contrato_pagamento_select",
                )
                contrato_pagamento_id = opcoes_contratos[contrato_pagamento_select]

                registro_pagamento_contrato = df[df["id"] == contrato_pagamento_id].iloc[0]

                if pagamentos_df.empty:
                    pagamentos_filtrados = pd.DataFrame(
                        columns=[
                            "id",
                            "contrato_id",
                            "data_vencimento",
                            "data_pagamento",
                            "valor_previsto",
                            "valor_pago",
                            "status",
                            "status_real",
                            "observacao",
                            "comprovante_pagamento",
                            "cliente",
                            "cliente_telefone",
                            "veiculo",
                            "placa",
                        ]
                    )
                else:
                    pagamentos_filtrados = pagamentos_df.copy()

                pagamentos_contrato = pagamentos_filtrados[pagamentos_filtrados["contrato_id"] == contrato_pagamento_id].copy()
                telefone_cliente = registro_pagamento_contrato["cliente_telefone"] or ""

                st.markdown(
                    f"""
                    <div class="contrato-info-box">
                        Contrato #{int(contrato_pagamento_id)} • {registro_pagamento_contrato['cliente']} •
                        {registro_pagamento_contrato['veiculo']} •
                        Pago: {formatar_moeda(registro_pagamento_contrato['valor_pago'])} •
                        Pendente: {formatar_moeda(registro_pagamento_contrato['valor_pendente'])}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if pagamentos_contrato.empty:
                    st.info("Este contrato ainda não possui cobranças cadastradas.")
                else:
                    pagamentos_exibicao = pagamentos_contrato[[
                        "id",
                        "data_vencimento",
                        "data_pagamento",
                        "valor_previsto",
                        "valor_pago",
                        "status_real",
                        "observacao",
                    ]].copy()
                    pagamentos_exibicao["valor_previsto"] = pagamentos_exibicao["valor_previsto"].apply(formatar_moeda)
                    pagamentos_exibicao["valor_pago"] = pagamentos_exibicao["valor_pago"].apply(formatar_moeda)
                    st.dataframe(pagamentos_exibicao, use_container_width=True)

                subt1, subt2, subt3, subt4 = st.tabs(["Nova cobrança semanal", "Editar cobrança", "Excluir cobrança", "Cobrança WhatsApp"])

                with subt1:
                    with st.form(f"form_novo_pagamento_{contrato_pagamento_id}"):
                        colp1, colp2, colp3 = st.columns(3)
                        with colp1:
                            data_vencimento = st.date_input("Data de vencimento", value=datetime.today().date())
                        with colp2:
                            valor_previsto = st.number_input("Valor previsto (R$)", min_value=0.0, step=50.0, format="%.2f")
                        with colp3:
                            valor_pago = st.number_input("Valor pago inicial (R$)", min_value=0.0, step=50.0, value=0.0, format="%.2f")

                        colp4, colp5 = st.columns(2)
                        with colp4:
                            marcar_como_pago = st.checkbox("Já registrar pagamento agora")
                        with colp5:
                            data_pagamento_novo = st.date_input(
                                "Data do pagamento",
                                value=datetime.today().date(),
                                key=f"data_pagto_novo_{contrato_pagamento_id}",
                            )

                        observacao = st.text_input("Observação da cobrança")
                        comprovante_novo = st.file_uploader(
                            "Comprovante (opcional)",
                            type=["jpg", "jpeg", "png", "pdf", "doc", "docx", "webp"],
                            key=f"novo_comprovante_{contrato_pagamento_id}",
                        )

                        if comprovante_novo is not None:
                            nome_arquivo = comprovante_novo.name.lower()
                            extensao_preview = os.path.splitext(nome_arquivo)[1]

                            st.write(f"**Arquivo selecionado:** {comprovante_novo.name}")

                            if extensao_preview in [".jpg", ".jpeg", ".png", ".webp"]:
                                st.image(comprovante_novo, width=180, caption="Pré-visualização do comprovante")
                            else:
                                st.info("Pré-visualização disponível apenas para arquivos de imagem.")

                        salvar_novo_pagamento = st.form_submit_button("Salvar nova cobrança")

                        if salvar_novo_pagamento:
                            status_novo = "Pendente"
                            data_pagto_salvar = None
                            valor_pago_salvar = float(valor_pago or 0.0)

                            if marcar_como_pago:
                                data_pagto_salvar = str(data_pagamento_novo)
                                status_novo = calcular_status_pagamento_item(
                                    valor_previsto=float(valor_previsto or 0.0),
                                    valor_pago=float(valor_pago_salvar or 0.0),
                                    data_vencimento=str(data_vencimento),
                                )
                                if status_novo == "Vencido":
                                    status_novo = "Pendente"
                            else:
                                valor_pago_salvar = 0.0
                                status_novo = calcular_status_pagamento_item(
                                    valor_previsto=float(valor_previsto or 0.0),
                                    valor_pago=0.0,
                                    data_vencimento=str(data_vencimento),
                                )

                            registrar_pagamento(
                                contrato_id=int(contrato_pagamento_id),
                                valor_previsto=float(valor_previsto or 0.0),
                                data_vencimento=str(data_vencimento),
                                valor_pago=float(valor_pago_salvar or 0.0),
                                data_pagamento=data_pagto_salvar,
                                status=normalizar_status_pagamento_visual(status_novo),
                                observacao=observacao,
                                comprovante_pagamento="",
                            )

                            pagamentos_atualizados = carregar_pagamentos(conn)
                            ultimo_pagamento = pagamentos_atualizados[pagamentos_atualizados["contrato_id"] == contrato_pagamento_id].sort_values("id", ascending=False).head(1)

                            if not ultimo_pagamento.empty and comprovante_novo is not None:
                                pagamento_id_novo = int(ultimo_pagamento.iloc[0]["id"])
                                caminho_comp = salvar_comprovante_pagamento(
                                    contrato_id=int(contrato_pagamento_id),
                                    pagamento_id=pagamento_id_novo,
                                    arquivo=comprovante_novo,
                                )

                                atualizar_pagamento_registrado(pagamento_id=pagamento_id_novo, comprovante_pagamento=caminho_comp)

                            st.success("Cobrança registrada com sucesso.")
                            st.rerun()

                with subt2:
                    if pagamentos_contrato.empty:
                        st.info("Esse contrato ainda não possui cobranças para editar.")
                    else:
                        opcoes_pag = {
                            f"Cobrança #{row['id']} - {row['observacao'] or 'Sem observação'} - {normalizar_status_pagamento_visual(row['status_real'])}": row["id"]
                            for _, row in pagamentos_contrato.iterrows()
                        }

                        pagamento_escolhido = st.selectbox(
                            "Selecione a cobrança",
                            list(opcoes_pag.keys()),
                            key=f"editar_pagamento_select_{contrato_pagamento_id}",
                        )

                        pagamento_id_editar = opcoes_pag[pagamento_escolhido]
                        registro_pagamento = pagamentos_contrato[pagamentos_contrato["id"] == pagamento_id_editar].iloc[0]

                        with st.form(f"form_editar_pagamento_{pagamento_id_editar}"):
                            colu1, colu2, colu3 = st.columns(3)
                            with colu1:
                                venc_default = registro_pagamento["data_vencimento"]
                                venc_default = venc_default.date() if pd.notna(venc_default) else datetime.today().date()
                                data_vencimento_edit = st.date_input("Data de vencimento", value=venc_default)
                            with colu2:
                                valor_previsto_edit = st.number_input(
                                    "Valor previsto (R$)",
                                    min_value=0.0,
                                    step=50.0,
                                    value=float(registro_pagamento["valor_previsto"] or 0.0),
                                    format="%.2f",
                                )
                            with colu3:
                                valor_pago_edit = st.number_input(
                                    "Valor pago (R$)",
                                    min_value=0.0,
                                    step=50.0,
                                    value=float(registro_pagamento["valor_pago"] or 0.0),
                                    format="%.2f",
                                )

                            data_pagto_default = registro_pagamento["data_pagamento"]
                            data_pagto_default = data_pagto_default.date() if pd.notna(data_pagto_default) else datetime.today().date()

                            colu4, colu5 = st.columns(2)
                            with colu4:
                                data_pagamento_edit = st.date_input(
                                    "Data do pagamento",
                                    value=data_pagto_default,
                                    key=f"data_pagto_edit_{pagamento_id_editar}",
                                )
                            with colu5:
                                status_manual = st.selectbox(
                                    "Status",
                                    ["Pendente", "Parcial", "Pago", "Vencido"],
                                    index=["Pendente", "Parcial", "Pago", "Vencido"].index(
                                        normalizar_status_pagamento_visual(registro_pagamento["status_real"])
                                    ),
                                )

                            observacao_edit = st.text_input("Observação", value=registro_pagamento["observacao"] or "")

                            comprovante_edit = st.file_uploader(
                                "Novo comprovante (opcional)",
                                type=["jpg", "jpeg", "png", "pdf", "doc", "docx", "webp"],
                                key=f"comprovante_edit_{pagamento_id_editar}",
                            )

                            salvar_edicao = st.form_submit_button("Salvar alterações da cobrança")

                            if salvar_edicao:
                                caminho_comp_edit = None
                                if comprovante_edit is not None:
                                    caminho_comp_edit = salvar_comprovante_pagamento(
                                        contrato_id=int(contrato_pagamento_id),
                                        pagamento_id=int(pagamento_id_editar),
                                        arquivo=comprovante_edit,
                                    )

                                atualizar_pagamento_registrado(
                                    pagamento_id=int(pagamento_id_editar),
                                    data_vencimento=str(data_vencimento_edit),
                                    data_pagamento=str(data_pagamento_edit) if status_manual in ["Pago", "Parcial"] else None,
                                    valor_previsto=float(valor_previsto_edit or 0.0),
                                    valor_pago=float(valor_pago_edit or 0.0),
                                    status=normalizar_status_pagamento_visual(status_manual),
                                    observacao=observacao_edit,
                                    comprovante_pagamento=caminho_comp_edit,
                                )

                                st.success("Cobrança atualizada com sucesso.")
                                st.rerun()

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
                                    key=f"download_comprovante_{pagamento_id_editar}",
                                )

                with subt3:
                    if pagamentos_contrato.empty:
                        st.info("Esse contrato ainda não possui cobranças para excluir.")
                    else:
                        opcoes_excluir = {
                            f"Cobrança #{row['id']} - {row['observacao'] or 'Sem observação'} - {normalizar_status_pagamento_visual(row['status_real'])}": row["id"]
                            for _, row in pagamentos_contrato.iterrows()
                        }

                        pagamento_excluir_nome = st.selectbox(
                            "Selecione a cobrança para excluir",
                            list(opcoes_excluir.keys()),
                            key=f"excluir_pagamento_select_{contrato_pagamento_id}",
                        )
                        pagamento_id_excluir = opcoes_excluir[pagamento_excluir_nome]

                        registro_excluir = pagamentos_contrato[pagamentos_contrato["id"] == pagamento_id_excluir].iloc[0]

                        st.markdown(
                            """
                        <div class="contrato-danger-box">
                            Atenção: esta exclusão remove a cobrança de forma definitiva e recalcula o resumo financeiro do contrato.
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )

                        st.write(f"**Cobrança selecionada:** #{int(registro_excluir['id'])}")
                        st.write(f"**Observação:** {registro_excluir['observacao'] or '-'}")
                        st.write(f"**Valor previsto:** {formatar_moeda(registro_excluir['valor_previsto'])}")
                        st.write(f"**Valor pago:** {formatar_moeda(registro_excluir['valor_pago'])}")
                        st.write(f"**Status:** {normalizar_status_pagamento_visual(registro_excluir['status_real'])}")

                        confirmar_exclusao = st.checkbox(
                            "Confirmo que desejo excluir esta cobrança",
                            key=f"confirmar_exclusao_{pagamento_id_excluir}",
                        )

                        if st.button("Excluir cobrança selecionada", key=f"btn_excluir_pag_{pagamento_id_excluir}"):
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
                    st.markdown(
                        """
                    <div class="contrato-whatsapp-box">
                        Gere cobranças prontas por WhatsApp sem depender de API paga.
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                    telefone_formatado = formatar_telefone(telefone_cliente)
                    st.write(f"**Cliente:** {registro_pagamento_contrato['cliente']}")
                    st.write(f"**Telefone:** {telefone_formatado or '-'}")

                    if not telefone_whatsapp_valido(telefone_cliente):
                        st.error("O telefone do cliente não está em formato válido para WhatsApp. Revise o cadastro do cliente.")
                    elif pagamentos_contrato.empty:
                        st.info("Esse contrato ainda não possui cobranças para WhatsApp.")
                    else:
                        pendentes_cobranca = pagamentos_contrato[pagamentos_contrato["status_real"].isin(["Pendente", "Parcial", "Vencido"])] .copy()

                        st.markdown("#### Cobrança de semana específica")

                        opcoes_cobranca = {
                            (
                                f"Cobrança #{int(row['id'])} - "
                                f"{row['observacao'] or 'Sem observação'} - "
                                f"{normalizar_status_pagamento_visual(row['status_real'])} - "
                                f"Previsto {formatar_moeda(row['valor_previsto'])}"
                            ): row["id"]
                            for _, row in pendentes_cobranca.iterrows()
                        }

                        if opcoes_cobranca:
                            pagamento_cobranca_nome = st.selectbox(
                                "Selecione a cobrança semanal",
                                list(opcoes_cobranca.keys()),
                                key=f"whatsapp_parcela_select_{contrato_pagamento_id}",
                            )

                            pagamento_cobranca_id = opcoes_cobranca[pagamento_cobranca_nome]
                            registro_cobranca = pendentes_cobranca[pendentes_cobranca["id"] == pagamento_cobranca_id].iloc[0]

                            mensagem_parcela = montar_mensagem_cobranca_parcela(
                                cliente_nome=registro_pagamento_contrato["cliente"],
                                veiculo=registro_pagamento_contrato["veiculo"],
                                contrato_id=int(contrato_pagamento_id),
                                parcela_id=int(registro_cobranca["id"]),
                                valor_previsto=float(registro_cobranca["valor_previsto"] or 0.0),
                                valor_pago=float(registro_cobranca["valor_pago"] or 0.0),
                                data_vencimento=registro_cobranca["data_vencimento"],
                                status=normalizar_status_pagamento_visual(registro_cobranca["status_real"]),
                                observacao=registro_cobranca["observacao"] or "",
                            )

                            link_parcela = gerar_link_whatsapp(telefone_cliente, mensagem_parcela)

                            st.text_area(
                                "Mensagem da cobrança semanal",
                                value=mensagem_parcela,
                                height=220,
                                key=f"msg_whatsapp_parcela_{contrato_pagamento_id}",
                            )

                            st.markdown(
                                f'<div class="contrato-link-box"><a href="{link_parcela}" target="_blank">Abrir cobrança desta semana no WhatsApp</a></div>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.success("Esse contrato não possui cobranças em aberto para WhatsApp.")

                        st.markdown("#### Cobrança resumida do contrato")

                        if pendentes_cobranca.empty:
                            st.success("Esse contrato não possui valores pendentes, parciais ou vencidos.")
                        else:
                            total_aberto = pendentes_cobranca["valor_previsto"].fillna(0.0).sum() - pendentes_cobranca["valor_pago"].fillna(0.0).sum()
                            total_aberto = max(float(total_aberto), 0.0)
                            primeira_data = pendentes_cobranca["data_vencimento"].min()

                            mensagem_resumo = montar_mensagem_cobranca_resumo(
                                cliente_nome=registro_pagamento_contrato["cliente"],
                                veiculo=registro_pagamento_contrato["veiculo"],
                                contrato_id=int(contrato_pagamento_id),
                                total_aberto=total_aberto,
                                qtd_itens=len(pendentes_cobranca),
                                primeira_data_vencimento=primeira_data,
                            )

                            link_resumo = gerar_link_whatsapp(telefone_cliente, mensagem_resumo)

                            st.text_area(
                                "Mensagem resumida do contrato",
                                value=mensagem_resumo,
                                height=200,
                                key=f"msg_whatsapp_resumo_{contrato_pagamento_id}",
                            )

                            st.markdown(
                                f'<div class="contrato-link-box"><a href="{link_resumo}" target="_blank">Abrir cobrança resumida no WhatsApp</a></div>',
                                unsafe_allow_html=True,
                            )

            st.divider()
            st.markdown("### Alertas de comprovantes")

            if pagamentos_df.empty:
                st.info("Ainda não existem cobranças cadastradas.")
            else:
                pagamentos_alerta = pagamentos_df.copy()

                df_sem_comprovante = pagamentos_alerta[
                    (pagamentos_alerta["status_real"].isin(["Pago", "Parcial"]))
                    & (pagamentos_alerta["comprovante_pagamento"].isna() | (pagamentos_alerta["comprovante_pagamento"] == ""))
                ].copy()

                if df_sem_comprovante.empty:
                    st.success("Todos os pagamentos já liquidados possuem comprovante.")
                else:
                    pagos_sem = df_sem_comprovante[df_sem_comprovante["status_real"] == "Pago"]
                    parciais_sem = df_sem_comprovante[df_sem_comprovante["status_real"] == "Parcial"]

                    c1, c2 = st.columns(2)
                    c1.metric("Pagos sem comprovante", len(pagos_sem))
                    c2.metric("Parciais sem comprovante", len(parciais_sem))

                    alerta_exibicao = df_sem_comprovante[[
                        "id",
                        "contrato_id",
                        "cliente",
                        "veiculo",
                        "data_vencimento",
                        "data_pagamento",
                        "valor_previsto",
                        "valor_pago",
                        "status_real",
                    ]].copy()
                    alerta_exibicao["valor_previsto"] = alerta_exibicao["valor_previsto"].apply(formatar_moeda)
                    alerta_exibicao["valor_pago"] = alerta_exibicao["valor_pago"].apply(formatar_moeda)
                    st.dataframe(alerta_exibicao, use_container_width=True)

            st.divider()
            st.markdown("### Cobranças rápidas por WhatsApp")

            if pagamentos_df.empty:
                st.info("Ainda não existem cobranças registradas.")
            else:
                pagamentos_rapidos = pagamentos_df[pagamentos_df["status_real"].isin(["Vencido", "Parcial", "Pendente"])].copy()

                if pagamentos_rapidos.empty:
                    st.success("Não há cobranças abertas para cobrança rápida.")
                else:
                    colr1, colr2 = st.columns([2, 1])
                    with colr1:
                        busca_cobranca = st.text_input("Buscar cobrança rápida", placeholder="Digite cliente, veículo ou placa")
                    with colr2:
                        filtro_cobranca = st.selectbox("Prioridade", ["Todas", "Vencido", "Parcial", "Pendente"])

                    if busca_cobranca:
                        termo = busca_cobranca.strip().lower()
                        pagamentos_rapidos = pagamentos_rapidos[
                            pagamentos_rapidos["cliente"].astype(str).str.lower().str.contains(termo, na=False)
                            | pagamentos_rapidos["veiculo"].astype(str).str.lower().str.contains(termo, na=False)
                            | pagamentos_rapidos["placa"].astype(str).str.lower().str.contains(termo, na=False)
                        ]

                    if filtro_cobranca != "Todas":
                        pagamentos_rapidos = pagamentos_rapidos[pagamentos_rapidos["status_real"] == filtro_cobranca]

                    rapidos_exibicao = pagamentos_rapidos[[
                        "id",
                        "contrato_id",
                        "cliente",
                        "cliente_telefone",
                        "veiculo",
                        "data_vencimento",
                        "valor_previsto",
                        "valor_pago",
                        "status_real",
                        "observacao",
                    ]].copy()
                    rapidos_exibicao["valor_previsto"] = rapidos_exibicao["valor_previsto"].apply(formatar_moeda)
                    rapidos_exibicao["valor_pago"] = rapidos_exibicao["valor_pago"].apply(formatar_moeda)
                    st.dataframe(rapidos_exibicao, use_container_width=True)

                    opcoes_rapidas = {
                        (
                            f"Cobrança #{int(row['id'])} - "
                            f"Contrato #{int(row['contrato_id'])} - "
                            f"{row['cliente']} - "
                            f"{normalizar_status_pagamento_visual(row['status_real'])}"
                        ): row["id"]
                        for _, row in pagamentos_rapidos.iterrows()
                    }

                    if opcoes_rapidas:
                        pagamento_rapido_nome = st.selectbox("Selecione a cobrança rápida", list(opcoes_rapidas.keys()), key="cobranca_rapida_select")
                        pagamento_rapido_id = opcoes_rapidas[pagamento_rapido_nome]
                        registro_rapido = pagamentos_rapidos[pagamentos_rapidos["id"] == pagamento_rapido_id].iloc[0]

                        if not telefone_whatsapp_valido(registro_rapido["cliente_telefone"]):
                            st.error("O telefone deste cliente não está válido para WhatsApp.")
                        else:
                            msg_rapida = montar_mensagem_cobranca_parcela(
                                cliente_nome=registro_rapido["cliente"],
                                veiculo=registro_rapido["veiculo"],
                                contrato_id=int(registro_rapido["contrato_id"]),
                                parcela_id=int(registro_rapido["id"]),
                                valor_previsto=float(registro_rapido["valor_previsto"] or 0.0),
                                valor_pago=float(registro_rapido["valor_pago"] or 0.0),
                                data_vencimento=registro_rapido["data_vencimento"],
                                status=normalizar_status_pagamento_visual(registro_rapido["status_real"]),
                                observacao=registro_rapido["observacao"] or "",
                            )
                            link_rapido = gerar_link_whatsapp(registro_rapido["cliente_telefone"], msg_rapida)

                            st.text_area("Mensagem da cobrança rápida", value=msg_rapida, height=220, key="msg_cobranca_rapida")

                            st.markdown(
                                f'<div class="contrato-link-box"><a href="{link_rapido}" target="_blank">Abrir cobrança rápida no WhatsApp</a></div>',
                                unsafe_allow_html=True,
                            )

            st.divider()
            st.markdown("### Baixar contrato salvo")

            opcoes_download = {f"Contrato #{row['id']} - {row['cliente']} - {row['veiculo']}": row["id"] for _, row in df_filtrado.iterrows()}

            if opcoes_download:
                contrato_download_escolhido = st.selectbox(
                    "Selecione o contrato para baixar",
                    list(opcoes_download.keys()),
                    key="baixar_contrato_existente",
                )

                contrato_download_id = opcoes_download[contrato_download_escolhido]
                registro_download = df_filtrado[df_filtrado["id"] == contrato_download_id].iloc[0]
                caminho_arquivo = registro_download["arquivo_contrato"]

                st.write(f"**Cliente:** {registro_download['cliente']}")
                st.write(f"**Veículo:** {registro_download['veiculo']}")
                st.write(f"**Status contrato:** {registro_download['status']}")
                st.write(f"**Status pagamento:** {registro_download['status_pagamento']}")

                if caminho_arquivo and os.path.exists(caminho_arquivo):
                    with open(caminho_arquivo, "rb") as f:
                        st.download_button(
                            "✅ Baixar contrato selecionado",
                            data=f,
                            file_name=os.path.basename(caminho_arquivo),
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True,
                            key=f"download_contrato_{contrato_download_id}",
                        )
                else:
                    st.warning("Arquivo do contrato não encontrado no sistema.")
            else:
                st.info("Nenhum contrato encontrado para download.")

            st.divider()
            st.markdown("### Finalizar contrato")

            contratos_ativos_finalizar = df[df["status"] == "Ativo"]

            if contratos_ativos_finalizar.empty:
                st.info("Não há contratos ativos para finalizar.")
            else:
                opcoes_contrato = {f"Contrato #{row['id']} - {row['cliente']} - {row['veiculo']}": row["id"] for _, row in contratos_ativos_finalizar.iterrows()}

                contrato_escolhido = st.selectbox("Selecione o contrato ativo", list(opcoes_contrato.keys()), key="finalizar_contrato_select")
                contrato_id = opcoes_contrato[contrato_escolhido]

                st.markdown(
                    """
                <div class="contrato-warning-box">
                    Ao finalizar o contrato, o veículo volta automaticamente para o status de disponível.
                </div>
                """,
                    unsafe_allow_html=True,
                )

                if st.button("Finalizar contrato selecionado", type="primary"):
                    sucesso, mensagem = finalizar_contrato(contrato_id)

                    if sucesso:
                        st.success(mensagem)
                        st.rerun()
                    else:
                        st.warning(mensagem)

    with tab3:
        st.markdown(
            """
        <div class="contrato-box">
            <div class="contrato-box-title">Excluir contrato</div>
            <div class="contrato-box-sub">
                Remova contratos de forma definitiva, com confirmação explícita antes da exclusão.
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if df.empty:
            st.info("Não há contratos para excluir.")
        else:
            opcoes_excluir_contrato = {
                f"Contrato #{row['id']} - {row['cliente']} - {row['veiculo']} - {row['status']}": row["id"]
                for _, row in df.iterrows()
            }

            contrato_excluir_escolhido = st.selectbox(
                "Selecione o contrato para excluir",
                list(opcoes_excluir_contrato.keys()),
                key="excluir_contrato_tab_select",
            )

            contrato_id_excluir = opcoes_excluir_contrato[contrato_excluir_escolhido]
            registro_excluir_contrato = df[df["id"] == contrato_id_excluir].iloc[0]

            st.markdown(
                """
                <div class="contrato-danger-box">
                    Atenção: esta exclusão remove o contrato de forma definitiva, apaga as cobranças vinculadas
                    e pode liberar o veículo caso o contrato ainda esteja ativo. Os documentos do locatário são preservados.
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.write(f"**Contrato selecionado:** #{int(registro_excluir_contrato['id'])}")
            st.write(f"**Cliente:** {registro_excluir_contrato['cliente']}")
            st.write(f"**Veículo:** {registro_excluir_contrato['veiculo']}")
            st.write(f"**Status:** {registro_excluir_contrato['status']}")
            st.write(f"**Valor total:** {formatar_moeda(registro_excluir_contrato['valor_total_contrato'])}")

            confirmar_exclusao_contrato = st.checkbox(
                "Confirmo que desejo excluir este contrato permanentemente",
                key=f"confirmar_exclusao_contrato_tab_{contrato_id_excluir}",
            )

            if st.button(
                "Excluir contrato selecionado",
                key=f"btn_excluir_contrato_tab_{contrato_id_excluir}"
            ):
                if not confirmar_exclusao_contrato:
                    st.warning("Marque a confirmação antes de excluir o contrato.")
                else:
                    sucesso, mensagem = excluir_contrato_completo(int(contrato_id_excluir))
                    if sucesso:
                        st.success(mensagem)
                        st.rerun()
                    else:
                        st.warning(mensagem)

    conn.close()
