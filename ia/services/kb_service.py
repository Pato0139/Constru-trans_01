import logging
import re

from ia.models import KnowledgeBase

logger = logging.getLogger(__name__)


def check_knowledge_base(mensaje: str):
    try:
        mensaje_norm = mensaje.strip().lower()

        for entry in KnowledgeBase.objects.all():
            pattern = entry.question_pattern.strip().lower()
            try:
                if re.search(pattern, mensaje_norm):
                    return entry
            except re.error:
                logger.warning(f"Pattern inválido en KB: {entry.question_pattern}")
                continue
        return None
    except Exception:
        logger.exception("Error consultando knowledge base")
        return None


def update_knowledge_base(user_message, bot_response, feedback_type: str):
    try:
        if feedback_type == "good":
            question = user_message.strip()
            if len(question) > 5:
                # Escapar caracteres especiales de regex antes de guardar
                escaped_question = re.escape(question)
                existing = KnowledgeBase.objects.filter(
                    question_pattern__iexact=escaped_question
                ).first()
                if existing:
                    existing.success_count += 1
                    existing.save()
                else:
                    KnowledgeBase.objects.create(
                        question_pattern=escaped_question,
                        best_response=bot_response.strip(),
                        category="general",
                    )
    except Exception:
        logger.exception("Error actualizando knowledge base")
