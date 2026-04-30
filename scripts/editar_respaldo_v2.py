import json

# Cargar el respaldo ORIGINAL
with open('backups/db_backup.json', 'r', encoding='utf-8') as f:
    datos = json.load(f)

# NO agregamos el campo 'activo' - lo dejamos como está para que se cargue

# Guardar como respaldo final
with open('backups/db_backup_final.json', 'w', encoding='utf-8') as f:
    json.dump(datos, f, indent=2, ensure_ascii=False)

print("Respaldo final listo (sin campo 'activo')!")
