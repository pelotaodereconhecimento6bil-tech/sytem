import os
from datetime import datetime

import pandas as pd
import sqlite3


DB_NAME = "banco.db"


def conectar():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn



def registrar_log(conn, usuario, acao, modulo, referencia_id=None, descricao=""):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO logs_acoes (usuario, acao, modulo, referencia_id, descricao)
        VALUES (?, ?, ?, ?, ?)
    """, (
        (usuario or "sistema")[:100],
        (acao or "")[:100],
        (modulo or "")[:100],
        referencia_id,
        (descricao or "")[:1000],
    ))


def obter_logs_recentes(conn, limite=20):
    limite = int(limite or 20)
    return pd.read_sql_query(
        """
        SELECT id, data_hora, usuario, acao, modulo, referencia_id, descricao
        FROM logs_acoes
        ORDER BY id DESC
        LIMIT ?
        """,
        conn,
        params=(limite,)
    )

def tabela_existe(cursor, tabela):
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
    """, (tabela,))
    return cursor.fetchone() is not None


def coluna_existe(cursor, tabela, coluna):
    cursor.execute(f"PRAGMA table_info({tabela})")
    colunas = [item[1] for item in cursor.fetchall()]
    return coluna in colunas


def indice_existe(cursor, nome_indice):
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'index' AND name = ?
    """, (nome_indice,))
    return cursor.fetchone() is not None


def criar_indice_se_nao_existir(cursor, nome_indice, sql_create):
    if not indice_existe(cursor, nome_indice):
        cursor.execute(sql_create)


def adicionar_coluna_se_nao_existir(cursor, tabela, coluna, definicao_sql):
    if not coluna_existe(cursor, tabela, coluna):
        cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao_sql}")


def obter_primeiro_pagamento_efetivo(cursor, contrato_id):
    if not tabela_existe(cursor, "pagamentos"):
        return None, None, None

    cursor.execute("""
        SELECT
            COALESCE(SUM(valor_pago), 0) AS total_pago,
            MAX(data_pagamento) AS ultima_data_pagamento,
            MAX(comprovante_pagamento) AS algum_comprovante
        FROM pagamentos
        WHERE contrato_id = ?
          AND (status = 'Pago' OR status = 'Parcial' OR COALESCE(valor_pago, 0) > 0)
    """, (contrato_id,))
    row = cursor.fetchone()

    if not row:
        return 0.0, None, ""

    total_pago = float(row[0] or 0.0)
    data_pagamento = row[1]
    comprovante = row[2] or ""

    return total_pago, data_pagamento, comprovante


def resumir_status_pagamento(cursor, contrato_id, valor_total_contrato):
    if not tabela_existe(cursor, "pagamentos"):
        valor_total_contrato = float(valor_total_contrato or 0)
        if valor_total_contrato <= 0:
            return 0.0, "Sem valor", None, ""

        return 0.0, "Pendente", None, ""

    cursor.execute("""
        SELECT
            COUNT(*) AS total_parcelas,
            COALESCE(SUM(valor_previsto), 0) AS total_previsto,
            COALESCE(SUM(valor_pago), 0) AS total_pago,
            SUM(CASE WHEN status = 'Pago' THEN 1 ELSE 0 END) AS qtd_pago,
            SUM(CASE WHEN status = 'Parcial' THEN 1 ELSE 0 END) AS qtd_parcial,
            SUM(CASE WHEN status = 'Pendente' THEN 1 ELSE 0 END) AS qtd_pendente,
            SUM(
                CASE
                    WHEN status != 'Pago'
                     AND data_vencimento IS NOT NULL
                     AND date(data_vencimento) < date('now')
                    THEN 1 ELSE 0
                END
            ) AS qtd_vencido
        FROM pagamentos
        WHERE contrato_id = ?
    """, (contrato_id,))
    row = cursor.fetchone()

    total_parcelas = int(row[0] or 0)
    total_previsto = float(row[1] or 0.0)
    total_pago = float(row[2] or 0.0)
    qtd_pago = int(row[3] or 0)
    qtd_parcial = int(row[4] or 0)
    qtd_pendente = int(row[5] or 0)
    qtd_vencido = int(row[6] or 0)

    cursor.execute("""
        SELECT
            MAX(data_pagamento) AS ultima_data_pagamento,
            MAX(comprovante_pagamento) AS algum_comprovante
        FROM pagamentos
        WHERE contrato_id = ?
          AND (status = 'Pago' OR status = 'Parcial' OR COALESCE(valor_pago, 0) > 0)
    """, (contrato_id,))
    row2 = cursor.fetchone()
    ultima_data_pagamento = row2[0] if row2 else None
    algum_comprovante = (row2[1] if row2 else "") or ""

    base_total = float(valor_total_contrato or 0.0)
    if base_total <= 0:
        base_total = total_previsto

    if total_parcelas == 0:
        if base_total <= 0:
            status_resumo = "Sem valor"
        else:
            status_resumo = "Pendente"
        return total_pago, status_resumo, ultima_data_pagamento, algum_comprovante

    pendente = max(base_total - total_pago, 0.0)

    if qtd_vencido > 0 and pendente > 0:
        status_resumo = "Vencido"
    elif pendente <= 0:
        status_resumo = "Pago"
    elif total_pago > 0 or qtd_pago > 0 or qtd_parcial > 0:
        status_resumo = "Parcial"
    elif qtd_pendente > 0:
        status_resumo = "Pendente"
    else:
        status_resumo = "Pendente"

    return total_pago, status_resumo, ultima_data_pagamento, algum_comprovante


def atualizar_resumo_pagamento_contrato(conn, contrato_id):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT valor_total_contrato
        FROM contratos
        WHERE id = ?
    """, (contrato_id,))
    row = cursor.fetchone()

    if not row:
        return False

    valor_total_contrato = float(row[0] or 0.0)

    valor_pago, status_pagamento, data_pagamento, comprovante_pagamento = resumir_status_pagamento(
        cursor,
        contrato_id,
        valor_total_contrato
    )

    cursor.execute("""
        UPDATE contratos
        SET
            valor_pago = ?,
            status_pagamento = ?,
            data_pagamento = ?,
            comprovante_pagamento = ?
        WHERE id = ?
    """, (
        valor_pago,
        status_pagamento,
        data_pagamento,
        comprovante_pagamento,
        contrato_id
    ))

    conn.commit()
    return True


def sincronizar_contratos_com_pagamentos(conn):
    cursor = conn.cursor()

    if not tabela_existe(cursor, "pagamentos"):
        return

    cursor.execute("SELECT id FROM contratos")
    contratos = cursor.fetchall()

    for row in contratos:
        contrato_id = int(row[0])
        atualizar_resumo_pagamento_contrato(conn, contrato_id)


def criar_tabelas():
    conn = conectar()
    cursor = conn.cursor()

    # =========================
    # LOGS / AUDITORIA
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs_acoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            acao TEXT NOT NULL,
            modulo TEXT NOT NULL,
            referencia_id INTEGER,
            descricao TEXT,
            data_hora TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =========================
    # CLIENTES
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT,
            rg TEXT,
            telefone TEXT,
            endereco TEXT,
            numero TEXT,
            complemento TEXT,
            cidade TEXT,
            estado TEXT,
            cep TEXT
        )
    """)

    adicionar_coluna_se_nao_existir(cursor, "clientes", "numero", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "clientes", "complemento", "TEXT")

    # =========================
    # VEÍCULOS
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS veiculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            modelo TEXT NOT NULL,
            marca TEXT,
            ano TEXT,
            placa TEXT,
            cor TEXT,
            status TEXT DEFAULT 'Disponível',
            observacoes TEXT,
            km_inicial INTEGER DEFAULT 0,
            data_entrada_frota TEXT,
            observacao_entrada TEXT,
            renavam TEXT,
            valor_aquisicao REAL DEFAULT 0,
            valor_fipe REAL DEFAULT 0,
            data_referencia_fipe TEXT,
            codigo_fipe TEXT,
            tipo_veiculo_fipe TEXT DEFAULT 'Carro'
        )
    """)

    adicionar_coluna_se_nao_existir(cursor, "veiculos", "km_inicial", "INTEGER DEFAULT 0")
    adicionar_coluna_se_nao_existir(cursor, "veiculos", "data_entrada_frota", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "veiculos", "observacao_entrada", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "veiculos", "renavam", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "veiculos", "valor_aquisicao", "REAL DEFAULT 0")
    adicionar_coluna_se_nao_existir(cursor, "veiculos", "valor_fipe", "REAL DEFAULT 0")
    adicionar_coluna_se_nao_existir(cursor, "veiculos", "data_referencia_fipe", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "veiculos", "codigo_fipe", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "veiculos", "tipo_veiculo_fipe", "TEXT DEFAULT 'Carro'")

    # =========================
    # LOCADOR / CONFIGURAÇÕES CONTRATUAIS
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS locador_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            nome TEXT,
            cpf TEXT,
            telefone TEXT,
            estado_civil TEXT,
            profissao TEXT,
            cidade TEXT,
            estado TEXT,
            cep TEXT,
            endereco TEXT,
            numero TEXT,
            complemento TEXT,
            endereco_referencia TEXT,
            prazo_minimo_padrao INTEGER DEFAULT 90,
            multa_atraso_padrao REAL DEFAULT 50,
            valor_franquia_padrao REAL DEFAULT 0,
            hora_limite_padrao TEXT DEFAULT '18:00',
            observacoes TEXT,
            atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    adicionar_coluna_se_nao_existir(cursor, "locador_config", "nome", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locador_config", "cpf", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locador_config", "telefone", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locador_config", "estado_civil", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locador_config", "profissao", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locador_config", "cidade", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locador_config", "estado", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locador_config", "cep", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locador_config", "endereco", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locador_config", "numero", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locador_config", "complemento", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locador_config", "endereco_referencia", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locador_config", "prazo_minimo_padrao", "INTEGER DEFAULT 90")
    adicionar_coluna_se_nao_existir(cursor, "locador_config", "multa_atraso_padrao", "REAL DEFAULT 50")
    adicionar_coluna_se_nao_existir(cursor, "locador_config", "valor_franquia_padrao", "REAL DEFAULT 0")
    adicionar_coluna_se_nao_existir(cursor, "locador_config", "hora_limite_padrao", "TEXT DEFAULT '18:00'")
    adicionar_coluna_se_nao_existir(cursor, "locador_config", "observacoes", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locador_config", "atualizado_em", "TEXT DEFAULT CURRENT_TIMESTAMP")

    # =========================
    # LOCADORES (CADASTRO MÚLTIPLO)
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS locadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT,
            telefone TEXT,
            estado_civil TEXT,
            profissao TEXT,
            cidade TEXT,
            estado TEXT,
            cep TEXT,
            endereco TEXT,
            numero TEXT,
            complemento TEXT,
            endereco_referencia TEXT,
            observacoes TEXT,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    adicionar_coluna_se_nao_existir(cursor, "locadores", "nome", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locadores", "cpf", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locadores", "telefone", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locadores", "estado_civil", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locadores", "profissao", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locadores", "cidade", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locadores", "estado", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locadores", "cep", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locadores", "endereco", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locadores", "numero", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locadores", "complemento", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locadores", "endereco_referencia", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locadores", "observacoes", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "locadores", "criado_em", "TEXT DEFAULT CURRENT_TIMESTAMP")
    adicionar_coluna_se_nao_existir(cursor, "locadores", "atualizado_em", "TEXT DEFAULT CURRENT_TIMESTAMP")

    # =========================
    # CONTRATOS
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contratos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            veiculo_id INTEGER NOT NULL,
            data_inicio TEXT,
            data_fim TEXT,
            valor_semanal REAL,
            valor_total_contrato REAL DEFAULT 0,
            caucao REAL,
            status TEXT DEFAULT 'Ativo',
            arquivo_contrato TEXT,
            valor_pago REAL DEFAULT 0,
            status_pagamento TEXT DEFAULT 'Pendente',
            data_pagamento TEXT,
            comprovante_pagamento TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id),
            FOREIGN KEY (veiculo_id) REFERENCES veiculos(id)
        )
    """)

    adicionar_coluna_se_nao_existir(cursor, "contratos", "valor_total_contrato", "REAL DEFAULT 0")
    adicionar_coluna_se_nao_existir(cursor, "contratos", "valor_pago", "REAL DEFAULT 0")
    adicionar_coluna_se_nao_existir(cursor, "contratos", "status_pagamento", "TEXT DEFAULT 'Pendente'")
    adicionar_coluna_se_nao_existir(cursor, "contratos", "data_pagamento", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "contratos", "comprovante_pagamento", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "contratos", "numero_contrato", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "contratos", "locador_id", "INTEGER")
    adicionar_coluna_se_nao_existir(cursor, "contratos", "prazo_minimo", "INTEGER DEFAULT 0")
    adicionar_coluna_se_nao_existir(cursor, "contratos", "hora_limite_pagamento", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "contratos", "multa_atraso_dia", "REAL DEFAULT 0")
    adicionar_coluna_se_nao_existir(cursor, "contratos", "franquia_valor", "REAL DEFAULT 0")

    # =========================
    # PAGAMENTOS
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pagamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contrato_id INTEGER NOT NULL,
            data_vencimento TEXT,
            data_pagamento TEXT,
            valor_previsto REAL DEFAULT 0,
            valor_pago REAL DEFAULT 0,
            status TEXT DEFAULT 'Pendente',
            observacao TEXT,
            comprovante_pagamento TEXT,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contrato_id) REFERENCES contratos(id) ON DELETE CASCADE
        )
    """)

    adicionar_coluna_se_nao_existir(cursor, "pagamentos", "data_vencimento", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "pagamentos", "data_pagamento", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "pagamentos", "valor_previsto", "REAL DEFAULT 0")
    adicionar_coluna_se_nao_existir(cursor, "pagamentos", "valor_pago", "REAL DEFAULT 0")
    adicionar_coluna_se_nao_existir(cursor, "pagamentos", "status", "TEXT DEFAULT 'Pendente'")
    adicionar_coluna_se_nao_existir(cursor, "pagamentos", "observacao", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "pagamentos", "comprovante_pagamento", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "pagamentos", "criado_em", "TEXT DEFAULT CURRENT_TIMESTAMP")
    adicionar_coluna_se_nao_existir(cursor, "pagamentos", "atualizado_em", "TEXT DEFAULT CURRENT_TIMESTAMP")

    # =========================
    # VISTORIAS
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vistorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            veiculo_id INTEGER NOT NULL,
            contrato_id INTEGER,
            cliente_contrato TEXT,
            vistoriador TEXT,
            data_vistoria TEXT,
            odometro INTEGER,
            observacoes TEXT,
            foto_path TEXT,
            latitude REAL,
            longitude REAL,
            endereco TEXT,
            data_hora_real TEXT,
            hash_vistoria TEXT,
            assinatura_cliente TEXT,
            assinatura_vistoriador TEXT,
            pdf_path TEXT,
            FOREIGN KEY (veiculo_id) REFERENCES veiculos(id),
            FOREIGN KEY (contrato_id) REFERENCES contratos(id)
        )
    """)

    adicionar_coluna_se_nao_existir(cursor, "vistorias", "foto_path", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "vistorias", "latitude", "REAL")
    adicionar_coluna_se_nao_existir(cursor, "vistorias", "longitude", "REAL")
    adicionar_coluna_se_nao_existir(cursor, "vistorias", "endereco", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "vistorias", "data_hora_real", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "vistorias", "hash_vistoria", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "vistorias", "assinatura_cliente", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "vistorias", "assinatura_vistoriador", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "vistorias", "pdf_path", "TEXT")

    # =========================
    # MANUTENÇÕES
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS manutencoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            veiculo_id INTEGER NOT NULL,
            data_manutencao TEXT,
            tipo_servico TEXT,
            descricao TEXT,
            valor REAL DEFAULT 0,
            oficina TEXT,
            km_atual INTEGER DEFAULT 0,
            proxima_troca_oleo INTEGER,
            km_prox_revisao INTEGER,
            km_prox_pneu INTEGER,
            km_prox_freio INTEGER,
            km_prox_bateria INTEGER,
            km_ultimo_recompletamento_oleo INTEGER DEFAULT 0,
            intervalo_recompletamento_oleo INTEGER DEFAULT 2600,
            foto_path TEXT,
            FOREIGN KEY (veiculo_id) REFERENCES veiculos(id)
        )
    """)

    adicionar_coluna_se_nao_existir(cursor, "manutencoes", "data_manutencao", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "manutencoes", "tipo_servico", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "manutencoes", "descricao", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "manutencoes", "valor", "REAL DEFAULT 0")
    adicionar_coluna_se_nao_existir(cursor, "manutencoes", "oficina", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "manutencoes", "km_atual", "INTEGER DEFAULT 0")
    adicionar_coluna_se_nao_existir(cursor, "manutencoes", "proxima_troca_oleo", "INTEGER")
    adicionar_coluna_se_nao_existir(cursor, "manutencoes", "km_prox_revisao", "INTEGER")
    adicionar_coluna_se_nao_existir(cursor, "manutencoes", "km_prox_pneu", "INTEGER")
    adicionar_coluna_se_nao_existir(cursor, "manutencoes", "km_prox_freio", "INTEGER")
    adicionar_coluna_se_nao_existir(cursor, "manutencoes", "km_prox_bateria", "INTEGER")
    adicionar_coluna_se_nao_existir(cursor, "manutencoes", "km_ultimo_recompletamento_oleo", "INTEGER DEFAULT 0")
    adicionar_coluna_se_nao_existir(cursor, "manutencoes", "intervalo_recompletamento_oleo", "INTEGER DEFAULT 2600")
    adicionar_coluna_se_nao_existir(cursor, "manutencoes", "foto_path", "TEXT")

    # =========================
    # DESPESAS DO VEÍCULO
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS despesas_veiculo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            veiculo_id INTEGER NOT NULL,
            data_despesa TEXT,
            categoria TEXT,
            descricao TEXT,
            valor REAL DEFAULT 0,
            observacoes TEXT,
            FOREIGN KEY (veiculo_id) REFERENCES veiculos(id)
        )
    """)

    adicionar_coluna_se_nao_existir(cursor, "despesas_veiculo", "data_despesa", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "despesas_veiculo", "categoria", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "despesas_veiculo", "descricao", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "despesas_veiculo", "valor", "REAL DEFAULT 0")
    adicionar_coluna_se_nao_existir(cursor, "despesas_veiculo", "observacoes", "TEXT")

    # =========================
    # DOCUMENTOS DO CLIENTE / CONTRATO
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documentos_cliente (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            contrato_id INTEGER,
            tipo_documento TEXT NOT NULL,
            nome_arquivo TEXT,
            caminho_arquivo TEXT NOT NULL,
            observacao TEXT,
            data_upload TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id),
            FOREIGN KEY (contrato_id) REFERENCES contratos(id)
        )
    """)

    adicionar_coluna_se_nao_existir(cursor, "documentos_cliente", "observacao", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "documentos_cliente", "data_upload", "TEXT DEFAULT CURRENT_TIMESTAMP")

    # =========================
    # DOCUMENTOS DO VEÍCULO
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documentos_veiculo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            veiculo_id INTEGER NOT NULL,
            tipo_documento TEXT NOT NULL,
            nome_arquivo TEXT,
            caminho_arquivo TEXT NOT NULL,
            observacao TEXT,
            data_upload TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (veiculo_id) REFERENCES veiculos(id) ON DELETE CASCADE
        )
    """)

    adicionar_coluna_se_nao_existir(cursor, "documentos_veiculo", "observacao", "TEXT")
    adicionar_coluna_se_nao_existir(cursor, "documentos_veiculo", "data_upload", "TEXT DEFAULT CURRENT_TIMESTAMP")

    # =========================
    # ÍNDICES
    # =========================
    criar_indice_se_nao_existir(
        cursor,
        "idx_clientes_cpf",
        "CREATE INDEX idx_clientes_cpf ON clientes(cpf)"
    )

    criar_indice_se_nao_existir(
        cursor,
        "idx_veiculos_placa",
        "CREATE INDEX idx_veiculos_placa ON veiculos(placa)"
    )

    criar_indice_se_nao_existir(
        cursor,
        "idx_contratos_cliente_id",
        "CREATE INDEX idx_contratos_cliente_id ON contratos(cliente_id)"
    )

    criar_indice_se_nao_existir(
        cursor,
        "idx_contratos_veiculo_id",
        "CREATE INDEX idx_contratos_veiculo_id ON contratos(veiculo_id)"
    )

    criar_indice_se_nao_existir(
        cursor,
        "idx_contratos_locador_id",
        "CREATE INDEX idx_contratos_locador_id ON contratos(locador_id)"
    )

    criar_indice_se_nao_existir(
        cursor,
        "idx_contratos_status",
        "CREATE INDEX idx_contratos_status ON contratos(status)"
    )

    criar_indice_se_nao_existir(
        cursor,
        "idx_pagamentos_contrato_id",
        "CREATE INDEX idx_pagamentos_contrato_id ON pagamentos(contrato_id)"
    )

    criar_indice_se_nao_existir(
        cursor,
        "idx_pagamentos_status",
        "CREATE INDEX idx_pagamentos_status ON pagamentos(status)"
    )

    criar_indice_se_nao_existir(
        cursor,
        "idx_pagamentos_data_vencimento",
        "CREATE INDEX idx_pagamentos_data_vencimento ON pagamentos(data_vencimento)"
    )

    criar_indice_se_nao_existir(
        cursor,
        "idx_pagamentos_data_pagamento",
        "CREATE INDEX idx_pagamentos_data_pagamento ON pagamentos(data_pagamento)"
    )

    criar_indice_se_nao_existir(
        cursor,
        "idx_vistorias_veiculo_id",
        "CREATE INDEX idx_vistorias_veiculo_id ON vistorias(veiculo_id)"
    )

    criar_indice_se_nao_existir(
        cursor,
        "idx_vistorias_contrato_id",
        "CREATE INDEX idx_vistorias_contrato_id ON vistorias(contrato_id)"
    )

    criar_indice_se_nao_existir(
        cursor,
        "idx_manutencoes_veiculo_id",
        "CREATE INDEX idx_manutencoes_veiculo_id ON manutencoes(veiculo_id)"
    )

    criar_indice_se_nao_existir(
        cursor,
        "idx_despesas_veiculo_id",
        "CREATE INDEX idx_despesas_veiculo_id ON despesas_veiculo(veiculo_id)"
    )

    criar_indice_se_nao_existir(
        cursor,
        "idx_documentos_cliente_id",
        "CREATE INDEX idx_documentos_cliente_id ON documentos_cliente(cliente_id)"
    )

    criar_indice_se_nao_existir(
        cursor,
        "idx_documentos_contrato_id",
        "CREATE INDEX idx_documentos_contrato_id ON documentos_cliente(contrato_id)"
    )

    criar_indice_se_nao_existir(
        cursor,
        "idx_documentos_tipo",
        "CREATE INDEX idx_documentos_tipo ON documentos_cliente(tipo_documento)"
    )

    criar_indice_se_nao_existir(
        cursor,
        "idx_documentos_veiculo_id",
        "CREATE INDEX idx_documentos_veiculo_id ON documentos_veiculo(veiculo_id)"
    )

    criar_indice_se_nao_existir(
        cursor,
        "idx_documentos_veiculo_tipo",
        "CREATE INDEX idx_documentos_veiculo_tipo ON documentos_veiculo(tipo_documento)"
    )

    # =========================
    # MIGRAÇÃO LEGADA DE LOCADOR ÚNICO -> LOCADORES
    # =========================
    try:
        df_locadores = pd.read_sql_query("SELECT COUNT(*) AS total FROM locadores", conn)
        total_locadores = int(df_locadores.iloc[0]["total"] or 0)
    except Exception:
        total_locadores = 0

    if total_locadores == 0 and tabela_existe(cursor, "locador_config"):
        try:
            df_legado = pd.read_sql_query("SELECT * FROM locador_config WHERE id = 1", conn)
            if not df_legado.empty:
                legado = df_legado.iloc[0].fillna("").to_dict()
                if str(legado.get("nome", "")).strip() or str(legado.get("cpf", "")).strip():
                    cursor.execute("""
                        INSERT INTO locadores (
                            nome, cpf, telefone, estado_civil, profissao, cidade, estado, cep,
                            endereco, numero, complemento, endereco_referencia, observacoes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        legado.get("nome", ""),
                        legado.get("cpf", ""),
                        legado.get("telefone", ""),
                        legado.get("estado_civil", ""),
                        legado.get("profissao", ""),
                        legado.get("cidade", ""),
                        legado.get("estado", ""),
                        legado.get("cep", ""),
                        legado.get("endereco", ""),
                        legado.get("numero", ""),
                        legado.get("complemento", ""),
                        legado.get("endereco_referencia", ""),
                        legado.get("observacoes", ""),
                    ))
        except Exception:
            pass

    try:
        if coluna_existe(cursor, "contratos", "locador_id"):
            df_primeiro_locador = pd.read_sql_query("SELECT id FROM locadores ORDER BY id LIMIT 1", conn)
            if not df_primeiro_locador.empty:
                primeiro_locador_id = int(df_primeiro_locador.iloc[0]["id"])
                cursor.execute(
                    "UPDATE contratos SET locador_id = ? WHERE locador_id IS NULL",
                    (primeiro_locador_id,)
                )
    except Exception:
        pass

    conn.commit()

    # =========================
    # SINCRONIZAÇÃO LEGADA
    # =========================
    sincronizar_contratos_com_pagamentos(conn)

    conn.close()




def registrar_pagamento_conn(
    conn,
    contrato_id,
    valor_previsto,
    data_vencimento=None,
    valor_pago=0.0,
    data_pagamento=None,
    status="Pendente",
    observacao="",
    comprovante_pagamento=""
):
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO pagamentos (
            contrato_id,
            data_vencimento,
            data_pagamento,
            valor_previsto,
            valor_pago,
            status,
            observacao,
            comprovante_pagamento
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        int(contrato_id),
        data_vencimento,
        data_pagamento,
        float(valor_previsto or 0.0),
        float(valor_pago or 0.0),
        status,
        observacao,
        comprovante_pagamento,
    ))

    pagamento_id = cursor.lastrowid
    atualizar_resumo_pagamento_contrato(conn, int(contrato_id))
    return pagamento_id

def registrar_pagamento(
    contrato_id,
    valor_previsto,
    data_vencimento=None,
    valor_pago=0.0,
    data_pagamento=None,
    status="Pendente",
    observacao="",
    comprovante_pagamento=""
):
    conn = conectar()
    try:
        pagamento_id = registrar_pagamento_conn(
            conn=conn,
            contrato_id=contrato_id,
            valor_previsto=valor_previsto,
            data_vencimento=data_vencimento,
            valor_pago=valor_pago,
            data_pagamento=data_pagamento,
            status=status,
            observacao=observacao,
            comprovante_pagamento=comprovante_pagamento,
        )
        conn.commit()
        return pagamento_id
    finally:
        conn.close()


def atualizar_pagamento_registrado(
    pagamento_id,
    data_vencimento=None,
    data_pagamento=None,
    valor_previsto=None,
    valor_pago=None,
    status=None,
    observacao=None,
    comprovante_pagamento=None
):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            contrato_id,
            data_vencimento,
            data_pagamento,
            valor_previsto,
            valor_pago,
            status,
            observacao,
            comprovante_pagamento
        FROM pagamentos
        WHERE id = ?
    """, (pagamento_id,))
    atual = cursor.fetchone()

    if not atual:
        conn.close()
        return False

    contrato_id = atual[0]

    novo_data_vencimento = atual[1] if data_vencimento is None else data_vencimento
    novo_data_pagamento = atual[2] if data_pagamento is None else data_pagamento
    novo_valor_previsto = atual[3] if valor_previsto is None else float(valor_previsto or 0.0)
    novo_valor_pago = atual[4] if valor_pago is None else float(valor_pago or 0.0)
    novo_status = atual[5] if status is None else status
    nova_observacao = atual[6] if observacao is None else observacao
    novo_comprovante = atual[7] if comprovante_pagamento is None else comprovante_pagamento

    cursor.execute("""
        UPDATE pagamentos
        SET
            data_vencimento = ?,
            data_pagamento = ?,
            valor_previsto = ?,
            valor_pago = ?,
            status = ?,
            observacao = ?,
            comprovante_pagamento = ?,
            atualizado_em = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        novo_data_vencimento,
        novo_data_pagamento,
        novo_valor_previsto,
        novo_valor_pago,
        novo_status,
        nova_observacao,
        novo_comprovante,
        pagamento_id
    ))

    conn.commit()
    atualizar_resumo_pagamento_contrato(conn, contrato_id)
    conn.close()
    return True


def excluir_pagamento_registrado(pagamento_id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT contrato_id FROM pagamentos WHERE id = ?", (pagamento_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return False

    contrato_id = int(row[0])

    cursor.execute("DELETE FROM pagamentos WHERE id = ?", (pagamento_id,))
    conn.commit()

    atualizar_resumo_pagamento_contrato(conn, contrato_id)
    conn.close()
    return True




def _gravar_documento_cliente_em_disco(cliente_id, contrato_id, arquivo, tipo_documento):
    nome_original = getattr(arquivo, "name", "documento") or "documento"
    base, extensao = os.path.splitext(nome_original)
    base_limpa = "".join(ch for ch in base if ch.isalnum() or ch in ("-", "_")) or "documento"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    pasta = os.path.join("documentos_clientes", f"cliente_{int(cliente_id)}", f"contrato_{int(contrato_id)}")
    os.makedirs(pasta, exist_ok=True)

    nome_salvo = f"{tipo_documento}_{timestamp}_{base_limpa}{extensao}"
    caminho = os.path.join(pasta, nome_salvo)

    with open(caminho, "wb") as f:
        f.write(arquivo.getbuffer())

    return nome_original, caminho


def salvar_documento_cliente_conn(conn, cliente_id, contrato_id, arquivo, tipo_documento, observacao=""):
    if arquivo is None:
        return None

    nome_original, caminho = _gravar_documento_cliente_em_disco(
        cliente_id=cliente_id,
        contrato_id=contrato_id,
        arquivo=arquivo,
        tipo_documento=tipo_documento,
    )

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO documentos_cliente (
            cliente_id, contrato_id, tipo_documento, nome_arquivo, caminho_arquivo, observacao, data_upload
        ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        int(cliente_id),
        int(contrato_id) if contrato_id is not None else None,
        str(tipo_documento),
        nome_original,
        caminho,
        observacao or "",
    ))
    return caminho

def salvar_documento_cliente(cliente_id, contrato_id, arquivo, tipo_documento, observacao=""):
    if arquivo is None:
        return None

    conn = conectar()
    try:
        caminho = salvar_documento_cliente_conn(
            conn=conn,
            cliente_id=cliente_id,
            contrato_id=contrato_id,
            arquivo=arquivo,
            tipo_documento=tipo_documento,
            observacao=observacao,
        )
        conn.commit()
        return caminho
    finally:
        conn.close()


def obter_documentos_cliente(cliente_id=None, contrato_id=None):
    conn = conectar()
    query = """
        SELECT
            id, cliente_id, contrato_id, tipo_documento, nome_arquivo,
            caminho_arquivo, observacao, data_upload
        FROM documentos_cliente
        WHERE 1 = 1
    """
    params = []

    if cliente_id is not None:
        query += " AND cliente_id = ?"
        params.append(int(cliente_id))

    if contrato_id is not None:
        query += " AND contrato_id = ?"
        params.append(int(contrato_id))

    query += " ORDER BY data_upload DESC, id DESC"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def salvar_documento_veiculo(veiculo_id, arquivo, tipo_documento, observacao=""):
    if arquivo is None:
        return None

    nome_original = getattr(arquivo, "name", "documento") or "documento"
    base, extensao = os.path.splitext(nome_original)
    base_limpa = "".join(ch for ch in base if ch.isalnum() or ch in ("-", "_")) or "documento"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    pasta = os.path.join("documentos_veiculo", f"veiculo_{int(veiculo_id)}")
    os.makedirs(pasta, exist_ok=True)

    nome_salvo = f"{tipo_documento}_{timestamp}_{base_limpa}{extensao}"
    caminho = os.path.join(pasta, nome_salvo)

    with open(caminho, "wb") as f:
        f.write(arquivo.getbuffer())

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO documentos_veiculo (
            veiculo_id, tipo_documento, nome_arquivo, caminho_arquivo, observacao, data_upload
        ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        int(veiculo_id),
        str(tipo_documento),
        nome_original,
        caminho,
        observacao or ""
    ))
    conn.commit()
    conn.close()

    return caminho


def listar_locadores(conn=None):
    fechar = False
    if conn is None:
        conn = conectar()
        fechar = True
    try:
        cursor = conn.cursor()
        if not tabela_existe(cursor, "locadores"):
            return pd.DataFrame(columns=[
                "id", "nome", "cpf", "telefone", "estado_civil", "profissao", "cidade", "estado",
                "cep", "endereco", "numero", "complemento", "endereco_referencia", "observacoes"
            ])
        return pd.read_sql_query("SELECT * FROM locadores ORDER BY nome, id", conn)
    finally:
        if fechar:
            conn.close()


def obter_locador_por_id(conn, locador_id):
    if not locador_id:
        return {}
    cursor = conn.cursor()
    if not tabela_existe(cursor, "locadores"):
        return {}
    df = pd.read_sql_query("SELECT * FROM locadores WHERE id = ?", conn, params=(int(locador_id),))
    if df.empty:
        return {}
    return df.iloc[0].fillna("").to_dict()


def salvar_locador(conn, dados, locador_id=None):
    cursor = conn.cursor()
    payload = {
        "nome": dados.get("nome", ""),
        "cpf": dados.get("cpf", ""),
        "telefone": dados.get("telefone", ""),
        "estado_civil": dados.get("estado_civil", ""),
        "profissao": dados.get("profissao", ""),
        "cidade": dados.get("cidade", ""),
        "estado": dados.get("estado", ""),
        "cep": dados.get("cep", ""),
        "endereco": dados.get("endereco", ""),
        "numero": dados.get("numero", ""),
        "complemento": dados.get("complemento", ""),
        "endereco_referencia": dados.get("endereco_referencia", ""),
        "observacoes": dados.get("observacoes", ""),
    }
    if locador_id:
        cursor.execute("""
            UPDATE locadores
            SET nome = ?, cpf = ?, telefone = ?, estado_civil = ?, profissao = ?, cidade = ?, estado = ?, cep = ?,
                endereco = ?, numero = ?, complemento = ?, endereco_referencia = ?, observacoes = ?,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            payload["nome"], payload["cpf"], payload["telefone"], payload["estado_civil"],
            payload["profissao"], payload["cidade"], payload["estado"], payload["cep"], payload["endereco"], payload["numero"],
            payload["complemento"], payload["endereco_referencia"], payload["observacoes"], int(locador_id)
        ))
        conn.commit()
        return int(locador_id)
    cursor.execute("""
        INSERT INTO locadores (
            nome, cpf, telefone, estado_civil, profissao, cidade, estado, cep,
            endereco, numero, complemento, endereco_referencia, observacoes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        payload["nome"], payload["cpf"], payload["telefone"], payload["estado_civil"], payload["profissao"], payload["cidade"],
        payload["estado"], payload["cep"], payload["endereco"], payload["numero"], payload["complemento"],
        payload["endereco_referencia"], payload["observacoes"]
    ))
    novo_id = int(cursor.lastrowid)
    conn.commit()
    return novo_id


def excluir_locador(conn, locador_id):
    cursor = conn.cursor()
    if coluna_existe(cursor, "contratos", "locador_id"):
        df = pd.read_sql_query(
            "SELECT COUNT(*) AS total FROM contratos WHERE locador_id = ?",
            conn,
            params=(int(locador_id),)
        )
        if int(df.iloc[0]["total"] or 0) > 0:
            return False, "Este locador possui contratos vinculados e não pode ser excluído."
    cursor.execute("DELETE FROM locadores WHERE id = ?", (int(locador_id),))
    conn.commit()
    return True, "Locador excluído com sucesso."


def obter_locador_config(conn=None):
    fechar = False
    if conn is None:
        conn = conectar()
        fechar = True
    try:
        df = listar_locadores(conn)
        if not df.empty:
            return df.iloc[0].fillna("").to_dict()
        cursor = conn.cursor()
        if not tabela_existe(cursor, "locador_config"):
            return {}
        df_legado = pd.read_sql_query("SELECT * FROM locador_config WHERE id = 1", conn)
        if df_legado.empty:
            return {}
        return df_legado.iloc[0].fillna("").to_dict()
    finally:
        if fechar:
            conn.close()


def salvar_locador_config(conn, dados):
    # Compatibilidade: salvar no cadastro múltiplo; se vazio, atualiza/insere também na tabela legada.
    df = listar_locadores(conn)
    if not df.empty:
        primeiro_id = int(df.iloc[0]["id"])
        salvar_locador(conn, dados, primeiro_id)
        return True

    # persistência no legado
    cursor = conn.cursor()
    campos = [
        "nome", "cpf", "telefone", "estado_civil", "profissao", "cidade", "estado", "cep",
        "endereco", "numero", "complemento", "endereco_referencia",
        "prazo_minimo_padrao", "multa_atraso_padrao", "valor_franquia_padrao",
        "hora_limite_padrao", "observacoes"
    ]
    atual = {}
    try:
        atual = obter_locador_config(conn)
    except Exception:
        atual = {}
    payload = {campo: dados.get(campo, atual.get(campo)) for campo in campos}
    payload["prazo_minimo_padrao"] = int(payload.get("prazo_minimo_padrao") or 0)
    payload["multa_atraso_padrao"] = float(payload.get("multa_atraso_padrao") or 0.0)
    payload["valor_franquia_padrao"] = float(payload.get("valor_franquia_padrao") or 0.0)

    cursor.execute("SELECT id FROM locador_config WHERE id = 1")
    existe = cursor.fetchone() is not None
    if existe:
        cursor.execute("""
            UPDATE locador_config
            SET nome = ?, cpf = ?, telefone = ?, estado_civil = ?, profissao = ?, cidade = ?, estado = ?, cep = ?,
                endereco = ?, numero = ?, complemento = ?, endereco_referencia = ?,
                prazo_minimo_padrao = ?, multa_atraso_padrao = ?, valor_franquia_padrao = ?,
                hora_limite_padrao = ?, observacoes = ?, atualizado_em = CURRENT_TIMESTAMP
            WHERE id = 1
        """, (
            payload["nome"], payload["cpf"], payload["telefone"], payload["estado_civil"],
            payload["profissao"], payload["cidade"], payload["estado"], payload["cep"], payload["endereco"], payload["numero"],
            payload["complemento"], payload["endereco_referencia"], payload["prazo_minimo_padrao"],
            payload["multa_atraso_padrao"], payload["valor_franquia_padrao"], payload["hora_limite_padrao"],
            payload["observacoes"]
        ))
    else:
        cursor.execute("""
            INSERT INTO locador_config (
                id, nome, cpf, telefone, estado_civil, profissao, cidade, estado, cep, endereco, numero,
                complemento, endereco_referencia, prazo_minimo_padrao, multa_atraso_padrao,
                valor_franquia_padrao, hora_limite_padrao, observacoes
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload["nome"], payload["cpf"], payload["telefone"], payload["estado_civil"],
            payload["profissao"], payload["cidade"], payload["estado"], payload["cep"], payload["endereco"], payload["numero"],
            payload["complemento"], payload["endereco_referencia"], payload["prazo_minimo_padrao"],
            payload["multa_atraso_padrao"], payload["valor_franquia_padrao"], payload["hora_limite_padrao"],
            payload["observacoes"]
        ))
    conn.commit()

    # espelha em locadores
    salvar_locador(conn, dados)
    return True
