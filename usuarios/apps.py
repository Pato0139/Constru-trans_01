from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "usuarios"

    def ready(self):
        # Parche para asegurar que los LogEntry del admin se guarden
        # en la misma base de datos que el `request.user`, evitando
        # violaciones de FK cuando se usan múltiples DBs.
        try:
            from django.contrib import admin
            from django.contrib.admin.options import ModelAdmin
            from django.contrib.contenttypes.models import ContentType
            from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION

            def _get_user_db(request):
                try:
                    return getattr(request.user, "_state", None).db or "default"
                except Exception:
                    return "default"

            def patched_log_action_save(entry, using_db):
                try:
                    entry.save(using=using_db)
                    return entry
                except Exception:
                    # Dejar registro en logs pero no impedir la operación
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.exception("No se pudo guardar LogEntry en DB %s", using_db)
                    return None

            def log_addition(self, request, obj, message):
                user_db = _get_user_db(request)
                ct_id = ContentType.objects.get_for_model(obj, for_concrete_model=False).pk
                entry = LogEntry(
                    user_id=request.user.pk,
                    content_type_id=ct_id,
                    object_id=obj.pk,
                    object_repr=str(obj)[:200],
                    action_flag=ADDITION,
                    change_message=message,
                )
                return patched_log_action_save(entry, user_db)

            def log_change(self, request, obj, message):
                user_db = _get_user_db(request)
                ct_id = ContentType.objects.get_for_model(obj, for_concrete_model=False).pk
                entry = LogEntry(
                    user_id=request.user.pk,
                    content_type_id=ct_id,
                    object_id=obj.pk,
                    object_repr=str(obj)[:200],
                    action_flag=CHANGE,
                    change_message=message,
                )
                return patched_log_action_save(entry, user_db)

            def log_deletions(self, request, queryset):
                user_db = _get_user_db(request)
                ct = ContentType
                log_entries = []
                for obj in queryset:
                    ct_id = ContentType.objects.get_for_model(obj, for_concrete_model=False).pk
                    entry = LogEntry(
                        user_id=request.user.pk,
                        content_type_id=ct_id,
                        object_id=obj.pk,
                        object_repr=str(obj)[:200],
                        action_flag=DELETION,
                        change_message="",
                    )
                    saved = patched_log_action_save(entry, user_db)
                    if saved:
                        log_entries.append(saved)
                return log_entries

            # Aplicar parche
            ModelAdmin.log_addition = log_addition
            ModelAdmin.log_change = log_change
            ModelAdmin.log_deletions = log_deletions

        except Exception:
            # No queremos que un fallo aquí impida levantar la app
            import logging

            logger = logging.getLogger(__name__)
            logger.exception("Error aplicando parche de LogEntry en UsuariosConfig.ready()")
