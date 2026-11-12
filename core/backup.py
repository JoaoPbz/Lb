import json

from django.core import serializers
from django.core.management.color import no_style
from django.core.serializers.base import DeserializationError
from django.db import DatabaseError, connection, transaction
from django.db.models import OuterRef, Subquery

from .models import Cliente, Compra, Despesa, ItemProva, ItemVenda, Pagamento, Produto, Prova, Venda
from .repositories import PagamentoRepository
from .services import RegraNegocioError

# Ordem em que as tabelas são restauradas (respeita as chaves estrangeiras)
MODELOS = [Cliente, Compra, Produto, Prova, ItemProva, Venda, ItemVenda, Pagamento, Despesa]


def normalizar_dados_legados():
    """Ajusta dados de backups gerados antes das provas parciais (mesma regra da migração 0008)."""
    ItemProva.objects.filter(prova__status='convertida', resultado='pendente').update(resultado='vendido')
    ItemProva.objects.filter(prova__status='devolvida', resultado='pendente').update(resultado='devolvido')

    custo = Produto.objects.filter(pk=OuterRef('produto_id')).values('preco_custo')[:1]
    ItemVenda.objects.filter(custo_unitario__isnull=True).update(custo_unitario=Subquery(custo))

    for venda in Venda.objects.filter(forma_pagamento='avista'):
        pago = PagamentoRepository.total_da_venda(venda)
        if pago < venda.total:
            PagamentoRepository.criar(venda, venda.data, venda.total - pago)


class BackupService:

    @staticmethod
    def exportar():
        dados = {
            modelo.__name__: json.loads(serializers.serialize('json', modelo.objects.order_by('pk')))
            for modelo in MODELOS
        }
        return json.dumps(dados, indent=2, ensure_ascii=False)

    @staticmethod
    def restaurar(conteudo):
        """Substitui todos os dados pelos do backup. Se algo falhar, nada é alterado."""
        try:
            dados = json.loads(conteudo.decode('utf-8-sig') if isinstance(conteudo, bytes) else conteudo)
        except (UnicodeDecodeError, ValueError):
            raise RegraNegocioError('O arquivo não é um backup válido (JSON ilegível).')
        nomes_validos = {m.__name__ for m in MODELOS}
        if not isinstance(dados, dict) or not dados or not set(dados) <= nomes_validos:
            raise RegraNegocioError('O arquivo não é um backup deste sistema.')

        try:
            with transaction.atomic():
                for modelo in reversed(MODELOS):
                    modelo.objects.all().delete()
                for modelo in MODELOS:
                    registros = dados.get(modelo.__name__, [])
                    for obj in serializers.deserialize('json', json.dumps(registros)):
                        obj.save()
                normalizar_dados_legados()
                BackupService._reiniciar_sequencias()
                # As chaves estrangeiras só seriam conferidas no commit; confere já para cair no except
                connection.check_constraints()
        except (DeserializationError, DatabaseError, KeyError, TypeError, ValueError) as erro:
            raise RegraNegocioError(f'Não foi possível restaurar o backup; nenhum dado foi alterado. ({erro})')

    @staticmethod
    def _reiniciar_sequencias():
        # Registros salvos com id explícito não avançam a sequência do PostgreSQL;
        # sem isso, o próximo cadastro tentaria reutilizar um id existente.
        with connection.cursor() as cursor:
            for sql in connection.ops.sequence_reset_sql(no_style(), MODELOS):
                cursor.execute(sql)
