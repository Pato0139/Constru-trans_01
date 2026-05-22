from django import template

register = template.Library()

@register.filter(name='currency')
def currency(value):
    try:
        # Convertimos a float para manejar decimales y dividimos por 100
        # ya que el usuario indica que 1.000.000 equivale a 10.000 pesos
        val = float(value) / 100
        # Formateamos con separador de miles (,) y 2 decimales
        formatted = "{:,.2f}".format(val)
        # Cambiamos , por . para miles y . por , para decimales (formato es-CO)
        # Usamos un placeholder temporal para no perder los puntos
        res = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"${res}"
    except (ValueError, TypeError):
        return value

@register.filter(name='split_list')
def split_list(value):
    """
    Convierte una cadena separada por pipe (|) en una lista de listas separadas por coma.
    Ej: 'a,b,c|d,e,f' -> [['a','b','c'], ['d','e','f']]
    """
    return [item.split(',') for item in value.split('|')]
