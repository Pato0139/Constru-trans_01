# Estructura Modular del Proyecto

## Árbol de Directorios (Real)

```
Constru-trans_01/
├── core/                          # Configuración central
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py               # Settings base
│   │   ├── development.py        # Settings desarrollo
│   │   └── production.py         # Settings producción
│   ├── __init__.py
│   ├── urls.py                   # URLs principales
│   ├── routers.py                # Router BD híbrida
│   ├── middleware.py
│   └── wsgi.py
├── usuarios/                     # App: Usuarios, Conductores, Vehículos
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   ├── urls.py
│   ├── admin.py
│   ├── apps.py
│   ├── migrations/
│   ├── templates/
│   └── tests/
├── clientes/                     # App: Clientes VIP
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── apps.py
│   ├── migrations/
│   └── templates/
├── inventario/                   # App: Materiales, Stock, Movimientos
│   ├── models/
│   ├── views/
│   ├── services/
│   ├── urls.py
│   ├── admin.py
│   ├── apps.py
│   ├── migrations/
│   ├── templates/
│   └── tests/
├── compras/                      # App: Proveedores, Compras
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   ├── urls.py
│   ├── admin.py
│   ├── apps.py
│   ├── migrations/
│   └── templates/
├── gestion_pedidos/              # App: Pedidos de clientes
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── apps.py
│   ├── migrations/
│   └── templates/
├── ordenes/                      # App: Órdenes de entrega
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── apps.py
│   ├── migrations/
│   └── templates/
├── facturacion/                  # App: Facturas
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── apps.py
│   └── migrations/
├── pagos/                        # App: Pagos
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── apps.py
│   └── migrations/
├── reportes/                     # App: Reportes PDF/Excel
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── apps.py
│   └── migrations/
├── ia/                           # App: Asistente IA
│   ├── models.py
│   ├── views/
│   ├── services/
│   ├── urls.py
│   ├── admin.py
│   ├── apps.py
│   ├── migrations/
│   ├── templates/
│   └── tests/
├── inicio/                       # App: Página de inicio
│   ├── views.py
│   ├── urls.py
│   ├── apps.py
│   ├── migrations/
│   └── templates/
├── historial/                    # App: Auditoría
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── apps.py
│   └── migrations/
├── licensing/                    # App: Licencias
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── apps.py
│   └── migrations/
├── media/                        # Archivos subidos (perfiles, etc.)
│   └── perfiles/
├── docs/                         # Documentación formal
│   ├── gestion/
│   ├── arquitectura/
│   ├── integracion/
│   └── calidad/
├── .github/
│   └── workflows/
│       └── ci.yml                # CI/CD Pipeline
├── manage.py
├── pyproject.toml                # Config Ruff, pytest
├── requirements.txt
├── .env.example
└── README.md
```

---

## Principios de Arquitectura

1. **Modularidad:** Cada funcionalidad en su propia app Django
2. **Separación de Responsabilidades:** Models ↔ Views ↔ Templates
3. **Hybrid Database:** SQLite local + PostgreSQL remoto via router
4. **Settings por Entorno:** base.py → development.py / production.py
