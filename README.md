[README (1).md](https://github.com/user-attachments/files/25614867/README.1.md)
# Sistema de Control de Materiales

Sistema web desarrollado con **Flask** y **SQL Server** para gestionar el préstamo de materiales en un entorno académico. Permite registrar usuarios, materiales, préstamos y devoluciones, además de cobrar multas mediante **PayPal**. Incluye funcionalidades extra como geolocalización por IP/dirección, consulta de clima en tiempo real y búsqueda automática de tutoriales en YouTube.

---

## Características principales

- **Materiales** — Alta, listado y control de stock de equipos disponibles.
- **Usuarios** — Registro de alumnos, maestros y administradores.
- **Préstamos** — Registro de préstamos con descuento automático de inventario.
- **Devoluciones** — Marcado de préstamos como devueltos con restitución de stock.
- **Pagos de multas** — Cobro de multas por atraso o pérdida integrado con PayPal (sandbox/live).
- **Geolocalización** — Consulta de ubicación por IP (ip-api.com) y por dirección (Nominatim/OpenStreetMap).
- **Clima** — Condiciones meteorológicas en tiempo real por coordenadas (Open-Meteo).
- **Tutoriales YouTube** — Búsqueda automática de videos embebibles relacionados con cada material.

---

## Tecnologías

| Capa | Tecnología |
|------|------------|
| Backend | Python 3.11+ / Flask |
| Base de datos | SQL Server (Express) con pyodbc |
| Pagos | PayPal REST API v2 |
| YouTube | Google API Python Client |
| Clima | Open-Meteo (sin API key) |
| Geocodificación | Nominatim (OpenStreetMap) |
| Geolocalización IP | ip-api.com |

---

## Requisitos previos

Antes de instalar asegúrate de tener lo siguiente:

- Python 3.11 o superior
- SQL Server (edición Express es suficiente) con el driver **ODBC Driver 17 for SQL Server**
- pip (incluido con Python)
- Git (opcional, para clonar el repositorio)
- Credenciales de PayPal (cuenta de desarrollador en [developer.paypal.com](https://developer.paypal.com))
- API Key de YouTube Data v3 (desde [Google Cloud Console](https://console.cloud.google.com))

---

## Instalación

### 1. Clonar o descargar el proyecto

```bash
git clone https://github.com/tu-usuario/tu-repositorio.git
cd tu-repositorio
```

O simplemente descarga y descomprime el ZIP del proyecto.

### 2. Crear un entorno virtual (recomendado)

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

Las dependencias instaladas son:

- `Flask` — framework web
- `pyodbc` — conector para SQL Server
- `google-api-python-client` — cliente de la API de YouTube

### 4. Configurar la base de datos

Abre SQL Server Management Studio (SSMS) o cualquier cliente compatible y ejecuta el script de inicialización:

```sql
-- Desde SSMS, abre el archivo y ejecútalo:
Integradora.sql
```

El script crea la base de datos `Integradora` con las tablas necesarias e inserta datos de prueba (3 usuarios y 3 materiales).

### 5. Configurar variables de entorno

Copia el archivo de ejemplo y rellena tus credenciales:

```bash
cp .env.example .env
```

Edita `.env` con tus datos reales:

```env
# Modo de PayPal: "sandbox" para pruebas, "live" para producción
PAYPAL_MODE=sandbox

# Credenciales de tu aplicación en developer.paypal.com
PAYPAL_CLIENT_ID=tu_client_id_aqui
PAYPAL_CLIENT_SECRET=tu_secret_aqui

# Moneda a usar en los cobros
PAYPAL_CURRENCY=MXN
```

> **Nota:** El archivo `.env` está en `.gitignore` y nunca debe subirse al repositorio.

### 6. (Opcional) Configurar conexión a SQL Server

Si tu instancia de SQL Server usa una configuración diferente a la predeterminada, puedes agregar las siguientes variables al `.env`:

```env
DB_DRIVER=ODBC Driver 17 for SQL Server
DB_SERVER=localhost\SQLEXPRESS
DB_NAME=Integradora
DB_TRUSTED_CONNECTION=yes
```

---

## Ejecución

### Iniciar el servidor de desarrollo

Con el entorno virtual activo, ejecuta:

```bash
python app.py
```

La aplicación estará disponible en:

```
http://127.0.0.1:5000
```

### Verificar la conexión a la base de datos

Puedes usar el script de prueba incluido:

```bash
python test_db.py
```

Si la conexión es exitosa verás:

```
Conexión exitosa ✅
materiales
usuarios
prestamos
devoluciones
pagos_multa
```

---

## Estructura del proyecto

```
/
├── app.py                  # Aplicación Flask principal (rutas y lógica)
├── database.py             # Conexión a SQL Server con pyodbc
├── models/
│   ├── material.py         # Lógica de materiales
│   ├── usuario.py          # Lógica de usuarios
│   ├── prestamo.py         # Lógica de préstamos
│   └── devolucion.py       # Lógica de devoluciones
├── templates/
│   ├── layout.html         # Plantilla base con navbar
│   ├── index.html          # Página de inicio
│   ├── materiales.html     # Listado de materiales + video tutorial
│   ├── registrar_material.html  # Formulario de nuevo material
│   ├── usuarios.html       # Gestión de usuarios
│   ├── prestamos.html      # Gestión de préstamos
│   ├── pagos.html          # Cobro de multas con PayPal
│   └── geolocalizacion.html     # Interfaz de APIs de geo/clima
├── static/                 # Archivos estáticos (CSS, imágenes)
├── Integradora.sql         # Script de creación de la base de datos
├── test_db.py              # Script de prueba de conexión
├── requirements.txt        # Dependencias Python
├── .env.example            # Plantilla de variables de entorno
└── .gitignore
```

---

## Módulos del sistema

### Materiales (`/materiales`)
Lista todos los materiales con su stock actual. Muestra automáticamente un video tutorial de YouTube relacionado con el primer material del catálogo. Permite agregar nuevos materiales desde `/materiales/nuevo`.

### Usuarios (`/usuarios`)
Permite registrar usuarios con rol `Alumno`, `Maestro` o `Admin`. Muestra el listado completo de usuarios registrados.

### Préstamos (`/prestamos`)
Registra el préstamo de un material a un usuario. Valida que haya stock suficiente antes de confirmar y descuenta automáticamente la cantidad del inventario.

### Pagos de multas (`/pagos`)
Genera cobros por **atraso** o **pérdida** de materiales. Usa el SDK de PayPal para procesar el pago directamente en la página. El estado del pago se actualiza en la base de datos al completarse.

### Geolocalización (`/geolocalizacion`)
Expone tres endpoints de API REST y una interfaz visual para probarlos:

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/geolocalizacion/ip` | GET | Geolocalización por dirección IP |
| `/api/v1/geolocalizacion/direccion` | POST | Coordenadas a partir de una dirección de texto |
| `/api/v1/clima/actual` | GET | Clima actual dado latitud y longitud |

### capturas de pantalla
<img width="1600" height="852" alt="image" src="https://github.com/user-attachments/assets/b3dd993e-5672-47cb-bbd8-8027c0389c7f" />
<img width="1600" height="727" alt="image" src="https://github.com/user-attachments/assets/65d9a6ee-a58f-4484-b2cb-b8ace83a7e21" />
<img width="1600" height="797" alt="image" src="https://github.com/user-attachments/assets/69ce2981-f3d9-42b8-aa2b-62eaf031e942" />
<img width="1600" height="760" alt="image" src="https://github.com/user-attachments/assets/d0faefe4-88bb-4dd0-ae0a-cf1a1ade01ce" />
<img width="1136" height="729" alt="image" src="https://github.com/user-attachments/assets/5b1d0a6b-729c-4f86-ad6e-4915bdbc9f1d" />
<img width="1600" height="839" alt="image" src="https://github.com/user-attachments/assets/f147cd67-0bfe-431a-9a8d-27f511c17743" />
<img width="1600" height="790" alt="image" src="https://github.com/user-attachments/assets/b8ec5ea4-9e97-4421-9b93-286b58656164" />
<img width="1600" height="844" alt="image" src="https://github.com/user-attachments/assets/258f02db-6d65-4af2-9cac-c70b6c72a94c" />

---

## Equipo de desarrollo

| Nombre | Rol |
|--------|-----|
| Jorge Alberto | Desarrollador |
| Diego David | Desarrollador |
| Cristian Uriel | Desarrollador |

Proyecto Integrador II — 7EE2
