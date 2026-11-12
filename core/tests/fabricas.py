from datetime import date
from decimal import Decimal

from core.models import Cliente, Produto

HOJE = date(2026, 11, 12)


def cliente(nome='Maria', telefone='51999990000'):
    return Cliente.objects.create(nome=nome, telefone=telefone)


def produto(codigo='100', nome='Blusa', tamanho='M', cor='Azul', custo='30.00', venda='59.90', estoque=1, ativo=True):
    return Produto.objects.create(
        codigo_marca=codigo, nome=nome, tamanho=tamanho, cor=cor, preco_custo=Decimal(custo),
        preco_venda=Decimal(venda), quantidade_estoque=estoque, ativo=ativo,
    )
