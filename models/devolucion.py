from datetime import datetime

from database import get_db


def registrar_devolucion(prestamo_id: int, observaciones: str | None = None) -> bool:
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT material_id, cantidad, estado FROM prestamos WHERE id = ?",
        (prestamo_id,),
    )
    prestamo = cursor.fetchone()

    if not prestamo or prestamo.estado == "Devuelto":
        db.close()
        return False

    cursor.execute(
        "INSERT INTO devoluciones (prestamo_id, fecha, observaciones) VALUES (?, ?, ?)",
        (prestamo_id, datetime.now(), observaciones),
    )

    cursor.execute(
        "UPDATE prestamos SET estado = 'Devuelto' WHERE id = ?",
        (prestamo_id,),
    )

    cursor.execute(
        "UPDATE materiales SET cantidad = cantidad + ? WHERE id = ?",
        (prestamo.cantidad, prestamo.material_id),
    )

    db.commit()
    db.close()
    return True
