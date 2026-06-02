from django.shortcuts import render, redirect
from .models import Cliente
from .models import Cliente, Produto
from .models import Cliente, Produto, Compra
from datetime import date
from .models import Cliente, Produto, Compra, Prova, ItemProva, Venda, ItemVenda

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