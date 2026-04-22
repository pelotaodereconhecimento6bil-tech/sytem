import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from docxtpl import DocxTemplate

from database import (
    atualizar_resumo_pagamento_contrato,
    registrar_pagamento_conn,
    salvar_documento_cliente_conn,
)

OUTPUT_DIR = "contratos_gerados"


# =========================
# HELPERS
# =========================

def _coluna_existe(conn, tabela, coluna):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({tabela})")
    return coluna in [row[1] for row in cursor.fetchall()]


def _template_path():
    candidatos = [
        Path("contrato_template.docx"),
        Path("templates") / "contrato_template.docx",
        Path(__file__).resolve().parent.parent / "contrato_template.docx",
    ]
    for caminho in candidatos:
        if caminho.exists():
            return caminho
    raise FileNotFoundError("contrato_template.docx não encontrado.")


def _normalizar_data(valor):
    data = pd.to_datetime(valor, errors="coerce")
    if pd.isna(data):
        return None
    return data.to_pydatetime().date()


def _normalizar_status_pagamento_visual(status):
    texto = str(status or "Pendente").strip().title()
    mapa = {
        "Pendente": "Pendente",
        "Parcial": "Parcial",
        "Pago": "Pago",
        "Vencido": "Vencido",
        "Sem Valor": "Sem valor",
    }
    return mapa.get(texto, "Pendente")


def normalizar_status_pagamento_visual(status):
    return _normalizar_status_pagamento_visual(status)


def calcular_status_pagamento_item(valor_previsto, valor_pago, data_vencimento=None):
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


def calcular_semanas_cobradas(data_inicio, data_fim):
    dt_inicio = _normalizar_data(data_inicio)
    dt_fim = _normalizar_data(data_fim)
    if not dt_inicio or not dt_fim or dt_fim < dt_inicio:
        return 0
    dias = (dt_fim - dt_inicio).days + 1
    return max(1, (dias + 6) // 7)


def gerar_cobrancas_semanais(data_inicio, data_fim, valor_semanal):
    dt_inicio = _normalizar_data(data_inicio)
    dt_fim = _normalizar_data(data_fim)
    if not dt_inicio or not dt_fim or dt_fim < dt_inicio:
        return []

    valor = round(float(valor_semanal or 0.0), 2)
    cobrancas = []
    referencia = dt_inicio
    parcela = 1

    while referencia <= dt_fim:
        cobrancas.append({
            "parcela": parcela,
            "data_vencimento": referencia.strftime("%Y-%m-%d"),
            "valor_previsto": valor,
            "observacao": f"Cobrança semanal {parcela}",
        })
        referencia += timedelta(days=7)
        parcela += 1

    return cobrancas


def _proximo_numero_contrato(conn, data_referencia=None):
    data_ref = _normalizar_data(data_referencia) or datetime.now().date()
    ano = data_ref.year

    if _coluna_existe(conn, "contratos", "numero_contrato"):
        df = pd.read_sql_query(
            """
            SELECT numero_contrato
            FROM contratos
            WHERE numero_contrato IS NOT NULL
              AND TRIM(numero_contrato) != ''
            """,
            conn,
        )
        sequenciais = []
        for valor in df.get("numero_contrato", pd.Series(dtype=str)).fillna(""):
            texto = str(valor).strip()
            if not texto.endswith(f"/{ano}"):
                continue
            try:
                sequenciais.append(int(texto.split("/")[0]))
            except Exception:
                continue
        proximo = (max(sequenciais) if sequenciais else 0) + 1
        return f"{proximo}/{ano}"

    df = pd.read_sql_query(
        "SELECT COUNT(*) AS total FROM contratos WHERE substr(COALESCE(data_inicio, ''), 1, 4) = ?",
        conn,
        params=(str(ano),),
    )
    total = int(df.iloc[0]["total"] or 0)
    return f"{total + 1}/{ano}"


def _gerar_arquivo_contrato(dados_template, numero_contrato):
    template = DocxTemplate(str(_template_path()))
    template.render(dados_template)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    nome_arquivo = f"contrato_{str(numero_contrato).replace('/', '_')}.docx"
    caminho = Path(OUTPUT_DIR) / nome_arquivo
    template.save(str(caminho))
    return str(caminho)


# =========================
# CARGA DE DADOS
# =========================

def carregar_contratos(conn):
    campos_extras = []
    if _coluna_existe(conn, "contratos", "numero_contrato"):
        campos_extras.append("c.numero_contrato")
    if _coluna_existe(conn, "contratos", "prazo_minimo"):
        campos_extras.append("c.prazo_minimo")
    if _coluna_existe(conn, "contratos", "hora_limite_pagamento"):
        campos_extras.append("c.hora_limite_pagamento")
    if _coluna_existe(conn, "contratos", "multa_atraso_dia"):
        campos_extras.append("c.multa_atraso_dia")
    if _coluna_existe(conn, "contratos", "franquia_valor"):
        campos_extras.append("c.franquia_valor")
    if _coluna_existe(conn, "contratos", "locador_id"):
        campos_extras.append("c.locador_id")

    extras_sql = (",\n            " + ",\n            ".join(campos_extras)) if campos_extras else ""

    df = pd.read_sql_query(
        f"""
        SELECT
            c.id,
            cl.nome AS cliente,
            cl.telefone,
            v.modelo || ' - ' || v.placa AS veiculo,
            v.placa,
            c.cliente_id,
            c.veiculo_id,
            c.data_inicio,
            c.data_fim,
            c.valor_semanal,
            c.valor_total_contrato,
            c.caucao,
            c.status,
            c.arquivo_contrato,
            c.valor_pago,
            c.status_pagamento,
            c.data_pagamento,
            c.comprovante_pagamento{extras_sql}
        FROM contratos c
        INNER JOIN clientes cl ON c.cliente_id = cl.id
        INNER JOIN veiculos v ON c.veiculo_id = v.id
        ORDER BY c.id DESC
        """,
        conn,
    )

    for coluna in ["data_inicio", "data_fim", "data_pagamento"]:
        if coluna in df.columns:
            df[coluna] = pd.to_datetime(df[coluna], errors="coerce")

    for coluna in ["valor_semanal", "valor_total_contrato", "caucao", "valor_pago"]:
        if coluna in df.columns:
            df[coluna] = pd.to_numeric(df[coluna], errors="coerce").fillna(0.0)

    if "numero_contrato" not in df.columns:
        df["numero_contrato"] = df["id"].astype(str)

    if "status_pagamento" not in df.columns:
        df["status_pagamento"] = "Pendente"

    return df


def carregar_pagamentos(conn):
    df = pd.read_sql_query(
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
            cl.nome AS cliente,
            v.modelo || ' - ' || v.placa AS veiculo,
            v.placa,
            c.status AS status_contrato,
            c.status_pagamento AS status_pagamento_contrato
        FROM pagamentos p
        INNER JOIN contratos c ON p.contrato_id = c.id
        INNER JOIN clientes cl ON c.cliente_id = cl.id
        INNER JOIN veiculos v ON c.veiculo_id = v.id
        ORDER BY p.id DESC
        """,
        conn,
    )

    for coluna in ["data_vencimento", "data_pagamento"]:
        if coluna in df.columns:
            df[coluna] = pd.to_datetime(df[coluna], errors="coerce")

    for coluna in ["valor_previsto", "valor_pago"]:
        if coluna in df.columns:
            df[coluna] = pd.to_numeric(df[coluna], errors="coerce").fillna(0.0)

    if not df.empty:
        df["status_real"] = df.apply(
            lambda row: calcular_status_pagamento_item(
                row.get("valor_previsto", 0.0),
                row.get("valor_pago", 0.0),
                row.get("data_vencimento"),
            ),
            axis=1,
        )
    else:
        df["status_real"] = pd.Series(dtype=str)

    return df


def atualizar_resumo_todos_contratos(conn):
    df = pd.read_sql_query("SELECT id FROM contratos", conn)
    for _, row in df.iterrows():
        atualizar_resumo_pagamento_contrato(conn, int(row["id"]))
    return True


# =========================
# AÇÕES
# =========================

def criar_contrato_completo(
    conn,
    cliente_id,
    veiculo_id,
    data_inicio,
    data_fim,
    valor_semanal,
    caucao,
    dados_template,
    documentos=None,
    locador_id=None,
):
    cursor = conn.cursor()
    numero_contrato = _proximo_numero_contrato(conn, data_inicio)
    data_inicio_str = _normalizar_data(data_inicio).strftime("%Y-%m-%d")
    data_fim_str = _normalizar_data(data_fim).strftime("%Y-%m-%d")
    valor_total = round(
        calcular_semanas_cobradas(data_inicio, data_fim) * float(valor_semanal or 0.0),
        2,
    )

    campos = [
        "cliente_id", "veiculo_id", "data_inicio", "data_fim", "valor_semanal",
        "valor_total_contrato", "caucao", "status", "arquivo_contrato", "valor_pago", "status_pagamento"
    ]
    valores = [
        int(cliente_id), int(veiculo_id), data_inicio_str, data_fim_str,
        float(valor_semanal or 0.0), valor_total, float(caucao or 0.0),
        "Ativo", "", 0.0, "Pendente"
    ]

    adicionais = {
        "numero_contrato": numero_contrato,
        "locador_id": int(locador_id) if locador_id else None,
        "prazo_minimo": int(dados_template.get("prazo_minimo_dias", 0) or 0),
        "hora_limite_pagamento": str(dados_template.get("hora_limite", "") or ""),
        "multa_atraso_dia": float(dados_template.get("multa_atraso_float", 0.0) or 0.0),
        "franquia_valor": float(dados_template.get("valor_franquia_float", 0.0) or 0.0),
    }
    for coluna, valor in adicionais.items():
        if _coluna_existe(conn, "contratos", coluna):
            campos.append(coluna)
            valores.append(valor)

    placeholders = ", ".join(["?"] * len(campos))
    sql = f"INSERT INTO contratos ({', '.join(campos)}) VALUES ({placeholders})"
    cursor.execute(sql, valores)
    contrato_id = int(cursor.lastrowid)

    cursor.execute("UPDATE veiculos SET status = 'Alugado' WHERE id = ?", (int(veiculo_id),))

    dados_final = dict(dados_template)
    dados_final.setdefault("numero_contrato", numero_contrato)
    dados_final.setdefault("cidade", dados_final.get("locador_cidade") or "")

    caminho_arquivo = _gerar_arquivo_contrato(dados_final, numero_contrato)
    cursor.execute(
        "UPDATE contratos SET arquivo_contrato = ? WHERE id = ?",
        (caminho_arquivo, contrato_id),
    )

    cobrancas = gerar_cobrancas_semanais(data_inicio, data_fim, valor_semanal)
    for item in cobrancas:
        registrar_pagamento_conn(
            conn=conn,
            contrato_id=contrato_id,
            valor_previsto=float(item["valor_previsto"]),
            data_vencimento=item["data_vencimento"],
            valor_pago=0.0,
            data_pagamento=None,
            status="Pendente",
            observacao=item.get("observacao", ""),
            comprovante_pagamento="",
        )

    for tipo_documento, arquivo in (documentos or {}).items():
        if arquivo is not None:
            salvar_documento_cliente_conn(
                conn=conn,
                cliente_id=int(cliente_id),
                contrato_id=contrato_id,
                arquivo=arquivo,
                tipo_documento=tipo_documento,
                observacao="Upload no ato da criação do contrato",
            )

    conn.commit()
    return {
        "contrato_id": contrato_id,
        "numero_contrato": numero_contrato,
        "caminho_arquivo": caminho_arquivo,
        "valor_total_contrato": valor_total,
        "cobrancas": cobrancas,
    }


def finalizar_contrato(conn, contrato_id):
    cursor = conn.cursor()
    cursor.execute("SELECT veiculo_id, status FROM contratos WHERE id = ?", (int(contrato_id),))
    row = cursor.fetchone()
    if not row:
        return False, "Contrato não encontrado."

    veiculo_id, status_atual = row
    if str(status_atual or "").strip().lower() == "finalizado":
        return False, "Este contrato já está finalizado."

    cursor.execute("UPDATE contratos SET status = 'Finalizado' WHERE id = ?", (int(contrato_id),))
    cursor.execute("UPDATE veiculos SET status = 'Disponível' WHERE id = ?", (int(veiculo_id),))
    conn.commit()
    return True, "Contrato finalizado com sucesso."


def excluir_contrato_completo(conn, contrato_id):
    cursor = conn.cursor()
    cursor.execute("SELECT veiculo_id, arquivo_contrato FROM contratos WHERE id = ?", (int(contrato_id),))
    row = cursor.fetchone()
    if not row:
        return False, "Contrato não encontrado."

    veiculo_id, caminho_arquivo = row

    docs = pd.read_sql_query(
        "SELECT caminho_arquivo FROM documentos_cliente WHERE contrato_id = ?",
        conn,
        params=(int(contrato_id),),
    )
    for caminho in docs.get("caminho_arquivo", pd.Series(dtype=str)).fillna(""):
        if caminho and os.path.exists(caminho):
            try:
                os.remove(caminho)
            except Exception:
                pass

    if caminho_arquivo and os.path.exists(caminho_arquivo):
        try:
            os.remove(caminho_arquivo)
        except Exception:
            pass

    cursor.execute("DELETE FROM documentos_cliente WHERE contrato_id = ?", (int(contrato_id),))
    cursor.execute("DELETE FROM pagamentos WHERE contrato_id = ?", (int(contrato_id),))
    cursor.execute("DELETE FROM contratos WHERE id = ?", (int(contrato_id),))

    contratos_ativos = pd.read_sql_query(
        "SELECT COUNT(*) AS total FROM contratos WHERE veiculo_id = ? AND status = 'Ativo'",
        conn,
        params=(int(veiculo_id),),
    )
    if int(contratos_ativos.iloc[0]["total"] or 0) == 0:
        cursor.execute("UPDATE veiculos SET status = 'Disponível' WHERE id = ?", (int(veiculo_id),))

    conn.commit()
    return True, "Contrato excluído com sucesso."


def gerar_contrato_docx(dados):
    numero_contrato = dados.get("numero_contrato") or f"preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    return _gerar_arquivo_contrato(dados, numero_contrato)
