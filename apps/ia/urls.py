from django.urls import path

from .views import chat_ia, feedback_ia

urlpatterns = [
    # La API del chat (solo para POST)
    path("chat/", chat_ia, name="chat_ia"),
    # Endpoint para feedback
    path("feedback/", feedback_ia, name="feedback_ia"),
]
