from collections import Counter
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.db import transaction
from django.db.models import F

from .models import Cliente, Compra, ItemProva, ItemVenda, Produto, Prova, Venda
from .repositories import (
    ClienteRepository, CompraRepository, DespesaRepository, PagamentoRepository,
    ProdutoRepository, ProvaRepository, VendaRepository,
)
from .templatetags.filtros import moeda

CENTAVO = Decimal('0.01')
ZERO = Decimal('0.00')
DESCONTOS_VALIDOS = {codigo for codigo, _ in Venda.DESCONTO_CHOICES}
FORMAS_PAGAMENTO = {codigo for codigo, _ in Venda.FORMA_PAGAMENTO_CHOICES}


class RegraNegocioError(Exception):
    """Violação de regra de negócio, com mensagem pronta para mostrar à usuária."""


# ---------- Leitura e validação de entradas ----------

def ler_decimal(valor, campo):
    texto = str(valor if valor is not None else '').replace('R$', '').strip()
    if ',' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    try:
        numero = Decimal(texto)
    except InvalidOperation:
        raise RegraNegocioError(f'{campo}: informe um valor numérico.')
    if not numero.is_finite() or numero < 0:
        raise RegraNegocioError(f'{campo}: informe um valor válido.')
    return numero.quantize(CENTAVO, ROUND_HALF_UP)


def ler_inteiro(valor, campo, minimo=0):
    try:
        numero = int(str(valor).strip())
    except (TypeError, ValueError):
        raise RegraNegocioError(f'{campo}: informe um número inteiro.')
    if numero < minimo:
        raise RegraNegocioError(f'{campo}: o mínimo é {minimo}.')
    return numero


def ler_data(valor, campo, obrigatoria=True):
    if not valor:
        if obrigatoria:
            raise RegraNegocioError(f'{campo}: informe a data.')
        return None
    try:
        return date.fromisoformat(str(valor))
    except ValueError:
        raise RegraNegocioError(f'{campo}: data inválida.')


def ler_ids(valores):
    try:
        return {int(v) for v in valores}
    except (TypeError, ValueError):
        raise RegraNegocioError('Seleção de itens inválida.')


def _buscar_cliente(cliente_id):
    try:
        return Cliente.objects.get(id=int(cliente_id))
    except (TypeError, ValueError, Cliente.DoesNotExist):
        raise RegraNegocioError('Selecione um cliente válido.')


# ---------- Serviços ----------

class ClienteService:

    @staticmethod
    def calcular_saldo_devedor(cliente):
        return ClienteRepository.listar_com_saldo().get(pk=cliente.pk).saldo

    @staticmethod
    def calcular_total_ano(cliente, ano=None):
        ano = ano or date.today().year
        return sum((v.total for v in cliente.vendas.filter(data__year=ano)), ZERO)

    @staticmethod
    def calcular_provas_abertas(cliente):
        return cliente.provas.filter(status='em_prova').count()

    @staticmethod
    def excluir(cliente):
        if ClienteRepository.possui_movimentacao(cliente):
            raise RegraNegocioError(
                f'O cliente "{cliente.nome}" não pode ser excluído pois possui vendas ou provas vinculadas.')
        cliente.delete()


class ProdutoService:

    @staticmethod
    def alterar_status(produto, ativo):
        produto.ativo = ativo
        produto.save(update_fields=['ativo'])


class CompraService:

    @staticmethod
    def _validar_item(item, numero):
        prefixo = f'Produto {numero}'
        textos = {}
        for campo, rotulo, limite in [('codigo_marca', 'código', 50), ('nome', 'nome', 100),
                                      ('tamanho', 'tamanho', 10), ('cor', 'cor', 30)]:
            texto = (item.get(campo) or '').strip()
            if not texto:
                raise RegraNegocioError(f'{prefixo}: informe o {rotulo}.')
            if len(texto) > limite:
                raise RegraNegocioError(f'{prefixo}: o {rotulo} pode ter no máximo {limite} caracteres.')
            textos[campo] = texto
        return {
            **textos,
            'preco_custo': ler_decimal(item.get('preco_custo'), f'{prefixo} - preço de custo'),
            'preco_venda': ler_decimal(item.get('preco_venda'), f'{prefixo} - preço de venda'),
            'quantidade': ler_inteiro(item.get('quantidade'), f'{prefixo} - quantidade', minimo=1),
        }

    @staticmethod
    def registrar(data, observacoes, itens):
        """Registra um lote. Produto já cadastrado (mesmo código, tamanho e cor) tem o estoque somado."""
        data = ler_data(data, 'Data da compra')
        validados = [CompraService._validar_item(item, n) for n, item in enumerate(itens, start=1)]
        if not validados:
            raise RegraNegocioError('Adicione ao menos um produto à compra.')
        total = sum((i['preco_custo'] * i['quantidade'] for i in validados), ZERO)

        with transaction.atomic():
            compra = Compra.objects.create(data=data, valor_total=total, observacoes=(observacoes or '').strip() or None)
            for item in validados:
                quantidade = item.pop('quantidade')
                produto = ProdutoRepository.buscar_por_sku(item['codigo_marca'], item['tamanho'], item['cor'])
                if produto is None:
                    Produto.objects.create(**item, quantidade_estoque=quantidade, compra=compra)
                    continue
                produto.nome = item['nome']
                produto.preco_custo = item['preco_custo']
                produto.preco_venda = item['preco_venda']
                produto.quantidade_estoque = F('quantidade_estoque') + quantidade
                produto.ativo = True
                produto.compra = compra
                produto.save()
        return compra


class VendaService:

    @staticmethod
    def calcular_total(subtotal, desconto_percentual):
        return (subtotal * (100 - desconto_percentual) / 100).quantize(CENTAVO, ROUND_HALF_UP)

    @staticmethod
    def calcular_saldo_devedor(venda):
        return venda.total - PagamentoRepository.total_da_venda(venda)

    @staticmethod
    def criar(cliente_id, data, forma_pagamento, desconto_percentual, quantidades, origem='direta', prova=None):
        """Cria a venda calculando o total no servidor. `quantidades` mapeia produto_id -> quantidade."""
        cliente = _buscar_cliente(cliente_id)
        data = ler_data(data, 'Data da venda')
        if forma_pagamento not in FORMAS_PAGAMENTO:
            raise RegraNegocioError('Selecione a forma de pagamento.')
        desconto = ler_inteiro(desconto_percentual or 0, 'Desconto')
        if desconto not in DESCONTOS_VALIDOS:
            raise RegraNegocioError('Desconto inválido.')
        if forma_pagamento == 'fiado':
            desconto = 0  # desconto só vale para pagamento à vista

        itens = {}
        for produto_id, quantidade in quantidades.items():
            (pid,) = ler_ids([produto_id])
            itens[pid] = ler_inteiro(quantidade, 'Quantidade', minimo=1)
        if not itens:
            raise RegraNegocioError('Selecione ao menos um produto.')

        with transaction.atomic():
            produtos = ProdutoRepository.bloquear(itens)
            reservados = ProdutoRepository.quantidade_reservada(itens)
            for pid, quantidade in itens.items():
                produto = produtos.get(pid)
                if produto is None or (origem == 'direta' and not produto.ativo):
                    raise RegraNegocioError('Um dos produtos selecionados não existe ou está inativo.')
                # Na conversão de prova a peça já está com a cliente, então reservas não contam
                reservado = 0 if origem == 'prova' else reservados.get(pid, 0)
                disponivel = produto.quantidade_estoque - reservado
                if quantidade > disponivel:
                    raise RegraNegocioError(
                        f'Estoque insuficiente para "{produto}": disponível {max(disponivel, 0)}.')

            subtotal = sum((produtos[pid].preco_venda * qtd for pid, qtd in itens.items()), ZERO)
            venda = Venda.objects.create(
                cliente=cliente, data=data, forma_pagamento=forma_pagamento, desconto_percentual=desconto,
                origem=origem, prova=prova, total=VendaService.calcular_total(subtotal, desconto),
            )
            for pid, quantidade in itens.items():
                produto = produtos[pid]
                ItemVenda.objects.create(
                    venda=venda, produto=produto, quantidade=quantidade,
                    preco_unitario=produto.preco_venda, custo_unitario=produto.preco_custo,
                )
                produto.quantidade_estoque -= quantidade
                produto.save(update_fields=['quantidade_estoque'])

            if forma_pagamento == 'avista':
                PagamentoRepository.criar(venda, data, venda.total)
        return venda

    @staticmethod
    def registrar_pagamento(venda, data, valor):
        data = ler_data(data, 'Data do pagamento')
        valor = ler_decimal(valor, 'Valor')
        if valor <= 0:
            raise RegraNegocioError('O valor do pagamento deve ser maior que zero.')
        with transaction.atomic():
            venda = Venda.objects.select_for_update().get(pk=venda.pk)
            saldo = VendaService.calcular_saldo_devedor(venda)
            if valor > saldo:
                raise RegraNegocioError(f'O valor é maior que o saldo devedor (R$ {moeda(saldo)}).')
            return PagamentoRepository.criar(venda, data, valor)

    @staticmethod
    def excluir(venda):
        """Exclui a venda devolvendo as peças ao estoque. Se veio de prova, a prova volta a ficar aberta."""
        with transaction.atomic():
            for item in venda.itens.all():
                Produto.objects.filter(pk=item.produto_id).update(
                    quantidade_estoque=F('quantidade_estoque') + item.quantidade)
            if venda.prova_id:
                ItemProva.objects.filter(prova_id=venda.prova_id, resultado='vendido').update(resultado='pendente')
                Prova.objects.filter(pk=venda.prova_id).update(status='em_prova')
            venda.delete()


class ProvaService:

    @staticmethod
    def criar(cliente_id, data_saida, data_devolucao_prevista, produto_ids):
        cliente = _buscar_cliente(cliente_id)
        data_saida = ler_data(data_saida, 'Data de saída')
        data_devolucao = ler_data(data_devolucao_prevista, 'Devolução prevista', obrigatoria=False)
        if data_devolucao and data_devolucao < data_saida:
            raise RegraNegocioError('A devolução prevista não pode ser antes da data de saída.')
        ids = ler_ids(produto_ids)
        if not ids:
            raise RegraNegocioError('Selecione ao menos um produto para a prova.')

        with transaction.atomic():
            produtos = ProdutoRepository.bloquear(ids)
            reservados = ProdutoRepository.quantidade_reservada(ids)
            for pid in ids:
                produto = produtos.get(pid)
                if produto is None or not produto.ativo:
                    raise RegraNegocioError('Um dos produtos selecionados não existe ou está inativo.')
                if produto.quantidade_estoque - reservados.get(pid, 0) < 1:
                    raise RegraNegocioError(f'"{produto}" não está disponível (sem estoque ou já em outra prova).')
            prova = Prova.objects.create(
                cliente=cliente, data_saida=data_saida, data_devolucao_prevista=data_devolucao, status='em_prova')
            ItemProva.objects.bulk_create([ItemProva(prova=prova, produto_id=pid) for pid in ids])
        return prova

    @staticmethod
    def resolver(prova, itens_vendidos_ids, forma_pagamento, desconto_percentual, data=None):
        """Fecha a prova: os itens marcados viram venda e o restante volta para a loja."""
        vendidos_ids = ler_ids(itens_vendidos_ids)
        with transaction.atomic():
            prova = ProvaRepository.bloquear(prova.pk)
            if prova.status != 'em_prova':
                raise RegraNegocioError('Esta prova já foi resolvida.')
            pendentes = {item.id: item for item in prova.itens.filter(resultado='pendente')}
            if not vendidos_ids <= pendentes.keys():
                raise RegraNegocioError('Seleção de itens inválida.')

            ItemProva.objects.filter(id__in=pendentes.keys() - vendidos_ids).update(resultado='devolvido')
            ItemProva.objects.filter(id__in=vendidos_ids).update(resultado='vendido')

            venda = None
            if vendidos_ids:
                quantidades = Counter(pendentes[i].produto_id for i in vendidos_ids)
                venda = VendaService.criar(
                    prova.cliente_id, data or date.today().isoformat(), forma_pagamento,
                    desconto_percentual, quantidades, origem='prova', prova=prova,
                )
            prova.status = 'convertida' if venda else 'devolvida'
            prova.save(update_fields=['status'])
        return venda


class RelatorioService:

    @staticmethod
    def calcular_resumo_mensal(mes, ano):
        vendas = list(VendaRepository.filtrar_por_mes_ano(mes, ano))
        despesas = list(DespesaRepository.filtrar_por_mes_ano(mes, ano))

        faturamento = sum((v.total for v in vendas), ZERO)
        cmv = VendaRepository.custo_das_vendas(mes, ano)
        recebido = PagamentoRepository.total_por_mes_ano(mes, ano)
        total_despesas = sum((d.valor for d in despesas), ZERO)
        total_compras = sum((c.valor_total for c in CompraRepository.filtrar_por_mes_ano(mes, ano)), ZERO)
        lucro_bruto = faturamento - cmv

        return {
            'faturamento': faturamento,
            'cmv': cmv,
            'lucro_bruto': lucro_bruto,
            'total_despesas': total_despesas,
            'lucro_liquido': lucro_bruto - total_despesas,
            'recebido': recebido,
            'total_compras': total_compras,
            'saldo_caixa': recebido - total_despesas - total_compras,
            'a_receber': VendaRepository.total_em_aberto(),
            'vendas': vendas,
            'despesas': despesas,
        }
