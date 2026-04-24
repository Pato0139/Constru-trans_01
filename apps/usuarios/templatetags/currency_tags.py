from django import template

register = template.Library()

@register.filter(name='currency')
def currency(value):
    try:
        value = int(value)
        return "${:,.0f}".format(value).replace(',', '.')
    except (ValueError, TypeError):
        return value

@register.filter(name='split_list')
def split_list(value):
    """
    Convierte una cadena separada por pipe (|) en una lista de listas separadas por coma.
    Ej: 'a,b,c|d,e,f' -> [['a','b','c'], ['d','e','f']]
    """
    return [item.split(',') for item in value.split('|')]
