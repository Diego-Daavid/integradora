from database import get_db


def listar_usuarios():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, nombre, rol FROM usuarios ORDER BY id DESC")
    rows = cursor.fetchall()
    db.close()
    return rows
