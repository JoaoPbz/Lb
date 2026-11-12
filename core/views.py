from datetime import date

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import content_disposition_header
from django.views.decorators.http import require_POST

from .backup import BackupService
from .exportacao import gerar_extrato_cliente, gerar_saldo_clientes
from .forms import ClienteForm, DespesaForm, ProdutoForm
from .models import Cliente, Despesa, Pagamento, Produto, Prova, Venda
from .repositories import ClienteRepository, DespesaRepository, ProdutoRepository, ProvaRepository, VendaRepository
from .services import (
    ClienteService, CompraService, ProdutoService, ProvaService, RegraNegocioError, RelatorioService, VendaService,
)

XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro',
         'Novembro', 'Dezembro']


def _formulario(request, form_class, template, destino, instancia=None, mensagem='Salvo com sucesso.'):
    """Fluxo padrão de cadastro/edição com ModelForm."""
    form = form_class(request.POST or None, instance=instancia)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, mensagem)
        return redirect(destino)
    return render(request, template, {'form': form, 'objeto': instancia})


def _planilha(workbook, nome_arquivo):
    response = HttpResponse(content_type=XLSX)
    response['Content-Disposition'] = content_disposition_header(as_attachment=True, filename=nome_arquivo)
    workbook.save(response)
    return response


# ---------- Clientes ----------

def clientes(request):
    return render(request, 'core/clientes.html', {'clientes': ClienteRepository.listar()})


def novo_cliente(request):
    return _formulario(request, ClienteForm, 'core/cliente_form.html', 'clientes', mensagem='Cliente cadastrado.')


def editar_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    return _formulario(request, ClienteForm, 'core/cliente_form.html', 'clientes', cliente, 'Cliente atualizado.')


@require_POST
def excluir_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    try:
        ClienteService.excluir(cliente)
        messages.success(request, 'Cliente excluído.')
    except RegraNegocioError as erro:
        messages.error(request, str(erro))
    return redirect('clientes')


def perfil_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    return render(request, 'core/perfil_cliente.html', {
        'cliente': cliente,
        'vendas': VendaRepository.do_cliente(cliente),
        'provas': ProvaRepository.do_cliente(cliente),
        'saldo_devedor': ClienteService.calcular_saldo_devedor(cliente),
        'total_ano': ClienteService.calcular_total_ano(cliente),
        'provas_abertas': ClienteService.calcular_provas_abertas(cliente),
        'hoje': date.today(),
    })


def exportar_extrato(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    return _planilha(gerar_extrato_cliente(cliente), f'extrato_{cliente.nome}.xlsx')


def exportar_clientes_excel(request):
    return _planilha(gerar_saldo_clientes(), 'clientes_saldo.xlsx')


# ---------- Produtos e compras ----------

def produtos(request):
    return render(request, 'core/produtos.html', {'produtos': ProdutoRepository.ativos()})


def produtos_inativos(request):
    return render(request, 'core/produtos_inativos.html', {'produtos': ProdutoRepository.inativos()})


def editar_produto(request, id):
    produto = get_object_or_404(Produto, id=id)
    return _formulario(request, ProdutoForm, 'core/produto_form.html', 'produtos', produto, 'Produto atualizado.')


@require_POST
def excluir_produto(request, id):
    ProdutoService.alterar_status(get_object_or_404(Produto, id=id), ativo=False)
    messages.success(request, 'Produto movido para os inativos.')
    return redirect('produtos')


@require_POST
def reativar_produto(request, id):
    ProdutoService.alterar_status(get_object_or_404(Produto, id=id), ativo=True)
    messages.success(request, 'Produto reativado.')
    return redirect('produtos_inativos')


def nova_compra(request):
    if request.method == 'POST':
        campos = ['codigo_marca', 'nome', 'tamanho', 'cor', 'preco_custo', 'preco_venda', 'quantidade']
        colunas = [request.POST.getlist(f'{campo}[]') for campo in campos]
        itens = [dict(zip(campos, linha)) for linha in zip(*colunas)]
        try:
            CompraService.registrar(request.POST.get('data'), request.POST.get('observacoes'), itens)
            messages.success(request, 'Compra registrada e estoque atualizado.')
            return redirect('produtos')
        except RegraNegocioError as erro:
            messages.error(request, str(erro))
    return render(request, 'core/nova_compra.html')


# ---------- Provas ----------

def provas(request):
    return render(request, 'core/provas.html', {'provas': ProvaRepository.listar(), 'hoje': date.today()})


def nova_prova(request):
    if request.method == 'POST':
        try:
            prova = ProvaService.criar(
                request.POST.get('cliente_id'), request.POST.get('data_saida'),
                request.POST.get('data_devolucao_prevista'), request.POST.getlist('produtos[]'),
            )
            messages.success(request, 'Prova registrada.')
            return redirect('detalhe_prova', id=prova.id)
        except RegraNegocioError as erro:
            messages.error(request, str(erro))
    return render(request, 'core/nova_prova.html', {
        'clientes': ClienteRepository.listar(),
        'produtos': ProdutoRepository.disponiveis(),
    })


def detalhe_prova(request, id):
    prova = get_object_or_404(Prova.objects.select_related('cliente'), id=id)
    return render(request, 'core/detalhe_prova.html', {
        'prova': prova,
        'itens': prova.itens.select_related('produto'),
        'venda': prova.vendas.first(),
        'hoje': date.today(),
    })


@require_POST
def resolver_prova(request, id):
    prova = get_object_or_404(Prova, id=id)
    try:
        venda = ProvaService.resolver(
            prova, request.POST.getlist('itens_vendidos[]'), request.POST.get('forma_pagamento'),
            request.POST.get('desconto_percentual', 0), request.POST.get('data'),
        )
        messages.success(request, 'Prova convertida em venda.' if venda else 'Prova marcada como devolvida.')
    except RegraNegocioError as erro:
        messages.error(request, str(erro))
    return redirect('detalhe_prova', id=prova.id)


@require_POST
def excluir_prova(request, id):
    get_object_or_404(Prova, id=id).delete()
    messages.success(request, 'Prova excluída.')
    return redirect('provas')


# ---------- Vendas ----------

def vendas(request):
    filtro = request.GET.get('filtro')
    lista = VendaRepository.com_saldo()
    if filtro == 'aberto':
        lista = lista.filter(saldo_devedor__gt=0)
    elif filtro == 'quitado':
        lista = lista.filter(saldo_devedor__lte=0)
    return render(request, 'core/vendas.html', {'vendas': lista, 'filtro': filtro})


def nova_venda(request):
    if request.method == 'POST':
        quantidades = {pid: request.POST.get(f'quantidade_{pid}', 1) for pid in request.POST.getlist('produtos[]')}
        try:
            VendaService.criar(
                request.POST.get('cliente_id'), request.POST.get('data'), request.POST.get('forma_pagamento'),
                request.POST.get('desconto_percentual', 0), quantidades,
            )
            messages.success(request, 'Venda registrada.')
            return redirect('vendas')
        except RegraNegocioError as erro:
            messages.error(request, str(erro))
    return render(request, 'core/nova_venda.html', {
        'clientes': ClienteRepository.listar(),
        'produtos': ProdutoRepository.disponiveis(),
    })


def detalhe_venda(request, id):
    venda = get_object_or_404(VendaRepository.com_saldo(), id=id)
    return render(request, 'core/detalhe_venda.html', {
        'venda': venda,
        'itens': venda.itens.select_related('produto'),
        'pagamentos': venda.pagamentos.order_by('data', 'id'),
    })


@require_POST
def novo_pagamento(request, id):
    venda = get_object_or_404(Venda, id=id)
    try:
        VendaService.registrar_pagamento(venda, request.POST.get('data'), request.POST.get('valor'))
        messages.success(request, 'Pagamento registrado.')
    except RegraNegocioError as erro:
        messages.error(request, str(erro))
    return redirect('detalhe_venda', id=venda.id)


@require_POST
def excluir_pagamento(request, id):
    pagamento = get_object_or_404(Pagamento, id=id)
    pagamento.delete()
    messages.success(request, 'Pagamento excluído.')
    return redirect('detalhe_venda', id=pagamento.venda_id)


@require_POST
def excluir_venda(request, id):
    venda = get_object_or_404(Venda, id=id)
    reabre_prova = venda.prova_id is not None
    VendaService.excluir(venda)
    messages.success(request, 'Venda excluída e peças devolvidas ao estoque.'
                     + (' A prova de origem voltou a ficar aberta.' if reabre_prova else ''))
    return redirect('vendas')


# ---------- Despesas ----------

def despesas(request):
    return render(request, 'core/despesas.html', {'despesas': DespesaRepository.listar()})


def nova_despesa(request):
    return _formulario(request, DespesaForm, 'core/despesa_form.html', 'despesas', mensagem='Despesa registrada.')


def editar_despesa(request, id):
    despesa = get_object_or_404(Despesa, id=id)
    return _formulario(request, DespesaForm, 'core/despesa_form.html', 'despesas', despesa, 'Despesa atualizada.')


@require_POST
def excluir_despesa(request, id):
    get_object_or_404(Despesa, id=id).delete()
    messages.success(request, 'Despesa excluída.')
    return redirect('despesas')


# ---------- Dashboard e backup ----------

def _ler_periodo(request):
    hoje = date.today()
    try:
        mes = int(request.GET.get('mes', hoje.month))
        ano = int(request.GET.get('ano', hoje.year))
    except ValueError:
        return hoje.month, hoje.year
    if not (1 <= mes <= 12 and 2000 <= ano <= 2100):
        return hoje.month, hoje.year
    return mes, ano


def dashboard(request):
    mes, ano = _ler_periodo(request)
    return render(request, 'core/dashboard.html', {
        'mes': mes,
        'ano': ano,
        'meses': list(enumerate(MESES, start=1)),
        'anos': list(range(2024, date.today().year + 2)),
        **RelatorioService.calcular_resumo_mensal(mes, ano),
    })


def backup(request):
    response = HttpResponse(BackupService.exportar(), content_type='application/json; charset=utf-8')
    nome = f"backup_{timezone.localtime().strftime('%Y%m%d_%H%M%S')}.json"
    response['Content-Disposition'] = content_disposition_header(as_attachment=True, filename=nome)
    return response


def restaurar_backup(request):
    if request.method == 'POST':
        arquivo = request.FILES.get('arquivo')
        if not arquivo:
            messages.error(request, 'Selecione um arquivo de backup.')
            return redirect('restaurar_backup')
        try:
            BackupService.restaurar(arquivo.read())
            messages.success(request, 'Backup restaurado com sucesso.')
            return redirect('dashboard')
        except RegraNegocioError as erro:
            messages.error(request, str(erro))
    return render(request, 'core/restaurar_backup.html')
