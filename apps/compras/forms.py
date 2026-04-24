from django import forms
from django.forms import inlineformset_factory
from .models import Compra, DetalleCompra
from apps.usuarios.models import Material, Proveedor

class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ['proveedor', 'observaciones']
        widgets = {
            'proveedor': forms.Select(attrs={'class': 'form-control select2'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Notas adicionales...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proveedor'].queryset = Proveedor.objects.all() # Podríamos filtrar por activos si existiera el campo

class DetalleCompraForm(forms.ModelForm):
    class Meta:
        model = DetalleCompra
        fields = ['material', 'cantidad', 'precio_unitario']
        widgets = {
            'material': forms.Select(attrs={'class': 'form-control select2 material-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control cantidad-input', 'min': 1}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control precio-input', 'step': '0.01', 'min': 0}),
        }

DetalleCompraFormSet = inlineformset_factory(
    Compra, 
    DetalleCompra, 
    form=DetalleCompraForm,
    extra=1, 
    can_delete=True
)
