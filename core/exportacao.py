from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .repositories import ClienteRepository, VendaRepository
from .services import ClienteService

FORMATO_MOEDA = '"R$" #,##0.00'
FORMATO_DATA = 'DD/MM/YYYY'
FONTE_CABECALHO = Font(bold=True, color="FFFFFF")
FUNDO_CABECALHO = PatternFill("solid", fgColor="333333")


def _titulo(ws, texto, colunas, linha=1, tamanho=14):
    ws.merge_cells(start_row=linha, start_column=1, end_row=linha, end_column=colunas)
    celula = ws.cell(row=linha, column=1, value=texto)
    celula.font = Font(bold=True, size=tamanho)
    celula.alignment = Alignment(horizontal='center')


def _cabecalho(ws, titulos):
    ws.append(titulos)
    for coluna in range(1, len(titulos) + 1):
        celula = ws.cell(row=ws.max_row, column=coluna)
        celula.font = FONTE_CABECALHO
        celula.fill = FUNDO_CABECALHO
        celula.alignment = Alignment(horizontal='center')


def _formatar_linha(ws, formatos):
    for coluna, formato in formatos.items():
        ws.cell(row=ws.max_row, column=coluna).number_format = formato


def _ajustar_larguras(ws, colunas):
    for indice in range(1, colunas + 1):
        letra = get_column_letter(indice)
        maior = max((len(str(c.value)) for c in ws[letra] if c.value is not None and c.row > 2), default=8)
        ws.column_dimensions[letra].width = max(maior, 12) + 4


def gerar_extrato_cliente(cliente):
    wb = Workbook()
    ws = wb.active
    ws.title = "Extrato"
    _titulo(ws, f"Extrato — {cliente.nome}", 6)
    _titulo(ws, f"Telefone: {cliente.telefone}", 6, linha=2, tamanho=11)
    ws.append([])

    _cabecalho(ws, ['Data', 'Total', 'Desconto', 'Pagamento', 'Total Pago', 'Saldo Devedor'])
    for venda in VendaRepository.do_cliente(cliente):
        ws.append([venda.data, venda.total, f"{venda.desconto_percentual}%",
                   venda.get_forma_pagamento_display(), venda.total_pago, venda.saldo_devedor])
        _formatar_linha(ws, {1: FORMATO_DATA, 2: FORMATO_MOEDA, 5: FORMATO_MOEDA, 6: FORMATO_MOEDA})

    ws.append([])
    ws.append(['', '', '', '', 'Saldo Devedor Total:', ClienteService.calcular_saldo_devedor(cliente)])
    _formatar_linha(ws, {6: FORMATO_MOEDA})
    ws.append(['', '', '', '', 'Total Gasto no Ano:', ClienteService.calcular_total_ano(cliente)])
    _formatar_linha(ws, {6: FORMATO_MOEDA})
    for linha in (ws.max_row - 1, ws.max_row):
        ws.cell(row=linha, column=5).font = Font(bold=True)
        ws.cell(row=linha, column=6).font = Font(bold=True)

    _ajustar_larguras(ws, 6)
    return wb


def gerar_saldo_clientes():
    wb = Workbook()
    ws = wb.active
    ws.title = "Clientes"
    _titulo(ws, "Saldo Devedor — Todos os Clientes", 5)
    ws.append([])

    _cabecalho(ws, ['Cliente', 'Telefone', 'Total Compras', 'Total Pago', 'Saldo Devedor'])
    for cliente in ClienteRepository.listar_com_saldo():
        ws.append([cliente.nome, cliente.telefone, cliente.total_comprado, cliente.total_pago, cliente.saldo])
        _formatar_linha(ws, {3: FORMATO_MOEDA, 4: FORMATO_MOEDA, 5: FORMATO_MOEDA})

    _ajustar_larguras(ws, 5)
    return wb
