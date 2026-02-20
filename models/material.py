from database import get_db


def listar_materiales():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, nombre, descripcion, cantidad, estado FROM materiales ORDER BY id DESC")
    rows = cursor.fetchall()
    db.close()
    return rows
