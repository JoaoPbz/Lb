from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Compra, Produto, Cliente, Prova, ItemProva, Venda, ItemVenda, Pagamento, Despesa

admin.site.register(Compra)
admin.site.register(Produto)
admin.site.register(Cliente)
admin.site.register(Prova)
admin.site.register(ItemProva)
admin.site.register(Venda)
admin.site.register(ItemVenda)
admin.site.register(Pagamento)
admin.site.register(Despesa)