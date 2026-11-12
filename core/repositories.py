from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce

from .models import Cliente, Compra, Despesa, ItemProva, ItemVenda, Pagamento, Produto, Prova, Venda

MOEDA = DecimalField(max_digits=12, decimal_places=2)
ZERO = Value(Decimal('0.00'), output_field=MOEDA)

# Peça reservada: está numa prova aberta e ainda não foi devolvida nem vendida
FILTRO_RESERVA = Q(itens_prova__prova__status='em_prova', itens_prova__resultado='pendente')


def _soma(queryset, campo, agrupar_por):
    """Subquery que soma `campo` de um queryset correlacionado (evita joins duplicados)."""
    soma = queryset.order_by().values(agrupar_por).annotate(s=Sum(campo)).values('s')[:1]
    return Coalesce(Subquery(soma), ZERO, output_field=MOEDA)


def _total_pago_da_venda():
    return _soma(Pagamento.objects.filter(venda=OuterRef('pk')), 'valor', 'venda')


class ClienteRepository:

    @staticmethod
    def listar():
        return Cliente.objects.order_by('nome')

    @staticmethod
    def listar_com_saldo():
        total_comprado = _soma(Venda.objects.filter(cliente=OuterRef('pk')), 'total', 'cliente')
        total_pago = _soma(Pagamento.objects.filter(venda__cliente=OuterRef('pk')), 'valor', 'venda__cliente')
        return (
            Cliente.objects.order_by('nome')
            .annotate(total_comprado=total_comprado, total_pago=total_pago)
            .annotate(saldo=ExpressionWrapper(F('total_comprado') - F('total_pago'), output_field=MOEDA))
        )

    @staticmethod
    def possui_movimentacao(cliente):
        return cliente.vendas.exists() or cliente.provas.exists()


class ProdutoRepository:

    @staticmethod
    def _com_reserva(queryset):
        return queryset.annotate(em_prova=Count('itens_prova', filter=FILTRO_RESERVA)).annotate(
            disponivel=F('quantidade_estoque') - F('em_prova')
        )

    @staticmethod
    def ativos():
        return ProdutoRepository._com_reserva(Produto.objects.filter(ativo=True)).order_by('nome', 'tamanho', 'cor')

    @staticmethod
    def inativos():
        return Produto.objects.filter(ativo=False).order_by('nome', 'tamanho', 'cor')

    @staticmethod
    def disponiveis():
        return ProdutoRepository.ativos().filter(disponivel__gt=0)

    @staticmethod
    def buscar_por_sku(codigo_marca, tamanho, cor):
        return Produto.objects.filter(
            codigo_marca__iexact=codigo_marca, tamanho__iexact=tamanho, cor__iexact=cor
        ).first()

    @staticmethod
    def bloquear(ids):
        """Trava as linhas dos produtos até o fim da transação (evita vender a mesma peça duas vezes)."""
        return {p.id: p for p in Produto.objects.select_for_update().filter(id__in=ids)}

    @staticmethod
    def quantidade_reservada(ids):
        reservas = (
            ItemProva.objects.filter(produto_id__in=ids, prova__status='em_prova', resultado='pendente')
            .values('produto_id').annotate(qtd=Count('id'))
        )
        return {r['produto_id']: r['qtd'] for r in reservas}


class ProvaRepository:

    @staticmethod
    def listar():
        return Prova.objects.select_related('cliente').order_by('-data_saida', '-id')

    @staticmethod
    def do_cliente(cliente):
        return cliente.provas.order_by('-data_saida', '-id')

    @staticmethod
    def bloquear(prova_id):
        return Prova.objects.select_for_update().get(id=prova_id)


class VendaRepository:

    @staticmethod
    def com_saldo(queryset=None):
        queryset = Venda.objects.all() if queryset is None else queryset
        return (
            queryset.select_related('cliente')
            .annotate(total_pago=_total_pago_da_venda())
            .annotate(saldo_devedor=ExpressionWrapper(F('total') - F('total_pago'), output_field=MOEDA))
            .order_by('-data', '-id')
        )

    @staticmethod
    def do_cliente(cliente):
        return VendaRepository.com_saldo(cliente.vendas.all())

    @staticmethod
    def filtrar_por_mes_ano(mes, ano):
        return VendaRepository.com_saldo(Venda.objects.filter(data__month=mes, data__year=ano))

    @staticmethod
    def total_em_aberto():
        return VendaRepository.com_saldo().filter(saldo_devedor__gt=0).aggregate(
            s=Coalesce(Sum('saldo_devedor'), ZERO))['s']

    @staticmethod
    def custo_das_vendas(mes, ano):
        custo = Coalesce(F('custo_unitario'), F('produto__preco_custo'))
        itens = ItemVenda.objects.filter(venda__data__month=mes, venda__data__year=ano)
        return itens.aggregate(
            s=Coalesce(Sum(ExpressionWrapper(custo * F('quantidade'), output_field=MOEDA)), ZERO))['s']


class PagamentoRepository:

    @staticmethod
    def criar(venda, data, valor):
        return Pagamento.objects.create(venda=venda, data=data, valor=valor)

    @staticmethod
    def total_da_venda(venda):
        return venda.pagamentos.aggregate(s=Coalesce(Sum('valor'), ZERO))['s']

    @staticmethod
    def total_por_mes_ano(mes, ano):
        return Pagamento.objects.filter(data__month=mes, data__year=ano).aggregate(
            s=Coalesce(Sum('valor'), ZERO))['s']


class DespesaRepository:

    @staticmethod
    def listar():
        return Despesa.objects.order_by('-data', '-id')

    @staticmethod
    def filtrar_por_mes_ano(mes, ano):
        return Despesa.objects.filter(data__month=mes, data__year=ano).order_by('-data', '-id')


class CompraRepository:

    @staticmethod
    def filtrar_por_mes_ano(mes, ano):
        return Compra.objects.filter(data__month=mes, data__year=ano)
