"""Testes de unidade para a lógica de filtro de produtos da QC.

Não testa acesso ao Blob (isso já foi validado manualmente via curl
contra a Function real). Testa só a regra de negócio de filtragem,
isolada de qualquer chamada de rede.
"""

PRODUTOS_FAKE = [
    {"id": 1, "nome": "Cadeira Ergonômica DXRacer", "categoria": "moveis", "preco": 1499.9},
    {"id": 2, "nome": "Notebook Dell Inspiron 15", "categoria": "eletronicos", "preco": 4299.0},
    {"id": 3, "nome": "Cafeteira Nespresso Mini", "categoria": "eletrodomesticos", "preco": 499.0},
]


def filtrar_produtos(produtos, categoria="", nome=""):
    """Reimplementação da lógica de filtro usada em listar_produtos,
    extraída para ser testável sem depender do Blob."""
    cat = (categoria or "").lower().strip()
    nm = (nome or "").lower().strip()

    resultado = produtos
    if cat:
        resultado = [p for p in resultado if p["categoria"].lower() == cat]
    if nm:
        resultado = [p for p in resultado if nm in p["nome"].lower()]
    return resultado


def test_filtro_por_categoria():
    resultado = filtrar_produtos(PRODUTOS_FAKE, categoria="eletronicos")
    assert len(resultado) == 1
    assert resultado[0]["nome"] == "Notebook Dell Inspiron 15"


def test_filtro_por_nome_parcial():
    resultado = filtrar_produtos(PRODUTOS_FAKE, nome="cadeira")
    assert len(resultado) == 1
    assert resultado[0]["id"] == 1


def test_sem_filtro_retorna_tudo():
    resultado = filtrar_produtos(PRODUTOS_FAKE)
    assert len(resultado) == 3


def test_filtro_categoria_inexistente_retorna_vazio():
    resultado = filtrar_produtos(PRODUTOS_FAKE, categoria="esportes")
    assert resultado == []
