from copy import copy as _copy

import django.template.context as _template_context

# Patch para evitar que errores al crear LogEntry rompan el flujo del admin
try:
    from django.contrib.admin.models import LogEntry, LogEntryManager
    from django.contrib.contenttypes.models import ContentType
    from django.db.utils import IntegrityError

    _orig_log_actions = LogEntryManager.log_actions

    def _safe_log_actions(self, user_id, queryset, action_flag, change_message="", *, single_object=False):
        try:
            return _orig_log_actions(self, user_id, queryset, action_flag, change_message, single_object=single_object)
        except IntegrityError:
            # Fallback: intentar insertar los log entries individualmente en la BD 'default'
            try:
                results = []
                for obj in queryset:
                    ct_id = ContentType.objects.get_for_model(obj, for_concrete_model=False).id
                    entry = LogEntry(
                        user_id=user_id,
                        content_type_id=ct_id,
                        object_id=str(obj.pk),
                        object_repr=str(obj)[:200],
                        action_flag=action_flag,
                        change_message=change_message,
                    )
                    entry.save(using="default")
                    results.append(entry)
                if single_object and results:
                    return results[0]
                return results
            except Exception:
                import logging

                logger = logging.getLogger(__name__)
                logger.exception("Fallo al crear LogEntry en fallback; se omite el log")
                return None
    LogEntryManager.log_actions = _safe_log_actions
except Exception:
    # No detener el arranque si falla el parche
    pass


def _patched_basecontext_copy(self):
    duplicate = self.__class__.__new__(self.__class__)
    duplicate.__dict__.update(getattr(self, "__dict__", {}))
    duplicate.dicts = self.dicts[:] if hasattr(self, "dicts") else []
    if hasattr(self, "render_context"):
        duplicate.render_context = _copy(self.render_context)
    return duplicate


_template_context.BaseContext.__copy__ = _patched_basecontext_copy
