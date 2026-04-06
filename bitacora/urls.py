from django.urls import path
from . import views

app_name = 'bitacora'

urlpatterns = [
    path('lista/', views.lista_bitacora, name='lista'),
]
