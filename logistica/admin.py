from django.contrib import admin

from .models import (ConductorVehiculo, Entrega, Novedad, RespuestaSeguimiento,
                     Seguimiento, Vehiculo)

admin.site.register(Vehiculo)
admin.site.register(ConductorVehiculo)
admin.site.register(Entrega)
admin.site.register(Novedad)
admin.site.register(Seguimiento)
admin.site.register(RespuestaSeguimiento)
