from datetime import datetime

from database import get_db


def registrar_prestamo(usuario_id: int, material_id: int, cantidad: int) -> bool:
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT cantidad FROM materiales WHERE id = ?", (material_id,))
    material = cursor.fetchone()

    if not material or material.cantidad < cantidad or cantidad <= 0:
        db.close()
        return False

    cursor.execute(
        """
        INSERT INTO prestamos (usuario_id, material_id, cantidad, fecha, estado)
        VALUES (?, ?, ?, ?, ?)
        """,
        (usuario_id, material_id, cantidad, datetime.now(), "Activo"),
    )

    cursor.execute(
        "UPDATE materiales SET cantidad = cantidad - ? WHERE id = ?",
        (cantidad, material_id),
    )

    db.commit()
    db.close()
    return True
