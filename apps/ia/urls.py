from django.urls import path
from .views import chat_ia

urlpatterns = [
    path("chat/", chat_ia, name="chat_ia"),
]
