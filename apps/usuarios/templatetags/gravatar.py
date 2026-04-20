import hashlib
from django import template

register = template.Library()

@register.filter(name='gravatar_url')
def gravatar_url(email, size=100):
    """
    Genera la URL de Gravatar para un correo electrónico dado.
    """
    if not email:
        return f"https://www.gravatar.com/avatar/?s={size}&d=mp"
    
    email_hash = hashlib.md5(email.lower().encode('utf-8')).hexdigest()
    return f"https://www.gravatar.com/avatar/{email_hash}?s={size}&d=mp"
