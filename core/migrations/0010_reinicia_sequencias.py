from django.core.management.color import no_style
from django.db import migrations

MODELOS = ['Cliente', 'Compra', 'Produto', 'Prova', 'ItemProva', 'Venda', 'ItemVenda', 'Pagamento', 'Despesa']


def reiniciar_sequencias(apps, schema_editor):
    """Acerta o próximo id de cada tabela.

    A restauração de backup das versões antigas gravava ids explícitos sem avançar as
    sequências do PostgreSQL, e o cadastro seguinte falhava com chave duplicada (erro 500).
    Em um banco que já está correto, isto não muda nada.
    """
    modelos = [apps.get_model('core', nome) for nome in MODELOS]
    for sql in schema_editor.connection.ops.sequence_reset_sql(no_style(), modelos):
        schema_editor.execute(sql)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_forma_pagamento_cartao_e_a_prazo'),
    ]

    operations = [
        migrations.RunPython(reiniciar_sequencias, migrations.RunPython.noop),
    ]
