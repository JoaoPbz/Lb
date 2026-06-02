from django.shortcuts import render, redirect
from .models import Cliente

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