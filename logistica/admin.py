from django.contrib import admin
from .models import (
    Vehiculo,
    ConductorVehiculo,
    Entrega,
    Novedad,
    Seguimiento,
    RespuestaSeguimiento,
)

admin.site.register(Vehiculo)
admin.site.register(ConductorVehiculo)
admin.site.register(Entrega)
admin.site.register(Novedad)
admin.site.register(Seguimiento)
admin.site.register(RespuestaSeguimiento)
