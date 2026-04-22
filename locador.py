import pandas as pd
import streamlit as st

from database import conectar, listar_locadores, obter_locador_por_id, salvar_locador, excluir_locador
from utils import buscar_cep, formatar_cpf, formatar_cep, formatar_nome, formatar_telefone


def aplicar_estilo_locador():
    st.markdown("""
    <style>
    .locador-top-card {
        background: linear-gradient(180deg, #111827 0%, #0f172a 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 18px;
        padding: 18px;
        margin-bottom: 14px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.16);
    }

    .locador-top-title {
        color: #f8fafc;
        font-size: 1.08rem;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .locador-top-sub {
        color: #94a3b8;
        font-size: 0.92rem;
        margin-bottom: 0;
    }

    .locador-section-title {
        font-size: 1rem;
        font-weight: 800;
        margin-top: 0.3rem;
        margin-bottom: 0.8rem;
        color: #e5e7eb;
    }

    .locador-warning-box {
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.22);
        border-radius: 14px;
        padding: 12px 14px;
        margin-top: 10px;
        margin-bottom: 12px;
        color: #fbbf24;
        font-weight: 600;
    }

    .locador-box {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 14px;
        padding: 12px 14px;
        margin-top: 8px;
        margin-bottom: 12px;
    }
    </style>
    """, unsafe_allow_html=True)


def card_abertura_locador():
    st.markdown("""
    <div class="locador-top-card">
        <div class="locador-top-title">Gestão de locadores</div>
        <div class="locador-top-sub">
            Cadastre, edite e organize os locadores com dados padronizados, endereço completo e fluxo próximo ao módulo de clientes.
        </div>
    </div>
    """, unsafe_allow_html=True)


def _montar_endereco_resumo(dados):
    partes = []
    endereco = str(dados.get("endereco", "") or "").strip()
    numero = str(dados.get("numero", "") or "").strip()
    complemento = str(dados.get("complemento", "") or "").strip()
    referencia = str(dados.get("endereco_referencia", "") or "").strip()

    if endereco:
        partes.append(endereco)
    if numero:
        partes.append(f"nº {numero}")

    base = ", ".join(partes)
    if complemento:
        base = f"{base} - {complemento}" if base else complemento
    if referencia:
        base = f"{base} | Ref.: {referencia}" if base else f"Ref.: {referencia}"

    return base or "-"


def _inicializar_estado_locador(prefixo, dados=None):
    dados = dados or {}
    defaults = {
        f"{prefixo}_cep": dados.get("cep", "") or "",
        f"{prefixo}_endereco": dados.get("endereco", "") or "",
        f"{prefixo}_numero": dados.get("numero", "") or "",
        f"{prefixo}_complemento": dados.get("complemento", "") or "",
        f"{prefixo}_referencia": dados.get("endereco_referencia", "") or "",
        f"{prefixo}_cidade": dados.get("cidade", "") or "",
        f"{prefixo}_estado": dados.get("estado", "") or "",
    }
    for chave, valor in defaults.items():
        if chave not in st.session_state:
            st.session_state[chave] = valor


def _limpar_estado_locador(prefixo):
    for chave in list(st.session_state.keys()):
        if chave.startswith(f"{prefixo}_"):
            del st.session_state[chave]


def _agendar_resultado_cep(prefixo):
    cep = st.session_state.get(f"{prefixo}_cep", "")
    dados_cep = buscar_cep(cep)

    if dados_cep:
        st.session_state[f"{prefixo}_cep_resultado_pendente"] = {
            "endereco": dados_cep.get("endereco", "") or "",
            "cidade": dados_cep.get("cidade", "") or "",
            "estado": (dados_cep.get("estado", "") or "").upper(),
        }
        st.session_state[f"{prefixo}_cep_feedback"] = ("success", "CEP encontrado com sucesso.")
    else:
        st.session_state[f"{prefixo}_cep_resultado_pendente"] = None
        st.session_state[f"{prefixo}_cep_feedback"] = ("warning", "CEP não encontrado.")

    st.rerun()


def _aplicar_resultado_cep_pendente(prefixo):
    resultado = st.session_state.pop(f"{prefixo}_cep_resultado_pendente", None)
    if resultado:
        st.session_state[f"{prefixo}_endereco"] = resultado.get("endereco", "") or ""
        st.session_state[f"{prefixo}_cidade"] = resultado.get("cidade", "") or ""
        st.session_state[f"{prefixo}_estado"] = resultado.get("estado", "") or ""


def _exibir_feedback_cep(prefixo):
    feedback = st.session_state.pop(f"{prefixo}_cep_feedback", None)
    if not feedback:
        return
    tipo, mensagem = feedback
    if tipo == "success":
        st.success(mensagem)
    else:
        st.warning(mensagem)


def _render_form_locador(prefixo, dados=None, texto_botao="Salvar locador", locador_id=None):
    dados = dados or {}
    _inicializar_estado_locador(prefixo, dados)
    _aplicar_resultado_cep_pendente(prefixo)

    nome_padrao = dados.get("nome", "") or ""
    cpf_padrao = dados.get("cpf", "") or ""
    telefone_padrao = dados.get("telefone", "") or ""
    estado_civil_padrao = dados.get("estado_civil", "casado") or "casado"
    profissao_padrao = dados.get("profissao", "") or ""
    observacoes_padrao = dados.get("observacoes", "") or ""

    with st.form(f"form_{prefixo}"):
        nome = st.text_input("Nome do locador", value=nome_padrao, key=f"{prefixo}_nome")
        cpf = st.text_input("CPF", value=cpf_padrao, key=f"{prefixo}_cpf")
        telefone = st.text_input("Telefone", value=telefone_padrao, key=f"{prefixo}_telefone")

        col_dados1, col_dados2 = st.columns(2)
        with col_dados1:
            estado_civil = st.text_input("Estado civil", value=estado_civil_padrao, key=f"{prefixo}_estado_civil")
        with col_dados2:
            profissao = st.text_input("Profissão", value=profissao_padrao, key=f"{prefixo}_profissao")

        observacoes = st.text_area(
            "Observações internas do cadastro",
            value=observacoes_padrao,
            height=120,
            key=f"{prefixo}_observacoes",
        )

        st.markdown("### Endereço")

        col_cep1, col_cep2 = st.columns([2, 1])
        with col_cep1:
            st.text_input("CEP", key=f"{prefixo}_cep")
        with col_cep2:
            buscar = st.form_submit_button("Buscar CEP")

        col_end1, col_end2, col_end3 = st.columns([3, 1, 2])
        with col_end1:
            endereco = st.text_input("Endereço", key=f"{prefixo}_endereco")
        with col_end2:
            numero = st.text_input("Número", key=f"{prefixo}_numero")
        with col_end3:
            complemento = st.text_input("Complemento", key=f"{prefixo}_complemento")

        referencia = st.text_input("Referência", key=f"{prefixo}_referencia")

        col_cidade, col_estado = st.columns([3, 1])
        with col_cidade:
            cidade = st.text_input("Cidade", key=f"{prefixo}_cidade")
        with col_estado:
            estado = st.text_input("Estado", key=f"{prefixo}_estado")

        salvar = st.form_submit_button(texto_botao)

        if buscar:
            _agendar_resultado_cep(prefixo)

        if salvar:
            payload = {
                "nome": formatar_nome(nome),
                "cpf": formatar_cpf(cpf),
                "telefone": formatar_telefone(telefone),
                "estado_civil": (estado_civil or "").strip(),
                "profissao": (profissao or "").strip(),
                "cidade": formatar_nome(cidade),
                "estado": (estado or "").strip().upper(),
                "cep": formatar_cep(st.session_state.get(f"{prefixo}_cep", "")),
                "endereco": (endereco or "").strip(),
                "numero": (numero or "").strip(),
                "complemento": (complemento or "").strip(),
                "endereco_referencia": (referencia or "").strip(),
                "observacoes": (observacoes or "").strip(),
            }

            if not payload["nome"]:
                st.error("O nome do locador é obrigatório.")
                return

            conn = conectar()
            salvar_locador(conn, payload, locador_id=locador_id)
            conn.close()

            _limpar_estado_locador(prefixo)
            if locador_id is not None:
                st.session_state.pop("locador_editando_id", None)

            st.success("Dados do locador salvos com sucesso.")
            st.rerun()


def tela_locador():
    aplicar_estilo_locador()
    st.subheader("Cadastro de Locador")
    card_abertura_locador()

    _exibir_feedback_cep("locador_cadastro")
    editing_id = st.session_state.get("locador_editando_id")
    if editing_id is not None:
        _exibir_feedback_cep(f"locador_editar_{editing_id}")

    conn = conectar()
    df = listar_locadores(conn)
    conn.close()

    tab1, tab2, tab3 = st.tabs(["Cadastrar", "Editar", "Excluir"])

    with tab1:
        st.markdown('<div class="locador-section-title">Novo locador</div>', unsafe_allow_html=True)
        st.caption("Preencha os dados abaixo. O sistema padroniza nome, CPF, telefone e CEP.")
        _render_form_locador("locador_cadastro", {}, "Salvar locador")

        if not df.empty:
            resumo = df.copy()
            if "profissao" not in resumo.columns:
                resumo["profissao"] = ""
            resumo["Cidade/UF"] = resumo.apply(
                lambda row: f"{row.get('cidade', '')}/{row.get('estado', '')}".strip("/"),
                axis=1,
            )
            resumo["Endereço completo"] = resumo.apply(
                lambda row: _montar_endereco_resumo(row.to_dict()),
                axis=1,
            )
            st.dataframe(
                resumo[["id", "nome", "cpf", "telefone", "estado_civil", "profissao", "Cidade/UF", "Endereço completo"]],
                use_container_width=True,
                hide_index=True,
            )

    with tab2:
        st.markdown('<div class="locador-section-title">Editar locador</div>', unsafe_allow_html=True)

        if df.empty:
            st.info("Nenhum locador cadastrado ainda.")
        else:
            st.caption("Selecione um locador para atualizar os dados cadastrais.")

            opcoes = {
                f"{row['nome']} - CPF: {row['cpf']}": int(row["id"])
                for _, row in df.iterrows()
            }

            locador_escolhido = st.selectbox(
                "Selecione o locador para editar",
                list(opcoes.keys()),
                key="editar_locador"
            )
            locador_id = opcoes[locador_escolhido]

            conn = conectar()
            locador_df = listar_locadores(conn)
            conn.close()

            if "profissao" not in locador_df.columns:
                locador_df["profissao"] = ""

            locador = locador_df[locador_df["id"] == locador_id].iloc[0].to_dict()

            prefixo_edicao = f"locador_editar_{locador_id}"
            if st.session_state.get("locador_editando_id") != locador_id:
                _limpar_estado_locador(prefixo_edicao)
                _inicializar_estado_locador(prefixo_edicao, locador)
                st.session_state["locador_editando_id"] = locador_id

            _render_form_locador(prefixo_edicao, locador, "Atualizar locador", locador_id=locador_id)

            st.markdown("### Dados atuais")
            st.dataframe(
                locador_df[locador_df["id"] == locador_id][[
                    "id", "nome", "cpf", "telefone", "estado_civil", "profissao",
                    "endereco", "numero", "complemento", "endereco_referencia",
                    "cidade", "estado", "cep", "observacoes"
                ]],
                use_container_width=True,
                hide_index=True
            )

    with tab3:
        st.markdown('<div class="locador-section-title">Excluir locador</div>', unsafe_allow_html=True)

        if df.empty:
            st.info("Nenhum locador cadastrado ainda.")
        else:
            st.caption("A exclusão deve ser usada com cuidado para evitar perda de histórico.")

            opcoes = {
                f"{row['nome']} - CPF: {row['cpf']}": int(row["id"])
                for _, row in df.iterrows()
            }

            locador_excluir = st.selectbox(
                "Selecione o locador para excluir",
                list(opcoes.keys()),
                key="excluir_locador"
            )
            locador_id = opcoes[locador_excluir]

            conn = conectar()
            dados = obter_locador_por_id(conn, locador_id)
            conn.close()

            st.markdown(f"""
            <div class="locador-warning-box">
                Você está prestes a excluir o locador <strong>{dados.get('nome', '-') or '-'}</strong>.
                Revise os dados antes de confirmar.
            </div>
            """, unsafe_allow_html=True)

            st.write(f"**Nome:** {dados.get('nome', '-') or '-'}")
            st.write(f"**CPF:** {dados.get('cpf', '-') or '-'}")
            st.write(f"**Telefone:** {dados.get('telefone', '-') or '-'}")
            st.write(f"**Estado civil:** {dados.get('estado_civil', '-') or '-'}")
            st.write(f"**Profissão:** {dados.get('profissao', '-') or '-'}")
            st.write(f"**Endereço:** {_montar_endereco_resumo(dados)}")
            st.write(f"**Cidade:** {dados.get('cidade', '-') or '-'}")

            confirmar_exclusao = st.checkbox(
                "Confirmo que desejo excluir este locador permanentemente.",
                key=f"confirmar_exclusao_locador_{locador_id}"
            )

            if st.button("Excluir locador selecionado", type="primary", use_container_width=True):
                if not confirmar_exclusao:
                    st.warning("Confirme a exclusão antes de continuar.")
                else:
                    conn = conectar()
                    ok, msg = excluir_locador(conn, locador_id)
                    conn.close()

                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

            lista_exibicao = df.copy()
            if "profissao" not in lista_exibicao.columns:
                lista_exibicao["profissao"] = ""

            st.markdown("### Lista de locadores")
            st.dataframe(
                lista_exibicao[[
                    "id", "nome", "cpf", "telefone", "estado_civil", "profissao",
                    "endereco", "numero", "complemento", "cidade", "estado"
                ]],
                use_container_width=True,
                hide_index=True
            )
