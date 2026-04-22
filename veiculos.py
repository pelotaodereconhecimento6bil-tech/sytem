import os
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

try:
    from database import conectar, registrar_log
except ImportError:
    from database import conectar
    registrar_log = None

from utils import formatar_placa


PASTA_DOCUMENTOS_VEICULO = Path("documentos_veiculo")
FIPE_API_BASE = "https://fipe.parallelum.com.br/api/v2"
STATUS_VEICULO_OPCOES = ["Disponível", "Alugado", "Reservado", "Em manutenção"]
TIPOS_VEICULO_FIPE = {
    "Carro": "cars",
    "Moto": "motorcycles",
    "Caminhão": "trucks",
}


def aplicar_estilo_veiculos():
    st.markdown("""
    <style>
    .veiculo-top-card {
        background: linear-gradient(180deg, #111827 0%, #0f172a 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 18px;
        padding: 18px;
        margin-bottom: 14px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.16);
    }

    .veiculo-top-title {
        color: #f8fafc;
        font-size: 1.08rem;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .veiculo-top-sub {
        color: #94a3b8;
        font-size: 0.92rem;
        margin-bottom: 0;
    }

    .veiculo-section-title {
        font-size: 1rem;
        font-weight: 800;
        margin-top: 0.3rem;
        margin-bottom: 0.8rem;
        color: #e5e7eb;
    }

    .veiculo-warning-box {
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.22);
        border-radius: 14px;
        padding: 12px 14px;
        margin-top: 10px;
        margin-bottom: 12px;
        color: #fbbf24;
        font-weight: 600;
    }

    .veiculo-doc-box {
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 12px;
        margin-bottom: 10px;
        background: rgba(255,255,255,0.02);
    }
    </style>
    """, unsafe_allow_html=True)


def card_abertura_veiculos():
    st.markdown("""
    <div class="veiculo-top-card">
        <div class="veiculo-top-title">Gestão de veículos</div>
        <div class="veiculo-top-sub">
            Cadastre, edite, organize a frota, mantenha a documentação centralizada e acompanhe base patrimonial com FIPE.
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


def placa_ja_cadastrada(conn, placa, veiculo_id_atual=None):
    placa = formatar_placa(placa)

    if not placa:
        return False

    if veiculo_id_atual is None:
        df = pd.read_sql_query(
            "SELECT id FROM veiculos WHERE placa = ?",
            conn,
            params=(placa,)
        )
    else:
        df = pd.read_sql_query(
            "SELECT id FROM veiculos WHERE placa = ? AND id != ?",
            conn,
            params=(placa, veiculo_id_atual)
        )

    return not df.empty


def carregar_veiculos(conn):
    return pd.read_sql_query(
        "SELECT * FROM veiculos ORDER BY id DESC",
        conn
    )


def normalizar_km_inicial(valor):
    try:
        return max(0, int(float(valor or 0)))
    except Exception:
        return 0


def normalizar_valor_monetario(valor):
    try:
        return round(max(0.0, float(valor or 0.0)), 2)
    except Exception:
        return 0.0


def nome_seguro_arquivo(nome):
    nome = os.path.basename(nome or "arquivo")
    nome = re.sub(r"[^A-Za-z0-9._-]+", "_", nome)
    return nome[:180] or "arquivo"


def normalizar_renavam(valor):
    return re.sub(r"\D", "", str(valor or ""))[:11]


def formatar_renavam(valor):
    numeros = normalizar_renavam(valor)
    if not numeros:
        return ""
    if len(numeros) == 11:
        return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}"
    return numeros


def formatar_moeda_brl(valor):
    try:
        valor = float(valor or 0)
    except Exception:
        valor = 0.0
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def texto_normalizado_comparacao(texto):
    texto = str(texto or "").strip().upper()
    texto = re.sub(r"[^A-Z0-9]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def obter_token_fipe():
    token = st.secrets.get("FIPE_TOKEN", "") if hasattr(st, "secrets") else ""
    return str(token or "").strip()


def requisicao_fipe(caminho, params=None):
    headers = {"accept": "application/json"}
    token = obter_token_fipe()
    if token:
        headers["X-Subscription-Token"] = token

    resposta = requests.get(
        f"{FIPE_API_BASE}{caminho}",
        params=params or {},
        headers=headers,
        timeout=20,
    )
    resposta.raise_for_status()
    return resposta.json()


def inferir_tipo_veiculo_fipe(texto_tipo):
    texto = str(texto_tipo or "Carro").strip()
    return TIPOS_VEICULO_FIPE.get(texto, "cars")


def pontuar_correspondencia_modelo(modelo_digitado, nome_modelo_api):
    alvo = texto_normalizado_comparacao(modelo_digitado)
    candidato = texto_normalizado_comparacao(nome_modelo_api)

    if not alvo or not candidato:
        return 0
    if alvo == candidato:
        return 1000
    if alvo in candidato:
        return 700 + len(alvo)

    tokens_alvo = set(alvo.split())
    tokens_candidato = set(candidato.split())
    intersecao = len(tokens_alvo & tokens_candidato)
    if not intersecao:
        return 0
    return (intersecao * 100) - abs(len(candidato) - len(alvo))


def buscar_valor_fipe_api(tipo_veiculo, marca, modelo, ano_modelo):
    tipo_api = inferir_tipo_veiculo_fipe(tipo_veiculo)
    marca_limpa = texto_normalizado_comparacao(marca)
    modelo_limpo = texto_normalizado_comparacao(modelo)
    ano_limpo = re.sub(r"\D", "", str(ano_modelo or ""))[:4]

    if not marca_limpa or not modelo_limpo or len(ano_limpo) != 4:
        raise ValueError("Para atualizar a FIPE, informe tipo, marca, modelo e ano válidos.")

    referencias = requisicao_fipe("/references")
    referencia = None
    if isinstance(referencias, list) and referencias:
        referencia = referencias[0].get("code")

    params = {"reference": referencia} if referencia else {}

    marcas = requisicao_fipe(f"/{tipo_api}/brands", params=params)
    marca_encontrada = None
    for item in marcas:
        nome_marca = texto_normalizado_comparacao(item.get("name"))
        if marca_limpa == nome_marca or marca_limpa in nome_marca or nome_marca in marca_limpa:
            marca_encontrada = item
            break

    if not marca_encontrada:
        raise ValueError("Marca não encontrada na base FIPE para o tipo selecionado.")

    modelos = requisicao_fipe(f"/{tipo_api}/brands/{marca_encontrada['code']}/models", params=params)
    if not isinstance(modelos, list) or not modelos:
        raise ValueError("Nenhum modelo FIPE encontrado para a marca selecionada.")

    modelo_encontrado = max(
        modelos,
        key=lambda item: pontuar_correspondencia_modelo(modelo_limpo, item.get("name"))
    )

    melhor_score = pontuar_correspondencia_modelo(modelo_limpo, modelo_encontrado.get("name"))
    if melhor_score <= 0:
        raise ValueError("Não foi possível identificar o modelo na FIPE com segurança.")

    anos = requisicao_fipe(
        f"/{tipo_api}/brands/{marca_encontrada['code']}/models/{modelo_encontrado['code']}/years",
        params=params,
    )
    ano_encontrado = None
    for item in anos:
        codigo_ano = str(item.get("code") or "")
        if codigo_ano.startswith(ano_limpo):
            ano_encontrado = item
            break

    if not ano_encontrado:
        raise ValueError("Ano não encontrado na FIPE para o modelo localizado.")

    detalhe = requisicao_fipe(
        f"/{tipo_api}/brands/{marca_encontrada['code']}/models/{modelo_encontrado['code']}/years/{ano_encontrado['code']}",
        params=params,
    )

    valor_texto = str(detalhe.get("price") or "").strip()
    valor_num = re.sub(r"[^0-9,.-]", "", valor_texto).replace(".", "").replace(",", ".")
    try:
        valor_fipe = float(valor_num)
    except Exception:
        raise ValueError("A API retornou um valor FIPE inválido.")

    return {
        "tipo_veiculo_fipe": tipo_veiculo,
        "codigo_fipe": str(detalhe.get("codeFipe") or detalhe.get("code") or ""),
        "valor_fipe": round(valor_fipe, 2),
        "data_referencia_fipe": str(detalhe.get("referenceMonth") or detalhe.get("month") or ""),
        "marca_fipe": str(detalhe.get("brand") or marca_encontrada.get("name") or ""),
        "modelo_fipe": str(detalhe.get("model") or modelo_encontrado.get("name") or ""),
        "ano_fipe": str(detalhe.get("modelYear") or ano_limpo),
        "combustivel_fipe": str(detalhe.get("fuel") or ""),
        "observacao_fipe": (
            f"{modelo_encontrado.get('name', '')} | referência {detalhe.get('referenceMonth', '')}".strip(" |")
        ),
    }


def garantir_pasta_documentos_veiculo(veiculo_id):
    pasta = PASTA_DOCUMENTOS_VEICULO / str(veiculo_id)
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def salvar_upload_documento_veiculo(arquivo, veiculo_id, tipo_documento, observacao="", usuario_logado=""):
    if arquivo is None:
        return None

    pasta = garantir_pasta_documentos_veiculo(veiculo_id)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    nome_original = nome_seguro_arquivo(getattr(arquivo, "name", "arquivo"))
    caminho = pasta / f"{timestamp}_{nome_original}"

    with open(caminho, "wb") as f:
        f.write(arquivo.getbuffer())

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO documentos_veiculo (
            veiculo_id, tipo_documento, nome_arquivo, caminho_arquivo, observacao
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        int(veiculo_id),
        tipo_documento,
        nome_original,
        str(caminho),
        (observacao or "").strip()
    ))
    documento_id = cursor.lastrowid
    conn.commit()
    conn.close()

    registrar_log_seguro(
        usuario=usuario_logado or st.session_state.get("usuario", ""),
        acao="UPLOAD_DOCUMENTO_VEICULO",
        modulo="VEICULOS",
        descricao=f"Documento '{tipo_documento}' enviado para o veículo ID {veiculo_id} ({nome_original}).",
        referencia_id=documento_id
    )

    return str(caminho)


def salvar_multiplos_documentos_veiculo(arquivos, veiculo_id, tipo_documento, observacao="", usuario_logado=""):
    for arquivo in arquivos or []:
        salvar_upload_documento_veiculo(
            arquivo=arquivo,
            veiculo_id=veiculo_id,
            tipo_documento=tipo_documento,
            observacao=observacao,
            usuario_logado=usuario_logado
        )


def carregar_documentos_veiculo(conn, veiculo_id):
    try:
        return pd.read_sql_query("""
            SELECT id, veiculo_id, tipo_documento, nome_arquivo, caminho_arquivo, observacao, data_upload
            FROM documentos_veiculo
            WHERE veiculo_id = ?
            ORDER BY id DESC
        """, conn, params=(veiculo_id,))
    except Exception:
        return pd.DataFrame(columns=[
            "id", "veiculo_id", "tipo_documento", "nome_arquivo",
            "caminho_arquivo", "observacao", "data_upload"
        ])


def excluir_documento_veiculo(conn, documento_id, usuario_logado=""):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, veiculo_id, tipo_documento, nome_arquivo, caminho_arquivo
        FROM documentos_veiculo
        WHERE id = ?
    """, (documento_id,))
    row = cursor.fetchone()

    if not row:
        return False

    _, veiculo_id, tipo_documento, nome_arquivo, caminho_arquivo = row

    if caminho_arquivo:
        caminho = Path(caminho_arquivo)
        if caminho.exists():
            try:
                caminho.unlink()
            except Exception:
                pass
        pasta_pai = caminho.parent
        if pasta_pai.exists():
            try:
                if not any(pasta_pai.iterdir()):
                    pasta_pai.rmdir()
            except Exception:
                pass

    cursor.execute("DELETE FROM documentos_veiculo WHERE id = ?", (documento_id,))
    conn.commit()

    registrar_log_seguro(
        usuario=usuario_logado or st.session_state.get("usuario", ""),
        acao="EXCLUIR_DOCUMENTO_VEICULO",
        modulo="VEICULOS",
        descricao=f"Documento '{tipo_documento}' removido do veículo ID {veiculo_id} ({nome_arquivo}).",
        referencia_id=documento_id
    )
    return True


def veiculo_tem_vinculos(conn, veiculo_id):
    contratos = pd.read_sql_query(
        "SELECT COUNT(*) AS total FROM contratos WHERE veiculo_id = ?",
        conn,
        params=(veiculo_id,)
    ).iloc[0]["total"]

    vistorias = pd.read_sql_query(
        "SELECT COUNT(*) AS total FROM vistorias WHERE veiculo_id = ?",
        conn,
        params=(veiculo_id,)
    ).iloc[0]["total"]

    manutencoes = pd.read_sql_query(
        "SELECT COUNT(*) AS total FROM manutencoes WHERE veiculo_id = ?",
        conn,
        params=(veiculo_id,)
    ).iloc[0]["total"]

    despesas = pd.read_sql_query(
        "SELECT COUNT(*) AS total FROM despesas_veiculo WHERE veiculo_id = ?",
        conn,
        params=(veiculo_id,)
    ).iloc[0]["total"]

    try:
        documentos = pd.read_sql_query(
            "SELECT COUNT(*) AS total FROM documentos_veiculo WHERE veiculo_id = ?",
            conn,
            params=(veiculo_id,)
        ).iloc[0]["total"]
    except Exception:
        documentos = 0

    return {
        "contratos": int(contratos),
        "vistorias": int(vistorias),
        "manutencoes": int(manutencoes),
        "despesas": int(despesas),
        "documentos": int(documentos),
    }


def renderizar_documentos_do_veiculo(conn, veiculo_id):
    st.markdown("### Documentação do veículo")
    st.caption("Centralize ATPV-e, CRLV, seguro e demais arquivos do veículo no mesmo cadastro.")

    docs = carregar_documentos_veiculo(conn, veiculo_id)
    usuario_logado = st.session_state.get("usuario", "")

    if docs.empty:
        st.info("Nenhum documento do veículo foi anexado ainda.")
    else:
        for _, doc in docs.iterrows():
            st.markdown('<div class="veiculo-doc-box">', unsafe_allow_html=True)
            c1, c2 = st.columns([4, 1])

            with c1:
                st.write(f"**{doc.get('tipo_documento', '-') or '-'}**")
                st.caption(doc.get("nome_arquivo", "-") or "-")
                if doc.get("observacao"):
                    st.caption(f"Obs.: {doc.get('observacao')}")
                if doc.get("data_upload"):
                    st.caption(f"Upload: {doc.get('data_upload')}")

            with c2:
                caminho = Path(doc.get("caminho_arquivo") or "")
                if caminho.exists():
                    try:
                        with open(caminho, "rb") as f:
                            st.download_button(
                                "Baixar",
                                data=f.read(),
                                file_name=doc.get("nome_arquivo") or caminho.name,
                                mime="application/octet-stream",
                                key=f"baixar_doc_veiculo_{int(doc['id'])}",
                                use_container_width=True
                            )
                    except Exception:
                        st.warning("Arquivo físico indisponível.")
                else:
                    st.warning("Arquivo não encontrado.")

                if st.button(
                    "Excluir",
                    key=f"excluir_doc_veiculo_{int(doc['id'])}",
                    use_container_width=True
                ):
                    if excluir_documento_veiculo(conn, int(doc["id"]), usuario_logado=usuario_logado):
                        st.success("Documento excluído com sucesso.")
                    else:
                        st.error("Não foi possível excluir o documento.")
                    st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("Adicionar novos documentos", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            novo_atpve = st.file_uploader(
                "ATPV-e",
                type=["pdf", "png", "jpg", "jpeg", "webp"],
                key=f"novo_atpve_{veiculo_id}"
            )
            novo_crlv = st.file_uploader(
                "CRLV / documento do veículo",
                type=["pdf", "png", "jpg", "jpeg", "webp"],
                key=f"novo_crlv_{veiculo_id}"
            )
            nova_apolice = st.file_uploader(
                "Apólice de seguro",
                type=["pdf", "png", "jpg", "jpeg", "webp"],
                key=f"novo_seguro_{veiculo_id}"
            )

        with col2:
            nova_observacao = st.text_area(
                "Observação dos novos arquivos",
                key=f"obs_docs_veiculo_{veiculo_id}",
                placeholder="Ex.: documento renovado, segunda via, frente/verso etc."
            )
            novos_outros = st.file_uploader(
                "Outros documentos",
                type=["pdf", "png", "jpg", "jpeg", "webp", "doc", "docx"],
                accept_multiple_files=True,
                key=f"outros_docs_veiculo_{veiculo_id}"
            )

        if st.button("Salvar novos documentos", key=f"salvar_docs_veiculo_{veiculo_id}", use_container_width=True):
            quantidade = 0

            if novo_atpve is not None:
                salvar_upload_documento_veiculo(novo_atpve, veiculo_id, "ATPV-e", nova_observacao, usuario_logado)
                quantidade += 1
            if novo_crlv is not None:
                salvar_upload_documento_veiculo(novo_crlv, veiculo_id, "CRLV", nova_observacao, usuario_logado)
                quantidade += 1
            if nova_apolice is not None:
                salvar_upload_documento_veiculo(nova_apolice, veiculo_id, "Apólice de seguro", nova_observacao, usuario_logado)
                quantidade += 1
            if novos_outros:
                salvar_multiplos_documentos_veiculo(novos_outros, veiculo_id, "Documento adicional", nova_observacao, usuario_logado)
                quantidade += len(novos_outros)

            if quantidade == 0:
                st.warning("Selecione pelo menos um arquivo para salvar.")
            else:
                st.success(f"{quantidade} documento(s) salvo(s) com sucesso.")
                st.rerun()


def tela_veiculos():
    aplicar_estilo_veiculos()
    st.subheader("Cadastro de Veículos")
    card_abertura_veiculos()

    tab1, tab2, tab3 = st.tabs(["Cadastrar", "Editar", "Excluir"])
    usuario_logado = st.session_state.get("usuario", "")

    with tab1:
        st.markdown('<div class="veiculo-section-title">Novo veículo</div>', unsafe_allow_html=True)
        st.caption("Cadastre a identificação do ativo, a base patrimonial e a documentação inicial da frota.")

        with st.form("form_veiculo"):
            st.markdown("### Identificação")
            col1, col2 = st.columns(2)

            with col1:
                modelo = st.text_input("Modelo")
                marca = st.text_input("Marca")
                ano = st.text_input("Ano")
                placa = st.text_input("Placa")
                renavam = st.text_input("RENAVAM", max_chars=11)

            with col2:
                cor = st.text_input("Cor")
                tipo_veiculo_fipe = st.selectbox("Tipo do veículo (FIPE)", list(TIPOS_VEICULO_FIPE.keys()), index=0)
                status = st.selectbox("Status", STATUS_VEICULO_OPCOES)
                observacoes = st.text_area("Observações gerais")

            st.markdown("### Base patrimonial")
            patr1, patr2 = st.columns(2)
            with patr1:
                valor_aquisicao = st.number_input(
                    "Valor de aquisição (R$)",
                    min_value=0.0,
                    step=100.0,
                    value=0.0,
                    format="%.2f"
                )
                codigo_fipe = st.text_input("Código FIPE (opcional)")
            with patr2:
                valor_fipe = st.number_input(
                    "Valor FIPE atual (R$)",
                    min_value=0.0,
                    step=100.0,
                    value=0.0,
                    format="%.2f"
                )
                data_referencia_fipe = st.text_input("Referência FIPE", placeholder="Ex.: março de 2026")

            st.caption(
                f"Aquisição: {formatar_moeda_brl(valor_aquisicao)} | FIPE: {formatar_moeda_brl(valor_fipe)}"
            )
            st.caption("Se quiser automatizar depois, deixe marca, modelo, ano e tipo preenchidos corretamente. A atualização FIPE via API fica disponível na edição.")

            st.markdown("### Entrada na frota")
            col_frota1, col_frota2 = st.columns(2)
            with col_frota1:
                km_inicial = st.number_input("KM inicial de cadastro", min_value=0, step=1, value=0)
            with col_frota2:
                data_entrada_frota = st.date_input("Data de entrada na frota")

            observacao_entrada = st.text_area(
                "Observação da entrada na frota",
                placeholder="Ex.: veículo comprado com desconto, revisado, único dono, etc."
            )

            st.markdown("### Documentação inicial do veículo (opcional)")
            d1, d2 = st.columns(2)
            with d1:
                arquivo_atpve = st.file_uploader(
                    "ATPV-e",
                    type=["pdf", "png", "jpg", "jpeg", "webp"],
                    key="cadastro_veiculo_atpve"
                )
                arquivo_crlv = st.file_uploader(
                    "CRLV / documento do veículo",
                    type=["pdf", "png", "jpg", "jpeg", "webp"],
                    key="cadastro_veiculo_crlv"
                )
                arquivo_seguro = st.file_uploader(
                    "Apólice de seguro",
                    type=["pdf", "png", "jpg", "jpeg", "webp"],
                    key="cadastro_veiculo_seguro"
                )
            with d2:
                arquivos_outros = st.file_uploader(
                    "Outros documentos",
                    type=["pdf", "png", "jpg", "jpeg", "webp", "doc", "docx"],
                    accept_multiple_files=True,
                    key="cadastro_veiculo_outros"
                )
                observacao_documentos = st.text_area(
                    "Observação dos documentos",
                    placeholder="Ex.: ATPV assinado, CRLV vigente, seguro da frota, segunda via etc."
                )

            salvar = st.form_submit_button("Salvar veículo")

            if salvar:
                modelo = (modelo or "").strip()
                marca = (marca or "").strip()
                ano = re.sub(r"\D", "", str(ano or ""))[:4]
                placa = formatar_placa(placa)
                renavam = normalizar_renavam(renavam)
                cor = (cor or "").strip()
                codigo_fipe = (codigo_fipe or "").strip()
                data_referencia_fipe = (data_referencia_fipe or "").strip()
                km_inicial = normalizar_km_inicial(km_inicial)
                valor_aquisicao = normalizar_valor_monetario(valor_aquisicao)
                valor_fipe = normalizar_valor_monetario(valor_fipe)

                if not modelo:
                    st.error("O modelo do veículo é obrigatório.")
                else:
                    conn = conectar()

                    if placa_ja_cadastrada(conn, placa):
                        conn.close()
                        st.error("Já existe um veículo cadastrado com esta placa.")
                    else:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO veiculos (
                                modelo, marca, ano, placa, cor, status, observacoes,
                                km_inicial, data_entrada_frota, observacao_entrada,
                                renavam, valor_aquisicao, valor_fipe, data_referencia_fipe,
                                codigo_fipe, tipo_veiculo_fipe
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            modelo,
                            marca,
                            ano,
                            placa,
                            cor,
                            status,
                            observacoes,
                            km_inicial,
                            str(data_entrada_frota),
                            observacao_entrada,
                            renavam,
                            valor_aquisicao,
                            valor_fipe,
                            data_referencia_fipe,
                            codigo_fipe,
                            tipo_veiculo_fipe,
                        ))
                        veiculo_id = cursor.lastrowid
                        conn.commit()
                        conn.close()

                        registrar_log_seguro(
                            usuario=usuario_logado,
                            acao="CRIAR_VEICULO",
                            modulo="VEICULOS",
                            descricao=f"Veículo cadastrado: {modelo} - {placa}.",
                            referencia_id=veiculo_id
                        )

                        if arquivo_atpve is not None:
                            salvar_upload_documento_veiculo(arquivo_atpve, veiculo_id, "ATPV-e", observacao_documentos, usuario_logado)
                        if arquivo_crlv is not None:
                            salvar_upload_documento_veiculo(arquivo_crlv, veiculo_id, "CRLV", observacao_documentos, usuario_logado)
                        if arquivo_seguro is not None:
                            salvar_upload_documento_veiculo(arquivo_seguro, veiculo_id, "Apólice de seguro", observacao_documentos, usuario_logado)
                        if arquivos_outros:
                            salvar_multiplos_documentos_veiculo(arquivos_outros, veiculo_id, "Documento adicional", observacao_documentos, usuario_logado)

                        st.success("Veículo cadastrado com sucesso.")
                        st.rerun()

    conn = conectar()
    df = carregar_veiculos(conn)

    with tab2:
        st.markdown('<div class="veiculo-section-title">Editar veículo</div>', unsafe_allow_html=True)

        if df.empty:
            st.info("Nenhum veículo cadastrado ainda.")
        else:
            st.caption("Selecione um veículo para atualizar os dados da frota, a base patrimonial e gerenciar a documentação vinculada.")

            opcoes = {
                f"{row['modelo']} - {row['placa']}": row["id"]
                for _, row in df.iterrows()
            }

            veiculo_escolhido = st.selectbox(
                "Selecione o veículo para editar",
                list(opcoes.keys()),
                key="editar_veiculo"
            )
            veiculo_id = opcoes[veiculo_escolhido]
            veiculo = df[df["id"] == veiculo_id].iloc[0]

            tipo_atual = veiculo.get("tipo_veiculo_fipe", "Carro") or "Carro"
            if tipo_atual not in TIPOS_VEICULO_FIPE:
                tipo_atual = "Carro"

            status_atual = veiculo["status"] if veiculo["status"] in STATUS_VEICULO_OPCOES else "Disponível"

            st.markdown("### Atualização FIPE via API")
            st.caption("A busca usa a API FIPE pública a partir de tipo, marca, modelo e ano do cadastro. Quanto mais limpos estiverem esses campos, melhor a correspondência.")

            if st.button("Atualizar FIPE automaticamente", key=f"atualizar_fipe_{veiculo_id}", use_container_width=True):
                try:
                    retorno_fipe = buscar_valor_fipe_api(
                        tipo_veiculo=tipo_atual,
                        marca=veiculo.get("marca", ""),
                        modelo=veiculo.get("modelo", ""),
                        ano_modelo=veiculo.get("ano", ""),
                    )

                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE veiculos
                        SET valor_fipe = ?,
                            data_referencia_fipe = ?,
                            codigo_fipe = ?,
                            tipo_veiculo_fipe = ?
                        WHERE id = ?
                    """, (
                        normalizar_valor_monetario(retorno_fipe.get("valor_fipe")),
                        retorno_fipe.get("data_referencia_fipe", ""),
                        retorno_fipe.get("codigo_fipe", ""),
                        retorno_fipe.get("tipo_veiculo_fipe", tipo_atual),
                        veiculo_id,
                    ))
                    conn.commit()

                    registrar_log_seguro(
                        usuario=usuario_logado,
                        acao="ATUALIZAR_FIPE_VEICULO",
                        modulo="VEICULOS",
                        descricao=(
                            f"FIPE atualizada para o veículo ID {veiculo_id}: "
                            f"{formatar_moeda_brl(retorno_fipe.get('valor_fipe', 0))} | "
                            f"ref. {retorno_fipe.get('data_referencia_fipe', '-')}."
                        ),
                        referencia_id=veiculo_id,
                    )

                    st.success(
                        f"FIPE atualizada com sucesso: {formatar_moeda_brl(retorno_fipe.get('valor_fipe', 0))} "
                        f"| referência {retorno_fipe.get('data_referencia_fipe', '-')} "
                        f"| código {retorno_fipe.get('codigo_fipe', '-')}."
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Não foi possível atualizar a FIPE automaticamente: {e}")

            with st.form("form_editar_veiculo"):
                st.markdown("### Identificação")
                col1, col2 = st.columns(2)

                with col1:
                    novo_modelo = st.text_input("Modelo", value=veiculo["modelo"] or "")
                    nova_marca = st.text_input("Marca", value=veiculo["marca"] or "")
                    novo_ano = st.text_input("Ano", value=veiculo["ano"] or "")
                    nova_placa = st.text_input("Placa", value=veiculo["placa"] or "")
                    novo_renavam = st.text_input("RENAVAM", value=normalizar_renavam(veiculo.get("renavam", "")), max_chars=11)

                with col2:
                    nova_cor = st.text_input("Cor", value=veiculo["cor"] or "")
                    novo_tipo_veiculo_fipe = st.selectbox(
                        "Tipo do veículo (FIPE)",
                        list(TIPOS_VEICULO_FIPE.keys()),
                        index=list(TIPOS_VEICULO_FIPE.keys()).index(tipo_atual),
                    )
                    novo_status = st.selectbox(
                        "Status",
                        STATUS_VEICULO_OPCOES,
                        index=STATUS_VEICULO_OPCOES.index(status_atual)
                    )
                    novas_observacoes = st.text_area(
                        "Observações gerais",
                        value=veiculo.get("observacoes", "") or ""
                    )

                st.markdown("### Base patrimonial")
                patr1, patr2 = st.columns(2)
                with patr1:
                    novo_valor_aquisicao = st.number_input(
                        "Valor de aquisição (R$)",
                        min_value=0.0,
                        step=100.0,
                        value=normalizar_valor_monetario(veiculo.get("valor_aquisicao", 0.0)),
                        format="%.2f",
                    )
                    novo_codigo_fipe = st.text_input("Código FIPE (opcional)", value=veiculo.get("codigo_fipe", "") or "")
                with patr2:
                    novo_valor_fipe = st.number_input(
                        "Valor FIPE atual (R$)",
                        min_value=0.0,
                        step=100.0,
                        value=normalizar_valor_monetario(veiculo.get("valor_fipe", 0.0)),
                        format="%.2f",
                    )
                    nova_data_referencia_fipe = st.text_input(
                        "Referência FIPE",
                        value=veiculo.get("data_referencia_fipe", "") or ""
                    )

                st.caption(
                    f"Aquisição: {formatar_moeda_brl(novo_valor_aquisicao)} | FIPE: {formatar_moeda_brl(novo_valor_fipe)}"
                )

                st.markdown("### Entrada na frota")
                data_entrada_atual = pd.to_datetime(veiculo.get("data_entrada_frota"), errors="coerce")
                if pd.isna(data_entrada_atual):
                    data_entrada_atual = pd.Timestamp.today()

                col_frota1, col_frota2 = st.columns(2)
                with col_frota1:
                    novo_km_inicial = st.number_input(
                        "KM inicial de cadastro",
                        min_value=0,
                        step=1,
                        value=normalizar_km_inicial(veiculo.get("km_inicial", 0)),
                    )
                with col_frota2:
                    nova_data_entrada_frota = st.date_input(
                        "Data de entrada na frota",
                        value=data_entrada_atual.date(),
                    )

                nova_observacao_entrada = st.text_area(
                    "Observação da entrada na frota",
                    value=veiculo.get("observacao_entrada", "") or ""
                )

                atualizar = st.form_submit_button("Atualizar veículo")

                if atualizar:
                    novo_modelo = (novo_modelo or "").strip()
                    nova_marca = (nova_marca or "").strip()
                    novo_ano = re.sub(r"\D", "", str(novo_ano or ""))[:4]
                    nova_placa = formatar_placa(nova_placa)
                    novo_renavam = normalizar_renavam(novo_renavam)
                    nova_cor = (nova_cor or "").strip()
                    novo_km_inicial = normalizar_km_inicial(novo_km_inicial)
                    novo_valor_aquisicao = normalizar_valor_monetario(novo_valor_aquisicao)
                    novo_valor_fipe = normalizar_valor_monetario(novo_valor_fipe)
                    novo_codigo_fipe = (novo_codigo_fipe or "").strip()
                    nova_data_referencia_fipe = (nova_data_referencia_fipe or "").strip()

                    if not novo_modelo:
                        st.error("O modelo do veículo é obrigatório.")
                    elif placa_ja_cadastrada(conn, nova_placa, veiculo_id_atual=veiculo_id):
                        st.error("Já existe outro veículo cadastrado com esta placa.")
                    else:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE veiculos
                            SET modelo = ?, marca = ?, ano = ?, placa = ?,
                                cor = ?, status = ?, observacoes = ?,
                                km_inicial = ?, data_entrada_frota = ?, observacao_entrada = ?,
                                renavam = ?, valor_aquisicao = ?, valor_fipe = ?,
                                data_referencia_fipe = ?, codigo_fipe = ?, tipo_veiculo_fipe = ?
                            WHERE id = ?
                        """, (
                            novo_modelo,
                            nova_marca,
                            novo_ano,
                            nova_placa,
                            nova_cor,
                            novo_status,
                            novas_observacoes,
                            novo_km_inicial,
                            str(nova_data_entrada_frota),
                            nova_observacao_entrada,
                            novo_renavam,
                            novo_valor_aquisicao,
                            novo_valor_fipe,
                            nova_data_referencia_fipe,
                            novo_codigo_fipe,
                            novo_tipo_veiculo_fipe,
                            veiculo_id,
                        ))
                        conn.commit()

                        registrar_log_seguro(
                            usuario=usuario_logado,
                            acao="ATUALIZAR_VEICULO",
                            modulo="VEICULOS",
                            descricao=f"Veículo atualizado: ID {veiculo_id} - {novo_modelo} - {nova_placa}.",
                            referencia_id=veiculo_id
                        )

                        st.success("Veículo atualizado com sucesso.")
                        st.rerun()

            st.markdown("### Dados atuais")
            df_exibir = df[df["id"] == veiculo_id].copy()
            if "renavam" in df_exibir.columns:
                df_exibir["renavam"] = df_exibir["renavam"].map(formatar_renavam)
            for coluna_monetaria in ["valor_aquisicao", "valor_fipe"]:
                if coluna_monetaria in df_exibir.columns:
                    df_exibir[coluna_monetaria] = df_exibir[coluna_monetaria].map(formatar_moeda_brl)

            colunas_exibir = [
                "id", "modelo", "marca", "ano", "placa", "renavam", "cor", "status",
                "tipo_veiculo_fipe", "codigo_fipe", "valor_aquisicao", "valor_fipe",
                "data_referencia_fipe", "km_inicial", "data_entrada_frota",
                "observacao_entrada", "observacoes"
            ]
            colunas_exibir = [col for col in colunas_exibir if col in df_exibir.columns]

            st.dataframe(
                df_exibir[colunas_exibir],
                use_container_width=True
            )

            renderizar_documentos_do_veiculo(conn, veiculo_id)

    with tab3:
        st.markdown('<div class="veiculo-section-title">Excluir veículo</div>', unsafe_allow_html=True)

        if df.empty:
            st.info("Nenhum veículo cadastrado ainda.")
        else:
            st.caption("A exclusão deve ser usada com cuidado para não comprometer o histórico operacional.")

            opcoes = {
                f"{row['modelo']} - {row['placa']}": row["id"]
                for _, row in df.iterrows()
            }

            veiculo_excluir = st.selectbox(
                "Selecione o veículo para excluir",
                list(opcoes.keys()),
                key="excluir_veiculo"
            )
            veiculo_id = opcoes[veiculo_excluir]
            veiculo = df[df["id"] == veiculo_id].iloc[0]

            st.markdown(f"""
            <div class="veiculo-warning-box">
                Você está prestes a excluir o veículo <strong>{veiculo['modelo']} - {veiculo['placa']}</strong>.
                Revise os vínculos antes de confirmar.
            </div>
            """, unsafe_allow_html=True)

            st.write(f"**Modelo:** {veiculo['modelo']}")
            st.write(f"**Marca:** {veiculo['marca'] or '-'}")
            st.write(f"**Ano:** {veiculo['ano'] or '-'}")
            st.write(f"**Placa:** {veiculo['placa'] or '-'}")
            st.write(f"**RENAVAM:** {formatar_renavam(veiculo.get('renavam', '')) or '-'}")
            st.write(f"**Status atual:** {veiculo['status'] or '-'}")
            st.write(f"**Valor de aquisição:** {formatar_moeda_brl(veiculo.get('valor_aquisicao', 0))}")
            st.write(f"**Valor FIPE:** {formatar_moeda_brl(veiculo.get('valor_fipe', 0))}")

            vinculos = veiculo_tem_vinculos(conn, veiculo_id)

            v1, v2, v3, v4, v5 = st.columns(5)
            v1.metric("Contratos", vinculos["contratos"])
            v2.metric("Vistorias", vinculos["vistorias"])
            v3.metric("Manutenções", vinculos["manutencoes"])
            v4.metric("Despesas", vinculos["despesas"])
            v5.metric("Documentos", vinculos["documentos"])

            confirmar_exclusao = st.checkbox(
                "Confirmo que desejo excluir este veículo permanentemente.",
                key="confirmar_exclusao_veiculo"
            )

            if st.button("Excluir veículo selecionado", type="primary", use_container_width=True):
                if not confirmar_exclusao:
                    st.warning("Confirme a exclusão antes de continuar.")
                elif sum(vinculos.values()) > 0:
                    st.error(
                        "Este veículo possui vínculos no sistema e não pode ser excluído. "
                        "Remova os documentos e demais vínculos antes de tentar novamente."
                    )
                else:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM veiculos WHERE id = ?", (veiculo_id,))
                    conn.commit()

                    registrar_log_seguro(
                        usuario=usuario_logado,
                        acao="EXCLUIR_VEICULO",
                        modulo="VEICULOS",
                        descricao=f"Veículo excluído: ID {veiculo_id} - {veiculo['modelo']} - {veiculo['placa']}.",
                        referencia_id=veiculo_id
                    )

                    st.success("Veículo excluído com sucesso.")
                    st.rerun()

    conn.close()
