
import os
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    from database import conectar, registrar_log
except ImportError:
    from database import conectar
    registrar_log = None

from utils import (
    buscar_cep,
    formatar_nome,
    formatar_cpf,
    formatar_rg,
    formatar_telefone,
    formatar_cep,
)


def aplicar_estilo_clientes():
    st.markdown("""
    <style>
    .cliente-top-card {
        background: linear-gradient(180deg, #111827 0%, #0f172a 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 18px;
        padding: 18px;
        margin-bottom: 14px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.16);
    }

    .cliente-top-title {
        color: #f8fafc;
        font-size: 1.08rem;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .cliente-top-sub {
        color: #94a3b8;
        font-size: 0.92rem;
        margin-bottom: 0;
    }

    .cliente-section-title {
        font-size: 1rem;
        font-weight: 800;
        margin-top: 0.3rem;
        margin-bottom: 0.8rem;
        color: #e5e7eb;
    }

    .cliente-warning-box {
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.22);
        border-radius: 14px;
        padding: 12px 14px;
        margin-top: 10px;
        margin-bottom: 12px;
        color: #fbbf24;
        font-weight: 600;
    }

    .cliente-doc-box {
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 12px;
        margin-bottom: 10px;
        background: rgba(255,255,255,0.02);
    }
    </style>
    """, unsafe_allow_html=True)


def card_abertura_clientes():
    st.markdown("""
    <div class="cliente-top-card">
        <div class="cliente-top-title">Gestão de clientes</div>
        <div class="cliente-top-sub">
            Cadastre, edite e organize os clientes com dados padronizados, endereço completo e trilha de auditoria.
        </div>
    </div>
    """, unsafe_allow_html=True)


def registrar_log_seguro(usuario, acao, modulo, descricao="", referencia_id=None):
    if not callable(registrar_log):
        return

    try:
        try:
            registrar_log(
                usuario=usuario,
                acao=acao,
                modulo=modulo,
                descricao=descricao,
                referencia_id=referencia_id,
            )
        except TypeError:
            try:
                registrar_log(usuario, acao, modulo, descricao, referencia_id)
            except TypeError:
                registrar_log(usuario, acao, modulo, descricao)
    except Exception:
        pass


def cpf_ja_cadastrado(conn, cpf, cliente_id_atual=None):
    cpf = (cpf or "").strip()

    if not cpf:
        return False

    if cliente_id_atual is None:
        df = pd.read_sql_query(
            "SELECT id FROM clientes WHERE cpf = ?",
            conn,
            params=(cpf,)
        )
    else:
        df = pd.read_sql_query(
            "SELECT id FROM clientes WHERE cpf = ? AND id != ?",
            conn,
            params=(cpf, cliente_id_atual)
        )

    return not df.empty


def carregar_clientes(conn):
    return pd.read_sql_query(
        "SELECT * FROM clientes ORDER BY id DESC",
        conn
    )


def carregar_documentos_cliente(conn, cliente_id):
    try:
        return pd.read_sql_query("""
            SELECT id, cliente_id, contrato_id, tipo_documento, nome_arquivo, caminho_arquivo, observacao, data_upload
            FROM documentos_cliente
            WHERE cliente_id = ?
            ORDER BY id DESC
        """, conn, params=(cliente_id,))
    except Exception:
        return pd.DataFrame(columns=[
            "id", "cliente_id", "contrato_id", "tipo_documento",
            "nome_arquivo", "caminho_arquivo", "observacao", "data_upload"
        ])


def excluir_documento_cliente(conn, documento_id, usuario_logado=""):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, cliente_id, contrato_id, tipo_documento, nome_arquivo, caminho_arquivo
        FROM documentos_cliente
        WHERE id = ?
    """, (documento_id,))
    row = cursor.fetchone()

    if not row:
        return False

    _, cliente_id, contrato_id, tipo_documento, nome_arquivo, caminho_arquivo = row

    if caminho_arquivo and os.path.exists(caminho_arquivo):
        try:
            os.remove(caminho_arquivo)
        except Exception:
            pass

    cursor.execute("DELETE FROM documentos_cliente WHERE id = ?", (documento_id,))
    conn.commit()

    registrar_log_seguro(
        usuario=usuario_logado or st.session_state.get("usuario", ""),
        acao="EXCLUIR_DOCUMENTO_CLIENTE",
        modulo="CLIENTES",
        descricao=(
            f"Documento '{tipo_documento}' removido do cliente ID {cliente_id}"
            f"{' vinculado ao contrato ID ' + str(contrato_id) if contrato_id else ''}"
            f" ({nome_arquivo})."
        ),
        referencia_id=documento_id
    )
    return True


def diagnosticar_vinculos_cliente(conn, cliente_id):
    diagnostico = {}

    try:
        contratos = pd.read_sql_query(
            "SELECT COUNT(*) AS total FROM contratos WHERE cliente_id = ?",
            conn,
            params=(cliente_id,)
        ).iloc[0]["total"]
        diagnostico["contratos"] = int(contratos)
    except Exception:
        diagnostico["contratos"] = 0

    try:
        documentos = pd.read_sql_query(
            "SELECT COUNT(*) AS total FROM documentos_cliente WHERE cliente_id = ?",
            conn,
            params=(cliente_id,)
        ).iloc[0]["total"]
        diagnostico["documentos_cliente"] = int(documentos)
    except Exception:
        diagnostico["documentos_cliente"] = 0

    return diagnostico


def renderizar_documentos_cliente(conn, cliente_id, contexto="padrao"):
    st.markdown("### Documentos do cliente")
    st.caption("Exclua primeiro os documentos vinculados quando precisar liberar a exclusão do cliente.")

    documentos = carregar_documentos_cliente(conn, cliente_id)
    usuario_logado = st.session_state.get("usuario", "")

    if documentos.empty:
        st.info("Este cliente não possui documentos vinculados.")
        return

    for _, doc in documentos.iterrows():
        st.markdown('<div class="cliente-doc-box">', unsafe_allow_html=True)
        c1, c2 = st.columns([4, 1])

        with c1:
            st.write(f"**{doc.get('tipo_documento', '-') or '-'}**")
            st.caption(doc.get("nome_arquivo", "-") or "-")
            if doc.get("contrato_id"):
                st.caption(f"Contrato vinculado: {doc.get('contrato_id')}")
            if doc.get("observacao"):
                st.caption(f"Obs.: {doc.get('observacao')}")
            if doc.get("data_upload"):
                st.caption(f"Upload: {doc.get('data_upload')}")

        with c2:
            caminho = doc.get("caminho_arquivo") or ""
            if caminho and os.path.exists(caminho):
                try:
                    with open(caminho, "rb") as f:
                        st.download_button(
                            "Baixar",
                            data=f.read(),
                            file_name=doc.get("nome_arquivo") or os.path.basename(caminho),
                            mime="application/octet-stream",
                            key=f"baixar_doc_cliente_{contexto}_{cliente_id}_{int(doc['id'])}",
                            use_container_width=True
                        )
                except Exception:
                    st.warning("Arquivo físico indisponível.")
            else:
                st.warning("Arquivo não encontrado.")

            if st.button(
                "Excluir",
                key=f"excluir_doc_cliente_{contexto}_{cliente_id}_{int(doc['id'])}",
                use_container_width=True
            ):
                if excluir_documento_cliente(conn, int(doc["id"]), usuario_logado=usuario_logado):
                    st.success("Documento excluído com sucesso.")
                else:
                    st.error("Não foi possível excluir o documento.")
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)


def tela_clientes():
    aplicar_estilo_clientes()
    st.subheader("Cadastro de Clientes")
    card_abertura_clientes()
    usuario_logado = st.session_state.get("usuario", "")

    tab1, tab2, tab3 = st.tabs(["Cadastrar", "Editar", "Excluir"])

    with tab1:
        st.markdown('<div class="cliente-section-title">Novo cliente</div>', unsafe_allow_html=True)
        st.caption("Preencha os dados abaixo. O sistema padroniza nome, CPF, RG, telefone e CEP.")

        if "cliente_endereco_auto" not in st.session_state:
            st.session_state.cliente_endereco_auto = ""
            st.session_state.cliente_cidade_auto = ""
            st.session_state.cliente_estado_auto = ""

        with st.form("form_cliente"):
            nome = st.text_input("Nome completo")
            cpf = st.text_input("CPF")
            rg = st.text_input("RG")
            telefone = st.text_input("Telefone")

            st.markdown("### Endereço")

            col_cep1, col_cep2 = st.columns([2, 1])
            with col_cep1:
                cep = st.text_input("CEP")
            with col_cep2:
                buscar = st.form_submit_button("Buscar CEP")

            if buscar:
                dados_cep = buscar_cep(cep)
                if dados_cep:
                    st.session_state.cliente_endereco_auto = dados_cep["endereco"]
                    st.session_state.cliente_cidade_auto = dados_cep["cidade"]
                    st.session_state.cliente_estado_auto = dados_cep["estado"]
                    st.success("CEP encontrado com sucesso.")
                else:
                    st.warning("CEP não encontrado.")

            col_end1, col_end2, col_end3 = st.columns([3, 1, 2])
            with col_end1:
                endereco = st.text_input("Endereço", value=st.session_state.cliente_endereco_auto)
            with col_end2:
                numero = st.text_input("Número")
            with col_end3:
                complemento = st.text_input("Complemento")

            cidade = st.text_input("Cidade", value=st.session_state.cliente_cidade_auto)
            estado = st.text_input("Estado", value=st.session_state.cliente_estado_auto)

            salvar = st.form_submit_button("Salvar cliente")

            if salvar:
                nome = formatar_nome(nome)
                cpf = formatar_cpf(cpf)
                rg = formatar_rg(rg)
                telefone = formatar_telefone(telefone)
                cep = formatar_cep(cep)
                cidade = formatar_nome(cidade)
                estado = (estado or "").strip().upper()
                numero = (numero or "").strip()
                complemento = (complemento or "").strip()

                if not nome:
                    st.error("O nome do cliente é obrigatório.")
                else:
                    conn = conectar()

                    if cpf_ja_cadastrado(conn, cpf):
                        conn.close()
                        st.error("Já existe um cliente cadastrado com este CPF.")
                    else:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO clientes (
                                nome, cpf, rg, telefone, endereco, numero, complemento, cidade, estado, cep
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (nome, cpf, rg, telefone, endereco, numero, complemento, cidade, estado, cep))
                        cliente_id = cursor.lastrowid
                        conn.commit()
                        conn.close()

                        registrar_log_seguro(
                            usuario=usuario_logado,
                            acao="CRIAR_CLIENTE",
                            modulo="CLIENTES",
                            descricao=f"Cliente cadastrado: {nome} - CPF {cpf}.",
                            referencia_id=cliente_id
                        )

                        st.session_state.cliente_endereco_auto = ""
                        st.session_state.cliente_cidade_auto = ""
                        st.session_state.cliente_estado_auto = ""

                        st.success("Cliente cadastrado com sucesso.")
                        st.rerun()

    conn = conectar()
    df = carregar_clientes(conn)

    with tab2:
        st.markdown('<div class="cliente-section-title">Editar cliente</div>', unsafe_allow_html=True)

        if df.empty:
            st.info("Nenhum cliente cadastrado ainda.")
        else:
            st.caption("Selecione um cliente para atualizar os dados e visualizar os documentos vinculados.")

            opcoes = {
                f"{row['nome']} - CPF: {row['cpf']}": row["id"]
                for _, row in df.iterrows()
            }

            cliente_escolhido = st.selectbox(
                "Selecione o cliente para editar",
                list(opcoes.keys()),
                key="editar_cliente"
            )
            cliente_id = opcoes[cliente_escolhido]
            cliente = df[df["id"] == cliente_id].iloc[0]

            with st.form("form_editar_cliente"):
                novo_nome = st.text_input("Nome completo", value=cliente["nome"] or "")
                novo_cpf = st.text_input("CPF", value=cliente["cpf"] or "")
                novo_rg = st.text_input("RG", value=cliente["rg"] or "")
                novo_telefone = st.text_input("Telefone", value=cliente["telefone"] or "")

                st.markdown("### Endereço")

                novo_cep = st.text_input("CEP", value=cliente["cep"] or "")
                col_edit1, col_edit2, col_edit3 = st.columns([3, 1, 2])
                with col_edit1:
                    novo_endereco = st.text_input("Endereço", value=cliente["endereco"] or "")
                with col_edit2:
                    novo_numero = st.text_input("Número", value=cliente["numero"] or "")
                with col_edit3:
                    novo_complemento = st.text_input("Complemento", value=cliente["complemento"] or "")

                nova_cidade = st.text_input("Cidade", value=cliente["cidade"] or "")
                novo_estado = st.text_input("Estado", value=cliente["estado"] or "")

                atualizar = st.form_submit_button("Atualizar cliente")

                if atualizar:
                    novo_nome = formatar_nome(novo_nome)
                    novo_cpf = formatar_cpf(novo_cpf)
                    novo_rg = formatar_rg(novo_rg)
                    novo_telefone = formatar_telefone(novo_telefone)
                    novo_cep = formatar_cep(novo_cep)
                    nova_cidade = formatar_nome(nova_cidade)
                    novo_estado = (novo_estado or "").strip().upper()
                    novo_numero = (novo_numero or "").strip()
                    novo_complemento = (novo_complemento or "").strip()

                    if not novo_nome:
                        st.error("O nome do cliente é obrigatório.")
                    elif cpf_ja_cadastrado(conn, novo_cpf, cliente_id_atual=cliente_id):
                        st.error("Já existe outro cliente cadastrado com este CPF.")
                    else:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE clientes
                            SET nome = ?, cpf = ?, rg = ?, telefone = ?,
                                endereco = ?, numero = ?, complemento = ?, cidade = ?, estado = ?, cep = ?
                            WHERE id = ?
                        """, (
                            novo_nome,
                            novo_cpf,
                            novo_rg,
                            novo_telefone,
                            novo_endereco,
                            novo_numero,
                            novo_complemento,
                            nova_cidade,
                            novo_estado,
                            novo_cep,
                            cliente_id
                        ))
                        conn.commit()

                        registrar_log_seguro(
                            usuario=usuario_logado,
                            acao="ATUALIZAR_CLIENTE",
                            modulo="CLIENTES",
                            descricao=f"Cliente atualizado: ID {cliente_id} - {novo_nome} - CPF {novo_cpf}.",
                            referencia_id=cliente_id
                        )

                        st.success("Cliente atualizado com sucesso.")
                        st.rerun()

            st.markdown("### Dados atuais")
            st.dataframe(
                df[df["id"] == cliente_id][[
                    "id", "nome", "cpf", "rg", "telefone",
                    "endereco", "numero", "complemento", "cidade", "estado", "cep"
                ]],
                use_container_width=True
            )

            renderizar_documentos_cliente(conn, cliente_id, contexto="editar")

    with tab3:
        st.markdown('<div class="cliente-section-title">Excluir cliente</div>', unsafe_allow_html=True)

        if df.empty:
            st.info("Nenhum cliente cadastrado ainda.")
        else:
            st.caption("A exclusão deve ser usada com cuidado para evitar perda de histórico.")

            opcoes = {
                f"{row['nome']} - CPF: {row['cpf']}": row["id"]
                for _, row in df.iterrows()
            }

            cliente_excluir = st.selectbox(
                "Selecione o cliente para excluir",
                list(opcoes.keys()),
                key="excluir_cliente"
            )
            cliente_id = opcoes[cliente_excluir]
            cliente = df[df["id"] == cliente_id].iloc[0]

            st.markdown(f"""
            <div class="cliente-warning-box">
                Você está prestes a excluir o cliente <strong>{cliente['nome']}</strong>.
                Revise os vínculos antes de confirmar.
            </div>
            """, unsafe_allow_html=True)

            endereco_exibicao = f"{cliente['endereco'] or '-'}, nº {cliente['numero'] or '-'}"
            if cliente["complemento"]:
                endereco_exibicao += f" - {cliente['complemento']}"

            st.write(f"**Nome:** {cliente['nome']}")
            st.write(f"**CPF:** {cliente['cpf'] or '-'}")
            st.write(f"**Telefone:** {cliente['telefone'] or '-'}")
            st.write(f"**Endereço:** {endereco_exibicao}")
            st.write(f"**Cidade:** {cliente['cidade'] or '-'}")

            vinculos = diagnosticar_vinculos_cliente(conn, cliente_id)

            c1, c2 = st.columns(2)
            c1.metric("Contratos vinculados", vinculos.get("contratos", 0))
            c2.metric("Documentos vinculados", vinculos.get("documentos_cliente", 0))

            if vinculos.get("documentos_cliente", 0) > 0:
                st.info("Este cliente possui documentos vinculados. Exclua os documentos primeiro para liberar a exclusão do cadastro.")
                renderizar_documentos_cliente(conn, cliente_id, contexto="excluir")

            confirmar_exclusao = st.checkbox(
                "Confirmo que desejo excluir este cliente permanentemente.",
                key="confirmar_exclusao_cliente"
            )

            if st.button("Excluir cliente selecionado", type="primary", use_container_width=True):
                if not confirmar_exclusao:
                    st.warning("Confirme a exclusão antes de continuar.")
                else:
                    vinculos_atualizados = diagnosticar_vinculos_cliente(conn, cliente_id)
                    bloqueios = {k: v for k, v in vinculos_atualizados.items() if int(v or 0) > 0}

                    if bloqueios:
                        descricao = ", ".join(f"{k} ({v})" for k, v in bloqueios.items())
                        registrar_log_seguro(
                            usuario=usuario_logado,
                            acao="TENTATIVA_EXCLUIR_CLIENTE_BLOQUEADA",
                            modulo="CLIENTES",
                            descricao=f"Tentativa bloqueada para excluir cliente ID {cliente_id} - {cliente['nome']}. Vínculos: {descricao}.",
                            referencia_id=cliente_id
                        )
                        st.error(
                            f"Este cliente não pode ser excluído porque ainda possui registros vinculados: {descricao}."
                        )
                    else:
                        try:
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
                            conn.commit()

                            registrar_log_seguro(
                                usuario=usuario_logado,
                                acao="EXCLUIR_CLIENTE",
                                modulo="CLIENTES",
                                descricao=f"Cliente excluído: ID {cliente_id} - {cliente['nome']} - CPF {cliente['cpf']}.",
                                referencia_id=cliente_id
                            )

                            st.success("Cliente excluído com sucesso.")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Não foi possível excluir o cliente: {e}")

            st.markdown("### Lista de clientes")
            st.dataframe(
                df[[
                    "id", "nome", "cpf", "telefone", "endereco", "numero", "complemento", "cidade", "estado"
                ]],
                use_container_width=True
            )

    conn.close()
