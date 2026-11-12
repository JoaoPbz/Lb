from decimal import Decimal

from django.test import TestCase

from core.models import Compra, ItemProva, Pagamento, Produto, Venda
from core.repositories import ProdutoRepository
from core.services import (
    ClienteService, CompraService, ProvaService, RegraNegocioError, RelatorioService, VendaService, ler_decimal,
)
from core.templatetags.filtros import moeda

from . import fabricas
from .fabricas import HOJE


class LeituraDeValoresTest(TestCase):

    def test_aceita_ponto_ou_virgula_decimal(self):
        self.assertEqual(ler_decimal('59.90', 'x'), Decimal('59.90'))
        self.assertEqual(ler_decimal('1.234,50', 'x'), Decimal('1234.50'))

    def test_rejeita_negativo_e_texto(self):
        for valor in ['-1', 'abc', '', None, 'NaN']:
            with self.assertRaises(RegraNegocioError):
                ler_decimal(valor, 'x')

    def test_filtro_moeda(self):
        self.assertEqual(moeda(Decimal('1234.5')), '1.234,50')
        self.assertEqual(moeda(Decimal('59.9')), '59,90')
        self.assertEqual(moeda(''), '')


class VendaServiceTest(TestCase):

    def setUp(self):
        self.cliente = fabricas.cliente()
        self.blusa = fabricas.produto(venda='59.90', estoque=3)
        self.casaco = fabricas.produto(codigo='200', nome='Casaco', venda='1234.50', custo='600.00', estoque=1)

    def criar(self, quantidades, forma='fiado', desconto=0):
        return VendaService.criar(self.cliente.id, HOJE.isoformat(), forma, desconto, quantidades)

    def test_total_calculado_no_servidor_com_centavos(self):
        venda = self.criar({self.blusa.id: 1, self.casaco.id: 1})
        self.assertEqual(venda.total, Decimal('1294.40'))

    def test_desconto_a_vista_e_arredondamento(self):
        venda = self.criar({self.blusa.id: 1}, forma='avista', desconto=10)
        self.assertEqual(venda.total, Decimal('53.91'))

    def test_fiado_ignora_desconto(self):
        venda = self.criar({self.blusa.id: 1}, forma='fiado', desconto=10)
        self.assertEqual(venda.desconto_percentual, 0)
        self.assertEqual(venda.total, Decimal('59.90'))

    def test_desconto_fora_das_opcoes_e_rejeitado(self):
        with self.assertRaises(RegraNegocioError):
            self.criar({self.blusa.id: 1}, forma='avista', desconto=50)

    def test_a_vista_ja_nasce_quitada(self):
        venda = self.criar({self.blusa.id: 1}, forma='avista')
        self.assertEqual(VendaService.calcular_saldo_devedor(venda), 0)

    def test_quantidade_maior_que_um_baixa_estoque(self):
        venda = self.criar({self.blusa.id: 2})
        self.blusa.refresh_from_db()
        self.assertEqual(self.blusa.quantidade_estoque, 1)
        self.assertEqual(venda.total, Decimal('119.80'))
        self.assertEqual(venda.itens.get().custo_unitario, Decimal('30.00'))

    def test_nao_vende_mais_que_o_estoque(self):
        with self.assertRaisesMessage(RegraNegocioError, 'Estoque insuficiente'):
            self.criar({self.casaco.id: 2})
        self.assertFalse(Venda.objects.exists())

    def test_nao_vende_peca_reservada_em_prova(self):
        ProvaService.criar(self.cliente.id, HOJE.isoformat(), '', [self.casaco.id])
        with self.assertRaisesMessage(RegraNegocioError, 'Estoque insuficiente'):
            self.criar({self.casaco.id: 1})

    def test_venda_sem_produtos_e_rejeitada(self):
        with self.assertRaises(RegraNegocioError):
            self.criar({})

    def test_produto_inativo_nao_pode_ser_vendido(self):
        inativo = fabricas.produto(codigo='300', ativo=False)
        with self.assertRaises(RegraNegocioError):
            self.criar({inativo.id: 1})

    def test_pagamentos_parciais_e_limite_do_saldo(self):
        venda = self.criar({self.blusa.id: 1})
        VendaService.registrar_pagamento(venda, HOJE.isoformat(), '20.00')
        self.assertEqual(VendaService.calcular_saldo_devedor(venda), Decimal('39.90'))
        with self.assertRaisesMessage(RegraNegocioError, 'maior que o saldo'):
            VendaService.registrar_pagamento(venda, HOJE.isoformat(), '40.00')
        with self.assertRaises(RegraNegocioError):
            VendaService.registrar_pagamento(venda, HOJE.isoformat(), '0')
        VendaService.registrar_pagamento(venda, HOJE.isoformat(), '39.90')
        self.assertEqual(VendaService.calcular_saldo_devedor(venda), 0)

    def test_excluir_venda_devolve_estoque(self):
        venda = self.criar({self.blusa.id: 2}, forma='avista')
        VendaService.excluir(venda)
        self.blusa.refresh_from_db()
        self.assertEqual(self.blusa.quantidade_estoque, 3)
        self.assertFalse(Pagamento.objects.exists())


class ProvaServiceTest(TestCase):

    def setUp(self):
        self.cliente = fabricas.cliente()
        self.blusa = fabricas.produto(venda='59.90', custo='30.00')
        self.saia = fabricas.produto(codigo='200', nome='Saia', venda='80.00', custo='40.00')
        self.prova = ProvaService.criar(self.cliente.id, HOJE.isoformat(), '', [self.blusa.id, self.saia.id])

    def item(self, produto):
        return self.prova.itens.get(produto=produto)

    def test_prova_reserva_as_pecas(self):
        self.assertFalse(ProdutoRepository.disponiveis().exists())
        with self.assertRaisesMessage(RegraNegocioError, 'não está disponível'):
            ProvaService.criar(fabricas.cliente('Ana').id, HOJE.isoformat(), '', [self.blusa.id])

    def test_devolvida_libera_reserva_sem_criar_venda(self):
        venda = ProvaService.resolver(self.prova, [], 'fiado', 0)
        self.prova.refresh_from_db()
        self.assertIsNone(venda)
        self.assertEqual(self.prova.status, 'devolvida')
        self.assertFalse(Venda.objects.exists())
        self.assertEqual(ProdutoRepository.disponiveis().count(), 2)
        self.assertEqual(set(self.prova.itens.values_list('resultado', flat=True)), {'devolvido'})

    def test_conversao_parcial(self):
        venda = ProvaService.resolver(self.prova, [self.item(self.blusa).id], 'fiado', 0, HOJE.isoformat())
        self.prova.refresh_from_db()
        self.assertEqual(self.prova.status, 'convertida')
        self.assertEqual(venda.prova, self.prova)
        self.assertEqual(venda.origem, 'prova')
        self.assertEqual(venda.total, Decimal('59.90'))
        self.assertEqual(self.item(self.blusa).resultado, 'vendido')
        self.assertEqual(self.item(self.saia).resultado, 'devolvido')
        self.blusa.refresh_from_db()
        self.saia.refresh_from_db()
        self.assertEqual((self.blusa.quantidade_estoque, self.saia.quantidade_estoque), (0, 1))

    def test_conversao_a_vista_fica_quitada(self):
        itens = [self.item(self.blusa).id, self.item(self.saia).id]
        venda = ProvaService.resolver(self.prova, itens, 'avista', 10, HOJE.isoformat())
        self.assertEqual(venda.total, Decimal('125.91'))
        self.assertEqual(VendaService.calcular_saldo_devedor(venda), 0)

    def test_nao_resolve_duas_vezes(self):
        ProvaService.resolver(self.prova, [], 'fiado', 0)
        with self.assertRaisesMessage(RegraNegocioError, 'já foi resolvida'):
            ProvaService.resolver(self.prova, [], 'fiado', 0)

    def test_erro_na_venda_nao_deixa_prova_pela_metade(self):
        with self.assertRaises(RegraNegocioError):
            ProvaService.resolver(self.prova, [self.item(self.blusa).id], 'pix', 0)
        self.prova.refresh_from_db()
        self.assertEqual(self.prova.status, 'em_prova')
        self.assertFalse(ItemProva.objects.exclude(resultado='pendente').exists())

    def test_excluir_venda_da_prova_reabre_a_prova(self):
        venda = ProvaService.resolver(self.prova, [self.item(self.blusa).id], 'fiado', 0)
        VendaService.excluir(venda)
        self.prova.refresh_from_db()
        self.assertEqual(self.prova.status, 'em_prova')
        self.assertEqual(self.item(self.blusa).resultado, 'pendente')
        self.assertEqual(self.item(self.saia).resultado, 'devolvido')
        self.blusa.refresh_from_db()
        self.assertEqual(self.blusa.quantidade_estoque, 1)

    def test_devolucao_antes_da_saida_e_rejeitada(self):
        with self.assertRaises(RegraNegocioError):
            ProvaService.criar(self.cliente.id, '2026-11-12', '2026-11-01', [fabricas.produto(codigo='9').id])


class CompraServiceTest(TestCase):

    def item(self, **extra):
        base = {'codigo_marca': '100', 'nome': 'Blusa', 'tamanho': 'M', 'cor': 'Azul',
                'preco_custo': '30.00', 'preco_venda': '59.90', 'quantidade': '2'}
        return {**base, **extra}

    def test_cadastra_produtos_e_total(self):
        compra = CompraService.registrar(HOJE.isoformat(), '', [self.item(), self.item(codigo_marca='200')])
        self.assertEqual(compra.valor_total, Decimal('120.00'))
        self.assertEqual(Produto.objects.count(), 2)

    def test_recompra_soma_estoque_atualiza_precos_e_reativa(self):
        existente = fabricas.produto(codigo='100', cor='Azul', estoque=1, ativo=False)
        CompraService.registrar(HOJE.isoformat(), '', [self.item(cor='azul', preco_venda='65.00')])
        existente.refresh_from_db()
        self.assertEqual(Produto.objects.count(), 1)
        self.assertEqual(existente.quantidade_estoque, 3)
        self.assertEqual(existente.preco_venda, Decimal('65.00'))
        self.assertTrue(existente.ativo)

    def test_mesmo_produto_repetido_na_mesma_compra(self):
        CompraService.registrar(HOJE.isoformat(), '', [self.item(), self.item(quantidade='3')])
        self.assertEqual(Produto.objects.get().quantidade_estoque, 5)

    def test_item_invalido_nao_deixa_compra_orfa(self):
        with self.assertRaises(RegraNegocioError):
            CompraService.registrar(HOJE.isoformat(), '', [self.item(), self.item(quantidade='0')])
        self.assertFalse(Compra.objects.exists())
        self.assertFalse(Produto.objects.exists())


class ClienteERelatorioTest(TestCase):

    def setUp(self):
        self.cliente = fabricas.cliente()
        self.blusa = fabricas.produto(venda='100.00', custo='40.00', estoque=5)

    def test_saldo_e_total_do_ano(self):
        venda = VendaService.criar(self.cliente.id, '2026-03-01', 'fiado', 0, {self.blusa.id: 2})
        VendaService.registrar_pagamento(venda, '2026-03-10', '50')
        VendaService.criar(self.cliente.id, '2025-12-01', 'avista', 0, {self.blusa.id: 1})
        self.assertEqual(ClienteService.calcular_saldo_devedor(self.cliente), Decimal('150.00'))
        self.assertEqual(ClienteService.calcular_total_ano(self.cliente, 2026), Decimal('200.00'))

    def test_cliente_com_venda_nao_pode_ser_excluido(self):
        VendaService.criar(self.cliente.id, HOJE.isoformat(), 'fiado', 0, {self.blusa.id: 1})
        with self.assertRaises(RegraNegocioError):
            ClienteService.excluir(self.cliente)

    def test_resumo_mensal_separa_competencia_e_caixa(self):
        CompraService.registrar('2026-03-01', '', [{
            'codigo_marca': '9', 'nome': 'Calça', 'tamanho': 'P', 'cor': 'Preta',
            'preco_custo': '50', 'preco_venda': '90', 'quantidade': '4'}])
        fiado = VendaService.criar(self.cliente.id, '2026-03-05', 'fiado', 0, {self.blusa.id: 2})
        VendaService.criar(self.cliente.id, '2026-03-06', 'avista', 10, {self.blusa.id: 1})
        VendaService.registrar_pagamento(fiado, '2026-04-02', '80')
        from core.models import Despesa
        Despesa.objects.create(descricao='MEI', valor=Decimal('75.00'), data='2026-03-20')

        marco = RelatorioService.calcular_resumo_mensal(3, 2026)
        self.assertEqual(marco['faturamento'], Decimal('290.00'))
        self.assertEqual(marco['cmv'], Decimal('120.00'))
        self.assertEqual(marco['lucro_bruto'], Decimal('170.00'))
        self.assertEqual(marco['lucro_liquido'], Decimal('95.00'))
        self.assertEqual(marco['recebido'], Decimal('90.00'))
        self.assertEqual(marco['total_compras'], Decimal('200.00'))
        self.assertEqual(marco['saldo_caixa'], Decimal('-185.00'))
        self.assertEqual(marco['a_receber'], Decimal('120.00'))

        abril = RelatorioService.calcular_resumo_mensal(4, 2026)
        self.assertEqual(abril['faturamento'], 0)
        self.assertEqual(abril['recebido'], Decimal('80.00'))
