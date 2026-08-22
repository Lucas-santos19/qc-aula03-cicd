"""
Function HTTP da Quantum Commerce — versão L₂.

Lê produtos.csv do Blob Storage do catálogo (criado nesta aula) via Managed Identity.
SEM credenciais no código — autenticação via DefaultAzureCredential que detecta
a Managed Identity SystemAssigned do Function App em runtime.

Variável de ambiente esperada (configurada pelo Terraform):
    STORAGE_ACCOUNT_CATALOGO — nome do Storage Account com o container 'catalogo'
"""
import csv
import json
import logging
import os

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

logger = logging.getLogger(__name__)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

STORAGE_ACCOUNT = os.environ["STORAGE_ACCOUNT_CATALOGO"]
CONTAINER       = "catalogo"
BLOB_NAME       = "produtos.csv"

_credential = DefaultAzureCredential()
_blob_service = BlobServiceClient(
    f"https://{STORAGE_ACCOUNT}.blob.core.windows.net",
    credential=_credential,
)


def carregar_produtos() -> list[dict]:
    """Baixa produtos.csv do Blob e converte em lista de dicts."""
    blob_client = _blob_service.get_blob_client(container=CONTAINER, blob=BLOB_NAME)
    csv_content = blob_client.download_blob().readall().decode("utf-8")
    rows = list(csv.DictReader(csv_content.splitlines()))
    for r in rows:
        r["id"]      = int(r["id"])
        r["preco"]   = float(r["preco"])
        r["estoque"] = int(r["estoque"])
    return rows


@app.route(route="produtos", methods=["GET"])
def listar_produtos(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/produtos?categoria=moveis&nome=cadeira"""
    logger.info("Endpoint /produtos chamado")
    try:
        produtos = carregar_produtos()
    except Exception as e:
        logger.exception("Falha ao carregar produtos do Blob")
        return func.HttpResponse(
            json.dumps({"erro": f"falha ao acessar storage: {e!s}"}),
            mimetype="application/json",
            status_code=500,
        )

    categoria = (req.params.get("categoria") or "").lower().strip()
    nome      = (req.params.get("nome")      or "").lower().strip()

    resultado = produtos
    if categoria:
        resultado = [p for p in resultado if p["categoria"].lower() == categoria]
    if nome:
        resultado = [p for p in resultado if nome in p["nome"].lower()]

    return func.HttpResponse(
        json.dumps({"total": len(resultado), "produtos": resultado}, ensure_ascii=False),
        mimetype="application/json",
        status_code=200,
    )


@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"status": "ok", "service": "qc-catalogo", "source": "blob"}),
        mimetype="application/json",
    )
# Deploy validado via func CLI no CI


@app.route(route="frete", methods=["GET"])
def calcular_frete(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/frete?cep_origem=X&cep_destino=Y&peso=Z"""
    logger.info("Endpoint /frete chamado")
    try:
        cep_origem_raw = req.params.get("cep_origem", "")
        cep_destino_raw = req.params.get("cep_destino", "")
        peso_str = req.params.get("peso", "")

        if not cep_origem_raw or not cep_destino_raw or not peso_str:
            return func.HttpResponse(
                json.dumps({"erro": "parametros cep_origem, cep_destino e peso sao obrigatorios"}),
                mimetype="application/json",
                status_code=400,
            )

        cep_origem = "".join(filter(str.isdigit, cep_origem_raw))
        cep_destino = "".join(filter(str.isdigit, cep_destino_raw))

        if len(cep_origem) < 5 or len(cep_destino) < 5:
            return func.HttpResponse(
                json.dumps({"erro": "cep_origem e cep_destino devem conter ao menos 5 digitos"}),
                mimetype="application/json",
                status_code=400,
            )

        try:
            peso = float(peso_str)
        except ValueError:
            return func.HttpResponse(
                json.dumps({"erro": "peso deve ser um numero valido"}),
                mimetype="application/json",
                status_code=400,
            )

        if peso <= 0:
            return func.HttpResponse(
                json.dumps({"erro": "peso deve ser maior que zero"}),
                mimetype="application/json",
                status_code=400,
            )

        # Distancia ficticia baseada no prefixo regional do CEP (5 primeiros digitos)
        prefixo_origem = int(cep_origem[:5])
        prefixo_destino = int(cep_destino[:5])
        distancia_km = abs(prefixo_origem - prefixo_destino) / 100

        preco_por_km = 0.05
        preco_por_kg = 2.50
        valor_frete = round(distancia_km * preco_por_km + peso * preco_por_kg, 2)
        prazo_dias = max(1, round(distancia_km / 500))

        return func.HttpResponse(
            json.dumps({
                "cep_origem": cep_origem_raw,
                "cep_destino": cep_destino_raw,
                "peso_kg": peso,
                "distancia_estimada_km": round(distancia_km, 1),
                "valor_frete": valor_frete,
                "prazo_dias": prazo_dias,
            }, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as e:
        logger.exception("Falha inesperada no calculo de frete")
        return func.HttpResponse(
            json.dumps({"erro": "falha interna", "tipo": type(e).__name__, "detalhe": str(e)}),
            mimetype="application/json",
            status_code=500,
        )

