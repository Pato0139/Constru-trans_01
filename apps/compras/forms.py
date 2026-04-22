from django import forms
from django.forms import inlineformset_factory
from .models import OrdenCompra, ItemOrdenCompra


class ItemOrdenCompraForm(forms.ModelForm):
    class Meta:
        model = ItemOrdenCompra
        fields = ['nombre_material', 'cantidad', 'precio_unitario']
        widgets = {
            'nombre_material': forms.TextInput(attrs={
                'class': 'form-control detalle-material',
                'placeholder': 'Ej: Cemento Portland',
            }),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control detalle-cantidad',
                'min': 1,
                'step': '0.01',
                'placeholder': '0',
            }),
            'precio_unitario': forms.NumberInput(attrs={
                'class': 'form-control detalle-precio',
                'min': 0,
                'step': '0.01',
                'placeholder': '0.00',
            }),
        }

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        if cantidad is not None and cantidad <= 0:
            raise forms.ValidationError('La cantidad debe ser mayor a 0.')
        return cantidad

    def clean_precio_unitario(self):
        precio = self.cleaned_data.get('precio_unitario')
        if precio is not None and precio <= 0:
            raise forms.ValidationError('El precio debe ser mayor a 0.')
        return precio


# CT-461: Permite agregar uno o más materiales a la orden
ItemOrdenCompraFormSet = inlineformset_factory(
    OrdenCompra,
    ItemOrdenCompra,
    form=ItemOrdenCompraForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)