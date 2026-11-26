from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from config.forms_base import StrictForm, StrictModelForm

from apps.usuarios.models import Conductor

from .models import ConductorVehiculo, Novedad, Vehiculo


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

        self.fields["vehiculo"].queryset = disponibles.filter(capacidad_carga__gte=5).order_by("placa")


MOTIVOS_REASIGNACION = [
    ("conductor_incidente", "Accidente o inconveniente del conductor"),
    ("conductor_ausente", "Enfermedad o ausencia del conductor"),
    ("falla_mecanica", "Falla mecánica del vehículo"),
    ("vehiculo_indisponible", "Indisponibilidad del vehículo"),
    ("operativo", "Cambio operativo"),
    ("otro", "Otro motivo"),
]

MOTIVOS_REAGENDA = [
    ("clima", "Condiciones climáticas desfavorables"),
    ("via_cerrada", "Derrumbes o vías cerradas"),
    ("mecanico", "Problemas mecánicos"),
    ("preparacion", "Retrasos en la preparación"),
    ("operativo", "Inconvenientes operativos"),
    ("cliente", "Solicitud del cliente"),
    ("otro", "Otro motivo"),
]


class ReasignarRecursosForm(StrictForm):
    conductor = forms.ModelChoiceField(
        queryset=Conductor.objects.none(), required=False, label="Nuevo conductor",
        empty_label="Conservar conductor actual", widget=forms.Select(attrs={"class": "form-select"}),
    )
    vehiculo = forms.ModelChoiceField(
        queryset=Vehiculo.objects.none(), required=False, label="Nuevo vehículo",
        empty_label="Conservar vehículo actual", widget=forms.Select(attrs={"class": "form-select"}),
    )
    motivo = forms.ChoiceField(choices=MOTIVOS_REASIGNACION, label="Motivo", widget=forms.Select(attrs={"class": "form-select"}))
    detalle_motivo = forms.CharField(
        required=False, label="Descripción del motivo",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "maxlength": 1000}),
    )

    def __init__(self, *args, entrega=None, **kwargs):
        super().__init__(*args, **kwargs)
        conductores = Conductor.objects.filter(estado="activo", usuario__is_active=True, usuario__estado="activo")
        asignados_a_otro = ConductorVehiculo.objects.filter(fecha_fin__isnull=True).values_list(
            "vehiculo_id", flat=True
        )
        vehiculos = Vehiculo.objects.filter(
            estado="disponible", capacidad_carga__gte=5
        ).exclude(pk__in=asignados_a_otro)
        if entrega and entrega.conductor_id:
            conductores = Conductor.objects.filter(Q(pk=entrega.conductor_id) | Q(pk__in=conductores.values("pk")))
        if entrega and entrega.vehiculo_id:
            vehiculos = Vehiculo.objects.filter(
                Q(pk=entrega.vehiculo_id) | Q(pk__in=vehiculos.values("pk"))
            )
        self.fields["conductor"].queryset = conductores.select_related("usuario").order_by("usuario__nombres")
        self.fields["vehiculo"].queryset = vehiculos.order_by("placa")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("motivo") == "otro" and not (cleaned.get("detalle_motivo") or "").strip():
            self.add_error("detalle_motivo", "Describe el motivo de la reasignación.")
        if not cleaned.get("conductor") and not cleaned.get("vehiculo"):
            self.add_error(None, "Selecciona al menos un recurso para reasignar.")
        return cleaned


class ReagendarEntregaForm(StrictForm):
    fecha_entrega_programada = forms.DateTimeField(
        label="Nueva fecha y hora", input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local", "class": "form-control"}),
    )
    motivo = forms.ChoiceField(choices=MOTIVOS_REAGENDA, label="Motivo", widget=forms.Select(attrs={"class": "form-select"}))
    detalle_motivo = forms.CharField(
        required=False, label="Descripción del motivo",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "maxlength": 1000}),
    )

    def clean(self):
        cleaned = super().clean()
        fecha = cleaned.get("fecha_entrega_programada")
        if fecha and fecha <= timezone.now():
            self.add_error("fecha_entrega_programada", "La nueva fecha debe ser futura.")
        if cleaned.get("motivo") == "otro" and not (cleaned.get("detalle_motivo") or "").strip():
            self.add_error("detalle_motivo", "Describe el motivo del reagendamiento.")
        return cleaned


class NovedadForm(StrictModelForm):
    class Meta:
        model = Novedad
        fields = ("tipo", "descripcion", "solucion", "evidencia")
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select form-select-lg"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 5, "maxlength": 5000}),
            "solucion": forms.Textarea(attrs={"class": "form-control", "rows": 3, "maxlength": 3000}),
            "evidencia": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
        }
        labels = {"tipo": "Tipo de novedad", "descripcion": "Descripción detallada", "solucion": "Acción o solución aplicada", "evidencia": "Evidencia fotográfica (opcional)"}
        help_texts = {"evidencia": "Imagen de hasta 5 MB."}

    def clean_evidencia(self):
        archivo = self.cleaned_data.get("evidencia")
        if archivo and archivo.size > 5 * 1024 * 1024:
            raise ValidationError("La imagen no puede superar 5 MB.")
        return archivo
