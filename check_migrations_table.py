import sqlite3

# Connect to the database
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

print("Contents of django_migrations table:")
cursor.execute('SELECT id, app, name FROM django_migrations')
rows = cursor.fetchall()

for row in rows:
    print(row)

# Close the connection
conn.close()
