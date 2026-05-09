from django.contrib.auth import get_user_model
User = get_user_model()
print('=== Usuarios del sistema:')
for u in User.objects.all():
    try:
        rol = u.usuario.rol if hasattr(u, 'usuario') else 'SIN ROL'
        print(f'- {u.username} ({u.email}) - Rol: {rol}')
    except Exception as e:
        print(f'- {u.username} - Error: {e}')
