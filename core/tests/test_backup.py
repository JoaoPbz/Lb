import json
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from core.backup import BackupService
from core.models import Cliente, ItemProva, Prova, Venda
from core.services import ProvaService, RegraNegocioError, VendaService

from . import fabricas
from .fabricas import HOJE

BACKUP_EXEMPLO = Path(settings.BASE_DIR) / 'Backup Alimentado' / 'backup_20260615_193932.json'


class BackupTest(TestCase):

    def setUp(self):
        self.cliente = fabricas.cliente()
        produto = fabricas.produto(estoque=3)
        VendaService.criar(self.cliente.id, HOJE.isoformat(), 'fiado', 0, {produto.id: 1})
        ProvaService.criar(self.cliente.id, HOJE.isoformat(), '', [produto.id])

    def test_exportar_e_restaurar(self):
        conteudo = BackupService.exportar()
        Cliente.objects.create(nome='Some depois', telefone='0')
        BackupService.restaurar(conteudo.encode('utf-8'))
        self.assertEqual(list(Cliente.objects.values_list('nome', flat=True)), ['Maria'])
        self.assertEqual(Venda.objects.count(), 1)
        self.assertEqual(Prova.objects.get().status, 'em_prova')

    def test_cadastro_funciona_depois_de_restaurar(self):
        # Sem reiniciar as sequências do PostgreSQL, este create colidiria com um id restaurado
        dados = json.loads(BackupService.exportar())
        dados['Cliente'][0]['pk'] = 500
        for modelo in ['Venda', 'Prova']:
            for registro in dados[modelo]:
                registro['fields']['cliente'] = 500
        BackupService.restaurar(json.dumps(dados))
        novo = Cliente.objects.create(nome='Nova', telefone='1')
        self.assertGreater(novo.id, 500)

    def test_arquivo_invalido_nao_apaga_nada(self):
        for conteudo in [b'nao e json', b'[1, 2]', b'{"Tabela": []}']:
            with self.subTest(conteudo=conteudo):
                with self.assertRaises(RegraNegocioError):
                    BackupService.restaurar(conteudo)
        self.assertEqual(Cliente.objects.count(), 1)

    def test_falha_no_meio_desfaz_tudo(self):
        dados = json.loads(BackupService.exportar())
        dados['Venda'][0]['fields']['cliente'] = 9999  # chave estrangeira quebrada
        with self.assertRaises(RegraNegocioError):
            BackupService.restaurar(json.dumps(dados))
        self.assertEqual(Cliente.objects.get().nome, 'Maria')
        self.assertEqual(Venda.objects.count(), 1)

    def test_restaurar_backup_de_exemplo_da_versao_antiga(self):
        BackupService.restaurar(BACKUP_EXEMPLO.read_bytes())
        self.assertEqual(Cliente.objects.count(), 4)
        for prova in Prova.objects.exclude(status='em_prova'):
            esperado = 'vendido' if prova.status == 'convertida' else 'devolvido'
            self.assertEqual(set(prova.itens.values_list('resultado', flat=True)) - {esperado}, set())
        self.assertFalse(ItemProva.objects.filter(prova__status='convertida', resultado='pendente').exists())
        for venda in Venda.objects.filter(forma_pagamento='avista'):
            self.assertEqual(VendaService.calcular_saldo_devedor(venda), Decimal('0'))
        self.assertTrue(all(i.custo_unitario is not None for v in Venda.objects.all() for i in v.itens.all()))

    def test_tela_de_restaurar(self):
        arquivo = SimpleUploadedFile('backup.json', BackupService.exportar().encode('utf-8'))
        resposta = self.client.post(reverse('restaurar_backup'), {'arquivo': arquivo})
        self.assertRedirects(resposta, reverse('dashboard'))
        ruim = SimpleUploadedFile('backup.json', b'lixo')
        resposta = self.client.post(reverse('restaurar_backup'), {'arquivo': ruim}, follow=True)
        self.assertContains(resposta, 'não é um backup válido')
