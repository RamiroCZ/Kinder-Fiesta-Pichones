import sqlite3

def crear_bd():
    conn = sqlite3.connect("kinderfiesta.db")
    c = conn.cursor()

    # Tabla principal de salones
    c.execute("""
    CREATE TABLE IF NOT EXISTS salones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        direccion TEXT NOT NULL,
        telefono TEXT NOT NULL,
        mapa_url TEXT,
        imagenes TEXT
    )
    """)

    # Tabla de comentarios
    c.execute("""
    CREATE TABLE IF NOT EXISTS comentarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        salon_id INTEGER NOT NULL,
        usuario TEXT NOT NULL,
        comentario TEXT NOT NULL,
        estrellas INTEGER NOT NULL CHECK (estrellas BETWEEN 1 AND 5),
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (salon_id) REFERENCES salones(id)
    )
    """)

    # Tabla de salones pendientes (solo una vez)
    c.execute("""
    CREATE TABLE IF NOT EXISTS salones_pendientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        direccion TEXT NOT NULL,
        telefono TEXT NOT NULL,
        mapa_url TEXT,
        imagenes TEXT,
        estado TEXT DEFAULT 'pendiente'
    )
    """)

    conn.commit()
    conn.close()

def seed_demo():
    conn = sqlite3.connect("kinderfiesta.db")
    c = conn.cursor()

    # Limpiar datos previos
    c.execute("DELETE FROM comentarios")
    c.execute("DELETE FROM salones")
    c.execute("DELETE FROM salones_pendientes")

    # Insertar salones
    salones = [
        ("Salón Estrellitas","Carretera a Viacha, C. 137, El Alto","+591 73097977","https://maps.app.goo.gl/rb8swGawEhhoS9eaA",'["salones/SE1.PNG","salones/SE2.PNG","salones/SE3.JPG"]'),
        ("Salón Principito","Av. 16 de Julio, #60, El Alto","+591 68071787","https://maps.app.goo.gl/KtpzqzpXxDeGpBHL6",'["salones/SP1.JPG","salones/SP2.JPG"]'),
        ("Salón Condorito","Zona San Salvador, #50, El Alto","+591 71578344","https://maps.app.goo.gl/xSKrP13RYBLHLZr1A",'["salones/SC1.JPG","salones/SC2.JPG"]'),
        ("Salón Mi Pequeño Amor","Zona Echenique, La Paz","+591 79698747","https://maps.app.goo.gl/y3G31aPfYZWfyQve7",'["salones/PA1.JPG","salones/PA2.JPG","salones/PA3.JPG"]'),
        ("Salón Acuarela","Av. Buenos Aires, #591, La Paz","+591 62548751","https://maps.app.goo.gl/bJqBTqqvXTdhRpJ56",'["salones/SA1.JPG","salones/SA2.JPG","salones/SA3.JPG"]'),
        ("Salón Arca de Noé","Entre Av. Manuel Ballivian y Av. Alberto Gutierrez, La Paz","+591 71226763","https://maps.app.goo.gl/3mXvSWJhn8vHNVqr5",'["salones/AN1.JPG","salones/AN2.JPG","salones/AN3.JPG"]'),
        ("Salón Oso Goloso","Av. Eduardo Calderón, #2096, La Paz","+591 74518963","https://maps.app.goo.gl/rbNLmC1zejgQjKgz6",'["salones/OG1.JPG","salones/OG2.JPG"]'),
        ("Salón Cocazos","Av. Fernán Caballero, #868, El Alto","+591 69852147","https://maps.app.goo.gl/Vndp6eVqv1v7WHvj7",'["salones/SCO1.JPG","salones/SCO2.JPG"]'),
        ("Salón Rinconcito Feliz","C. Satélite, La Paz","+591 61246696","https://maps.app.goo.gl/Gumj7LQukB6ebG6c7",'["salones/SRF1.JPG","salones/SRF2.JPG"]'),
        ("Salón Burbujas","Av. Escalona y Aguero, Calle 27, El Alto","+591 78896967","https://maps.app.goo.gl/4E6LwAphBzZU7kb29",'["salones/SB1.JPG","salones/SB2.JPG","salones/SB3.JPG"]'),
    ]

    c.executemany(
        "INSERT INTO salones (nombre,direccion,telefono,mapa_url,imagenes) VALUES (?,?,?,?,?)",
        salones
    )

    conn.commit()
    conn.close()

if __name__ == "__main__":
    crear_bd()
    seed_demo()
    print("BD creada y 10 salones cargados.")



