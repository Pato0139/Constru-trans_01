import json

# Cargar el respaldo
with open('backups/db_backup.json', 'r', encoding='utf-8') as f:
    datos = json.load(f)

# Editar cada material para agregar el campo 'activo': True
for item in datos:
    if item['model'] == 'usuarios.material':
        item['fields']['activo'] = True

# Guardar el respaldo editado
with open('backups/db_backup_actualizado.json', 'w', encoding='utf-8') as f:
    json.dump(datos, f, indent=2, ensure_ascii=False)

print("Respaldo actualizado exitosamente!")
