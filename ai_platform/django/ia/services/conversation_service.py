import logging

from django.utils import timezone

from ia.models import ConversationHistory, ConversationMessage

logger = logging.getLogger(__name__)


def get_conversation(usuario=None, session_id=None):
    # Usuario y conversación deben vivir en la misma base para respetar la FK.
    db_alias = getattr(getattr(usuario, "_state", None), "db", None) or "default"
    try:
        if usuario and usuario.is_authenticated:
            conv, created = ConversationHistory.objects.using(db_alias).get_or_create(
                user_id=usuario.pk,
                defaults={
                    "session_id": session_id or "",
                },
            )
        elif session_id:
            conv, created = ConversationHistory.objects.using(db_alias).get_or_create(
                session_id=session_id, user=None, defaults={}
            )
        else:
            conv = ConversationHistory.objects.using(db_alias).create(user=None, session_id="")
            created = True

        return conv
    except Exception:
        logger.exception("Error obteniendo conversación")
        return ConversationHistory.objects.using(db_alias).create(user=None, session_id="")


def add_message_to_conversation(
    conversation,
    role: str,
    content: str,
    prompt_used: str = None,
    model_used: str = None,
    response_time: float = None,
):
    try:
        db_alias = getattr(getattr(conversation, "_state", None), "db", None) or "default"
        return ConversationMessage.objects.using(db_alias).create(
            conversation=conversation,
            role=role,
            content=content,
            prompt_used=prompt_used,
            model_used=model_used,
            response_time=response_time,
            timestamp=timezone.now(),
        )
    except Exception:
        logger.exception("Error guardando mensaje en conversación")
        return None
