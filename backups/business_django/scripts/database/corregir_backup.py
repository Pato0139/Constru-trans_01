import json
import os
import sys

# Añadir el directorio raíz al sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django  # noqa: E402
from django.apps import apps  # noqa: E402
from django.db import models  # noqa: E402

django.setup()

# Obtener todos los campos válidos por modelo
campos_validos_por_modelo = {}
campos_obligatorios_por_modelo = {}
for modelo in apps.get_models():
    app_label = modelo._meta.app_label
    model_name = modelo._meta.model_name
    key = f"{app_label}.{model_name}"
    campos = [f.name for f in modelo._meta.fields]
    campos_validos_por_modelo[key] = campos
    # Identificar campos obligatorios sin valor predeterminado
    obligatorios = []
    for field in modelo._meta.fields:
        if not field.null and field.default == models.NOT_PROVIDED and not field.primary_key:
            obligatorios.append(field)
    campos_obligatorios_por_modelo[key] = obligatorios
    print(f"Modelo {key}: campos={campos}, obligatorios={[f.name for f in obligatorios]}")


# Leer el backup original
with open("backups/db_backup_actualizado.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Corregir los objetos
datos_corregidos = []
for obj in data:
    model_key = obj["model"]
    if model_key in campos_validos_por_modelo:
        campos_validos = campos_validos_por_modelo[model_key]
        campos_obligatorios = campos_obligatorios_por_modelo[model_key]
        fields_corregidos = {}

        # Primero, copiar los campos que sí existen
        for campo, valor in obj["fields"].items():
            if campo in campos_validos:
                fields_corregidos[campo] = valor

        # Ahora, agregar valores predeterminados para campos obligatorios que falten
        for field in campos_obligatorios:
            if field.name not in fields_corregidos:
                # Determinar valor predeterminado según tipo de campo
                if isinstance(field, models.CharField):
                    fields_corregidos[field.name] = ""
                elif isinstance(field, models.TextField):
                    fields_corregidos[field.name] = ""
                elif isinstance(field, models.IntegerField):
                    fields_corregidos[field.name] = 0
                elif isinstance(field, models.DecimalField):
                    fields_corregidos[field.name] = "0.00"
                elif isinstance(field, models.BooleanField):
                    fields_corregidos[field.name] = False
                elif isinstance(field, models.DateField):
                    fields_corregidos[field.name] = "2026-01-01"
                elif isinstance(field, models.DateTimeField):
                    fields_corregidos[field.name] = "2026-01-01T00:00:00Z"

        datos_corregidos.append(
            {"model": obj["model"], "pk": obj["pk"], "fields": fields_corregidos}
        )
    else:
        print(f"Modelo {model_key} no encontrado en la app, saltando...")

# Guardar el backup corregido
with open("backups/db_backup_corregido.json", "w", encoding="utf-8") as f:
    json.dump(datos_corregidos, f, ensure_ascii=False, indent=2)

print("\nBackup corregido guardado como backups/db_backup_corregido.json")
print(f"Total objetos: {len(datos_corregidos)}")
