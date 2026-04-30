import json

# Cargar el respaldo ORIGINAL
with open('backups/db_backup.json', 'r', encoding='utf-8') as f:
    datos = json.load(f)

# Filtrar para quitar los objetos de tipo 'clientes.cliente'
datos_filtrados = []
for item in datos:
    if item['model'] != 'clientes.cliente':
        datos_filtrados.append(item)

# Guardar el respaldo filtrado
with open('backups/db_backup_sin_clientes.json', 'w', encoding='utf-8') as f:
    json.dump(datos_filtrados, f, indent=2, ensure_ascii=False)

print("Respaldo filtrado listo (sin clientes.Cliente)!")
