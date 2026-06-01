from django.db import models


class Compra(models.Model):
    data = models.DateField()
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    observacoes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Compra {self.data} - R$ {self.valor_total}"


class Produto(models.Model):
    codigo_marca = models.CharField(max_length=50, unique=True)
    nome = models.CharField(max_length=100)
    categoria = models.CharField(max_length=50)
    tamanho = models.CharField(max_length=10)
    cor = models.CharField(max_length=30)
    preco_custo = models.DecimalField(max_digits=10, decimal_places=2)
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2)
    quantidade_estoque = models.IntegerField(default=0)
    compra = models.ForeignKey(Compra, on_delete=models.SET_NULL, null=True, blank=True, related_name='produtos')

    def __str__(self):
        return f"{self.nome} - {self.tamanho} {self.cor}"


class Cliente(models.Model):
    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=20)

    def __str__(self):
        return self.nome


class Prova(models.Model):
    STATUS_CHOICES = [
        ('em_prova', 'Em Prova'),
        ('devolvida', 'Devolvida'),
        ('convertida', 'Convertida em Venda'),
    ]
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='provas')
    data_saida = models.DateField()
    data_devolucao_prevista = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='em_prova')

    def __str__(self):
        return f"Prova {self.cliente.nome} - {self.status}"


class ItemProva(models.Model):
    prova = models.ForeignKey(Prova, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.produto.nome} - {self.prova}"


class Venda(models.Model):
    ORIGEM_CHOICES = [
        ('direta', 'Direta'),
        ('prova', 'Convertida de Prova'),
    ]
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='vendas')
    data = models.DateField()
    total = models.DecimalField(max_digits=10, decimal_places=2)
    origem = models.CharField(max_length=10, choices=ORIGEM_CHOICES, default='direta')

    def __str__(self):
        return f"Venda {self.cliente.nome} - {self.data}"


class ItemVenda(models.Model):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.IntegerField()
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.produto.nome} x{self.quantidade}"


class Pagamento(models.Model):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='pagamentos')
    data = models.DateField()
    valor = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Pagamento R$ {self.valor} - {self.data}"


class Despesa(models.Model):
    descricao = models.CharField(max_length=100)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateField()
    categoria = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.descricao} - R$ {self.valor}"