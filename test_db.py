from database import get_db

try:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sys.tables")
    tablas = cursor.fetchall()

    print("Conexión exitosa ✅")
    for t in tablas:
        print(t[0])

    conn.close()
except Exception as e:
    print("Error ❌")
    print(e)
