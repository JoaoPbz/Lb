from datetime import date
from .models import Venda, Pagamento, Despesa, Compra


class ClienteService:

    @staticmethod
    def calcular_saldo_devedor(cliente):
        total_vendas = sum(v.total for v in cliente.vendas.all())
        total_pago = sum(
            p.valor
            for v in cliente.vendas.all()
            for p in v.pagamentos.all()
        )
        return total_vendas - total_pago

    @staticmethod
    def calcular_total_ano(cliente, ano=None):
        if ano is None:
            ano = date.today().year
        return sum(
            v.total
            for v in cliente.vendas.all()
            if v.data.year == ano
        )

    @staticmethod
    def calcular_provas_abertas(cliente):
        return cliente.provas.filter(status='em_prova').count()


class VendaService:

    @staticmethod
    def calcular_saldo_devedor(venda):
        total_pago = sum(p.valor for p in venda.pagamentos.all())
        return venda.total - total_pago

    @staticmethod
    def registrar_pagamento(venda, data, valor):
        return Pagamento.objects.create(venda=venda, data=data, valor=valor)


class RelatorioService:

    @staticmethod
    def calcular_resumo_mensal(mes, ano):
        vendas = Venda.objects.filter(data__month=mes, data__year=ano)
        despesas = Despesa.objects.filter(data__month=mes, data__year=ano)
        compras = Compra.objects.filter(data__month=mes, data__year=ano)

        total_vendido = sum(v.total for v in vendas)
        total_despesas = sum(d.valor for d in despesas)
        total_compras = sum(c.valor_total for c in compras)
        lucro = total_vendido - total_despesas - total_compras

        return {
            'total_vendido': total_vendido,
            'total_despesas': total_despesas,
            'total_compras': total_compras,
            'lucro': lucro,
            'vendas': vendas,
            'despesas': despesas,
        }