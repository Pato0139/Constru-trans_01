from django.urls import path
from . import views

app_name = 'historial'

urlpatterns = [
    path('lista/', views.lista_historial, name='lista'),
]
