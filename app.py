import os
import ipaddress
import json
import base64
from datetime import datetime
from urllib import parse, request as urlrequest
from urllib.error import HTTPError

from flask import Flask, jsonify, redirect, render_template, request, url_for
from googleapiclient.discovery import build

from database import get_db

app = Flask(__name__)


def _load_dotenv(dotenv_path: str = ".env"):
    if not os.path.exists(dotenv_path):
        return

    try:
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        return


_load_dotenv()

YOUTUBE_API_KEY = "AIzaSyBvnMwemkmGmNx0KINLpLxHAXL82p3miPQ"
VIDEO_FALLBACK = "https://www.youtube.com/embed/dQw4w9WgXcQ"
PAYPAL_MODE = os.getenv("PAYPAL_MODE", "sandbox").strip().lower()
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "").strip()
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "").strip()
PAYPAL_CURRENCY = os.getenv("PAYPAL_CURRENCY", "MXN").strip().upper()


def buscar_video_tutorial(nombre_material: str):
    print("API key cargada:", bool(YOUTUBE_API_KEY))

    if not YOUTUBE_API_KEY:
        return None, None

    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

        search_res = youtube.search().list(
            q=f"tutorial {nombre_material}",
            part="snippet",
            type="video",
            maxResults=10,
        ).execute()

        video_ids = [item["id"]["videoId"] for item in search_res.get("items", [])]
        print("Video IDs encontrados:", video_ids)

        if not video_ids:
            return None, None

        details = youtube.videos().list(
            part="status",
            id=",".join(video_ids),
        ).execute()

        embeddable_ids = {
            item["id"]
            for item in details.get("items", [])
            if item.get("status", {}).get("embeddable") is True
        }
        print("Embeddables:", embeddable_ids)

        for vid in video_ids:
            if vid in embeddable_ids:
                return (
                    f"https://www.youtube.com/embed/{vid}",
                    f"https://www.youtube.com/watch?v={vid}",
                )

    except Exception as e:
        print("Error YouTube:", e)

    return None, None


def _api_error(message: str, status_code: int = 400):
    return jsonify({"ok": False, "error": message}), status_code


def _paypal_api_base():
    return "https://api-m.paypal.com" if PAYPAL_MODE == "live" else "https://api-m.sandbox.paypal.com"


def _paypal_configured():
    return bool(PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET)


def _paypal_request(path: str, method: str = "GET", body: dict | None = None, token: str | None = None):
    url = f"{_paypal_api_base()}{path}"
    headers = {"Content-Type": "application/json"}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urlrequest.Request(url=url, data=data, headers=headers, method=method)

    try:
        with urlrequest.urlopen(req, timeout=15) as response:
            return response.getcode(), json.loads(response.read().decode("utf-8"))
    except HTTPError as e:
        raw = e.read().decode("utf-8") if e.fp else "{}"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"message": raw}
        return e.code, payload


def _paypal_access_token():
    credentials = f"{PAYPAL_CLIENT_ID}:{PAYPAL_CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

    req = urlrequest.Request(
        url=f"{_paypal_api_base()}/v1/oauth2/token",
        data=b"grant_type=client_credentials",
        headers={
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    try:
        with urlrequest.urlopen(req, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("access_token")
    except Exception:
        return None


def _ensure_pagos_table():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        IF OBJECT_ID('pagos_multa', 'U') IS NULL
        BEGIN
            CREATE TABLE pagos_multa (
                id INT IDENTITY(1,1) PRIMARY KEY,
                usuario_id INT NOT NULL,
                prestamo_id INT NULL,
                motivo VARCHAR(20) NOT NULL,
                descripcion VARCHAR(255) NULL,
                monto DECIMAL(10,2) NOT NULL,
                moneda VARCHAR(10) NOT NULL,
                estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
                paypal_order_id VARCHAR(64) NULL,
                paypal_capture_id VARCHAR(64) NULL,
                fecha_creacion DATETIME NOT NULL DEFAULT GETDATE(),
                fecha_pago DATETIME NULL,
                CONSTRAINT fk_pago_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                CONSTRAINT fk_pago_prestamo FOREIGN KEY (prestamo_id) REFERENCES prestamos(id)
            );
        END
        """
    )
    conn.commit()
    conn.close()


def _cliente_ip():
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or ""


def _ip_valida(ip_texto: str):
    try:
        return str(ipaddress.ip_address(ip_texto))
    except ValueError:
        return None


@app.route("/api/v1/geolocalizacion/ip", methods=["GET"])
def geolocalizacion_por_ip():
    ip_entrada = (request.args.get("ip") or _cliente_ip()).strip()
    ip_limpia = _ip_valida(ip_entrada)

    if not ip_limpia:
        return _api_error("IP invalida. Usa IPv4 o IPv6.", 400)

    campos = "status,message,country,regionName,city,zip,lat,lon,timezone,isp,query"
    url = f"http://ip-api.com/json/{parse.quote(ip_limpia)}?fields={campos}"

    try:
        with urlrequest.urlopen(url, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return _api_error("No se pudo consultar el servicio de geolocalizacion por IP.", 502)

    if payload.get("status") != "success":
        return _api_error(payload.get("message", "No se encontro informacion para la IP."), 404)

    return jsonify(
        {
            "ok": True,
            "ip": payload.get("query"),
            "pais": payload.get("country"),
            "region": payload.get("regionName"),
            "ciudad": payload.get("city"),
            "codigo_postal": payload.get("zip"),
            "latitud": payload.get("lat"),
            "longitud": payload.get("lon"),
            "zona_horaria": payload.get("timezone"),
            "proveedor_internet": payload.get("isp"),
        }
    )


@app.route("/api/v1/geolocalizacion/direccion", methods=["POST"])
def geolocalizacion_por_direccion():
    data = request.get_json(silent=True) or {}
    direccion = str(data.get("direccion", "")).strip()

    if not direccion:
        return _api_error("Debes enviar 'direccion' en el body JSON.", 400)

    query_string = parse.urlencode({"format": "jsonv2", "limit": 1, "q": direccion})
    url = f"https://nominatim.openstreetmap.org/search?{query_string}"
    req = urlrequest.Request(
        url,
        headers={
            "User-Agent": "IntegradoraApp/1.0 (geolocalizacion)",
            "Accept": "application/json",
        },
    )

    try:
        with urlrequest.urlopen(req, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return _api_error("No se pudo consultar el servicio de geocodificacion.", 502)

    if not payload:
        return _api_error("No se encontraron coordenadas para esa direccion.", 404)

    resultado = payload[0]
    return jsonify(
        {
            "ok": True,
            "direccion_consultada": direccion,
            "direccion_formateada": resultado.get("display_name"),
            "latitud": float(resultado.get("lat")),
            "longitud": float(resultado.get("lon")),
        }
    )


@app.route("/api/v1/clima/actual", methods=["GET"])
def clima_actual():
    lat_texto = (request.args.get("lat") or "").strip()
    lon_texto = (request.args.get("lon") or "").strip()

    if not lat_texto or not lon_texto:
        return _api_error("Debes enviar 'lat' y 'lon' como query params.", 400)

    try:
        latitud = float(lat_texto)
        longitud = float(lon_texto)
    except ValueError:
        return _api_error("Los valores de 'lat' y 'lon' deben ser numericos.", 400)

    if not -90 <= latitud <= 90:
        return _api_error("La latitud debe estar entre -90 y 90.", 400)
    if not -180 <= longitud <= 180:
        return _api_error("La longitud debe estar entre -180 y 180.", 400)

    query_string = parse.urlencode(
        {
            "latitude": latitud,
            "longitude": longitud,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
            "timezone": "auto",
        }
    )
    url = f"https://api.open-meteo.com/v1/forecast?{query_string}"

    try:
        with urlrequest.urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return _api_error("No se pudo consultar el servicio de clima.", 502)

    clima = payload.get("current")
    unidades = payload.get("current_units", {})
    if not clima:
        return _api_error("No se encontro informacion de clima para esas coordenadas.", 404)

    return jsonify(
        {
            "ok": True,
            "latitud": payload.get("latitude"),
            "longitud": payload.get("longitude"),
            "zona_horaria": payload.get("timezone"),
            "hora_medicion": clima.get("time"),
            "temperatura": clima.get("temperature_2m"),
            "sensacion_termica": clima.get("apparent_temperature"),
            "humedad_relativa": clima.get("relative_humidity_2m"),
            "precipitacion": clima.get("precipitation"),
            "codigo_clima": clima.get("weather_code"),
            "velocidad_viento": clima.get("wind_speed_10m"),
            "unidades": {
                "temperatura": unidades.get("temperature_2m"),
                "sensacion_termica": unidades.get("apparent_temperature"),
                "humedad_relativa": unidades.get("relative_humidity_2m"),
                "precipitacion": unidades.get("precipitation"),
                "velocidad_viento": unidades.get("wind_speed_10m"),
            },
        }
    )





@app.route("/")
def index():
    return render_template("index.html")


@app.route("/geolocalizacion")
def geolocalizacion():
    return render_template("geolocalizacion.html")


@app.route("/materiales")
def materiales():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, nombre, descripcion, cantidad, estado
        FROM materiales
        ORDER BY id DESC
        """
    )
    materiales_db = cursor.fetchall()
    conn.close()

    video_url, video_watch_url = buscar_video_tutorial(
    materiales_db[0].nombre if materiales_db else "herramienta de laboratorio"
)


    return render_template(
        "materiales.html",
        materiales=materiales_db,
        video_url=video_url,
        video_watch_url=video_watch_url,
    )



@app.route("/materiales/nuevo", methods=["GET", "POST"])
def nuevo_material():
    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        descripcion = request.form.get("descripcion", "").strip()
        cantidad = int(request.form["cantidad"])
        estado = request.form["estado"].strip()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO materiales (nombre, descripcion, cantidad, estado)
            VALUES (?, ?, ?, ?)
            """,
            (nombre, descripcion, cantidad, estado),
        )
        conn.commit()
        conn.close()

        return redirect(url_for("materiales"))

    return render_template("registrar_material.html")


@app.route("/usuarios", methods=["GET", "POST"])
def usuarios():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        rol = request.form["rol"].strip()

        if nombre and rol:
            cursor.execute(
                "INSERT INTO usuarios (nombre, rol) VALUES (?, ?)",
                (nombre, rol),
            )
            conn.commit()
            conn.close()
            return redirect(url_for("usuarios"))

    cursor.execute("SELECT id, nombre, rol FROM usuarios ORDER BY id DESC")
    usuarios_db = cursor.fetchall()
    conn.close()

    return render_template("usuarios.html", usuarios=usuarios_db)


@app.route("/prestamos", methods=["GET", "POST"])
def prestamos():
    error = None
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        try:
            usuario_id = int(request.form["usuario_id"])
            material_id = int(request.form["material_id"])
            cantidad = int(request.form["cantidad"])
        except (ValueError, KeyError):
            error = "Datos inválidos en el formulario."
        else:
            if cantidad <= 0:
                error = "La cantidad debe ser mayor a 0."
            else:
                cursor.execute("SELECT cantidad FROM materiales WHERE id = ?", (material_id,))
                material = cursor.fetchone()

                if not material:
                    error = "El material no existe."
                elif material.cantidad < cantidad:
                    error = "No hay stock suficiente para ese préstamo."
                else:
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
                    conn.commit()
                    conn.close()
                    return redirect(url_for("prestamos"))

    cursor.execute(
        """
        SELECT
            p.id,
            u.nombre AS usuario,
            m.nombre AS material,
            p.cantidad,
            p.fecha,
            p.estado
        FROM prestamos p
        JOIN usuarios u ON p.usuario_id = u.id
        JOIN materiales m ON p.material_id = m.id
        ORDER BY p.id DESC
        """
    )
    prestamos_db = cursor.fetchall()

    cursor.execute("SELECT id, nombre, cantidad FROM materiales WHERE cantidad > 0 ORDER BY nombre")
    materiales_db = cursor.fetchall()

    cursor.execute("SELECT id, nombre, rol FROM usuarios ORDER BY nombre")
    usuarios_db = cursor.fetchall()

    conn.close()

    return render_template(
        "prestamos.html",
        prestamos=prestamos_db,
        materiales=materiales_db,
        usuarios=usuarios_db,
        error=error,
    )


@app.route("/pagos")
def pagos():
    _ensure_pagos_table()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, nombre, rol FROM usuarios ORDER BY nombre")
    usuarios_db = cursor.fetchall()

    try:
        cursor.execute(
            """
            SELECT p.id, u.nombre AS usuario, m.nombre AS material, p.fecha, p.estado
            FROM prestamos p
            JOIN usuarios u ON p.usuario_id = u.id
            JOIN materiales m ON p.material_id = m.id
            ORDER BY p.id DESC
            """
        )
        prestamos_db = cursor.fetchall()
    except Exception:
        # Compatibilidad con esquemas antiguos de la tabla prestamos.
        cursor.execute(
            """
            SELECT
                p.id,
                CAST(p.id AS VARCHAR(30)) AS usuario,
                'Prestamo' AS material,
                GETDATE() AS fecha,
                'Activo' AS estado
            FROM prestamos p
            ORDER BY p.id DESC
            """
        )
        prestamos_db = cursor.fetchall()

    cursor.execute(
        """
        SELECT
            pm.id,
            u.nombre AS usuario,
            pm.motivo,
            pm.descripcion,
            pm.monto,
            pm.moneda,
            pm.estado,
            pm.paypal_order_id,
            pm.paypal_capture_id,
            pm.fecha_creacion,
            pm.fecha_pago
        FROM pagos_multa pm
        JOIN usuarios u ON pm.usuario_id = u.id
        ORDER BY pm.id DESC
        """
    )
    pagos_db = cursor.fetchall()
    conn.close()

    return render_template(
        "pagos.html",
        usuarios=usuarios_db,
        prestamos=prestamos_db,
        pagos=pagos_db,
        paypal_client_id=PAYPAL_CLIENT_ID,
        paypal_currency=PAYPAL_CURRENCY,
        paypal_configured=_paypal_configured(),
        paypal_mode=PAYPAL_MODE,
    )


@app.route("/pagos/crear-orden", methods=["POST"])
def crear_orden_pago():
    if not _paypal_configured():
        return _api_error("PayPal no esta configurado. Falta PAYPAL_CLIENT_ID o PAYPAL_CLIENT_SECRET.", 500)

    _ensure_pagos_table()
    data = request.get_json(silent=True) or {}

    try:
        usuario_id = int(data.get("usuario_id"))
        prestamo_id_raw = data.get("prestamo_id")
        prestamo_id = int(prestamo_id_raw) if prestamo_id_raw else None
        monto = round(float(data.get("monto")), 2)
    except (TypeError, ValueError):
        return _api_error("Datos invalidos para crear el pago.", 400)

    motivo = str(data.get("motivo", "")).strip().lower()
    descripcion = str(data.get("descripcion", "")).strip()

    if motivo not in {"atraso", "perdida"}:
        return _api_error("El motivo debe ser 'atraso' o 'perdida'.", 400)
    if monto <= 0:
        return _api_error("El monto debe ser mayor a 0.", 400)

    access_token = _paypal_access_token()
    if not access_token:
        return _api_error("No se pudo autenticar con PayPal.", 502)

    amount_str = f"{monto:.2f}"
    body = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {
                    "currency_code": PAYPAL_CURRENCY,
                    "value": amount_str,
                },
                "description": f"Multa por {motivo}: {descripcion or 'Sin descripcion'}",
            }
        ],
        "application_context": {
            "brand_name": "Sistema de Control de Materiales",
            "shipping_preference": "NO_SHIPPING",
            "user_action": "PAY_NOW",
        },
    }

    status, payload = _paypal_request(
        path="/v2/checkout/orders",
        method="POST",
        body=body,
        token=access_token,
    )
    if status not in {200, 201}:
        return _api_error(f"PayPal rechazo la orden: {payload.get('message', 'sin detalle')}", 502)

    order_id = payload.get("id")
    if not order_id:
        return _api_error("No se recibio un order id de PayPal.", 502)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO pagos_multa
        (usuario_id, prestamo_id, motivo, descripcion, monto, moneda, estado, paypal_order_id, fecha_creacion)
        VALUES (?, ?, ?, ?, ?, ?, 'PENDIENTE', ?, ?)
        """,
        (
            usuario_id,
            prestamo_id,
            motivo,
            descripcion,
            monto,
            PAYPAL_CURRENCY,
            order_id,
            datetime.now(),
        ),
    )
    conn.commit()
    cursor.execute("SELECT TOP 1 id FROM pagos_multa WHERE paypal_order_id = ? ORDER BY id DESC", (order_id,))
    pago = cursor.fetchone()
    conn.close()

    return jsonify({"ok": True, "order_id": order_id, "pago_id": pago.id if pago else None})


@app.route("/pagos/capturar/<order_id>", methods=["POST"])
def capturar_orden_pago(order_id):
    if not _paypal_configured():
        return _api_error("PayPal no esta configurado.", 500)

    access_token = _paypal_access_token()
    if not access_token:
        return _api_error("No se pudo autenticar con PayPal.", 502)

    status, payload = _paypal_request(
        path=f"/v2/checkout/orders/{parse.quote(order_id)}/capture",
        method="POST",
        body={},
        token=access_token,
    )
    if status not in {200, 201}:
        return _api_error(f"No se pudo capturar el pago: {payload.get('message', 'sin detalle')}", 502)

    capture_id = None
    try:
        capture_id = (
            payload.get("purchase_units", [])[0]
            .get("payments", {})
            .get("captures", [])[0]
            .get("id")
        )
    except (IndexError, AttributeError):
        capture_id = None

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE pagos_multa
        SET estado = 'PAGADO', paypal_capture_id = ?, fecha_pago = ?
        WHERE paypal_order_id = ?
        """,
        (capture_id, datetime.now(), order_id),
    )
    conn.commit()
    conn.close()

    return jsonify({"ok": True, "order_id": order_id, "capture_id": capture_id})


if __name__ == "__main__":
    app.run(debug=True)
