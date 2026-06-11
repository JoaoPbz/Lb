from .models import Venda, Pagamento, Despesa, Compra


class VendaRepository:

    @staticmethod
    def filtrar_por_mes_ano(mes, ano):
        return Venda.objects.filter(data__month=mes, data__year=ano)


class PagamentoRepository:

    @staticmethod
    def criar(venda, data, valor):
        return Pagamento.objects.create(venda=venda, data=data, valor=valor)


class DespesaRepository:

    @staticmethod
    def filtrar_por_mes_ano(mes, ano):
        return Despesa.objects.filter(data__month=mes, data__year=ano)


class CompraRepository:

    @staticmethod
    def filtrar_por_mes_ano(mes, ano):
        return Compra.objects.filter(data__month=mes, data__year=ano)