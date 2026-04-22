from num2words import num2words
import requests
import re
from datetime import datetime, timedelta
import pandas as pd


# ==============================
# BUSCA CEP
# ==============================

def buscar_cep(cep):
    cep = cep.replace("-", "").strip()
    cep = re.sub(r"\D", "", cep)

    if len(cep) != 8:
        return None

    url = f"https://viacep.com.br/ws/{cep}/json/"

    try:
        response = requests.get(url, timeout=5)
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    dados = response.json()

    if "erro" in dados:
        return None

    return {
        "endereco": dados.get("logradouro", ""),
        "cidade": dados.get("localidade", ""),
        "estado": dados.get("uf", "")
    }


# ==============================
# FORMATAÇÕES
# ==============================

def formatar_nome(nome):
    if not nome:
        return ""

    palavras = nome.lower().split()
    excecoes = ["da", "de", "do", "dos", "das", "e"]

    resultado = []
    for p in palavras:
        if p in excecoes:
            resultado.append(p)
        else:
            resultado.append(p.capitalize())

    return " ".join(resultado)


def formatar_cpf(cpf):
    cpf = re.sub(r"\D", "", str(cpf))

    if len(cpf) != 11:
        return cpf

    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


def formatar_rg(rg):
    rg = re.sub(r"\D", "", str(rg))

    if len(rg) < 8:
        return rg

    if len(rg) == 8:
        return f"{rg[:2]}.{rg[2:5]}.{rg[5:8]}"

    return f"{rg[:2]}.{rg[2:5]}.{rg[5:8]}-{rg[8:]}"


def formatar_telefone(telefone):
    telefone = re.sub(r"\D", "", str(telefone))

    if len(telefone) == 11:
        return f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:]}"
    if len(telefone) == 10:
        return f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:]}"
    return telefone


def formatar_placa(placa):
    if not placa:
        return ""
    return str(placa).strip().upper()


def formatar_cep(cep):
    cep = re.sub(r"\D", "", str(cep))

    if len(cep) == 8:
        return f"{cep[:5]}-{cep[5:]}"
    return cep


def formatar_moeda(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ==============================
# TEXTO
# ==============================

def valor_por_extenso(valor):
    inteiro = int(valor)
    centavos = int(round((valor - inteiro) * 100))

    extenso = num2words(inteiro, lang="pt_BR").upper() + " REAIS"

    if centavos > 0:
        extenso += f" E {num2words(centavos, lang='pt_BR').upper()} CENTAVOS"

    return extenso


def data_por_extenso(data_obj):
    meses = [
        "janeiro", "fevereiro", "março", "abril",
        "maio", "junho", "julho", "agosto",
        "setembro", "outubro", "novembro", "dezembro"
    ]

    dia = data_obj.day
    mes = meses[data_obj.month - 1].capitalize()
    ano = data_obj.year

    return f"{dia} de {mes} de {ano}"


def duracao_texto(data_inicio, data_fim):
    dias = (data_fim - data_inicio).days

    if dias <= 1:
        return "1 dia"

    return f"{dias} dias"


# ==============================
# IMAGENS / SELFIE / BOOLEANOS
# ==============================

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


def normalizar_selfie_motorista(dados):
    dados = dados or {}
    selfie_raw = dados.get("selfie_motorista", "")
    selfie_autorizada = normalizar_bool_seguro(dados.get("selfie_autorizada", False))

    selfie_dict = {
        "foto": "",
        "autorizada": selfie_autorizada,
        "origem": "",
        "data_hora": "",
        "observacao": "",
    }

    if isinstance(selfie_raw, dict):
        selfie_dict["foto"] = str(selfie_raw.get("foto", "") or "").strip()
        selfie_dict["origem"] = str(selfie_raw.get("origem", "") or "").strip()
        selfie_dict["data_hora"] = str(selfie_raw.get("data_hora", "") or "").strip()
        selfie_dict["observacao"] = str(selfie_raw.get("observacao", "") or "").strip()

        if "autorizada" in selfie_raw:
            selfie_dict["autorizada"] = normalizar_bool_seguro(selfie_raw.get("autorizada"))
    else:
        selfie_dict["foto"] = str(selfie_raw or "").strip()

    selfie_dict["autorizada"] = normalizar_bool_seguro(selfie_dict["autorizada"])

    if not selfie_dict["foto"]:
        selfie_dict["autorizada"] = False

    return selfie_dict


def obter_caminho_selfie(dados):
    selfie = normalizar_selfie_motorista(dados)
    return selfie.get("foto", ""), selfie.get("autorizada", False)


# ==============================
# ODÔMETRO / KM
# ==============================

def _normalizar_data_referencia(valor):
    if valor is None:
        return None
    data = pd.to_datetime(valor, errors="coerce")
    if pd.isna(data):
        return None
    return data.to_pydatetime()


def _carregar_leituras_odometro(conn, veiculo_id=None, data_inicio=None, data_fim=None, contrato_id=None):
    filtros = ["odometro IS NOT NULL"]
    params = []

    if veiculo_id is not None:
        filtros.append("veiculo_id = ?")
        params.append(int(veiculo_id))

    if contrato_id is not None:
        filtros.append("contrato_id = ?")
        params.append(int(contrato_id))

    if data_inicio:
        filtros.append("date(data_vistoria) >= date(?)")
        params.append(str(data_inicio))

    if data_fim:
        filtros.append("date(data_vistoria) <= date(?)")
        params.append(str(data_fim))

    query = f"""
        SELECT
            id,
            veiculo_id,
            contrato_id,
            data_vistoria,
            odometro
        FROM vistorias
        WHERE {' AND '.join(filtros)}
        ORDER BY date(data_vistoria) ASC, id ASC
    """

    df = pd.read_sql_query(query, conn, params=params)

    if df.empty:
        return df

    df["data_vistoria"] = pd.to_datetime(df["data_vistoria"], errors="coerce")
    df["odometro"] = pd.to_numeric(df["odometro"], errors="coerce")
    df = df.dropna(subset=["data_vistoria", "odometro"]).copy()

    if df.empty:
        return df

    df["odometro"] = df["odometro"].astype(int)
    df = df.sort_values(by=["data_vistoria", "id"]).reset_index(drop=True)
    return df


def _diferenca_primeiro_ultimo(df):
    if df.empty or len(df) < 2:
        return 0
    return max(0, int(df.iloc[-1]["odometro"]) - int(df.iloc[0]["odometro"]))


def _obter_data_base_veiculo(conn, veiculo_id, data_referencia=None):
    data_ref = _normalizar_data_referencia(data_referencia)
    if data_ref is not None:
        return data_ref

    df = _carregar_leituras_odometro(conn, veiculo_id=veiculo_id)
    if df.empty:
        return datetime.now()

    return df.iloc[-1]["data_vistoria"].to_pydatetime()


def classificar_status_km(percentual_mes):
    percentual_mes = float(percentual_mes or 0)

    if percentual_mes >= 100:
        return "excedido"
    if percentual_mes >= 90:
        return "critico"
    if percentual_mes >= 70:
        return "atencao"
    return "normal"


def obter_ultimo_odometro(conn, veiculo_id):
    df = _carregar_leituras_odometro(conn, veiculo_id=veiculo_id)
    if df.empty:
        return 0
    return int(df.iloc[-1]["odometro"])


def obter_quantidade_leituras_odometro(conn, veiculo_id):
    df = _carregar_leituras_odometro(conn, veiculo_id=veiculo_id)
    return int(len(df))


def calcular_km_contrato(conn, contrato_id):
    if not contrato_id:
        return 0

    df = _carregar_leituras_odometro(conn, contrato_id=contrato_id)
    return _diferenca_primeiro_ultimo(df)


def calcular_km_mes(conn, veiculo_id, data_referencia=None):
    data_base = _obter_data_base_veiculo(conn, veiculo_id, data_referencia)
    inicio_mes = data_base.replace(day=1).strftime("%Y-%m-%d")
    fim_mes = data_base.strftime("%Y-%m-%d")

    df = _carregar_leituras_odometro(
        conn,
        veiculo_id=veiculo_id,
        data_inicio=inicio_mes,
        data_fim=fim_mes,
    )
    return _diferenca_primeiro_ultimo(df)


def calcular_km_semana(conn, veiculo_id, data_referencia=None):
    data_base = _obter_data_base_veiculo(conn, veiculo_id, data_referencia)
    inicio_semana = (data_base - timedelta(days=data_base.weekday())).strftime("%Y-%m-%d")
    fim_semana = data_base.strftime("%Y-%m-%d")

    df = _carregar_leituras_odometro(
        conn,
        veiculo_id=veiculo_id,
        data_inicio=inicio_semana,
        data_fim=fim_semana,
    )
    return _diferenca_primeiro_ultimo(df)


def obter_resumo_km_veiculo(conn, veiculo_id, contrato_id=None, limite_mensal=8000):
    leituras = _carregar_leituras_odometro(conn, veiculo_id=veiculo_id)
    qtd_leituras = int(len(leituras))

    ultimo_odometro = int(leituras.iloc[-1]["odometro"]) if qtd_leituras else 0
    data_base = _obter_data_base_veiculo(conn, veiculo_id)
    km_semana = calcular_km_semana(conn, veiculo_id, data_referencia=data_base)
    km_mes = calcular_km_mes(conn, veiculo_id, data_referencia=data_base)
    km_contrato = calcular_km_contrato(conn, contrato_id) if contrato_id else 0

    percentual_mes = (
        (km_mes / float(limite_mensal)) * 100.0
        if limite_mensal and float(limite_mensal) > 0
        else 0.0
    )
    status = classificar_status_km(percentual_mes)

    if qtd_leituras == 0:
        observacao = "Sem leitura de odômetro registrada."
    elif qtd_leituras == 1:
        observacao = "Primeira leitura registrada. KM semanal e mensal serão calculados a partir da próxima vistoria."
    else:
        observacao = f"Histórico de odômetro atualizado com base em {data_base.strftime('%d/%m/%Y')}."

    return {
        "ultimo_odometro": ultimo_odometro,
        "km_semana": km_semana,
        "km_mes": km_mes,
        "km_contrato": km_contrato,
        "limite_mensal": int(limite_mensal or 0),
        "percentual": percentual_mes,
        "percentual_mes": percentual_mes,
        "status": status,
        "qtd_leituras": qtd_leituras,
        "tem_historico_km": qtd_leituras >= 2,
        "possui_primeira_leitura": qtd_leituras == 1,
        "data_base_calculo": data_base.strftime('%Y-%m-%d') if qtd_leituras else "",
        "observacao": observacao,
    }


def obter_resumo_km_contrato(conn, contrato_id, veiculo_id=None, limite_mensal=8000):
    if not contrato_id and not veiculo_id:
        return {
            "ultimo_odometro": 0,
            "km_contrato": 0,
            "km_mes": 0,
            "km_semana": 0,
            "limite_mensal": int(limite_mensal or 0),
            "percentual": 0.0,
            "percentual_mes": 0.0,
            "status": "normal",
            "qtd_leituras": 0,
            "tem_historico_km": False,
            "possui_primeira_leitura": False,
            "data_base_calculo": "",
            "observacao": "Sem leitura de odômetro registrada.",
        }

    if veiculo_id is None and contrato_id:
        df = pd.read_sql_query(
            """
            SELECT veiculo_id
            FROM contratos
            WHERE id = ?
            """,
            conn,
            params=(contrato_id,),
        )

        if not df.empty:
            veiculo_id = int(df.iloc[0]["veiculo_id"])

    if not veiculo_id:
        return {
            "ultimo_odometro": 0,
            "km_contrato": 0,
            "km_mes": 0,
            "km_semana": 0,
            "limite_mensal": int(limite_mensal or 0),
            "percentual": 0.0,
            "percentual_mes": 0.0,
            "status": "normal",
            "qtd_leituras": 0,
            "tem_historico_km": False,
            "possui_primeira_leitura": False,
            "data_base_calculo": "",
            "observacao": "Veículo não localizado para o contrato.",
        }

    return obter_resumo_km_veiculo(
        conn=conn,
        veiculo_id=veiculo_id,
        contrato_id=contrato_id,
        limite_mensal=limite_mensal,
    )

