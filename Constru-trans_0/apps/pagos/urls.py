from django.urls import path
from . import views

app_name = 'pagos'

urlpatterns = [
    path('historial/', views.lista_pagos, name='lista_pagos'),
]
