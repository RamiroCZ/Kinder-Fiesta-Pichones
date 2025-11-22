import sqlite3
import json
import re
from flask import Flask, render_template, request, jsonify, session

app = Flask(__name__)
app.secret_key = "clave-secreta-kinderfiesta"  # Necesario para usar session

def get_db_connection():
    conn = sqlite3.connect("kinderfiesta.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def ensure_schema():
    """Asegura que exista la tabla de salones pendientes para el panel admin."""
    conn = get_db_connection()
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
        # imagenes: JSON en texto -> lista
        try:
            imagenes = json.loads(s["imagenes"]) if s["imagenes"] else []
        except Exception:
            imagenes = []

        # promedio de estrellas
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
    usuario = (data.get("usuario") or "").strip()
    comentario = (data.get("comentario") or "").strip()
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
    # Verificar que el salon_id exista (por si foreign_keys estuviera off)
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

# ---------- API: recomendar salón (usuario) -> queda pendiente para revisión ----------
@app.route("/api/salones/recomendados", methods=["POST"])
def recomendar_salon():
    data = request.get_json() or {}
    campos = ["nombre", "direccion", "telefono", "mapa_url", "imagenes"]
    if not all((data.get(c) or "").strip() for c in campos):
        return jsonify({"error": "Todos los campos son obligatorios."}), 400

    # imagenes debe ser un JSON (lista de rutas). Admitimos string JSON o lista y lo normalizamos
    imagenes_val = data["imagenes"]
    if isinstance(imagenes_val, list):
        imagenes_text = json.dumps(imagenes_val, ensure_ascii=False)
    else:
        # intentar parsear si es string JSON; si no, rechazar
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
    """, (data["nombre"].strip(), data["direccion"].strip(), data["telefono"].strip(), data["mapa_url"].strip(), imagenes_text))
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

# ---------- Admin: aceptar salón pendiente -> mover a salones ----------
@app.route("/admin/salones-pendientes/<int:id>/aceptar", methods=["POST"])
def aceptar_salon(id):
    if not session.get("admin"):
        return jsonify({"error": "No autorizado"}), 403
    conn = get_db_connection()
    salon = conn.execute("SELECT * FROM salones_pendientes WHERE id = ?", (id,)).fetchone()
    if not salon:
        conn.close()
        return jsonify({"error": "Salón no encontrado"}), 404

    conn.execute("""
        INSERT INTO salones (nombre, direccion, telefono, mapa_url, imagenes)
        VALUES (?, ?, ?, ?, ?)
    """, (salon["nombre"], salon["direccion"], salon["telefono"], salon["mapa_url"], salon["imagenes"]))
    conn.execute("UPDATE salones_pendientes SET estado = 'aceptado' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Salón aceptado"}), 200

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
    conn.execute("UPDATE salones_pendientes SET estado = 'denegado' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Salón denegado"}), 200

# ---------- Inicio de la app ----------
if __name__ == "__main__":
    ensure_schema()
    app.run(debug=True)


