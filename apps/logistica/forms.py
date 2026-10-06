from django import forms
from django.db.models import Q

from .models import ConductorVehiculo, Vehiculo


class AsignarVehiculoForm(forms.Form):
    vehiculo = forms.ModelChoiceField(
        queryset=Vehiculo.objects.none(),
        label="Vehículo",
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, conductor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if conductor is None:
            self.fields["vehiculo"].queryset = Vehiculo.objects.none()
            return

        vehiculo_actual = conductor.vehiculo_actual

        asignados_activos = ConductorVehiculo.objects.filter(fecha_fin__isnull=True).values_list(
            "vehiculo_id", flat=True
        )

        if vehiculo_actual is not None:
            disponibles = Vehiculo.objects.filter(
                Q(id_vehiculo=vehiculo_actual.id_vehiculo)
                | (Q(estado="disponible") & ~Q(id_vehiculo__in=asignados_activos))
            ).distinct()
        else:
            disponibles = Vehiculo.objects.filter(estado="disponible").exclude(
                id_vehiculo__in=asignados_activos
            )

        self.fields["vehiculo"].queryset = disponibles.order_by("placa")
