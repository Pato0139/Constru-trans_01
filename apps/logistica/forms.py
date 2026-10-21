from django import forms
from django.db.models import Q

from config.forms_base import StrictForm, StrictModelForm
from config.validators import no_solo_espacios, placa_validator
from .models import ConductorVehiculo, Vehiculo


class VehiculoForm(StrictModelForm):
    campos_extra_permitidos = {"tipo", "capacidad", "conductor"}

    tipo = forms.CharField(required=False, max_length=50)
    capacidad = forms.DecimalField(required=False, max_digits=10, decimal_places=2, min_value=0.01)
    conductor = forms.IntegerField(required=False)

    class Meta:
        model = Vehiculo
        fields = ["placa", "tipo_vehiculo", "marca", "modelo", "capacidad_carga", "estado"]
        extra_kwargs = {
            "tipo_vehiculo": {"required": False},
            "capacidad_carga": {"required": False},
        }

    def clean_placa(self):
        placa = (self.cleaned_data.get("placa") or "").strip().upper()
        placa_validator(placa)
        return placa

    def clean_marca(self):
        marca = (self.cleaned_data.get("marca") or "").strip()
        no_solo_espacios(marca)
        return marca

    def clean_modelo(self):
        modelo = (self.cleaned_data.get("modelo") or "").strip()
        no_solo_espacios(modelo)
        return modelo

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo") or cleaned.get("tipo_vehiculo")
        if not tipo or not tipo.strip():
            self.add_error("tipo", "El tipo de vehículo es obligatorio.")
        else:
            cleaned["tipo_vehiculo"] = tipo.strip()
            self.instance.tipo_vehiculo = tipo.strip()

        capacidad = cleaned.get("capacidad") or cleaned.get("capacidad_carga")
        if capacidad is None or capacidad <= 0:
            self.add_error("capacidad", "La capacidad de carga debe ser mayor a 0.")
        else:
            cleaned["capacidad_carga"] = capacidad
            self.instance.capacidad_carga = capacidad
        return cleaned


class AsignarVehiculoForm(StrictForm):
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
