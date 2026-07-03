from django.db import models

from usuarios.models import Usuario


class ConversationHistory(models.Model):
    """Historial de conversaciones de la IA"""

    user = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, null=True, blank=True, related_name="ia_conversations"
    )
    session_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    context_metadata = models.JSONField(
        default=dict, blank=True, help_text="Metadatos del contexto de la conversación"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Historial de Conversación"
        verbose_name_plural = "Historiales de Conversación"

    def __str__(self):
        user_str = self.user.username if self.user else "Anónimo"
        return f"Conversación {self.id} - {user_str} - {self.created_at.strftime('%d/%m/%Y %H:%M')}"


class ConversationMessage(models.Model):
    """Mensajes individuales de una conversación"""

    ROLE_CHOICES = [
        ("user", "Usuario"),
        ("assistant", "Asistente"),
    ]

    conversation = models.ForeignKey(
        ConversationHistory, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    prompt_used = models.TextField(
        blank=True, null=True, help_text="Prompt usado para generar esta respuesta"
    )
    model_used = models.CharField(
        max_length=100, blank=True, null=True, help_text="Modelo de IA usado"
    )
    response_time = models.FloatField(
        blank=True, null=True, help_text="Tiempo de respuesta en segundos"
    )

    class Meta:
        ordering = ["timestamp"]
        verbose_name = "Mensaje de Conversación"
        verbose_name_plural = "Mensajes de Conversación"

    def __str__(self):
        return f"{self.get_role_display()}: {self.content[:50]}..."


class UserFeedback(models.Model):
    """Feedback de los usuarios sobre las respuestas de la IA"""

    FEEDBACK_CHOICES = [
        ("good", "Buena"),
        ("bad", "Mala"),
        ("neutral", "Neutral"),
    ]

    message = models.ForeignKey(
        ConversationMessage,
        on_delete=models.CASCADE,
        related_name="feedback",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, null=True, blank=True, related_name="ia_feedback"
    )
    feedback = models.CharField(max_length=20, choices=FEEDBACK_CHOICES)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Feedback del Usuario"
        verbose_name_plural = "Feedbacks del Usuario"

    def __str__(self):
        return f"Feedback {self.get_feedback_display()} - {self.created_at.strftime('%d/%m/%Y')}"


class AIPromptTemplate(models.Model):
    """Plantillas de prompts para mejorar la IA"""

    name = models.CharField(max_length=255)
    template = models.TextField(help_text="Plantilla de prompt. Usa {{variable}} para variables")
    is_active = models.BooleanField(default=True)
    usage_count = models.IntegerField(
        default=0, help_text="Número de veces que se ha usado esta plantilla"
    )
    success_rate = models.FloatField(default=0.0, help_text="Porcentaje de feedback positivo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-success_rate", "-created_at"]
        verbose_name = "Plantilla de Prompt IA"
        verbose_name_plural = "Plantillas de Prompt IA"

    def __str__(self):
        return f"{self.name} (Éxito: {self.success_rate:.1f}%)"

    def update_success_rate(self):
        """Actualiza la tasa de éxito basada en feedback"""
        messages = ConversationMessage.objects.filter(prompt_used__contains=self.name)
        total_feedback = 0
        positive_feedback = 0

        for msg in messages:
            for fb in msg.feedback.all():
                total_feedback += 1
                if fb.feedback == "good":
                    positive_feedback += 1

        if total_feedback > 0:
            self.success_rate = (positive_feedback / total_feedback) * 100
        else:
            self.success_rate = 0.0
        self.save()


class AIConfiguration(models.Model):
    """Configuración de la IA para auto-mejora"""

    key = models.CharField(max_length=255, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración IA"
        verbose_name_plural = "Configuraciones IA"

    def __str__(self):
        return f"{self.key}: {self.value[:50]}..."

    @classmethod
    def get_config(cls, key, default=None):
        """Obtiene una configuración"""
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set_config(cls, key, value, description=None):
        """Establece una configuración"""
        obj, created = cls.objects.get_or_create(key=key)
        obj.value = str(value)
        if description:
            obj.description = description
        obj.save()
        return obj


class KnowledgeBase(models.Model):
    """Base de conocimiento para respuestas rápidas y aprendizaje"""

    question_pattern = models.TextField(
        help_text="Patrón de pregunta (puede usar expresiones regulares)"
    )
    best_response = models.TextField(help_text="Mejor respuesta encontrada")
    category = models.CharField(max_length=100, blank=True, null=True)
    usage_count = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-usage_count", "-success_count"]
        verbose_name = "Base de Conocimiento"
        verbose_name_plural = "Base de Conocimiento"

    def __str__(self):
        return f"{self.question_pattern[:50]}... (Éxitos: {self.success_count}/{self.usage_count})"

    def success_rate(self):
        if self.usage_count == 0:
            return 0
        return (self.success_count / self.usage_count) * 100
