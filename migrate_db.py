import sqlite3

DATABASE = "project.db"

def migrate():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Add columns to courses table
    # We have to add them one by one because SQLite doesn't support multiple ADD COLUMN in one statement in older versions, 
    # and it's safer this way.
    columns = [
        ("weekdays", "TEXT"),
        ("time", "TEXT"),
        ("mode", "TEXT"),
        ("platform", "TEXT")
    ]

    print("Migrating database...")
    for col_name, col_type in columns:
        try:
            c.execute(f"ALTER TABLE courses ADD COLUMN {col_name} {col_type}")
            print(f"Added column {col_name}")
        except sqlite3.OperationalError as e:
            print(f"Column {col_name} might already exist: {e}")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
