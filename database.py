import sqlite3
import os

def init_db():
    db_path = 'ecommerce.db'
    schema_path = 'database/schema.sql'

    if os.path.exists(db_path):
        os.remove(db_path)  # Delete the existing database

    connection = sqlite3.connect(db_path)
    with open(schema_path, 'r') as schema_file:
        connection.executescript(schema_file.read())
    connection.close()
    print("Database initialized with the new schema.")

