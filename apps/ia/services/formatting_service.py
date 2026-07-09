from decimal import Decimal, InvalidOperation


def format_number_es(value, decimals=None):
    """
    Enteros: 8337626 -> 8.337.626
    Decimales: 1234567.89 -> 1.234.567,89
    """
    try:
        num = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return str(value)

    sign = "-" if num < 0 else ""
    num = abs(num)

    if decimals is None:
        if num == num.to_integral():
            entero = int(num)
            return f"{sign}{entero:,}".replace(",", ".")
        decimals = 2

    q = Decimal(10) ** -decimals
    num = num.quantize(q)

    entero_str, frac_str = f"{num:.{decimals}f}".split(".")
    entero_str = f"{int(entero_str):,}".replace(",", ".")
    return f"{sign}{entero_str},{frac_str}"
