import sqlite3
import json
import os
import uuid

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'layers.db')

# Ensure the database and table exist
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS layers (
            uuid TEXT PRIMARY KEY,
            file_path TEXT,
            settings_json TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Save sidebar settings for a uuid (settings is a dict)
def save_layer_settings(uuid_val, file_path, settings):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    settings_json = json.dumps(settings)
    c.execute('''
        INSERT INTO layers (uuid, file_path, settings_json)
        VALUES (?, ?, ?)
        ON CONFLICT(uuid) DO UPDATE SET file_path=excluded.file_path, settings_json=excluded.settings_json
    ''', (uuid_val, file_path, settings_json))
    conn.commit()
    conn.close()

# Load sidebar settings for a uuid (returns dict or None)
def load_layer_settings(uuid_val):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT settings_json FROM layers WHERE uuid=?', (uuid_val,))
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None

# List all layers (uuid, file_path, settings)
def list_layers():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT uuid, file_path, settings_json FROM layers')
    rows = c.fetchall()
    conn.close()
    return [(uuid_val, fp, json.loads(js)) for uuid_val, fp, js in rows]

# Remove a layer by uuid
def remove_layer(uuid_val):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM layers WHERE uuid=?', (uuid_val,))
    conn.commit()
    conn.close()

# Generate a new unique layer id
def generate_layer_id():
    return str(uuid.uuid4())

# Call on startup to ensure DB exists
init_db()

# Call on startup to ensure DB exists
init_db()
