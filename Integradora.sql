USE Integradora;
GO

IF OBJECT_ID('devoluciones', 'U') IS NOT NULL DROP TABLE devoluciones;
IF OBJECT_ID('pagos_multa', 'U') IS NOT NULL DROP TABLE pagos_multa;
IF OBJECT_ID('prestamos', 'U') IS NOT NULL DROP TABLE prestamos;
IF OBJECT_ID('usuarios', 'U') IS NOT NULL DROP TABLE usuarios;
IF OBJECT_ID('materiales', 'U') IS NOT NULL DROP TABLE materiales;
GO

CREATE TABLE materiales (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion VARCHAR(255) NULL,
    cantidad INT NOT NULL CHECK (cantidad >= 0),
    estado VARCHAR(20) NOT NULL
);
GO

CREATE TABLE usuarios (
    id INT IDENTITY(1,1) PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    rol VARCHAR(20) NOT NULL
);
GO

CREATE TABLE prestamos (
    id INT IDENTITY(1,1) PRIMARY KEY,
    usuario_id INT NOT NULL,
    material_id INT NOT NULL,
    cantidad INT NOT NULL CHECK (cantidad > 0),
    fecha DATETIME NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'Activo',

    CONSTRAINT fk_prestamo_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    CONSTRAINT fk_prestamo_material FOREIGN KEY (material_id) REFERENCES materiales(id)
);
GO

CREATE TABLE devoluciones (
    id INT IDENTITY(1,1) PRIMARY KEY,
    prestamo_id INT NOT NULL,
    fecha DATETIME NOT NULL,
    observaciones VARCHAR(255) NULL,

    CONSTRAINT fk_devolucion_prestamo FOREIGN KEY (prestamo_id) REFERENCES prestamos(id)
);
GO

CREATE TABLE pagos_multa (
    id INT IDENTITY(1,1) PRIMARY KEY,
    usuario_id INT NOT NULL,
    prestamo_id INT NULL,
    motivo VARCHAR(20) NOT NULL,
    descripcion VARCHAR(255) NULL,
    monto DECIMAL(10,2) NOT NULL,
    moneda VARCHAR(10) NOT NULL DEFAULT 'MXN',
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
    paypal_order_id VARCHAR(64) NULL,
    paypal_capture_id VARCHAR(64) NULL,
    fecha_creacion DATETIME NOT NULL DEFAULT GETDATE(),
    fecha_pago DATETIME NULL,

    CONSTRAINT fk_pago_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    CONSTRAINT fk_pago_prestamo FOREIGN KEY (prestamo_id) REFERENCES prestamos(id)
);
GO

INSERT INTO usuarios (nombre, rol)
VALUES
('Jorge Alberto', 'Alumno'),
('Joshua Kimmich', 'Maestro'),
('Administrador', 'Admin');

INSERT INTO materiales (nombre, descripcion, cantidad, estado)
VALUES
('Proyector', 'Proyector HD para salón', 3, 'Disponible'),
('Laptop', 'Laptop para presentaciones', 5, 'Disponible'),
('Cable HDMI', 'Cable HDMI de 2 metros', 10, 'Disponible');

SELECT * FROM usuarios;
SELECT * FROM materiales;
