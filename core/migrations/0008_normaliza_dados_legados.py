from django.db import migrations
from django.db.models import OuterRef, Subquery, Sum


def normalizar(apps, schema_editor):
    """Ajusta registros criados antes da versão com provas parciais.

    Mesma regra de core.backup.normalizar_dados_legados, replicada aqui porque
    migrações não podem depender do código atual dos models.
    """
    ItemProva = apps.get_model('core', 'ItemProva')
    ItemVenda = apps.get_model('core', 'ItemVenda')
    Produto = apps.get_model('core', 'Produto')
    Venda = apps.get_model('core', 'Venda')
    Pagamento = apps.get_model('core', 'Pagamento')

    # Antes, converter uma prova vendia todas as peças dela
    ItemProva.objects.filter(prova__status='convertida', resultado='pendente').update(resultado='vendido')
    ItemProva.objects.filter(prova__status='devolvida', resultado='pendente').update(resultado='devolvido')

    custo = Produto.objects.filter(pk=OuterRef('produto_id')).values('preco_custo')[:1]
    ItemVenda.objects.filter(custo_unitario__isnull=True).update(custo_unitario=Subquery(custo))

    # Provas convertidas à vista não registravam o pagamento
    for venda in Venda.objects.filter(forma_pagamento='avista'):
        pago = Pagamento.objects.filter(venda=venda).aggregate(s=Sum('valor'))['s'] or 0
        if pago < venda.total:
            Pagamento.objects.create(venda=venda, data=venda.data, valor=venda.total - pago)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_integridade_e_provas_parciais'),
    ]

    operations = [
        migrations.RunPython(normalizar, migrations.RunPython.noop),
    ]
