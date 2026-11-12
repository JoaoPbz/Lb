from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from core.models import Despesa, Produto, Prova, Venda
from core.services import ProvaService, VendaService

from . import fabricas
from .fabricas import HOJE


class TelasTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.cliente = fabricas.cliente()
        cls.produto = fabricas.produto(estoque=5)
        cls.venda = VendaService.criar(cls.cliente.id, HOJE.isoformat(), 'fiado', 0, {cls.produto.id: 1})
        cls.prova = ProvaService.criar(cls.cliente.id, HOJE.isoformat(), '', [cls.produto.id])
        cls.despesa = Despesa.objects.create(descricao='Frete', valor=Decimal('12.50'), data=HOJE)

    def test_todas_as_telas_abrem(self):
        urls = [
            reverse('dashboard'), reverse('clientes'), reverse('novo_cliente'),
            reverse('editar_cliente', args=[self.cliente.id]), reverse('perfil_cliente', args=[self.cliente.id]),
            reverse('produtos'), reverse('produtos_inativos'), reverse('editar_produto', args=[self.produto.id]),
            reverse('nova_compra'), reverse('provas'), reverse('nova_prova'),
            reverse('detalhe_prova', args=[self.prova.id]), reverse('vendas'), reverse('vendas') + '?filtro=aberto',
            reverse('vendas') + '?filtro=quitado', reverse('nova_venda'), reverse('detalhe_venda', args=[self.venda.id]),
            reverse('despesas'), reverse('nova_despesa'), reverse('editar_despesa', args=[self.despesa.id]),
            reverse('restaurar_backup'),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_exportacoes(self):
        for url in [reverse('exportar_extrato', args=[self.cliente.id]), reverse('exportar_clientes_excel')]:
            resposta = self.client.get(url)
            self.assertEqual(resposta.status_code, 200)
            self.assertIn('spreadsheetml', resposta['Content-Type'])
        self.assertIn('backup_', self.client.get(reverse('backup'))['Content-Disposition'])

    def test_dashboard_com_parametros_invalidos(self):
        resposta = self.client.get(reverse('dashboard') + '?mes=abc&ano=99999')
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Fiado a receber')

    def test_edicao_mostra_valores_preenchidos(self):
        # Antes o filtro moeda gerava " 59,90", que o <input type=number> descartava
        produto = self.client.get(reverse('editar_produto', args=[self.produto.id]))
        self.assertContains(produto, 'value="59.90"')
        despesa = self.client.get(reverse('editar_despesa', args=[self.despesa.id]))
        self.assertContains(despesa, 'value="12.50"')
        self.assertContains(despesa, 'value="2026-11-12"')

    def test_exclusoes_nao_aceitam_get(self):
        urls = [
            reverse('excluir_cliente', args=[self.cliente.id]), reverse('excluir_produto', args=[self.produto.id]),
            reverse('reativar_produto', args=[self.produto.id]), reverse('excluir_prova', args=[self.prova.id]),
            reverse('resolver_prova', args=[self.prova.id]), reverse('excluir_venda', args=[self.venda.id]),
            reverse('novo_pagamento', args=[self.venda.id]), reverse('excluir_despesa', args=[self.despesa.id]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 405)


class FluxosTest(TestCase):

    def setUp(self):
        self.cliente = fabricas.cliente()
        self.produto = fabricas.produto(venda='59.90', estoque=2)

    def test_nova_venda_ignora_total_enviado_pelo_navegador(self):
        resposta = self.client.post(reverse('nova_venda'), {
            'cliente_id': self.cliente.id, 'data': '2026-11-12', 'forma_pagamento': 'fiado',
            'produtos[]': [self.produto.id], f'quantidade_{self.produto.id}': '2', 'total': '1.00',
        })
        self.assertRedirects(resposta, reverse('vendas'))
        self.assertEqual(Venda.objects.get().total, Decimal('119.80'))

    def test_nova_venda_invalida_mostra_erro(self):
        resposta = self.client.post(reverse('nova_venda'), {
            'cliente_id': self.cliente.id, 'data': '2026-11-12', 'forma_pagamento': 'fiado',
            'produtos[]': [self.produto.id], f'quantidade_{self.produto.id}': '5',
        }, follow=True)
        self.assertContains(resposta, 'Estoque insuficiente')
        self.assertFalse(Venda.objects.exists())

    def test_resolver_prova_como_devolvida(self):
        # Regressão: antes dava erro 500 (variável forma_pagamento indefinida)
        prova = ProvaService.criar(self.cliente.id, '2026-11-12', '', [self.produto.id])
        resposta = self.client.post(reverse('resolver_prova', args=[prova.id]), {'forma_pagamento': 'fiado'})
        self.assertRedirects(resposta, reverse('detalhe_prova', args=[prova.id]))
        prova.refresh_from_db()
        self.assertEqual(prova.status, 'devolvida')
        self.assertFalse(Venda.objects.exists())

    def test_resolver_prova_a_vista_pela_tela(self):
        prova = ProvaService.criar(self.cliente.id, '2026-11-12', '', [self.produto.id])
        item = prova.itens.get()
        self.client.post(reverse('resolver_prova', args=[prova.id]), {
            'itens_vendidos[]': [item.id], 'forma_pagamento': 'avista', 'desconto_percentual': '5',
            'data': '2026-11-12'})
        venda = Venda.objects.get()
        self.assertEqual(venda.total, Decimal('56.91'))
        self.assertEqual(VendaService.calcular_saldo_devedor(venda), 0)
        self.assertEqual(Prova.objects.get().status, 'convertida')

    def test_registrar_pagamento_acima_do_saldo(self):
        venda = VendaService.criar(self.cliente.id, '2026-11-12', 'fiado', 0, {self.produto.id: 1})
        resposta = self.client.post(reverse('novo_pagamento', args=[venda.id]),
                                    {'data': '2026-11-12', 'valor': '100'}, follow=True)
        self.assertContains(resposta, 'maior que o saldo devedor')
        self.assertFalse(venda.pagamentos.exists())

    def test_nova_compra_com_produto_existente(self):
        dados = {'data': '2026-11-12', 'codigo_marca[]': [self.produto.codigo_marca], 'nome[]': ['Blusa'],
                 'tamanho[]': ['M'], 'cor[]': ['Azul'], 'preco_custo[]': ['30'], 'preco_venda[]': ['59.90'],
                 'quantidade[]': ['3']}
        resposta = self.client.post(reverse('nova_compra'), dados)
        self.assertRedirects(resposta, reverse('produtos'))
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, 5)

    def test_editar_produto_para_sku_duplicado_mostra_erro(self):
        outro = fabricas.produto(codigo='200')
        resposta = self.client.post(reverse('editar_produto', args=[outro.id]), {
            'codigo_marca': self.produto.codigo_marca, 'nome': 'X', 'tamanho': 'M', 'cor': 'Azul',
            'preco_custo': '1', 'preco_venda': '2', 'quantidade_estoque': '1'})
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'já existe')
        outro.refresh_from_db()
        self.assertEqual(outro.codigo_marca, '200')

    def test_estoque_nao_pode_ficar_abaixo_das_pecas_em_prova(self):
        ProvaService.criar(self.cliente.id, '2026-11-12', '', [self.produto.id])
        resposta = self.client.post(reverse('editar_produto', args=[self.produto.id]), {
            'codigo_marca': '100', 'nome': 'Blusa', 'tamanho': 'M', 'cor': 'Azul',
            'preco_custo': '30', 'preco_venda': '59.90', 'quantidade_estoque': '0'})
        self.assertContains(resposta, 'em prova')
        self.assertEqual(Produto.objects.get(id=self.produto.id).quantidade_estoque, 2)

    def test_excluir_cliente_com_venda_mostra_erro(self):
        VendaService.criar(self.cliente.id, '2026-11-12', 'fiado', 0, {self.produto.id: 1})
        resposta = self.client.post(reverse('excluir_cliente', args=[self.cliente.id]), follow=True)
        self.assertContains(resposta, 'não pode ser excluído')
