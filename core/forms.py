from django import forms

from .models import Cliente, Despesa, Produto
from .repositories import ProdutoRepository


class BootstrapModelForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs.setdefault('class', 'form-control')

    def is_valid(self):
        valido = super().is_valid()
        for nome in self.errors:
            if nome in self.fields:
                self.fields[nome].widget.attrs['class'] += ' is-invalid'
        return valido


class ClienteForm(BootstrapModelForm):

    class Meta:
        model = Cliente
        fields = ['nome', 'telefone']


class ProdutoForm(BootstrapModelForm):

    class Meta:
        model = Produto
        fields = ['codigo_marca', 'nome', 'tamanho', 'cor', 'preco_custo', 'preco_venda', 'quantidade_estoque']
        widgets = {
            'preco_custo': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'preco_venda': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'quantidade_estoque': forms.NumberInput(attrs={'min': '0'}),
        }

    def clean_quantidade_estoque(self):
        quantidade = self.cleaned_data['quantidade_estoque']
        if self.instance.pk:
            em_prova = ProdutoRepository.quantidade_reservada([self.instance.pk]).get(self.instance.pk, 0)
            if quantidade < em_prova:
                raise forms.ValidationError(
                    f'Há {em_prova} peça(s) deste produto em prova; o estoque não pode ser menor que isso.')
        return quantidade


class DespesaForm(BootstrapModelForm):

    class Meta:
        model = Despesa
        fields = ['descricao', 'valor', 'data', 'categoria']
        widgets = {
            'valor': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'data': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'categoria': forms.TextInput(attrs={'placeholder': 'Ex: MEI, Frete...'}),
        }
