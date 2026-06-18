import logging
import re
from apps.ia.models import KnowledgeBase

logger = logging.getLogger(__name__)


def check_knowledge_base(mensaje: str):
    try:
        mensaje_norm = mensaje.strip().lower()
        
        for entry in KnowledgeBase.objects.filter(is_active=True):
            patterns = entry.get_search_patterns()
            for pattern in patterns:
                if re.search(pattern, mensaje_norm):
                    return entry
        return None
    except Exception:
        logger.exception("Error consultando knowledge base")
        return None


def update_knowledge_base(user_message, bot_response, feedback_type: str):
    try:
        if feedback_type == "good":
            question = user_message.strip()
            if len(question) > 5:
                existing = KnowledgeBase.objects.filter(question__iexact=question).first()
                if existing:
                    existing.success_count += 1
                    existing.save()
                else:
                    KnowledgeBase.objects.create(
                        question=question,
                        best_response=bot_response.strip(),
                        category="general"
                    )
    except Exception:
        logger.exception("Error actualizando knowledge base")
