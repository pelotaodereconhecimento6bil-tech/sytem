import os
import shutil
import sqlite3
from pathlib import Path

DB_NAME = "banco.db"

TABELAS_PARA_ZERAR = [
    "pagamentos",
    "documentos_cliente",
    "vistorias",
    "manutencoes",
    "despesas_veiculo",
    "contratos",
    "veiculos",
    "clientes",
]

PASTAS_PARA_LIMPAR = [
    "fotos_vistorias",
    "assinaturas_vistorias",
    "relatorios_vistorias",
    "fotos_manutencoes",
    "contratos_gerados",
    "comprovantes_pagamento",
    "documentos_clientes",
]


def tabela_existe(cursor, tabela):
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (tabela,),
    )
    return cursor.fetchone() is not None


def limpar_pasta(caminho):
    pasta = Path(caminho)
    if not pasta.exists():
        return False

    if pasta.is_file():
        pasta.unlink(missing_ok=True)
        return True

    for item in pasta.iterdir():
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)
        else:
            try:
                item.unlink()
            except FileNotFoundError:
                pass
    return True


def zerar_banco():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = OFF")
    cursor = conn.cursor()

    try:
        tabelas_limpas = []

        for tabela in TABELAS_PARA_ZERAR:
            if tabela_existe(cursor, tabela):
                cursor.execute(f"DELETE FROM {tabela}")
                tabelas_limpas.append(tabela)

        if tabela_existe(cursor, "sqlite_sequence"):
            for tabela in tabelas_limpas:
                cursor.execute("DELETE FROM sqlite_sequence WHERE name = ?", (tabela,))

        conn.commit()
        return tabelas_limpas
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()


def main():
    if not os.path.exists(DB_NAME):
        print(f"Banco não encontrado: {DB_NAME}")
        return

    tabelas = zerar_banco()
    print("Banco zerado com sucesso.")

    if tabelas:
        print("Tabelas limpas:")
        for tabela in tabelas:
            print(f"- {tabela}")

    print("\nLimpando arquivos gerados...")
    for pasta in PASTAS_PARA_LIMPAR:
        if limpar_pasta(pasta):
            print(f"- pasta limpa: {pasta}")
        else:
            print(f"- pasta não encontrada: {pasta}")

    print("\nEstrutura preservada. Agora você pode cadastrar os dados corrigidos do zero.")


if __name__ == "__main__":
    main()
