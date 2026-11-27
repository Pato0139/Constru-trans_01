from django import template

register = template.Library()


@register.filter(name="currency")
def currency(value):
    try:
        val = float(value)
        rounded = int(round(val))
        sign = "-" if rounded < 0 else ""
        s = str(abs(rounded))
        parts = []
        while s:
            parts.append(s[-3:])
            s = s[:-3]
        return sign + ".".join(reversed(parts))
    except (ValueError, TypeError):
        return value


@register.filter(name="split_list")
def split_list(value):
    return [item.split(",") for item in value.split("|")]
