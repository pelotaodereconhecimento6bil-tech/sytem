# BLOCO 5 (extras)

import os
import qrcode
from PIL import Image as PILImage

from utils import normalizar_bool_seguro, normalizar_selfie_motorista, obter_caminho_selfie

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image as RLImage,
    Table,
    TableStyle,
    KeepInFrame,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER


def valor_registro(registro, campo, padrao="-"):
    try:
        valor = registro[campo]
        if valor is None or valor == "":
            return padrao
        return valor
    except Exception:
        return padrao


def formatar_texto_quebra(texto, estilo=None):
    estilos = getSampleStyleSheet()

    if estilo is None:
        estilo = estilos["BodyText"]

    if not texto or texto == "-":
        texto = "-"

    texto = str(texto).replace("\n", "<br/>")
    return Paragraph(texto, estilo)


def obter_dimensoes_imagem(caminho):
    try:
        with PILImage.open(caminho) as img:
            return img.size
    except Exception:
        return None, None


def criar_imagem_proporcional(caminho, largura_maxima, altura_maxima, largura_minima=0):
    largura_original, altura_original = obter_dimensoes_imagem(caminho)

    if not largura_original or not altura_original:
        return RLImage(caminho, width=largura_maxima, height=altura_maxima)

    escala = min(largura_maxima / largura_original, altura_maxima / altura_original)
    escala = max(0.01, escala)

    largura_final = max(largura_minima or 0, largura_original * escala)
    altura_final = altura_original * (largura_final / largura_original)

    if altura_final > altura_maxima:
        escala = altura_maxima / altura_original
        largura_final = largura_original * escala
        altura_final = altura_original * escala

    return RLImage(caminho, width=largura_final, height=altura_final)


def criar_bloco_foto(caminho, titulo="", descricao="", largura_maxima=220, altura_maxima=180, centralizar_imagem=False):
    estilos = getSampleStyleSheet()
    elementos = []

    estilo_titulo_foto = ParagraphStyle(
        "titulo_foto_bloco",
        parent=estilos["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        spaceAfter=4,
    )

    estilo_desc_foto = ParagraphStyle(
        "descricao_foto_bloco",
        parent=estilos["BodyText"],
        fontName="Helvetica",
        fontSize=10.2,
        leading=13.8,
        textColor=colors.HexColor("#374151"),
        spaceAfter=6,
        alignment=TA_CENTER,
    )

    if titulo:
        elementos.append(Paragraph(f"<b>{titulo}</b>", estilo_titulo_foto))

    if descricao:
        elementos.append(formatar_texto_quebra(descricao, estilo_desc_foto))

    if caminho and os.path.exists(caminho):
        img = criar_imagem_proporcional(
            caminho=caminho,
            largura_maxima=largura_maxima,
            altura_maxima=altura_maxima,
        )

        if centralizar_imagem:
            tabela_centralizada = Table([[img]], colWidths=[largura_maxima])
            tabela_centralizada.setStyle(TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))
            elementos.append(tabela_centralizada)
        else:
            elementos.append(img)
    else:
        elementos.append(Paragraph("Imagem não encontrada.", estilos["BodyText"]))

    return elementos



def gerar_tabela_duas_colunas(blocos):
    linhas = []
    linha_atual = []

    for bloco in blocos:
        linha_atual.append(bloco)
        if len(linha_atual) == 2:
            linhas.append(linha_atual)
            linha_atual = []

    if linha_atual:
        linha_atual.append("")
        linhas.append(linha_atual)

    tabela = Table(linhas, colWidths=[255, 255])
    tabela.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.whitesmoke),
    ]))
    return tabela


def gerar_qr_vistoria(registro, caminho_qr):
    latitude = valor_registro(registro, "latitude", "Não capturada")
    longitude = valor_registro(registro, "longitude", "Não capturada")
    endereco = valor_registro(registro, "endereco", "Não capturado")
    data_hora_real = valor_registro(registro, "data_hora_real", "-")

    conteudo = (
        f"VISTORIA #{valor_registro(registro, 'id', '-')}\n"
        f"Veículo: {valor_registro(registro, 'veiculo', '-')}\n"
        f"Placa: {valor_registro(registro, 'placa', '-')}\n"
        f"Contrato ID: {valor_registro(registro, 'contrato_id', '-')}\n"
        f"Cliente do contrato: {valor_registro(registro, 'cliente_contrato', '-')}\n"
        f"CPF do cliente: {valor_registro(registro, 'cliente_cpf', '-')}\n"
        f"Vistoriador: {valor_registro(registro, 'vistoriador', '-')}\n"
        f"Data: {valor_registro(registro, 'data_vistoria', '-')}\n"
        f"Data/Hora real: {data_hora_real}\n"
        f"Odômetro: {valor_registro(registro, 'odometro', '-')}\n"
        f"Endereço: {endereco}\n"
        f"Latitude: {latitude}\n"
        f"Longitude: {longitude}\n"
        f"Hash: {valor_registro(registro, 'hash_vistoria', '-')}"
    )

    img_qr = qrcode.make(conteudo)
    img_qr.save(caminho_qr)


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


def listar_itens_nao_conformes(checklist_setorizado):
    itens = []
    for setor, dados_setor in (checklist_setorizado or {}).items():
        for item, valor in (((dados_setor or {}).get("itens", {}) or {}).items()):
            if normalizar_bool_seguro(valor):
                itens.append(f"{setor}: {item}")
    return itens


def adicionar_tabela_checklist(elementos, checklist, estilos, observacao_geral=""):
    checklist_setorizado = normalizar_checklist_setorizado(checklist)
    if not checklist_setorizado:
        return

    blocos_checklist = []
    blocos_checklist.append(Paragraph("CHECKLIST DA VISTORIA", estilos["Heading2"]))
    blocos_checklist.append(Spacer(1, 4))

    estilo_setor = ParagraphStyle(
        "checklist_setor_inline",
        parent=estilos["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=8.2,
        leading=10,
        textColor=colors.HexColor("#111827"),
        alignment=TA_CENTER,
        wordWrap="LTR",
    )

    estilo_item = ParagraphStyle(
        "checklist_item_compacto",
        parent=estilos["BodyText"],
        fontName="Helvetica",
        fontSize=7.9,
        leading=9,
        alignment=TA_LEFT,
        wordWrap="CJK",
    )

    estilo_status = ParagraphStyle(
        "checklist_status_compacto",
        parent=estilos["BodyText"],
        fontName="Helvetica",
        fontSize=7.8,
        leading=9,
        alignment=TA_CENTER,
        wordWrap="LTR",
    )

    estilo_obs_geral = ParagraphStyle(
        "checklist_obs_geral",
        parent=estilos["BodyText"],
        fontName="Helvetica",
        fontSize=8.2,
        leading=10,
        alignment=TA_LEFT,
        wordWrap="CJK",
        spaceAfter=1,
    )

    def formatar_setor_para_quebra(texto):
        texto = str(texto or "").strip().upper()
        if not texto:
            return "-"

        mapa_fixo = {
            "PORTA-MALAS": "PORTA<br/>MALAS",
            "PARTE INTERNA": "PARTE<br/>INTERNA",
            "ESTRUTURA EXTERNA": "ESTRUTURA<br/>EXTERNA",
        }
        if texto in mapa_fixo:
            return mapa_fixo[texto]

        partes = [p for p in texto.replace("-", " ").split() if p]
        return "<br/>".join(partes) if partes else texto

    def montar_tabela_setores(lista_setores):
        linhas = [[
            Paragraph("<b>Setor</b>", estilo_setor),
            Paragraph("<b>Item</b>", estilo_item),
            Paragraph("<b>Status</b>", estilo_status),
        ]]

        estilos_tabela = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDEDED")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("BOX", (0, 0), (-1, -1), 0.55, colors.grey),
            ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (2, 1), (2, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]

        linha_idx = 1
        for setor, dados_setor in lista_setores:
            itens = list(((dados_setor or {}).get("itens", {}) or {}).items())
            if not itens:
                continue

            linha_inicio_setor = linha_idx
            for item, status in itens:
                if bool(status):
                    status_paragraph = Paragraph('<font color="#B91C1C">Não<br/>conforme</font>', estilo_status)
                else:
                    status_paragraph = Paragraph('OK', estilo_status)

                setor_formatado = formatar_setor_para_quebra(setor)
                linhas.append([
                    Paragraph(setor_formatado, estilo_setor) if linha_idx == linha_inicio_setor else "",
                    Paragraph(str(item), estilo_item),
                    status_paragraph,
                ])
                linha_idx += 1

            linha_fim_setor = linha_idx - 1
            estilos_tabela.append(("BACKGROUND", (0, linha_inicio_setor), (0, linha_fim_setor), colors.HexColor("#F3F4F6")))
            estilos_tabela.append(("SPAN", (0, linha_inicio_setor), (0, linha_fim_setor)))
            estilos_tabela.append(("VALIGN", (0, linha_inicio_setor), (0, linha_fim_setor), "MIDDLE"))
            estilos_tabela.append(("ALIGN", (0, linha_inicio_setor), (0, linha_fim_setor), "CENTER"))

        return Table(linhas, colWidths=[66, 102, 42], hAlign="CENTER"), estilos_tabela

    setores = list(checklist_setorizado.items())
    meio = (len(setores) + 1) // 2
    esquerda = setores[:meio]
    direita = setores[meio:]

    tabela_esquerda, estilo_esquerda = montar_tabela_setores(esquerda)
    tabela_esquerda.setStyle(TableStyle(estilo_esquerda))

    if direita:
        tabela_direita, estilo_direita = montar_tabela_setores(direita)
        tabela_direita.setStyle(TableStyle(estilo_direita))
    else:
        tabela_direita = Spacer(1, 1)

    tabela_principal = Table(
        [[tabela_esquerda, tabela_direita]],
        colWidths=[225, 225],
        hAlign="CENTER",
    )
    tabela_principal.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    blocos_checklist.append(tabela_principal)
    blocos_checklist.append(Spacer(1, 4))

    itens_nao_conformes = listar_itens_nao_conformes(checklist_setorizado)
    observacao_geral = str(observacao_geral or "").strip()

    if itens_nao_conformes:
        texto_itens = "; ".join(itens_nao_conformes)
        blocos_checklist.append(Paragraph(f"<b>Itens não conformes:</b> {texto_itens}", estilo_obs_geral))
        blocos_checklist.append(Spacer(1, 2))

    if observacao_geral:
        blocos_checklist.append(Paragraph(f"<b>Observação geral:</b> {observacao_geral}", estilo_obs_geral))
        blocos_checklist.append(Spacer(1, 3))

    elementos.append(
        KeepInFrame(
            maxWidth=510,
            maxHeight=430,
            content=blocos_checklist,
            mode="shrink",
            hAlign="CENTER",
            vAlign="TOP",
        )
    )


def gerar_bloco_assinatura(caminho_assinatura, titulo, nome_linha_1, nome_linha_2=""):
    estilos = getSampleStyleSheet()

    estilo_ass_nome = ParagraphStyle(
        "assinatura_nome_bloco",
        parent=estilos["BodyText"],
        alignment=TA_CENTER,
        fontName="Times-Roman",
        fontSize=10,
        leading=13,
        textColor=colors.black,
        spaceAfter=2,
    )

    estilo_ass_linha2 = ParagraphStyle(
        "assinatura_linha2_bloco",
        parent=estilos["BodyText"],
        alignment=TA_CENTER,
        fontName="Times-Roman",
        fontSize=10,
        leading=13,
        textColor=colors.black,
        spaceAfter=0,
    )

    elementos = [Paragraph(titulo, estilos["Heading3"]), Spacer(1, 8)]

    if caminho_assinatura and os.path.exists(caminho_assinatura):
        assinatura_tabela = Table(
            [[criar_imagem_proporcional(caminho_assinatura, largura_maxima=220, altura_maxima=85, largura_minima=120)]],
            colWidths=[240]
        )
        assinatura_tabela.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        elementos.append(assinatura_tabela)
        elementos.append(Spacer(1, 2))
    else:
        elementos.append(Spacer(1, 87))

    linha = Table([[""]], colWidths=[220])
    linha.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, -1), 0.8, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elementos.append(linha)
    elementos.append(Spacer(1, 4))
    elementos.append(Paragraph(nome_linha_1 or "-", estilo_ass_nome))

    if nome_linha_2:
        elementos.append(Paragraph(nome_linha_2, estilo_ass_linha2))

    return elementos


def gerar_pdf_vistoria(registro, dados_fotos, caminho_pdf):
    doc = SimpleDocTemplate(
        caminho_pdf,
        pagesize=A4,
        rightMargin=28,
        leftMargin=28,
        topMargin=28,
        bottomMargin=28,
    )

    estilos = getSampleStyleSheet()

    estilo_obs = ParagraphStyle(
        "obs_custom",
        parent=estilos["BodyText"],
        alignment=TA_LEFT,
        leading=15,
        spaceAfter=6,
    )

    estilo_subtitulo = ParagraphStyle(
        "subtitulo_custom",
        parent=estilos["BodyText"],
        alignment=TA_CENTER,
        textColor=colors.grey,
        spaceAfter=4,
    )

    estilo_tabela = ParagraphStyle(
        "tabela_quebra",
        parent=estilos["BodyText"],
        alignment=TA_LEFT,
        fontName="Helvetica",
        fontSize=9,
        leading=10,
        wordWrap="CJK",
    )

    elementos = []

    latitude = valor_registro(registro, "latitude", None)
    longitude = valor_registro(registro, "longitude", None)
    endereco = valor_registro(registro, "endereco", "")
    data_hora_real = valor_registro(registro, "data_hora_real", "-")

    if latitude is not None and longitude is not None:
        coordenadas = f"{latitude}, {longitude}"
        status_localizacao = "Geolocalização capturada"
    else:
        coordenadas = "Não capturadas"
        status_localizacao = "Geolocalização não capturada no momento da vistoria"

    endereco_exibir = endereco if endereco else "Não capturado"

    pasta_qr = "temp_qr"
    os.makedirs(pasta_qr, exist_ok=True)
    caminho_qr = os.path.join(
        pasta_qr,
        f"vistoria_qr_{valor_registro(registro, 'id', 'sem_id')}.png"
    )
    gerar_qr_vistoria(registro, caminho_qr)

    cabecalho_esquerda = [
        Paragraph("RELATÓRIO DE VISTORIA", estilos["Title"]),
        Spacer(1, 4),
        Paragraph(
            "Escaneie o QR Code para visualizar o resumo desta vistoria.",
            estilo_subtitulo
        ),
    ]

    cabecalho = Table(
        [[cabecalho_esquerda, RLImage(caminho_qr, width=82, height=82)]],
        colWidths=[420, 82]
    )
    cabecalho.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    elementos.append(cabecalho)
    elementos.append(Spacer(1, 10))

    tipo_oleo_exibir = dados_fotos.get("tipo_oleo", valor_registro(registro, "tipo_oleo", "-"))
    if not tipo_oleo_exibir:
        tipo_oleo_exibir = "-"

    info_data = [
        ["Vistoria ID:", formatar_texto_quebra(str(valor_registro(registro, "id")), estilo_tabela)],
        ["Contrato ID:", formatar_texto_quebra(str(valor_registro(registro, "contrato_id")), estilo_tabela)],
        ["Nome do locatário:", formatar_texto_quebra(valor_registro(registro, "cliente_contrato"), estilo_tabela)],
        ["CPF:", formatar_texto_quebra(valor_registro(registro, "cliente_cpf"), estilo_tabela)],
        ["Veículo:", formatar_texto_quebra(valor_registro(registro, "veiculo"), estilo_tabela)],
        ["Placa:", formatar_texto_quebra(valor_registro(registro, "placa"), estilo_tabela)],
        ["Tipo do óleo:", formatar_texto_quebra(str(tipo_oleo_exibir), estilo_tabela)],
        ["Odômetro:", formatar_texto_quebra(str(valor_registro(registro, "odometro")), estilo_tabela)],
        ["Data/Hora da vistoria:", formatar_texto_quebra(str(data_hora_real), estilo_tabela)],
        ["Endereço:", formatar_texto_quebra(endereco_exibir, estilo_tabela)],
        ["Hash de segurança:", formatar_texto_quebra(valor_registro(registro, "hash_vistoria"), estilo_tabela)],
        ["Vistoriador:", formatar_texto_quebra(valor_registro(registro, "vistoriador"), estilo_tabela)],
        ["Observações gerais:", formatar_texto_quebra(str(valor_registro(registro, "observacoes")), estilo_tabela)],
    ]

    tabela_info = Table(info_data, colWidths=[135, 365])
    tabela_info.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F2F2F2")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elementos.append(tabela_info)
    elementos.append(Spacer(1, 10))

    checklist = dados_fotos.get("checklist", {})
    checklist_observacao_geral = dados_fotos.get("checklist_observacao_geral", "")
    adicionar_tabela_checklist(elementos, checklist, estilos, checklist_observacao_geral)

    observacoes_gerais = valor_registro(registro, "observacoes", "")
    if observacoes_gerais not in ["", "-"]:
        elementos.append(Paragraph("OBSERVAÇÕES", estilos["Heading2"]))
        elementos.append(formatar_texto_quebra(str(observacoes_gerais), estilo_obs))
        elementos.append(Spacer(1, 10))

    principais = dados_fotos.get("principais", {})
    blocos_principais = []

    for nome, caminho in principais.items():
        if caminho and os.path.exists(caminho):
            bloco = criar_bloco_foto(
                caminho=caminho,
                titulo=nome.replace("_", " ").title()
            )
            blocos_principais.append(bloco)

    if blocos_principais:
        elementos.append(Paragraph("FOTOS PRINCIPAIS", estilos["Heading2"]))
        elementos.append(Spacer(1, 8))
        elementos.append(gerar_tabela_duas_colunas(blocos_principais))
        elementos.append(Spacer(1, 14))

    observacoes_fotos = dados_fotos.get("observacoes_fotos", [])
    blocos_obs = []

    for i, item in enumerate(observacoes_fotos, start=1):
        caminho = item.get("foto", "")
        descricao = item.get("descricao", "")

        if caminho and os.path.exists(caminho):
            bloco = criar_bloco_foto(
                caminho=caminho,
                titulo=f"Observação {i}",
                descricao=descricao or "Sem descrição informada."
            )
            blocos_obs.append(bloco)

    if blocos_obs:
        elementos.append(Paragraph("FOTOS DE OBSERVAÇÃO", estilos["Heading2"]))
        elementos.append(Spacer(1, 8))
        elementos.append(gerar_tabela_duas_colunas(blocos_obs))
        elementos.append(Spacer(1, 12))

    selfie_dados = normalizar_selfie_motorista(dados_fotos)
    selfie_caminho, selfie_autorizada = obter_caminho_selfie(dados_fotos)

    if selfie_autorizada and selfie_caminho and os.path.exists(selfie_caminho):
        elementos.append(Paragraph("SELFIE DO MOTORISTA", estilos["Heading2"]))
        elementos.append(Spacer(1, 8))

        descricao_selfie = ""

        bloco_selfie = criar_bloco_foto(
            caminho=selfie_caminho,
            titulo="Identificação do condutor no momento da vistoria",
            descricao=descricao_selfie,
            largura_maxima=235,
            altura_maxima=200,
            centralizar_imagem=True,
        )
        tabela_selfie = Table([[bloco_selfie]], colWidths=[255])
        tabela_selfie.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("BOX", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ]))
        elementos.append(tabela_selfie)
        elementos.append(Spacer(1, 12))

    assinatura_cliente = dados_fotos.get("assinatura_cliente", "")
    assinatura_vistoriador = dados_fotos.get("assinatura_vistoriador", "")
    nome_cliente = valor_registro(registro, "cliente_contrato", "-")
    cpf_cliente = valor_registro(registro, "cliente_cpf", "-")
    nome_vistoriador = valor_registro(registro, "vistoriador", "-")

    if assinatura_cliente or assinatura_vistoriador:
        elementos.append(Paragraph("ASSINATURAS", estilos["Heading2"]))
        elementos.append(Spacer(1, 10))

        bloco_cliente = gerar_bloco_assinatura(
            caminho_assinatura=assinatura_cliente,
            titulo="Cliente",
            nome_linha_1=nome_cliente,
            nome_linha_2=cpf_cliente
        )

        bloco_vistoriador = gerar_bloco_assinatura(
            caminho_assinatura=assinatura_vistoriador,
            titulo="Vistoriador",
            nome_linha_1=nome_vistoriador,
            nome_linha_2=""
        )

        tabela_assinaturas = Table(
            [[bloco_cliente, bloco_vistoriador]],
            colWidths=[255, 255]
        )
        tabela_assinaturas.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        elementos.append(tabela_assinaturas)
        elementos.append(Spacer(1, 12))

    elementos.append(Paragraph(
        "Este relatório foi gerado pelo sistema interno da locadora e reúne checklist, imagens, assinaturas e dados registrados no momento da vistoria.",
        estilos["Italic"]
    ))

    doc.build(elementos)