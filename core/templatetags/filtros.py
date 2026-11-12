from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def moeda(value):
    """Formata no padrão brasileiro, sem o símbolo: 1234.5 -> '1.234,50'."""
    try:
        value = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return value
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
