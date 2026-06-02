from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('clientes/', views.clientes, name='clientes'),
    path('clientes/novo/', views.novo_cliente, name='novo_cliente'),
    path('clientes/editar/<int:id>/', views.editar_cliente, name='editar_cliente'),
    path('clientes/excluir/<int:id>/', views.excluir_cliente, name='excluir_cliente'),
    path('produtos/', views.produtos, name='produtos'),
    path('produtos/editar/<int:id>/', views.editar_produto, name='editar_produto'),
    path('produtos/excluir/<int:id>/', views.excluir_produto, name='excluir_produto'),
    path('compras/nova/', views.nova_compra, name='nova_compra'),
    path('provas/', views.provas, name='provas'),
    path('provas/nova/', views.nova_prova, name='nova_prova'),
    path('provas/<int:id>/', views.detalhe_prova, name='detalhe_prova'),
    path('provas/<int:id>/resolver/', views.resolver_prova, name='resolver_prova'),
    path('provas/<int:id>/excluir/', views.excluir_prova, name='excluir_prova'),
]