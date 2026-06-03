import sqlite3

# Connect to the database
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Empty the django_migrations table
cursor.execute('DELETE FROM django_migrations')

# Commit the changes
conn.commit()
print("Successfully cleared django_migrations table!")

# Close the connection
conn.close()
