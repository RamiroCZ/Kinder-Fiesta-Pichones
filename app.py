import os
import sqlite3
import json
import re
from flask import Flask, render_template, request, jsonify, session
import secrets
import html

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = secrets.token_hex(32)

# ======== Paths y configuración de subida ========
UPLOAD_DIR = os.path.join("static", "salones")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect("kinderfiesta.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def ensure_schema():
    """Asegura tablas base y de pendientes."""
    conn = get_db_connection()
    # Tabla principal de salones si no existe
    conn.execute("""
    CREATE TABLE IF NOT EXISTS salones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        direccion TEXT NOT NULL,
        telefono TEXT NOT NULL,
        mapa_url TEXT,
        imagenes TEXT
    )
    """)
    # Tabla de comentarios si no existe
    conn.execute("""
    CREATE TABLE IF NOT EXISTS comentarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        salon_id INTEGER NOT NULL,
        usuario TEXT NOT NULL,
        comentario TEXT NOT NULL,
        estrellas INTEGER NOT NULL,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(salon_id) REFERENCES salones(id) ON DELETE CASCADE
    )
    """)
    # Tabla de salones pendientes
    conn.execute("""
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

# ---------- Filtro de groserías ----------
BAD_WORDS = {
    "mierda","carajo","puta","puto","pendejo","imbecil","estupido","idiota",
    "hdp","concha","chingar","perra","culero","cagada","boludo","qlo","mrd","vrg","vrga",
    "pito","polla","pedo","coño","cabron","cabrón","joder","cojudo","cojudazo","cojudita",
    "pendejada","chingada","chingadera","chingón","huevón","webón","weón","guevón","cagón",
    "cagona","cabrona","zorra","malparido","malparida","güevón","güevona","pajuo","pajudo",
    "gilipollas","hostia","carajazo","cojudazo","cojonudo","pelotudo","forro","baboso",
    "babosa","tarado","tarada","tonto","tonta","bobo","boba","payaso","payasa","payasada",
    "mamón","mamona","mamadera","mamapito","chupapija","chupamedias","chupapolla",
    "chupapito","chupacabra","chupasangre","chupaverga","cagón","cagona","cagoncito",
    "mierdita","mierdero","mierdoso","asqueroso","asquerosa","apestoso","apestosa",
    "cerote","verga","vergazo","vergón","verguita","chingoncito","chingoncita",
    "hijueputa","hijodeputa","hijaputa","hijadelagranputa","hp","hpta","hpt","joputa",
    "caraculo","carepito","careverga","careburro","caremondá","carechimba",
    "maldito","maldita","malnacido","malnacida","maldito sea","que te jodan",
    "que te follen","follar","follón","follador","mamabicho","comemierda","tragamierda",
    "metemierda","huevada","huevadas","huevón","huevona","huevear","joder","jodido",
    "jodida","jodete","chingate","chingatumadre","chingatumadrecabron",
    "chingatumadreputo","cagaste","cagar","cagón","cagona","cojones","cojonudo",
    "cojonuda","pichichi","pichula","pichón","pichona","pichanga","pito chico",
    "pito grande","vergüenza ajena","estúpida","atontado","atontada","bestia","animal",
    "maldito perro","maldita sea","perro","perra","lagarto","basura","basurita",
    "asno","menso","mensazo","torpe","tarupido","pelmazo","pelmaza","patán","patana",
    "chaparra","vago","vaga","desgraciado","desgraciada","infeliz","descebrado",
    "cuero","cochinada","cochino","cochina","porquería","porquerías","porquerizo",
    "porqueriza","idiotez","idioteces","tontería","tonterías","babosada","babosadas",
    "¡bah!","retardado","retardada","gil","gila","gilazo","gilaza","sonso","sonsa",
    "sonsoide","mocoso","mocosa","malhablado","malhablada","grosero","grosera",
    "desubicado","desubicada","manoseado","manoseada","infeliz","arrastrado",
    "arrastrada","patético","patética","corriente","vulgar","bruto","bruta","bestiecilla",
    "burrada","burro","burra","torpe","zángano","zángana","majadero","majadera",
    "malagradecido","malagradecida","arrogante","patudo","patuda","cachetón","cachetona",
    "desquiciado","desquiciada","lunático","lunática","odioso","odiosa","sarnoso",
    "sarnosa","víbora","culebra","lagartón","lagartona","puñeta","huevónazo",
    "pajarraco","cabronazo","cabronaza"
}

def contains_profanity(text: str) -> bool:
    text = text.lower()
    return any(bad in text for bad in BAD_WORDS)

def mask_profanity(text: str) -> str:
    for bad in BAD_WORDS:
        text = re.sub(bad, "*" * len(bad), text, flags=re.IGNORECASE)
    return text

# ---------- Página principal ----------
@app.route("/")
def index():
    conn = get_db_connection()
    salones = conn.execute("SELECT * FROM salones").fetchall()

    salones_list = []
    for s in salones:
        try:
            imagenes = json.loads(s["imagenes"]) if s["imagenes"] else []
        except Exception:
            imagenes = []
            
        comentarios_rows = conn.execute(
            "SELECT estrellas FROM comentarios WHERE salon_id=?", (s["id"],)
        ).fetchall()
        promedio = round(
            sum(c["estrellas"] for c in comentarios_rows) / len(comentarios_rows), 1
        ) if comentarios_rows else None

        salones_list.append({
            "id": s["id"],
            "nombre": s["nombre"],
            "direccion": s["direccion"],
            "telefono": s["telefono"],
            "mapa_url": s["mapa_url"],
            "imagenes": imagenes,
            "promedio": promedio
        })

    conn.close()
    return render_template("index.html", salones=salones_list)

# ---------- API: obtener comentarios ----------
@app.route("/api/salones/<int:salon_id>/comentarios")
def get_comentarios(salon_id):
    conn = get_db_connection()
    comentarios = conn.execute(
        "SELECT id, salon_id, usuario, comentario, estrellas, fecha FROM comentarios WHERE salon_id=? ORDER BY fecha DESC",
        (salon_id,)
    ).fetchall()
    conn.close()
    return jsonify([dict(c) for c in comentarios])

# ---------- API: agregar comentario ----------
@app.route("/api/salones/<int:salon_id>/comentarios", methods=["POST"])
def add_comentario(salon_id):
    data = request.get_json() or {}
    usuario = html.escape((data.get("usuario") or "").strip())
    comentario = html.escape((data.get("comentario") or "").strip())
    try:
        estrellas = int(data.get("estrellas", 0))
    except (ValueError, TypeError):
        estrellas = 0

    if not usuario or not comentario:
        return jsonify({"error": "Nombre y comentario son obligatorios."}), 400
    if estrellas < 1 or estrellas > 5:
        return jsonify({"error": "Las estrellas deben estar entre 1 y 5."}), 400

    # filtro de groserías
    if contains_profanity(usuario):
        usuario = mask_profanity(usuario)
    if contains_profanity(comentario):
        comentario = mask_profanity(comentario)

    conn = get_db_connection()
    salon_existe = conn.execute("SELECT 1 FROM salones WHERE id = ?", (salon_id,)).fetchone()
    if not salon_existe:
        conn.close()
        return jsonify({"error": "Salón no existe."}), 404

    conn.execute(
        "INSERT INTO comentarios (salon_id, usuario, comentario, estrellas) VALUES (?, ?, ?, ?)",
        (salon_id, usuario, comentario, estrellas)
    )
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Comentario agregado"}), 201
# ---------- Admin: login ----------
@app.route("/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json() or {}
    if data.get("usuario") == "admin" and data.get("clave") == "admin123":
        session["admin"] = True
        return jsonify({"mensaje": "Login exitoso"}), 200
    return jsonify({"error": "Credenciales inválidas"}), 401

# ---------- API: eliminar comentario (solo admin logueado) ----------
@app.route("/api/comentarios/<int:id>", methods=["DELETE"])
def delete_comentario(id):
    if not session.get("admin"):
        return jsonify({"error": "No autorizado"}), 403
    conn = get_db_connection()
    conn.execute("DELETE FROM comentarios WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Comentario eliminado"}), 200

# ---------- Formulario Sugerir Salón (con archivos) ----------
@app.route("/sugerir", methods=["POST"])
def sugerir_salon():
    # Campos del formulario (FormData)
    nombre = (request.form.get("nombre") or "").strip()
    direccion = (request.form.get("direccion") or "").strip()
    telefono = (request.form.get("telefono") or "").strip()
    mapa_url = (request.form.get("mapa_url") or "").strip()

    if not nombre or not direccion or not telefono or not mapa_url:
        return jsonify({"error": "Todos los campos son obligatorios"}), 400

    # Imágenes: mínimo 1, máximo 3
    imagenes_files = request.files.getlist("imagenes")
    # Filtrar vacíos (algunos navegadores reportan un file vacío si nada fue seleccionado)
    imagenes_files = [f for f in imagenes_files if getattr(f, "filename", "")]

    if len(imagenes_files) < 1:
        return jsonify({"error": "Debes subir al menos una imagen"}), 400
    if len(imagenes_files) > 3:
        return jsonify({"error": "Máximo 3 imágenes"}), 400

    rutas_guardadas = []
    for f in imagenes_files[:3]:
        # Normaliza nombre simple (puedes agregar secure_filename si usas Werkzeug)
        filename = f.filename.replace(" ", "_")
        save_path = os.path.join(UPLOAD_DIR, filename)
        f.save(save_path)
        rutas_guardadas.append(f"salones/{filename}")

    # Guardar sugerencia en pendientes
    conn = get_db_connection()
    conn.execute("""
        INSERT INTO salones_pendientes (nombre, direccion, telefono, mapa_url, imagenes)
        VALUES (?, ?, ?, ?, ?)
    """, (html.escape(nombre), html.escape(direccion), html.escape(telefono), mapa_url, json.dumps(rutas_guardadas)))
    conn.commit()
    conn.close()

    return jsonify({"mensaje": "Sugerencia enviada. Será revisada por el administrador."}), 201

# ---------- API: recomendar salón (JSON) [opcional, compatibilidad] ----------
@app.route("/api/salones/recomendados", methods=["POST"])
def recomendar_salon():
    data = request.get_json() or {}
    campos = ["nombre", "direccion", "telefono", "mapa_url", "imagenes"]
    if not all((data.get(c) or "").strip() for c in campos):
        return jsonify({"error": "Todos los campos son obligatorios."}), 400

    imagenes_val = data["imagenes"]
    if isinstance(imagenes_val, list):
        imagenes_text = json.dumps(imagenes_val, ensure_ascii=False)
    else:
        try:
            parsed = json.loads(imagenes_val)
            if not isinstance(parsed, list):
                return jsonify({"error": "El campo imagenes debe ser una lista JSON."}), 400
            imagenes_text = json.dumps(parsed, ensure_ascii=False)
        except Exception:
            return jsonify({"error": "El campo imagenes debe ser una lista JSON."}), 400

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO salones_pendientes (nombre, direccion, telefono, mapa_url, imagenes)
        VALUES (?, ?, ?, ?, ?)
    """, (html.escape(data["nombre"].strip()),
          html.escape(data["direccion"].strip()),
          html.escape(data["telefono"].strip()),
          data["mapa_url"].strip(),
          imagenes_text))
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Salón recomendado. Será revisado por el administrador."}), 201

# ---------- Admin: ver salones pendientes ----------
@app.route("/admin/salones-pendientes")
def ver_pendientes():
    if not session.get("admin"):
        return jsonify({"error": "No autorizado"}), 403
    conn = get_db_connection()
    salones = conn.execute("SELECT * FROM salones_pendientes WHERE estado = 'pendiente'").fetchall()
    conn.close()
    return jsonify([dict(s) for s in salones])

# ---------- Admin: aceptar salón pendiente ----------
@app.route("/admin/salones-pendientes/<int:id>/aceptar", methods=["POST"])
def aceptar_salon(id):
    if not session.get("admin"):
        return jsonify({"error": "No autorizado"}), 403

    conn = get_db_connection()
    salon = conn.execute("SELECT * FROM salones_pendientes WHERE id = ?", (id,)).fetchone()
    if not salon:
        conn.close()
        return jsonify({"error": "Salón no encontrado"}), 404

    # Insertar en la tabla principal de salones
    conn.execute("""
        INSERT INTO salones (nombre, direccion, telefono, mapa_url, imagenes)
        VALUES (?, ?, ?, ?, ?)
    """, (
        html.escape(salon["nombre"]),
        html.escape(salon["direccion"]),
        html.escape(salon["telefono"]),
        salon["mapa_url"],
        salon["imagenes"]
    ))

    # Eliminar de pendientes (ya no debe aparecer ahí)
    conn.execute("DELETE FROM salones_pendientes WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return jsonify({"mensaje": "Salón aprobado y publicado."}), 200


# ---------- Admin: denegar salón pendiente ----------
@app.route("/admin/salones-pendientes/<int:id>/denegar", methods=["POST"])
def denegar_salon(id):
    if not session.get("admin"):
        return jsonify({"error": "No autorizado"}), 403

    conn = get_db_connection()
    existe = conn.execute("SELECT 1 FROM salones_pendientes WHERE id = ?", (id,)).fetchone()
    if not existe:
        conn.close()
        return jsonify({"error": "Salón no encontrado"}), 404

    # Eliminar de pendientes
    conn.execute("DELETE FROM salones_pendientes WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return jsonify({"mensaje": "Salón denegado y eliminado de pendientes."}), 200

@app.route("/admin/salones/<int:id>/eliminar", methods=["POST"])
def eliminar_salon(id):
    if not session.get("admin"):
        return jsonify({"error": "No autorizado"}), 403

    conn = get_db_connection()
    existe = conn.execute("SELECT 1 FROM salones WHERE id = ?", (id,)).fetchone()
    if not existe:
        conn.close()
        return jsonify({"error": "Salón no encontrado"}), 404

    conn.execute("DELETE FROM salones WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return jsonify({"mensaje": "Salón eliminado correctamente"}), 200


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin", None)
    return jsonify({"mensaje": "Sesión cerrada"}), 200

# ---------- Inicio de la app ----------
if __name__ == "__main__":
    ensure_schema()
    app.run(debug=True)




