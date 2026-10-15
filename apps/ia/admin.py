from django.contrib import admin

from .models import (AIConfiguration, AIPromptTemplate, ConversationHistory,
                     ConversationMessage, KnowledgeBase, UserFeedback)


# Register your models here.
@admin.register(ConversationHistory)
class ConversationHistoryAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "session_id", "created_at", "updated_at"]
    list_filter = ["created_at", "user", "updated_at"]
    search_fields = ["session_id", "user__username", "user__nombres", "user__apellidos"]


@admin.register(ConversationMessage)
class ConversationMessageAdmin(admin.ModelAdmin):
    list_display = ["id", "conversation", "role", "content", "timestamp"]
    list_filter = ["role", "timestamp", "conversation"]
    search_fields = ["content", "conversation__session_id"]


@admin.register(UserFeedback)
class UserFeedbackAdmin(admin.ModelAdmin):
    list_display = ["id", "message", "user", "feedback", "created_at"]
    list_filter = ["feedback", "created_at", "user"]
    search_fields = ["message", "user__username", "user__nombres"]


@admin.register(AIPromptTemplate)
class AIPromptTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "usage_count", "success_rate", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "content"]


@admin.register(AIConfiguration)
class AIConfigurationAdmin(admin.ModelAdmin):
    list_display = ["key", "value", "updated_at"]
    list_filter = ["updated_at"]
    search_fields = ["key", "value"]


@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "question_pattern",
        "category",
        "usage_count",
        "success_count",
        "created_at",
    ]
    list_filter = ["category", "created_at"]
    search_fields = ["question_pattern", "best_response"]
