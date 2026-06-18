from django.urls import path
from .views import chat_ia

urlpatterns = [
    # La API del chat (solo para POST)
    path("chat/", chat_ia, name="chat_ia"),
]
