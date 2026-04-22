# BLOCO 3 (operações)

import os
import io
import json
import base64
import hashlib
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
from streamlit_geolocation import streamlit_geolocation
from streamlit_drawable_canvas import st_canvas

from auth import verificar_login
from database import conectar, registrar_log
from relatorio_vistoria import gerar_pdf_vistoria
from utils import obter_ultimo_odometro, buscar_cep

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except Exception:
    pass


BASE_DIR = "fotos_vistorias"
PASTA_ASSINATURAS = "assinaturas_vistorias"
MAX_DIMENSAO_FOTO = 1000
QUALIDADE_FOTO = 72
FORMATOS_IMAGEM_ACEITOS = ["jpg", "jpeg", "png", "webp", "heic", "heif"]


def ler_bytes_upload(arquivo):
    if arquivo is None:
        return b""

    try:
        if hasattr(arquivo, "seek"):
            arquivo.seek(0)
        dados = arquivo.read()
        if hasattr(arquivo, "seek"):
            arquivo.seek(0)
        return dados or b""
    except Exception:
        try:
            if hasattr(arquivo, "seek"):
                arquivo.seek(0)
        except Exception:
            pass
        return b""


def abrir_imagem_upload(arquivo):
    if arquivo is None:
        return None

    dados = ler_bytes_upload(arquivo)
    if not dados:
        return None

    try:
        imagem = Image.open(io.BytesIO(dados))
        imagem.load()
        imagem = ImageOps.exif_transpose(imagem)

        if imagem.mode not in ("RGB", "RGBA"):
            imagem = imagem.convert("RGB")

        return imagem
    except Exception:
        return None


def preparar_imagem_para_salvar(arquivo, info_linhas=None):
    imagem = abrir_imagem_upload(arquivo)
    if imagem is None:
        return None

    imagem = imagem.convert("RGB")
    imagem.thumbnail((MAX_DIMENSAO_FOTO, MAX_DIMENSAO_FOTO))

    if not info_linhas:
        return imagem

    largura, altura = imagem.size
    linha_altura = 26
    padding = 14
    altura_legenda = (len(info_linhas) * linha_altura) + (padding * 2)

    imagem_final = Image.new(
        "RGB",
        (largura, altura + altura_legenda),
        "white"
    )
    imagem_final.paste(imagem, (0, 0))

    draw = ImageDraw.Draw(imagem_final)

    try:
        fonte = ImageFont.truetype("DejaVuSans.ttf", 18)
    except Exception:
        fonte = ImageFont.load_default()

    y_texto = altura + padding
    for linha in info_linhas:
        draw.text((12, y_texto), str(linha), fill="black", font=fonte)
        y_texto += linha_altura

    return imagem_final


def salvar_imagem_vistoria(pasta, nome_base, arquivo, info_linhas=None):
    if arquivo is None:
        return ""

    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, nome_base + ".jpg")

    imagem_final = preparar_imagem_para_salvar(arquivo, info_linhas=info_linhas)
    if imagem_final is None:
        return ""

    imagem_final.save(caminho, "JPEG", quality=QUALIDADE_FOTO, optimize=True)
    return caminho


def normalizar_bool_seguro(valor):
    if isinstance(valor, bool):
        return valor
    if valor is None:
        return False
    if isinstance(valor, (int, float)):
        return valor != 0

    texto = str(valor).strip().lower()
    if texto in {"1", "true", "t", "sim", "s", "yes", "y", "on", "x"}:
        return True
    if texto in {"0", "false", "f", "nao", "não", "n", "no", "off", "", "none", "null"}:
        return False

    return bool(valor)


def obter_caminho_selfie(dados):
    selfie = (dados or {}).get("selfie_motorista", "")
    selfie_autorizada = normalizar_bool_seguro((dados or {}).get("selfie_autorizada", False))
    selfie_caminho = selfie.get("foto", "") if isinstance(selfie, dict) else selfie
    selfie_caminho = str(selfie_caminho or "").strip()

    if not selfie_autorizada or not selfie_caminho:
        return "", selfie_autorizada

    return selfie_caminho, selfie_autorizada


def aplicar_css_mobile_vistoria():
    st.markdown("""
    <style>
    [data-testid="stFileUploaderDropzone"] small {
        display: none;
    }

    [data-testid="stFileUploaderDropzone"] div div div div p {
        font-size: 0;
    }

    [data-testid="stFileUploaderDropzone"] div div div div p::after {
        content: "Toque para enviar";
        font-size: 14px;
        color: #475569;
        font-weight: 600;
    }

    .vistoria-card {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid rgba(15,23,42,0.08);
        border-radius: 18px;
        padding: 16px;
        margin-bottom: 14px;
        box-shadow: 0 10px 25px rgba(15,23,42,0.05);
    }

    .vistoria-step {
        font-size: 1rem;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 0.65rem;
    }

    .vistoria-sub {
        font-size: 0.9rem;
        color: #64748b;
        margin-bottom: 0.3rem;
    }

    .mini-note {
        color: #64748b;
        font-size: 0.86rem;
    }

    .check-section {
        background: linear-gradient(180deg, rgba(15,23,42,0.96) 0%, rgba(2,6,23,0.98) 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
        padding: 12px 12px 8px 12px;
        margin-top: 8px;
        margin-bottom: 12px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.16);
    }

    .check-section-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        margin-bottom: 8px;
    }

    .check-section-title {
        color: #f8fafc;
        font-size: 0.98rem;
        font-weight: 800;
        line-height: 1.2;
    }

    .check-section-count {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 34px;
        height: 26px;
        padding: 0 8px;
        border-radius: 999px;
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.08);
        color: #cbd5e1;
        font-size: 0.78rem;
        font-weight: 800;
    }

    .check-card-compact {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid rgba(15,23,42,0.07);
        border-radius: 12px;
        padding: 10px 12px;
        margin-bottom: 8px;
        box-shadow: 0 4px 12px rgba(15,23,42,0.05);
        min-height: 54px;
    }

    .check-card-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
    }

    .check-card-title {
        color: #0f172a;
        font-size: 0.90rem;
        font-weight: 700;
        line-height: 1.2;
    }

    .check-card-sub {
        color: #64748b;
        font-size: 0.76rem;
        margin-top: 4px;
        line-height: 1.2;
    }

    .check-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 4px 8px;
        border-radius: 999px;
        font-size: 0.74rem;
        font-weight: 800;
        white-space: nowrap;
        flex-shrink: 0;
    }

    .check-badge-ok {
        background: rgba(34,197,94,0.12);
        border: 1px solid rgba(34,197,94,0.22);
        color: #166534;
    }

    .check-badge-nc {
        background: rgba(239,68,68,0.12);
        border: 1px solid rgba(239,68,68,0.22);
        color: #991b1b;
    }

    .hist-smart-card {
        background: linear-gradient(180deg, rgba(15,23,42,0.96) 0%, rgba(2,6,23,0.98) 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
        padding: 12px 14px;
        margin-top: 8px;
        margin-bottom: 12px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.16);
    }

    .hist-smart-title {
        color: #f8fafc;
        font-size: 0.96rem;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .hist-smart-sub {
        color: #cbd5e1;
        font-size: 0.84rem;
        line-height: 1.35;
        margin-bottom: 0;
    }

    .save-box {
        background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 18px;
        padding: 16px;
        margin-top: 8px;
        margin-bottom: 12px;
    }

    .save-title {
        color: #f8fafc;
        font-size: 1rem;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .save-sub {
        color: #cbd5e1;
        font-size: 0.92rem;
        margin-bottom: 0;
    }

    .geo-actions-wrap {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        margin-top: 8px;
        margin-bottom: 10px;
    }

    .geo-status-hint {
        font-size: 0.88rem;
        color: #64748b;
        margin-top: 4px;
    }

    .pdf-actions-card {
        background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 18px;
        padding: 14px;
        margin-top: 10px;
        margin-bottom: 10px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.14);
    }

    .pdf-actions-title {
        color: #f8fafc;
        font-size: 0.98rem;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .pdf-actions-sub {
        color: #cbd5e1;
        font-size: 0.90rem;
        margin-bottom: 0;
    }

    .save-feedback-ok {
        background: rgba(34, 197, 94, 0.10);
        border: 1px solid rgba(34, 197, 94, 0.24);
        color: #166534;
        border-radius: 14px;
        padding: 12px 14px;
        margin-top: 8px;
        margin-bottom: 12px;
        font-weight: 700;
    }

    .stButton > button {
        border-radius: 14px;
        font-weight: 700;
        min-height: 46px;
    }

    .stDownloadButton > button {
        border-radius: 14px;
        font-weight: 700;
        min-height: 46px;
        border: 1px solid rgba(37,99,235,0.22);
        box-shadow: 0 6px 16px rgba(37,99,235,0.10);
    }

    div[data-testid="stButton"] button[kind="primary"] {
        border: 1px solid rgba(37,99,235,0.30);
        box-shadow: 0 8px 18px rgba(37,99,235,0.16);
    }

    @media (max-width: 900px) {
        .check-card-compact {
            min-height: 50px;
            padding: 9px 10px;
        }

        .check-card-title {
            font-size: 0.86rem;
        }

        .check-badge {
            font-size: 0.70rem;
            padding: 4px 7px;
        }
    }
    </style>
    """, unsafe_allow_html=True)


def obter_endereco_por_coordenadas(latitude, longitude):
    if latitude is None or longitude is None:
        return ""

    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "lat": latitude,
                "lon": longitude,
                "format": "jsonv2",
                "addressdetails": 1,
            },
            headers={"User-Agent": "locadora-system-vistoria"},
            timeout=10,
        )
        response.raise_for_status()
        dados = response.json()
        return dados.get("display_name", "")
    except Exception:
        return ""


def buscar_contrato_ativo_do_veiculo(conn, veiculo_id):
    query = """
        SELECT
            contratos.id AS contrato_id,
            clientes.nome AS cliente_nome,
            clientes.cpf AS cliente_cpf
        FROM contratos
        INNER JOIN clientes ON clientes.id = contratos.cliente_id
        WHERE contratos.veiculo_id = ?
          AND contratos.status = 'Ativo'
        ORDER BY contratos.id DESC
        LIMIT 1
    """
    df = pd.read_sql_query(query, conn, params=(veiculo_id,))

    if df.empty:
        return None, "Sem contrato ativo", ""

    return (
        int(df.iloc[0]["contrato_id"]),
        df.iloc[0]["cliente_nome"],
        df.iloc[0]["cliente_cpf"] or ""
    )


def gerar_hash_vistoria(dados_hash):
    conteudo = json.dumps(dados_hash, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


def quebrar_texto(texto, limite=58):
    if not texto:
        return []

    palavras = texto.split()
    linhas = []
    atual = ""

    for palavra in palavras:
        teste = f"{atual} {palavra}".strip()
        if len(teste) <= limite:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = palavra

    if atual:
        linhas.append(atual)

    return linhas


def montar_info_legenda(endereco, latitude, longitude, data_hora_real, origem="gps"):
    linhas = []

    if endereco:
        linhas.extend(quebrar_texto(f"Local: {endereco}", limite=58))
    else:
        linhas.append("Local: não capturado")

    if origem == "gps" and latitude is not None and longitude is not None:
        linhas.append(f"Lat: {latitude:.5f} | Lon: {longitude:.5f}")
    else:
        linhas.append("Origem: local informado manualmente")

    linhas.append(f"Data/Hora: {data_hora_real}")
    return linhas


def salvar_assinatura(canvas_result, pasta, nome_base):
    if canvas_result is None or canvas_result.image_data is None:
        return ""

    image_data = canvas_result.image_data
    if image_data is None:
        return ""

    if image_data[:, :, 3].max() == 0:
        return ""

    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, f"{nome_base}.png")

    img = Image.fromarray((image_data[:, :, :4]).astype("uint8"), mode="RGBA")
    fundo_branco = Image.new("RGBA", img.size, "WHITE")
    fundo_branco.alpha_composite(img)
    fundo_branco.convert("RGB").save(caminho, "PNG")

    return caminho


def mostrar_preview_pdf(caminho_pdf):
    if not caminho_pdf or not os.path.exists(caminho_pdf):
        return

    st.markdown("### Pré-visualização")
    with open(caminho_pdf, "rb") as f:
        pdf_bytes = f.read()

    st.markdown("""
    <div class="pdf-actions-card">
        <div class="pdf-actions-title">Arquivo da vistoria pronto</div>
        <div class="pdf-actions-sub">
            Baixe o PDF abaixo e, se quiser, use a pré-visualização compacta em seguida.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.download_button(
        "⬇️ Baixar PDF",
        data=pdf_bytes,
        file_name=os.path.basename(caminho_pdf),
        mime="application/pdf",
        use_container_width=True,
        key=f"baixar_pdf_final_{os.path.basename(caminho_pdf)}"
    )

    base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
    pdf_display = f"""
        <iframe
            src="data:application/pdf;base64,{base64_pdf}"
            width="100%"
            height="560"
            style="border: 1px solid #dbe4ee; border-radius: 14px; background: white;"
        ></iframe>
    """
    st.components.v1.html(pdf_display, height=585, scrolling=True)


def inicializar_estado_geo():
    if "geo_latitude" not in st.session_state:
        st.session_state.geo_latitude = None
    if "geo_longitude" not in st.session_state:
        st.session_state.geo_longitude = None
    if "geo_endereco" not in st.session_state:
        st.session_state.geo_endereco = ""
    if "geo_capturada" not in st.session_state:
        st.session_state.geo_capturada = False
    if "geo_manual_cep" not in st.session_state:
        st.session_state.geo_manual_cep = ""
    if "geo_manual_endereco" not in st.session_state:
        st.session_state.geo_manual_endereco = ""
    if "geo_manual_numero" not in st.session_state:
        st.session_state.geo_manual_numero = ""
    if "geo_manual_complemento" not in st.session_state:
        st.session_state.geo_manual_complemento = ""
    if "geo_manual_cidade" not in st.session_state:
        st.session_state.geo_manual_cidade = ""
    if "geo_manual_estado" not in st.session_state:
        st.session_state.geo_manual_estado = ""
    if "ultimo_pdf_vistoria" not in st.session_state:
        st.session_state.ultimo_pdf_vistoria = None
    if "ultima_vistoria_salva" not in st.session_state:
        st.session_state.ultima_vistoria_salva = False
    if "assinatura_canvas_key" not in st.session_state:
        st.session_state.assinatura_canvas_key = 0
    if "assinatura_vistoriador_canvas_key" not in st.session_state:
        st.session_state.assinatura_vistoriador_canvas_key = 0


def montar_endereco_manual_vistoria(endereco_base="", numero="", complemento="", cidade="", estado=""):
    partes = []

    endereco_base = str(endereco_base or "").strip()
    numero = str(numero or "").strip()
    complemento = str(complemento or "").strip()
    cidade = str(cidade or "").strip()
    estado = str(estado or "").strip()

    if endereco_base:
        partes.append(f"{endereco_base}, nº {numero}" if numero else endereco_base)

    if complemento:
        partes.append(complemento)

    cidade_estado = " - ".join([p for p in [cidade, estado] if p])
    if cidade_estado:
        partes.append(cidade_estado)

    return ", ".join([p for p in partes if p]).strip()


def limpar_local_manual_vistoria():
    st.session_state["_resetar_geo_manual"] = True


def limpar_assinatura_cliente():
    st.session_state.assinatura_canvas_key += 1


def limpar_assinatura_vistoriador():
    st.session_state.assinatura_vistoriador_canvas_key += 1


def limpar_todas_assinaturas():
    limpar_assinatura_cliente()
    limpar_assinatura_vistoriador()


def processar_geolocalizacao(location):
    inicializar_estado_geo()

    if (
        location
        and location.get("latitude") is not None
        and location.get("longitude") is not None
    ):
        nova_lat = float(location["latitude"])
        nova_lon = float(location["longitude"])

        mudou = (
            st.session_state.geo_latitude != nova_lat
            or st.session_state.geo_longitude != nova_lon
        )

        st.session_state.geo_latitude = nova_lat
        st.session_state.geo_longitude = nova_lon
        st.session_state.geo_capturada = True

        if mudou or not st.session_state.geo_endereco:
            st.session_state.geo_endereco = obter_endereco_por_coordenadas(
                nova_lat,
                nova_lon
            )


def exibir_card_status_local(latitude, longitude, endereco):
    if latitude is not None and longitude is not None:
        st.success("📍 Local capturado via GPS")
        st.markdown('<div class="geo-status-hint">Toque em "Ver local" para conferir as informações completas.</div>', unsafe_allow_html=True)
        with st.expander("Ver local"):
            st.write(f"Latitude: {latitude:.6f}")
            st.write(f"Longitude: {longitude:.6f}")
            st.write(f"Endereço: {endereco or 'Endereço não encontrado'}")
    else:
        if endereco:
            st.info("📍 Local informado manualmente")
            st.markdown(f'<div class="geo-status-hint">{endereco}</div>', unsafe_allow_html=True)
        else:
            st.warning("📍 Local não capturado")
            st.markdown('<div class="geo-status-hint">Use o botão abaixo para tentar novamente ou preencha o endereço manualmente.</div>', unsafe_allow_html=True)


def preview_upload(label, arquivo):
    st.caption(label)
    if arquivo is not None:
        try:
            imagem = abrir_imagem_upload(arquivo)
            if imagem is not None:
                st.image(imagem, width=120)
            else:
                st.success("Arquivo selecionado")
        except Exception:
            st.success("Arquivo selecionado")
    else:
        st.caption("Nenhum arquivo enviado")


def card_abertura(titulo, subtitulo=""):
    st.markdown(
        f"""
        <div class="vistoria-card">
            <div class="vistoria-step">{titulo}</div>
            <div class="vistoria-sub">{subtitulo}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def obter_placa_do_label(veiculo_nome):
    partes = str(veiculo_nome).split(" - ")
    if len(partes) >= 2:
        return partes[-1].strip().upper().replace(" ", "")
    return "SEMPLACA"


def montar_checklist_dict(
    lataria_nc,
    retrovisores_nc,
    vidros_nc,
    limpadores_parabrisa_nc,
    limpador_traseiro_nc,
    pneus_nc,
    rodas_nc,
    placas_nc,
    farois_nc,
    setas_nc,
    lanternas_nc,
    luz_placa_nc,
    farol_milha_nc,
    luz_re_nc,
    luz_freio_nc,
    nivel_oleo_nc,
    nivel_agua_nc,
    agua_limpador_nc,
    fluido_freio_nc,
    buzina_nc,
    alertas_painel_nc,
    pisca_alerta_nc,
    vidros_eletricos_nc,
    retrovisor_interno_nc,
    freio_mao_nc,
    radio_nc,
    multimidia_nc,
    estofamento_nc,
    tapetes_nc,
    cintos_seguranca_nc,
    forro_interno_nc,
    extintor_nc,
    documento_veicular_nc,
    ar_condicionado_nc,
    carpete_nc,
    estepe_nc,
    macaco_nc,
    triangulo_nc,
    chave_roda_nc,
    limpeza_externa_nc,
    limpeza_interna_nc,
):
    return {
        "Estrutura externa": {
            "itens": {
                "Lataria": bool(lataria_nc),
                "Retrovisores": bool(retrovisores_nc),
                "Vidros": bool(vidros_nc),
                "Limpadores de para-brisa": bool(limpadores_parabrisa_nc),
                "Limpador traseiro": bool(limpador_traseiro_nc),
                "Pneus": bool(pneus_nc),
                "Rodas": bool(rodas_nc),
                "Placas": bool(placas_nc),
            },
            "observacao": "",
        },
        "Iluminação": {
            "itens": {
                "Faróis": bool(farois_nc),
                "Setas": bool(setas_nc),
                "Lanternas": bool(lanternas_nc),
                "Luz de placa": bool(luz_placa_nc),
                "Farol de milha": bool(farol_milha_nc),
                "Luz de ré": bool(luz_re_nc),
                "Luz de freio": bool(luz_freio_nc),
            },
            "observacao": "",
        },
        "Motor": {
            "itens": {
                "Nível do óleo": bool(nivel_oleo_nc),
                "Nível da água": bool(nivel_agua_nc),
                "Água do limpador": bool(agua_limpador_nc),
                "Nível do fluido de freio": bool(fluido_freio_nc),
                "Buzina": bool(buzina_nc),
            },
            "observacao": "",
        },
        "Parte interna": {
            "itens": {
                "Alertas no painel": bool(alertas_painel_nc),
                "Pisca-alerta": bool(pisca_alerta_nc),
                "Vidros elétricos": bool(vidros_eletricos_nc),
                "Retrovisor interno": bool(retrovisor_interno_nc),
                "Freio de mão": bool(freio_mao_nc),
                "Rádio": bool(radio_nc),
                "Multimídia": bool(multimidia_nc),
                "Estofamento": bool(estofamento_nc),
                "Tapetes": bool(tapetes_nc),
                "Cintos de segurança": bool(cintos_seguranca_nc),
                "Forro interno": bool(forro_interno_nc),
                "Extintor": bool(extintor_nc),
                "Documento veicular": bool(documento_veicular_nc),
                "Ar-condicionado": bool(ar_condicionado_nc),
            },
            "observacao": "",
        },
        "Porta-malas": {
            "itens": {
                "Carpete": bool(carpete_nc),
                "Estepe": bool(estepe_nc),
                "Macaco": bool(macaco_nc),
                "Triângulo": bool(triangulo_nc),
                "Chave de roda": bool(chave_roda_nc),
            },
            "observacao": "",
        },
        "Limpeza": {
            "itens": {
                "Limpeza externa": bool(limpeza_externa_nc),
                "Limpeza interna": bool(limpeza_interna_nc),
            },
            "observacao": "",
        },
    }


def checklist_esta_setorizado(checklist):
    if not isinstance(checklist, dict) or not checklist:
        return False

    primeiro_valor = next(iter(checklist.values()))
    return isinstance(primeiro_valor, dict) and "itens" in primeiro_valor


def normalizar_checklist_setorizado(checklist):
    if not isinstance(checklist, dict) or not checklist:
        return {}

    if checklist_esta_setorizado(checklist):
        normalizado = {}
        for setor, dados_setor in checklist.items():
            itens = (dados_setor or {}).get("itens", {}) or {}
            observacao = (dados_setor or {}).get("observacao", "") or ""
            normalizado[str(setor)] = {
                "itens": {str(item): normalizar_bool_seguro(valor) for item, valor in itens.items()},
                "observacao": str(observacao).strip(),
            }
        return normalizado

    return {
        "Checklist geral": {
            "itens": {str(item): normalizar_bool_seguro(valor) for item, valor in checklist.items()},
            "observacao": "",
        }
    }


def exibir_checklist_visual(checklist):
    checklist_setorizado = normalizar_checklist_setorizado(checklist)

    if not checklist_setorizado:
        st.info("Checklist não registrado.")
        return

    setores = list(checklist_setorizado.items())
    colunas_setores = st.columns(2)

    for idx_setor, (setor, dados_setor) in enumerate(setores):
        itens = (dados_setor or {}).get("itens", {}) or {}
        total_itens = len(itens)
        total_nao_conformes = sum(1 for valor in itens.values() if normalizar_bool_seguro(valor))

        with colunas_setores[idx_setor % 2]:
            st.markdown(
                f"""
                <div class="check-section">
                    <div class="check-section-head">
                        <div class="check-section-title">{setor}</div>
                        <div class="check-section-count">{total_nao_conformes}/{total_itens}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            cols_itens = st.columns(2)

            for idx_item, (nome, valor) in enumerate(itens.items()):
                nao_conforme = normalizar_bool_seguro(valor)
                classe_badge = "check-badge-nc" if nao_conforme else "check-badge-ok"
                badge = "Não conforme" if nao_conforme else "OK"
                detalhe = "Item com pendência registrada." if nao_conforme else "Item conferido sem apontamentos."

                with cols_itens[idx_item % 2]:
                    st.markdown(
                        f"""
                        <div class="check-card-compact">
                            <div class="check-card-top">
                                <div class="check-card-title">{nome}</div>
                                <div class="check-badge {classe_badge}">{badge}</div>
                            </div>
                            <div class="check-card-sub">{detalhe}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )


def obter_vistoria_anterior_mesmo_veiculo(df, vistoria_id, veiculo_id):
    try:
        vistoria_id = int(vistoria_id)
        veiculo_id = int(veiculo_id)
    except Exception:
        return None

    base = df.copy()
    if base.empty:
        return None

    if "id" not in base.columns or "veiculo_id" not in base.columns:
        return None

    try:
        base["id"] = pd.to_numeric(base["id"], errors="coerce")
        base["veiculo_id"] = pd.to_numeric(base["veiculo_id"], errors="coerce")
    except Exception:
        return None

    anteriores = base[(base["veiculo_id"] == veiculo_id) & (base["id"] < vistoria_id)].copy()
    if anteriores.empty:
        return None

    anteriores = anteriores.sort_values("id", ascending=False)
    return anteriores.iloc[0]


def resumir_nao_conformes(checklist):
    checklist_setorizado = normalizar_checklist_setorizado(checklist)
    itens = []

    for setor, dados_setor in checklist_setorizado.items():
        for item, valor in ((dados_setor or {}).get("itens", {}) or {}).items():
            if bool(valor):
                itens.append(f"{setor} • {item}")

    return itens


def comparar_checklists(atual, anterior):
    atual_norm = normalizar_checklist_setorizado(atual)
    anterior_norm = normalizar_checklist_setorizado(anterior)
    mudancas = []

    setores = list(dict.fromkeys(list(anterior_norm.keys()) + list(atual_norm.keys())))

    for setor in setores:
        itens_atuais = (atual_norm.get(setor, {}) or {}).get("itens", {}) or {}
        itens_anteriores = (anterior_norm.get(setor, {}) or {}).get("itens", {}) or {}

        itens = list(dict.fromkeys(list(itens_anteriores.keys()) + list(itens_atuais.keys())))

        for item in itens:
            valor_anterior = bool(itens_anteriores.get(item, False))
            valor_atual = bool(itens_atuais.get(item, False))

            if valor_anterior != valor_atual:
                mudancas.append({
                    "setor": setor,
                    "item": item,
                    "antes": valor_anterior,
                    "agora": valor_atual,
                })

    return mudancas


def exibir_historico_inteligente(df, registro, dados):
    st.markdown("### Histórico inteligente")
    st.markdown(
        """
        <div class="hist-smart-card">
            <div class="hist-smart-title">Comparação operacional</div>
            <div class="hist-smart-sub">
                Resumo enxuto da vistoria atual contra a vistoria anterior do mesmo veículo, com foco em mudanças e itens não conformes.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    vistoria_anterior = obter_vistoria_anterior_mesmo_veiculo(
        df=df,
        vistoria_id=registro.get("id"),
        veiculo_id=registro.get("veiculo_id"),
    )

    if vistoria_anterior is None:
        st.info("Esta é a primeira vistoria registrada para este veículo. Ainda não existe base anterior para comparação.")
        return

    dados_anteriores = carregar_dados_vistoria_fotos(vistoria_anterior.to_dict())
    checklist_atual = dados.get("checklist", {})
    checklist_anterior = dados_anteriores.get("checklist", {})

    mudancas = comparar_checklists(checklist_atual, checklist_anterior)
    nao_conformes_atuais = resumir_nao_conformes(checklist_atual)
    nao_conformes_anteriores = resumir_nao_conformes(checklist_anterior)

    col_hist_1, col_hist_2, col_hist_3 = st.columns(3)
    with col_hist_1:
        st.metric("Itens alterados", len(mudancas))
    with col_hist_2:
        st.metric("Não conformes atuais", len(nao_conformes_atuais))
    with col_hist_3:
        st.metric("Não conformes na anterior", len(nao_conformes_anteriores))

    st.caption(
        f"Comparação com a vistoria #{int(vistoria_anterior['id'])} de {vistoria_anterior.get('data_vistoria', '-')}."
    )

    km_anterior = pd.to_numeric(pd.Series([vistoria_anterior.get("odometro")]), errors="coerce").fillna(0).iloc[0]
    km_atual = pd.to_numeric(pd.Series([registro.get("odometro")]), errors="coerce").fillna(0).iloc[0]
    diferenca_km = max(0, int(km_atual - km_anterior))
    st.caption(f"KM desde a vistoria anterior: {diferenca_km} km")

    if not mudancas:
        st.success("Nenhuma mudança no checklist em relação à vistoria anterior.")
    else:
        st.markdown("#### Mudanças desde a última vistoria")
        for mudanca in mudancas:
            status_agora = "Não conforme" if mudanca["agora"] else "OK"
            status_antes = "Não conforme" if mudanca["antes"] else "OK"
            icone = "🔴" if mudanca["agora"] else "🟢"
            st.markdown(
                f"{icone} **{mudanca['setor']} • {mudanca['item']}** → {status_agora} _(antes: {status_antes})_"
            )

    st.markdown("#### Itens não conformes atuais")
    if nao_conformes_atuais:
        for item in nao_conformes_atuais:
            st.markdown(f"- {item}")
    else:
        st.success("Nenhum item não conforme na vistoria atual.")



def localizar_pdf_vistoria(vistoria_id, placa=None, data_vistoria=None):
    pasta_pdf = "relatorios_vistorias"
    if not os.path.exists(pasta_pdf):
        return ""

    if placa and data_vistoria:
        try:
            data_formatada = str(data_vistoria)[:10]
            nome_novo = f"VISTORIA_{str(placa).upper()}_{data_formatada}_{int(vistoria_id):04d}.pdf"
            caminho_novo = os.path.join(pasta_pdf, nome_novo)
            if os.path.exists(caminho_novo):
                return caminho_novo
        except Exception:
            pass

    for arquivo in os.listdir(pasta_pdf):
        if arquivo.lower().endswith(".pdf") and (
            f"_{vistoria_id}.pdf" in arquivo or
            arquivo.endswith(f"_{int(vistoria_id):04d}.pdf")
        ):
            return os.path.join(pasta_pdf, arquivo)

    return ""


def regerar_pdf_vistoria_historico(registro_dict, dados):
    pasta_pdf = "relatorios_vistorias"
    os.makedirs(pasta_pdf, exist_ok=True)

    placa = str(registro_dict.get("placa", "SEMPLACA")).upper()
    data_vistoria = str(registro_dict.get("data_vistoria", ""))[:10]
    vistoria_id = int(registro_dict.get("id"))

    nome_pdf = f"VISTORIA_{placa}_{data_vistoria}_{vistoria_id:04d}.pdf"
    caminho_pdf = os.path.join(pasta_pdf, nome_pdf)

    registro_pdf = {
        "id": registro_dict.get("id"),
        "veiculo": registro_dict.get("veiculo"),
        "placa": registro_dict.get("placa"),
        "contrato_id": registro_dict.get("contrato_id"),
        "cliente_contrato": registro_dict.get("cliente_contrato"),
        "cliente_cpf": registro_dict.get("cliente_cpf"),
        "vistoriador": registro_dict.get("vistoriador"),
        "tipo_oleo": (dados or {}).get("tipo_oleo", ""),
        "data_vistoria": registro_dict.get("data_vistoria"),
        "odometro": registro_dict.get("odometro"),
        "observacoes": registro_dict.get("observacoes"),
        "latitude": registro_dict.get("latitude"),
        "longitude": registro_dict.get("longitude"),
        "endereco": registro_dict.get("endereco"),
        "data_hora_real": registro_dict.get("data_hora_real"),
        "hash_vistoria": registro_dict.get("hash_vistoria"),
    }

    gerar_pdf_vistoria(registro_pdf, dados, caminho_pdf)
    return caminho_pdf




def remover_arquivo_seguro(caminho):
    try:
        if caminho and os.path.exists(caminho):
            os.remove(caminho)
            return True
    except Exception:
        return False
    return False


def limpar_pastas_vazias_subindo(caminho_inicial, limite=None):
    if not caminho_inicial:
        return

    try:
        atual = os.path.abspath(caminho_inicial)
        limite_abs = os.path.abspath(limite) if limite else None

        while os.path.isdir(atual):
            if os.listdir(atual):
                break
            os.rmdir(atual)
            pai = os.path.dirname(atual)
            if not pai or pai == atual:
                break
            if limite_abs and os.path.abspath(pai).startswith(limite_abs) is False:
                break
            atual = pai
    except Exception:
        pass


def coletar_arquivos_vistoria(registro, dados):
    arquivos = set()

    principais = (dados or {}).get("principais", {}) or {}
    for caminho in principais.values():
        if caminho:
            arquivos.add(str(caminho))

    for item in ((dados or {}).get("observacoes_fotos", []) or []):
        caminho = (item or {}).get("foto", "")
        if caminho:
            arquivos.add(str(caminho))

    selfie, selfie_autorizada = obter_caminho_selfie(dados)
    if selfie_autorizada and selfie:
        arquivos.add(str(selfie))

    for chave in ["assinatura_cliente", "assinatura_vistoriador"]:
        caminho = (dados or {}).get(chave, "")
        if caminho:
            arquivos.add(str(caminho))
        caminho_registro = registro.get(chave, "") if isinstance(registro, dict) else ""
        if caminho_registro:
            arquivos.add(str(caminho_registro))

    caminho_pdf = registro.get("pdf_path", "") if isinstance(registro, dict) else ""
    if caminho_pdf:
        arquivos.add(str(caminho_pdf))
    else:
        pdf_localizado = localizar_pdf_vistoria(
            vistoria_id=registro.get("id"),
            placa=registro.get("placa"),
            data_vistoria=registro.get("data_vistoria")
        )
        if pdf_localizado:
            arquivos.add(str(pdf_localizado))

    return sorted(a for a in arquivos if a)




def carregar_dados_vistoria_fotos(registro):
    dados = {
        "principais": {},
        "observacoes_fotos": [],
        "selfie_motorista": "",
        "selfie_autorizada": False,
        "assinatura_cliente": "",
        "assinatura_vistoriador": "",
        "checklist": {},
        "tipo_oleo": ""
    }

    foto_path = registro.get("foto_path", "") if isinstance(registro, dict) else ""
    if foto_path:
        try:
            dados_lidos = json.loads(foto_path)
            if isinstance(dados_lidos, dict):
                dados.update(dados_lidos)
        except Exception:
            pass

    return dados


def exibir_galeria_principais_duas_colunas(principais):
    itens = [
        (nome, caminho)
        for nome, caminho in (principais or {}).items()
        if caminho and os.path.exists(caminho)
    ]

    if not itens:
        st.info("Nenhuma foto principal.")
        return

    colunas = st.columns(2)
    for indice, (nome, caminho) in enumerate(itens):
        with colunas[indice % 2]:
            st.image(caminho, caption=nome.replace("_", " ").title(), use_container_width=True)


def exibir_galeria_extras_duas_colunas(observacoes_fotos):
    itens = []
    for i, item in enumerate(observacoes_fotos or [], start=1):
        caminho = (item or {}).get("foto", "")
        descricao = (item or {}).get("descricao", "")
        if caminho and os.path.exists(caminho):
            itens.append((i, caminho, descricao))

    if not itens:
        st.info("Nenhuma foto extra.")
        return

    colunas = st.columns(2)
    for indice, (numero, caminho, descricao) in enumerate(itens):
        with colunas[indice % 2]:
            st.markdown(f"**Foto extra {numero}**")
            st.caption(descricao or "Sem descrição.")
            st.image(caminho, use_container_width=True)


def renderizar_aba_excluir_vistorias(conn, df):
    st.markdown("""
    <div class="vistoria-card">
        <div class="vistoria-step">Excluir vistoria</div>
        <div class="vistoria-sub">Use esta área para remover registros incorretos sem depender da rolagem do histórico.</div>
    </div>
    """, unsafe_allow_html=True)

    if df.empty:
        st.info("Nenhuma vistoria cadastrada para excluir.")
        return

    opcoes_excluir = {
        f"Vistoria #{int(row['id'])} - {row['veiculo']} - {row['data_vistoria']}": int(row["id"])
        for _, row in df.iterrows()
    }

    escolha_exclusao = st.selectbox(
        "Selecione a vistoria para excluir",
        list(opcoes_excluir.keys()),
        key="aba_excluir_vistoria_select"
    )
    vistoria_id = opcoes_excluir[escolha_exclusao]
    registro = df[df["id"] == vistoria_id].iloc[0]
    registro_dict = registro.to_dict()
    dados = carregar_dados_vistoria_fotos(registro_dict)

    st.markdown(f"""
    <div class="vistoria-card">
        <div class="vistoria-step">Confirmação de exclusão</div>
        <div class="vistoria-sub">Você está prestes a excluir a vistoria <strong>#{int(registro['id'])}</strong> do veículo <strong>{registro['veiculo']}</strong>.</div>
    </div>
    """, unsafe_allow_html=True)

    st.write(f"**Cliente:** {registro['cliente_contrato'] or 'Sem contrato ativo'}")
    st.write(f"**Vistoriador:** {registro['vistoriador'] or '-'}")
    st.write(f"**Data:** {registro['data_vistoria']}")
    st.write(f"**KM:** {registro['odometro']}")

    confirmar_exclusao = st.checkbox(
        "Confirmo que desejo excluir esta vistoria permanentemente",
        key=f"confirmar_excluir_vistoria_{vistoria_id}"
    )

    col_exc1, col_exc2 = st.columns(2)
    with col_exc1:
        usuario_confirmacao = st.text_input(
            "Usuário para confirmação",
            value=st.session_state.get("usuario", ""),
            key=f"usuario_excluir_vistoria_{vistoria_id}"
        )
    with col_exc2:
        senha_confirmacao = st.text_input(
            "Senha",
            type="password",
            key=f"senha_excluir_vistoria_{vistoria_id}"
        )

    if st.button("🗑️ Excluir vistoria selecionada", type="primary", use_container_width=True, key=f"botao_excluir_vistoria_{vistoria_id}"):
        usuario_logado = st.session_state.get("usuario", "")

        if not confirmar_exclusao:
            st.error("Marque a confirmação antes de excluir a vistoria.")
        elif not usuario_logado:
            st.error("Sessão inválida. Faça login novamente.")
        elif usuario_confirmacao != usuario_logado:
            st.error("Informe o mesmo usuário que está logado no sistema.")
        elif not verificar_login(usuario_confirmacao, senha_confirmacao):
            st.error("Senha incorreta.")
        else:
            try:
                excluir_vistoria_com_auditoria(conn, registro_dict, dados, usuario_logado)
                st.success("Vistoria excluída com sucesso.")
                st.rerun()
            except Exception as e:
                conn.rollback()
                st.error(f"Erro ao excluir vistoria: {e}")

def excluir_vistoria_com_auditoria(conn, registro, dados, usuario_logado):
    cursor = conn.cursor()
    vistoria_id = int(registro["id"])
    arquivos = coletar_arquivos_vistoria(registro, dados)

    cursor.execute("DELETE FROM vistorias WHERE id = ?", (vistoria_id,))

    descricao = (
        f"Vistoria ID {vistoria_id} excluída | "
        f"veículo={registro.get('veiculo', '-') } | "
        f"placa={registro.get('placa', '-') } | "
        f"cliente={registro.get('cliente_contrato', '-') }"
    )
    registrar_log(
        conn,
        usuario=usuario_logado or "sistema",
        acao="EXCLUIR_VISTORIA",
        modulo="VISTORIAS",
        referencia_id=vistoria_id,
        descricao=descricao,
    )
    conn.commit()

    for caminho in arquivos:
        remover_arquivo_seguro(caminho)
        pasta = os.path.dirname(caminho)
        if pasta:
            limite = BASE_DIR if os.path.abspath(pasta).startswith(os.path.abspath(BASE_DIR)) else None
            limpar_pastas_vazias_subindo(pasta, limite=limite)

    return True

def tela_vistorias():
    aplicar_css_mobile_vistoria()
    st.subheader("Vistorias")

    conn = conectar()

    veiculos = pd.read_sql_query(
        "SELECT id, modelo, placa FROM veiculos ORDER BY modelo",
        conn
    )

    if veiculos.empty:
        st.info("Cadastre veículos antes de registrar vistorias.")
        conn.close()
        return

    df = pd.read_sql_query("""
        SELECT
            v.id,
            v.veiculo_id,
            v.contrato_id,
            v.cliente_contrato,
            c.cpf AS cliente_cpf,
            v.vistoriador,
            v.hash_vistoria,
            ve.modelo || ' - ' || ve.placa AS veiculo,
            ve.placa AS placa,
            v.data_vistoria,
            v.odometro,
            v.observacoes,
            v.foto_path,
            v.latitude,
            v.longitude,
            v.endereco,
            v.data_hora_real,
            v.assinatura_cliente,
            v.assinatura_vistoriador,
            v.pdf_path
        FROM vistorias v
        INNER JOIN veiculos ve ON v.veiculo_id = ve.id
        LEFT JOIN contratos ct ON v.contrato_id = ct.id
        LEFT JOIN clientes c ON ct.cliente_id = c.id
        ORDER BY v.id DESC
    """, conn)

    tab1, tab2, tab3 = st.tabs(["Nova vistoria", "Histórico", "Excluir vistoria"])

    with tab1:
        inicializar_estado_geo()

        if st.session_state.get("_resetar_geo_manual", False):
            for chave in [
                "geo_manual_cep",
                "geo_manual_endereco",
                "geo_manual_numero",
                "geo_manual_complemento",
                "geo_manual_cidade",
                "geo_manual_estado",
            ]:
                if chave in st.session_state:
                    del st.session_state[chave]

            st.session_state["_resetar_geo_manual"] = False
            st.rerun()

        if st.session_state.ultima_vistoria_salva:
            st.toast("✅ Vistoria salva com sucesso.", icon="✅")
            st.markdown("""
            <div class="save-feedback-ok">
                ✅ Vistoria salva com sucesso. O PDF foi gerado e está disponível para download logo abaixo.
            </div>
            """, unsafe_allow_html=True)
            st.session_state.ultima_vistoria_salva = False

        card_abertura(
            "Nova vistoria",
            "Fluxo otimizado para uso no celular, com fotos, localização, checklist e assinaturas."
        )

        st.markdown("### 1. Veículo")
        opcoes = {
            f"{row['modelo']} - {row['placa']}": row["id"]
            for _, row in veiculos.iterrows()
        }

        veiculo_nome = st.selectbox(
            "Selecione o veículo",
            list(opcoes.keys()),
            key="veiculo_vistoria_select"
        )
        veiculo_id = opcoes[veiculo_nome]
        placa_veiculo = obter_placa_do_label(veiculo_nome)

        contrato_id, cliente_contrato, cliente_cpf = buscar_contrato_ativo_do_veiculo(conn, veiculo_id)
        ultimo_odometro = obter_ultimo_odometro(conn, veiculo_id)

        if cliente_contrato and cliente_contrato != "Sem contrato ativo":
            st.info(f"👤 Cliente: {cliente_contrato}")
            if cliente_cpf:
                st.caption(f"CPF: {cliente_cpf}")
        else:
            st.warning("Sem contrato ativo para este veículo.")

        st.info(f"Último odômetro registrado: {ultimo_odometro} km")

        if contrato_id:
            st.caption("O painel visual completo de quilometragem está disponível na aba Odômetro.")
        else:
            st.caption("Sem contrato ativo. O painel visual completo pode ser consultado na aba Odômetro.")

        st.markdown("### 2. Localização")
        st.caption("Ative o GPS do celular para capturar o local.")

        location = streamlit_geolocation()
        processar_geolocalizacao(location)

        latitude = st.session_state.geo_latitude
        longitude = st.session_state.geo_longitude
        endereco = st.session_state.geo_endereco

        exibir_card_status_local(latitude, longitude, endereco)

        if latitude is None or longitude is None:
            st.markdown("#### Informar local manualmente")
            st.caption("Se o GPS falhar, informe o CEP para preencher o endereço e usar esse local na legenda das fotos.")

            col_cep1, col_cep2 = st.columns([2, 1])
            with col_cep1:
                cep_manual = st.text_input("CEP", key="geo_manual_cep")
            with col_cep2:
                st.write("")
                st.write("")
                buscar_cep_manual = st.button("Buscar CEP", use_container_width=True, key="buscar_cep_manual_vistoria")

            if buscar_cep_manual:
                dados_cep = buscar_cep(cep_manual)
                if dados_cep:
                    st.session_state.geo_manual_endereco = dados_cep.get("endereco", "")
                    st.session_state.geo_manual_cidade = dados_cep.get("cidade", "")
                    st.session_state.geo_manual_estado = dados_cep.get("estado", "")
                    st.success("Endereço manual preenchido com sucesso.")
                else:
                    st.warning("CEP não encontrado.")

            col_man1, col_man2, col_man3 = st.columns([3, 1, 2])
            with col_man1:
                st.text_input("Endereço", key="geo_manual_endereco")
            with col_man2:
                st.text_input("Número", key="geo_manual_numero")
            with col_man3:
                st.text_input("Complemento", key="geo_manual_complemento")

            col_man4, col_man5 = st.columns(2)
            with col_man4:
                st.text_input("Cidade", key="geo_manual_cidade")
            with col_man5:
                st.text_input("Estado", key="geo_manual_estado")

            endereco_manual_preview = montar_endereco_manual_vistoria(
                endereco_base=st.session_state.get("geo_manual_endereco", ""),
                numero=st.session_state.get("geo_manual_numero", ""),
                complemento=st.session_state.get("geo_manual_complemento", ""),
                cidade=st.session_state.get("geo_manual_cidade", ""),
                estado=st.session_state.get("geo_manual_estado", ""),
            )
            if endereco_manual_preview:
                st.caption(f"Local manual que será usado nas imagens: {endereco_manual_preview}")

        st.markdown('<div class="geo-actions-wrap"></div>', unsafe_allow_html=True)
        col_geo1, col_geo2 = st.columns(2)
        with col_geo1:
            if st.button("📍 Capturar localização", use_container_width=True, type="primary"):
                st.rerun()

        with col_geo2:
            if st.button("🗑️ Limpar localização", use_container_width=True):
                st.session_state.geo_latitude = None
                st.session_state.geo_longitude = None
                st.session_state.geo_endereco = ""
                st.session_state.geo_capturada = False
                limpar_local_manual_vistoria()
                st.rerun()

        st.markdown("### 3. Dados da vistoria")
        vistoriador = st.text_input("Vistoriador")
        tipo_oleo = st.text_input("Tipo do óleo")
        data_vistoria = st.date_input("Data")
        odometro = st.number_input(
            "KM",
            min_value=0,
            step=1,
            value=int(ultimo_odometro)
        )
        observacoes = st.text_area("Observações")

        diferenca_km = max(0, int(odometro) - int(ultimo_odometro))
        if ultimo_odometro > 0:
            st.caption(f"Rodado desde a última vistoria: {diferenca_km} km")

        if int(odometro) < int(ultimo_odometro):
            st.error("O KM informado não pode ser menor que o último odômetro registrado.")
        st.markdown("### 4. Checklist rápido")
        st.caption("Marque apenas os itens com problema ou fora de conformidade. O que ficar desmarcado será registrado como OK.")

        st.markdown("#### Estrutura externa")
        col_ext_1, col_ext_2 = st.columns(2)
        with col_ext_1:
            lataria_nc = st.checkbox("Lataria", value=False)
            retrovisores_nc = st.checkbox("Retrovisores", value=False)
            vidros_nc = st.checkbox("Vidros", value=False)
            limpadores_parabrisa_nc = st.checkbox("Limpadores de para-brisa", value=False)
        with col_ext_2:
            limpador_traseiro_nc = st.checkbox("Limpador traseiro", value=False)
            pneus_nc = st.checkbox("Pneus", value=False)
            rodas_nc = st.checkbox("Rodas", value=False)
            placas_nc = st.checkbox("Placas", value=False)

        st.markdown("#### Iluminação")
        col_ilum_1, col_ilum_2 = st.columns(2)
        with col_ilum_1:
            farois_nc = st.checkbox("Faróis", value=False)
            setas_nc = st.checkbox("Setas", value=False)
            lanternas_nc = st.checkbox("Lanternas", value=False)
            luz_placa_nc = st.checkbox("Luz de placa", value=False)
        with col_ilum_2:
            farol_milha_nc = st.checkbox("Farol de milha", value=False)
            luz_re_nc = st.checkbox("Luz de ré", value=False)
            luz_freio_nc = st.checkbox("Luz de freio", value=False)

        st.markdown("#### Motor")
        col_motor_1, col_motor_2 = st.columns(2)
        with col_motor_1:
            nivel_oleo_nc = st.checkbox("Nível do óleo", value=False)
            nivel_agua_nc = st.checkbox("Nível da água", value=False)
            agua_limpador_nc = st.checkbox("Água do limpador", value=False)
        with col_motor_2:
            fluido_freio_nc = st.checkbox("Nível do fluido de freio", value=False)
            buzina_nc = st.checkbox("Buzina", value=False)

        st.markdown("#### Parte interna")
        col_int_1, col_int_2 = st.columns(2)
        with col_int_1:
            alertas_painel_nc = st.checkbox("Alertas no painel", value=False)
            pisca_alerta_nc = st.checkbox("Pisca-alerta", value=False)
            vidros_eletricos_nc = st.checkbox("Vidros elétricos", value=False)
            retrovisor_interno_nc = st.checkbox("Retrovisor interno", value=False)
            freio_mao_nc = st.checkbox("Freio de mão", value=False)
            radio_nc = st.checkbox("Rádio", value=False)
            multimidia_nc = st.checkbox("Multimídia", value=False)
        with col_int_2:
            estofamento_nc = st.checkbox("Estofamento", value=False)
            tapetes_nc = st.checkbox("Tapetes", value=False)
            cintos_seguranca_nc = st.checkbox("Cintos de segurança", value=False)
            forro_interno_nc = st.checkbox("Forro interno", value=False)
            extintor_nc = st.checkbox("Extintor", value=False)
            documento_veicular_nc = st.checkbox("Documento veicular", value=False)
            ar_condicionado_nc = st.checkbox("Ar-condicionado", value=False)

        st.markdown("#### Porta-malas")
        col_pm_1, col_pm_2 = st.columns(2)
        with col_pm_1:
            carpete_nc = st.checkbox("Carpete", value=False)
            estepe_nc = st.checkbox("Estepe", value=False)
            macaco_nc = st.checkbox("Macaco", value=False)
        with col_pm_2:
            triangulo_nc = st.checkbox("Triângulo", value=False)
            chave_roda_nc = st.checkbox("Chave de roda", value=False)

        st.markdown("#### Limpeza")
        col_limpeza_1, col_limpeza_2 = st.columns(2)
        with col_limpeza_1:
            limpeza_externa_nc = st.checkbox("Limpeza externa", value=False)
        with col_limpeza_2:
            limpeza_interna_nc = st.checkbox("Limpeza interna", value=False)

        checklist_observacao_geral = st.text_area(
            "Observação geral do checklist",
            placeholder="Descreva apenas os itens não conformes identificados na vistoria.",
            key="checklist_observacao_geral"
        )

        checklist = montar_checklist_dict(
            lataria_nc=lataria_nc,
            retrovisores_nc=retrovisores_nc,
            vidros_nc=vidros_nc,
            limpadores_parabrisa_nc=limpadores_parabrisa_nc,
            limpador_traseiro_nc=limpador_traseiro_nc,
            pneus_nc=pneus_nc,
            rodas_nc=rodas_nc,
            placas_nc=placas_nc,
            farois_nc=farois_nc,
            setas_nc=setas_nc,
            lanternas_nc=lanternas_nc,
            luz_placa_nc=luz_placa_nc,
            farol_milha_nc=farol_milha_nc,
            luz_re_nc=luz_re_nc,
            luz_freio_nc=luz_freio_nc,
            nivel_oleo_nc=nivel_oleo_nc,
            nivel_agua_nc=nivel_agua_nc,
            agua_limpador_nc=agua_limpador_nc,
            fluido_freio_nc=fluido_freio_nc,
            buzina_nc=buzina_nc,
            alertas_painel_nc=alertas_painel_nc,
            pisca_alerta_nc=pisca_alerta_nc,
            vidros_eletricos_nc=vidros_eletricos_nc,
            retrovisor_interno_nc=retrovisor_interno_nc,
            freio_mao_nc=freio_mao_nc,
            radio_nc=radio_nc,
            multimidia_nc=multimidia_nc,
            estofamento_nc=estofamento_nc,
            tapetes_nc=tapetes_nc,
            cintos_seguranca_nc=cintos_seguranca_nc,
            forro_interno_nc=forro_interno_nc,
            extintor_nc=extintor_nc,
            documento_veicular_nc=documento_veicular_nc,
            ar_condicionado_nc=ar_condicionado_nc,
            carpete_nc=carpete_nc,
            estepe_nc=estepe_nc,
            macaco_nc=macaco_nc,
            triangulo_nc=triangulo_nc,
            chave_roda_nc=chave_roda_nc,
            limpeza_externa_nc=limpeza_externa_nc,
            limpeza_interna_nc=limpeza_interna_nc,
        )

        st.markdown("### 5. Fotos principais")

        foto_frente = st.file_uploader("Frente", type=FORMATOS_IMAGEM_ACEITOS, key="foto_frente")
        preview_upload("Prévia da frente", foto_frente)

        foto_motor = st.file_uploader("Motor", type=FORMATOS_IMAGEM_ACEITOS, key="foto_motor")
        preview_upload("Prévia do motor", foto_motor)

        foto_lat_esq = st.file_uploader("Lado esquerdo", type=FORMATOS_IMAGEM_ACEITOS, key="foto_lat_esq")
        preview_upload("Prévia do lado esquerdo", foto_lat_esq)

        foto_traseira = st.file_uploader("Traseira", type=FORMATOS_IMAGEM_ACEITOS, key="foto_traseira")
        preview_upload("Prévia da traseira", foto_traseira)

        foto_lat_dir = st.file_uploader("Lado direito", type=FORMATOS_IMAGEM_ACEITOS, key="foto_lat_dir")
        preview_upload("Prévia do lado direito", foto_lat_dir)

        foto_hodometro = st.file_uploader("Painel / KM", type=FORMATOS_IMAGEM_ACEITOS, key="foto_hodometro")
        preview_upload("Prévia do painel / KM", foto_hodometro)

        st.markdown("### 6. Fotos extras")

        obs_1_foto = st.file_uploader("Foto extra 1", type=FORMATOS_IMAGEM_ACEITOS, key="obs_1_foto")
        obs_1_texto = st.text_input("Descrição 1")
        preview_upload("Prévia extra 1", obs_1_foto)

        obs_2_foto = st.file_uploader("Foto extra 2", type=FORMATOS_IMAGEM_ACEITOS, key="obs_2_foto")
        obs_2_texto = st.text_input("Descrição 2")
        preview_upload("Prévia extra 2", obs_2_foto)

        obs_3_foto = st.file_uploader("Foto extra 3", type=FORMATOS_IMAGEM_ACEITOS, key="obs_3_foto")
        obs_3_texto = st.text_input("Descrição 3")
        preview_upload("Prévia extra 3", obs_3_foto)

        obs_4_foto = st.file_uploader("Foto extra 4", type=FORMATOS_IMAGEM_ACEITOS, key="obs_4_foto")
        obs_4_texto = st.text_input("Descrição 4")
        preview_upload("Prévia extra 4", obs_4_foto)

        st.markdown("### 7. Selfie do motorista")
        st.caption("Use o mesmo padrão das outras fotos: você pode tirar na hora pela câmera do celular ou escolher um arquivo/galeria.")

        selfie_motorista = st.file_uploader(
            "Foto do motorista no local",
            type=FORMATOS_IMAGEM_ACEITOS,
            key="selfie_motorista"
        )
        preview_upload("Prévia da selfie do motorista", selfie_motorista)

        autorizacao_selfie = st.checkbox(
            "Autorizo o uso da imagem para registro da vistoria e segurança contratual.",
            value=False,
            key="autorizacao_selfie_vistoria"
        )

        if selfie_motorista is not None and not autorizacao_selfie:
            st.warning("Para salvar a selfie no registro e no PDF, marque a autorização acima.")

        st.markdown("### 8. Assinatura do cliente")
        st.caption("Assine na área abaixo.")

        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 1)",
            stroke_width=2,
            stroke_color="#000000",
            background_color="#FFFFFF",
            height=160,
            width=320,
            drawing_mode="freedraw",
            key=f"assinatura_canvas_vistoria_{st.session_state.assinatura_canvas_key}",
            display_toolbar=False,
            update_streamlit=True,
        )

        if st.button("🗑️ Limpar assinatura do cliente", use_container_width=True):
            limpar_assinatura_cliente()
            st.rerun()

        st.markdown("### 9. Assinatura do vistoriador")
        st.caption("Assine na área abaixo para validar a vistoria.")

        canvas_result_vistoriador = st_canvas(
            fill_color="rgba(255, 255, 255, 1)",
            stroke_width=2,
            stroke_color="#000000",
            background_color="#FFFFFF",
            height=160,
            width=320,
            drawing_mode="freedraw",
            key=f"assinatura_canvas_vistoriador_{st.session_state.assinatura_vistoriador_canvas_key}",
            display_toolbar=False,
            update_streamlit=True,
        )

        if st.button("🗑️ Limpar assinatura do vistoriador", use_container_width=True):
            limpar_assinatura_vistoriador()
            st.rerun()

        st.markdown("### 10. Finalizar")
        st.markdown("""
        <div class="save-box">
            <div class="save-title">Finalização premium</div>
            <div class="save-sub">
                Ao salvar, o sistema registra checklist, localização, fotos, assinaturas, odômetro e gera o PDF da vistoria.
            </div>
        </div>
        """, unsafe_allow_html=True)

        salvar = st.button("✅ Salvar vistoria", use_container_width=True, type="primary")

        if salvar:
            if int(odometro) < int(ultimo_odometro):
                st.error("Não é possível salvar uma vistoria com KM menor que o último odômetro registrado.")
            else:
                latitude = st.session_state.geo_latitude
                longitude = st.session_state.geo_longitude
                endereco = st.session_state.geo_endereco

                endereco_manual = montar_endereco_manual_vistoria(
                    endereco_base=st.session_state.get("geo_manual_endereco", ""),
                    numero=st.session_state.get("geo_manual_numero", ""),
                    complemento=st.session_state.get("geo_manual_complemento", ""),
                    cidade=st.session_state.get("geo_manual_cidade", ""),
                    estado=st.session_state.get("geo_manual_estado", ""),
                )

                origem_local = "gps"
                if latitude is None or longitude is None:
                    origem_local = "manual"
                    if endereco_manual:
                        endereco = endereco_manual

                data_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                data_hora_real = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

                info_linhas = montar_info_legenda(
                    endereco=endereco,
                    latitude=latitude,
                    longitude=longitude,
                    data_hora_real=data_hora_real,
                    origem=origem_local,
                )

                pasta = os.path.join(
                    BASE_DIR,
                    veiculo_nome.replace(" ", "_").replace("/", "_"),
                    data_str
                )

                principais = {
                    "frente": salvar_imagem_vistoria(pasta, "frente", foto_frente, info_linhas),
                    "motor": salvar_imagem_vistoria(pasta, "motor", foto_motor, info_linhas),
                    "lateral_esquerda": salvar_imagem_vistoria(pasta, "lateral_esquerda", foto_lat_esq, info_linhas),
                    "traseira": salvar_imagem_vistoria(pasta, "traseira", foto_traseira, info_linhas),
                    "lateral_direita": salvar_imagem_vistoria(pasta, "lateral_direita", foto_lat_dir, info_linhas),
                    "hodometro": salvar_imagem_vistoria(pasta, "hodometro", foto_hodometro, info_linhas),
                }

                observacoes_fotos = []

                selfie_motorista_path = ""
                selfie_autorizada = bool(selfie_motorista is not None and autorizacao_selfie)
                if selfie_autorizada:
                    selfie_motorista_path = salvar_imagem_vistoria(
                        pasta,
                        "selfie_motorista",
                        selfie_motorista,
                        info_linhas,
                    )

                if obs_1_foto is not None:
                    caminho = salvar_imagem_vistoria(pasta, "obs_1", obs_1_foto, info_linhas)
                    observacoes_fotos.append({"foto": caminho, "descricao": obs_1_texto})

                if obs_2_foto is not None:
                    caminho = salvar_imagem_vistoria(pasta, "obs_2", obs_2_foto, info_linhas)
                    observacoes_fotos.append({"foto": caminho, "descricao": obs_2_texto})

                if obs_3_foto is not None:
                    caminho = salvar_imagem_vistoria(pasta, "obs_3", obs_3_foto, info_linhas)
                    observacoes_fotos.append({"foto": caminho, "descricao": obs_3_texto})

                if obs_4_foto is not None:
                    caminho = salvar_imagem_vistoria(pasta, "obs_4", obs_4_foto, info_linhas)
                    observacoes_fotos.append({"foto": caminho, "descricao": obs_4_texto})

                assinatura_cliente_path = salvar_assinatura(
                    canvas_result=canvas_result,
                    pasta=PASTA_ASSINATURAS,
                    nome_base=f"assinatura_cliente_{veiculo_id}_{data_str}"
                )

                assinatura_vistoriador_path = salvar_assinatura(
                    canvas_result=canvas_result_vistoriador,
                    pasta=PASTA_ASSINATURAS,
                    nome_base=f"assinatura_vistoriador_{veiculo_id}_{data_str}"
                )

                foto_path_dict = {
                    "principais": principais,
                    "observacoes_fotos": observacoes_fotos,
                    "selfie_motorista": selfie_motorista_path,
                    "selfie_autorizada": selfie_autorizada,
                    "assinatura_cliente": assinatura_cliente_path,
                    "assinatura_vistoriador": assinatura_vistoriador_path,
                    "checklist": checklist,
                    "checklist_observacao_geral": (checklist_observacao_geral or "").strip(),
                    "tipo_oleo": (tipo_oleo or "").strip(),
                    "local_origem": origem_local,
                    "endereco_manual": endereco_manual
                }
                foto_path = json.dumps(foto_path_dict, ensure_ascii=False)

                dados_hash = {
                    "veiculo_id": veiculo_id,
                    "veiculo_nome": veiculo_nome,
                    "contrato_id": contrato_id,
                    "cliente_contrato": cliente_contrato,
                    "cliente_cpf": cliente_cpf,
                    "vistoriador": vistoriador,
                    "tipo_oleo": (tipo_oleo or "").strip(),
                    "data_vistoria": str(data_vistoria),
                    "odometro": odometro,
                    "observacoes": observacoes,
                    "latitude": latitude,
                    "longitude": longitude,
                    "endereco": endereco,
                    "data_hora_real": data_hora_real,
                    "fotos": foto_path_dict,
                    "checklist": checklist,
                    "local_origem": origem_local,
                }
                hash_vistoria = gerar_hash_vistoria(dados_hash)

                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO vistorias (
                        veiculo_id, contrato_id, cliente_contrato, vistoriador,
                        data_vistoria, odometro, observacoes, foto_path,
                        latitude, longitude, endereco, data_hora_real, hash_vistoria,
                        assinatura_cliente, assinatura_vistoriador, pdf_path
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    veiculo_id,
                    contrato_id,
                    cliente_contrato,
                    vistoriador,
                    str(data_vistoria),
                    odometro,
                    observacoes,
                    foto_path,
                    latitude,
                    longitude,
                    endereco,
                    data_hora_real,
                    hash_vistoria,
                    assinatura_cliente_path,
                    assinatura_vistoriador_path,
                    ""
                ))

                conn.commit()
                vistoria_id = cursor.lastrowid

                registro_pdf = {
                    "id": vistoria_id,
                    "veiculo": veiculo_nome,
                    "placa": placa_veiculo,
                    "contrato_id": contrato_id,
                    "cliente_contrato": cliente_contrato,
                    "cliente_cpf": cliente_cpf,
                    "vistoriador": vistoriador,
                    "tipo_oleo": (tipo_oleo or "").strip(),
                    "data_vistoria": str(data_vistoria),
                    "odometro": odometro,
                    "observacoes": observacoes,
                    "latitude": latitude,
                    "longitude": longitude,
                    "endereco": endereco,
                    "data_hora_real": data_hora_real,
                    "hash_vistoria": hash_vistoria,
                    "local_origem": origem_local,
                }

                pasta_pdf = "relatorios_vistorias"
                os.makedirs(pasta_pdf, exist_ok=True)

                nome_pdf = f"VISTORIA_{placa_veiculo}_{datetime.now().strftime('%Y-%m-%d')}_{vistoria_id:04d}.pdf"
                caminho_pdf = os.path.join(pasta_pdf, nome_pdf)

                dados_pdf = {
                    "principais": principais,
                    "observacoes_fotos": observacoes_fotos,
                    "selfie_motorista": selfie_motorista_path,
                    "selfie_autorizada": selfie_autorizada,
                    "assinatura_cliente": assinatura_cliente_path,
                    "assinatura_vistoriador": assinatura_vistoriador_path,
                    "checklist": checklist,
                    "checklist_observacao_geral": (checklist_observacao_geral or "").strip(),
                    "tipo_oleo": (tipo_oleo or "").strip(),
                    "local_origem": origem_local,
                    "endereco_manual": endereco_manual
                }

                gerar_pdf_vistoria(registro_pdf, dados_pdf, caminho_pdf)

                cursor.execute(
                    "UPDATE vistorias SET pdf_path = ? WHERE id = ?",
                    (caminho_pdf, vistoria_id)
                )

                usuario_logado = st.session_state.get("usuario", "sistema")
                registrar_log(
                    conn,
                    usuario=usuario_logado,
                    acao="CRIAR_VISTORIA",
                    modulo="VISTORIAS",
                    referencia_id=vistoria_id,
                    descricao=f"Vistoria criada | veículo={veiculo_nome} | placa={placa_veiculo} | cliente={cliente_contrato or '-'}"
                )
                conn.commit()

                st.session_state.ultimo_pdf_vistoria = caminho_pdf
                st.session_state.ultima_vistoria_salva = True
                st.toast("✅ Vistoria salva e PDF gerado.", icon="✅")
                limpar_todas_assinaturas()
                st.rerun()

        if st.session_state.ultimo_pdf_vistoria:
            st.divider()
            mostrar_preview_pdf(st.session_state.ultimo_pdf_vistoria)

    with tab2:
        if df.empty:
            st.info("Nenhuma vistoria ainda.")
        else:
            st.dataframe(df.drop(columns=["foto_path"]), use_container_width=True)

            st.markdown("### Consulta premium")
            opcoes_hist = {
                f"Vistoria #{row['id']} - {row['veiculo']}": row["id"]
                for _, row in df.iterrows()
            }

            escolha = st.selectbox("Selecione a vistoria", list(opcoes_hist.keys()))
            registro = df[df["id"] == opcoes_hist[escolha]].iloc[0]

            st.markdown("""
            <div class="vistoria-card">
                <div class="vistoria-step">Resumo da vistoria</div>
                <div class="vistoria-sub">Informações principais, checklist, imagens, assinaturas e PDF registrado.</div>
            </div>
            """, unsafe_allow_html=True)

            st.write(f"**Veículo:** {registro['veiculo']}")
            st.write(f"**Cliente:** {registro['cliente_contrato'] or 'Sem contrato ativo'}")
            st.write(f"**CPF:** {registro['cliente_cpf'] or '-'}")
            st.write(f"**Vistoriador:** {registro['vistoriador'] or '-'}")
            st.write(f"**Data:** {registro['data_vistoria']}")
            st.write(f"**Hora real:** {registro['data_hora_real'] or '-'}")
            st.write(f"**KM:** {registro['odometro']}")
            st.write(f"**Local:** {registro['endereco'] or 'Não capturado'}")
            st.write(f"**Hash:** `{registro['hash_vistoria'] or '-'}`")
            st.write(f"**Observações:** {registro['observacoes'] or '-'}")
            st.caption("O acompanhamento gráfico do odômetro está disponível na aba Odômetro.")

            if pd.notna(registro["latitude"]) and pd.notna(registro["longitude"]):
                st.link_button(
                    "📍 Abrir no mapa",
                    f"https://www.google.com/maps?q={registro['latitude']},{registro['longitude']}",
                    use_container_width=True
                )

            dados = carregar_dados_vistoria_fotos(registro.to_dict())

            st.markdown("### Checklist registrado")
            exibir_checklist_visual(dados.get("checklist", {}))
            checklist_observacao_geral_hist = str(dados.get("checklist_observacao_geral", "") or "").strip()
            if checklist_observacao_geral_hist:
                st.caption(f"Observação geral do checklist: {checklist_observacao_geral_hist}")

            exibir_historico_inteligente(df, registro.to_dict(), dados)

            st.markdown("### Fotos principais")
            principais = dados.get("principais", {})
            exibir_galeria_principais_duas_colunas(principais)

            st.markdown("### Fotos extras")
            observacoes_fotos = dados.get("observacoes_fotos", [])
            exibir_galeria_extras_duas_colunas(observacoes_fotos)

            st.markdown("### Selfie do motorista")
            selfie_caminho, selfie_autorizada_hist = obter_caminho_selfie(dados)
            if selfie_autorizada_hist and selfie_caminho and os.path.exists(selfie_caminho):
                st.image(selfie_caminho, width=240)
                st.caption("Imagem registrada com legenda de localização e data/hora.")
                st.caption("Autorização de imagem registrada no momento da vistoria.")
            elif selfie_caminho and not os.path.exists(selfie_caminho):
                st.warning("A selfie foi registrada, mas o arquivo não foi localizado no armazenamento.")
            else:
                st.info("Sem selfie autorizada do motorista nesta vistoria.")

            st.markdown("### Assinaturas")
            col_ass1, col_ass2 = st.columns(2)

            with col_ass1:
                st.markdown("**Cliente**")
                assinatura = dados.get("assinatura_cliente", "")
                if assinatura and os.path.exists(assinatura):
                    st.image(assinatura, width=260)
                else:
                    st.info("Sem assinatura do cliente.")

            with col_ass2:
                st.markdown("**Vistoriador**")
                assinatura_v = dados.get("assinatura_vistoriador", "")
                if assinatura_v and os.path.exists(assinatura_v):
                    st.image(assinatura_v, width=260)
                else:
                    st.info("Sem assinatura do vistoriador.")

            st.markdown("### PDF da vistoria")

            registro_dict = registro.to_dict()

            caminho_pdf_existente = localizar_pdf_vistoria(
                vistoria_id=registro_dict["id"],
                placa=registro_dict.get("placa"),
                data_vistoria=registro_dict.get("data_vistoria")
            )

            col_pdf1, col_pdf2 = st.columns(2)

            with col_pdf1:
                if caminho_pdf_existente and os.path.exists(caminho_pdf_existente):
                    with open(caminho_pdf_existente, "rb") as f:
                        pdf_bytes = f.read()

                    st.download_button(
                        "⬇️ Baixar PDF novamente",
                        data=pdf_bytes,
                        file_name=os.path.basename(caminho_pdf_existente),
                        mime="application/pdf",
                        use_container_width=True,
                        key=f"download_pdf_hist_{registro_dict['id']}"
                    )
                else:
                    st.info("PDF original não encontrado.")

            with col_pdf2:
                if st.button("♻️ Regerar PDF", use_container_width=True, key=f"regerar_pdf_{registro_dict['id']}"):
                    caminho_pdf_novo = regerar_pdf_vistoria_historico(registro_dict, dados)

                    if caminho_pdf_novo and os.path.exists(caminho_pdf_novo):
                        st.success("PDF regerado com sucesso.")

                        with open(caminho_pdf_novo, "rb") as f:
                            pdf_bytes_reg = f.read()

                        st.download_button(
                            "⬇️ Baixar PDF regerado",
                            data=pdf_bytes_reg,
                            file_name=os.path.basename(caminho_pdf_novo),
                            mime="application/pdf",
                            use_container_width=True,
                            key=f"download_pdf_regerado_{registro_dict['id']}"
                        )
                    else:
                        st.error("Não foi possível regerar o PDF.")
    with tab3:
        renderizar_aba_excluir_vistorias(conn, df)

    conn.close()
