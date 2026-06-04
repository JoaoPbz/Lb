from django.shortcuts import render, redirect
from .models import Cliente
from .models import Cliente, Produto
from .models import Cliente, Produto, Compra
from datetime import date
from .models import Cliente, Produto, Compra, Prova, ItemProva, Venda, ItemVenda
from .models import Cliente, Produto, Compra, Prova, ItemProva, Venda, ItemVenda, Pagamento
from .models import Cliente, Produto, Compra, Prova, ItemProva, Venda, ItemVenda, Pagamento, Despesa
from datetime import date

def clientes(request):
    lista_clientes = Cliente.objects.all()
    return render(request, 'core/clientes.html', {'clientes': lista_clientes})

def novo_cliente(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        telefone = request.POST.get('telefone')
        Cliente.objects.create(nome=nome, telefone=telefone)
        return redirect('clientes')
    return render(request, 'core/cliente_form.html')
from django.shortcuts import render, redirect, get_object_or_404

def editar_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    if request.method == 'POST':
        cliente.nome = request.POST.get('nome')
        cliente.telefone = request.POST.get('telefone')
        cliente.save()
        return redirect('clientes')
    return render(request, 'core/cliente_form.html', {'cliente': cliente})

def excluir_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    cliente.delete()
    return redirect('clientes')


def produtos(request):
    lista_produtos = Produto.objects.all()
    return render(request, 'core/produtos.html', {'produtos': lista_produtos})

def editar_produto(request, id):
    produto = get_object_or_404(Produto, id=id)
    if request.method == 'POST':
        produto.codigo_marca = request.POST.get('codigo_marca')
        produto.nome = request.POST.get('nome')
        produto.tamanho = request.POST.get('tamanho')
        produto.cor = request.POST.get('cor')
        produto.preco_custo = request.POST.get('preco_custo')
        produto.preco_venda = request.POST.get('preco_venda')
        produto.quantidade_estoque = request.POST.get('quantidade_estoque')
        produto.save()
        return redirect('produtos')
    return render(request, 'core/produto_form.html', {'produto': produto})

def excluir_produto(request, id):
    produto = get_object_or_404(Produto, id=id)
    produto.delete()
    return redirect('produtos')



def nova_compra(request):
    if request.method == 'POST':
        data = request.POST.get('data')
        observacoes = request.POST.get('observacoes')
        
        codigos = request.POST.getlist('codigo_marca[]')
        nomes = request.POST.getlist('nome[]')
        tamanhos = request.POST.getlist('tamanho[]')
        cores = request.POST.getlist('cor[]')
        precos_custo = request.POST.getlist('preco_custo[]')
        precos_venda = request.POST.getlist('preco_venda[]')
        quantidades = request.POST.getlist('quantidade[]')

        total = sum(float(p) for p in precos_custo)

        compra = Compra.objects.create(data=data, valor_total=total, observacoes=observacoes)

        for i in range(len(codigos)):
            Produto.objects.create(
                codigo_marca=codigos[i],
                nome=nomes[i],
                tamanho=tamanhos[i],
                cor=cores[i],
                preco_custo=precos_custo[i],
                preco_venda=precos_venda[i],
                quantidade_estoque=int(quantidades[i]),
                compra=compra
            )

        return redirect('produtos')
    return render(request, 'core/nova_compra.html')


def provas(request):
    lista_provas = Prova.objects.all().order_by('-data_saida')
    return render(request, 'core/provas.html', {'provas': lista_provas})

def nova_prova(request):
    if request.method == 'POST':
        cliente_id = request.POST.get('cliente_id')
        data_saida = request.POST.get('data_saida')
        data_devolucao = request.POST.get('data_devolucao_prevista')
        produtos_ids = request.POST.getlist('produtos[]')

        prova = Prova.objects.create(
            cliente_id=cliente_id,
            data_saida=data_saida,
            data_devolucao_prevista=data_devolucao if data_devolucao else None,
            status='em_prova'
        )

        for produto_id in produtos_ids:
            ItemProva.objects.create(prova=prova, produto_id=produto_id)

        return redirect('provas')

    clientes = Cliente.objects.all()
    produtos = Produto.objects.filter(quantidade_estoque__gt=0)
    return render(request, 'core/nova_prova.html', {'clientes': clientes, 'produtos': produtos})

def detalhe_prova(request, id):
    prova = get_object_or_404(Prova, id=id)
    return render(request, 'core/detalhe_prova.html', {'prova': prova})

def resolver_prova(request, id):
    prova = get_object_or_404(Prova, id=id)
    if request.method == 'POST':
        prova.status = request.POST.get('status')
        prova.save()
        return redirect('detalhe_prova', id=prova.id)
    return redirect('provas')

def excluir_prova(request, id):
    prova = get_object_or_404(Prova, id=id)
    prova.delete()
    return redirect('provas')


def vendas(request):
    lista_vendas = Venda.objects.all().order_by('-data')
    filtro = request.GET.get('filtro')

    for venda in lista_vendas:
        total_pago = sum(p.valor for p in venda.pagamentos.all())
        venda.saldo_devedor = venda.total - total_pago

    if filtro == 'aberto':
        lista_vendas = [v for v in lista_vendas if v.saldo_devedor > 0]
    elif filtro == 'quitado':
        lista_vendas = [v for v in lista_vendas if v.saldo_devedor <= 0]

    return render(request, 'core/vendas.html', {'vendas': lista_vendas, 'filtro': filtro})

def nova_venda(request):
    if request.method == 'POST':
        cliente_id = request.POST.get('cliente_id')
        data = request.POST.get('data')
        forma_pagamento = request.POST.get('forma_pagamento')
        desconto_percentual = int(request.POST.get('desconto_percentual', 0))
        total = request.POST.get('total')
        produtos_ids = request.POST.getlist('produtos[]')

        venda = Venda.objects.create(
            cliente_id=cliente_id,
            data=data,
            forma_pagamento=forma_pagamento,
            desconto_percentual=desconto_percentual,
            total=total,
            origem='direta'
        )

        for produto_id in produtos_ids:
            produto = Produto.objects.get(id=produto_id)
            ItemVenda.objects.create(
                venda=venda,
                produto=produto,
                quantidade=1,
                preco_unitario=produto.preco_venda
            )
            produto.quantidade_estoque -= 1
            produto.save()

        if forma_pagamento == 'avista':
            Pagamento.objects.create(
                venda=venda,
                data=data,
                valor=total
            )

        return redirect('vendas')

    clientes = Cliente.objects.all()
    produtos = Produto.objects.filter(quantidade_estoque__gt=0)
    return render(request, 'core/nova_venda.html', {'clientes': clientes, 'produtos': produtos})

def detalhe_venda(request, id):
    venda = get_object_or_404(Venda, id=id)
    return render(request, 'core/detalhe_venda.html', {'venda': venda})

def novo_pagamento(request, id):
    venda = get_object_or_404(Venda, id=id)
    if request.method == 'POST':
        data = request.POST.get('data')
        valor = request.POST.get('valor')
        Pagamento.objects.create(venda=venda, data=data, valor=valor)
        return redirect('detalhe_venda', id=venda.id)
    return redirect('vendas')

def excluir_venda(request, id):
    venda = get_object_or_404(Venda, id=id)
    for item in venda.itens.all():
        item.produto.quantidade_estoque += item.quantidade
        item.produto.save()
    venda.delete()
    return redirect('vendas')


def despesas(request):
    lista_despesas = Despesa.objects.all().order_by('-data')
    return render(request, 'core/despesas.html', {'despesas': lista_despesas})

def nova_despesa(request):
    if request.method == 'POST':
        Despesa.objects.create(
            descricao=request.POST.get('descricao'),
            valor=request.POST.get('valor'),
            data=request.POST.get('data'),
            categoria=request.POST.get('categoria')
        )
        return redirect('despesas')
    return render(request, 'core/despesa_form.html')

def editar_despesa(request, id):
    despesa = get_object_or_404(Despesa, id=id)
    if request.method == 'POST':
        despesa.descricao = request.POST.get('descricao')
        despesa.valor = request.POST.get('valor')
        despesa.data = request.POST.get('data')
        despesa.categoria = request.POST.get('categoria')
        despesa.save()
        return redirect('despesas')
    return render(request, 'core/despesa_form.html', {'despesa': despesa})

def excluir_despesa(request, id):
    despesa = get_object_or_404(Despesa, id=id)
    despesa.delete()
    return redirect('despesas')


def perfil_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    vendas = cliente.vendas.all().order_by('-data')
    provas = cliente.provas.all().order_by('-data_saida')

    for venda in vendas:
        total_pago = sum(p.valor for p in venda.pagamentos.all())
        venda.saldo_devedor = venda.total - total_pago

    saldo_devedor = sum(v.saldo_devedor for v in vendas)
    total_ano = sum(v.total for v in vendas if v.data.year == date.today().year)
    provas_abertas = provas.filter(status='em_prova').count()

    return render(request, 'core/perfil_cliente.html', {
        'cliente': cliente,
        'vendas': vendas,
        'provas': provas,
        'saldo_devedor': saldo_devedor,
        'total_ano': total_ano,
        'provas_abertas': provas_abertas,
    })
    
def dashboard(request):
    hoje = date.today()
    mes = int(request.GET.get('mes', hoje.month))
    ano = int(request.GET.get('ano', hoje.year))
    anos = list(range(2024, hoje.year + 2))

    vendas = Venda.objects.filter(data__month=mes, data__year=ano)
    despesas = Despesa.objects.filter(data__month=mes, data__year=ano)
    compras = Compra.objects.filter(data__month=mes, data__year=ano)

    total_vendido = sum(v.total for v in vendas)
    total_despesas = sum(d.valor for d in despesas)
    total_compras = sum(c.valor_total for c in compras)
    lucro = total_vendido - total_despesas - total_compras

    return render(request, 'core/dashboard.html', {
        'mes': mes,
        'ano': ano,
        'anos': anos,
        'vendas': vendas,
        'despesas': despesas,
        'total_vendido': total_vendido,
        'total_despesas': total_despesas,
        'total_compras': total_compras,
        'lucro': lucro,
    })    