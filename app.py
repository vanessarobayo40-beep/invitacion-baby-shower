"""
Invitación Baby Shower · Lista de Regalos con reserva
------------------------------------------------------
Los invitados pueden apartar un regalo y los demás ven en tiempo real cuáles
ya están reservados (sin registrarse).

Almacenamiento:
  • En tu PC (local): SQLite -> archivo regalos.db
  • En la nube (producción): PostgreSQL si existe la variable DATABASE_URL
    (así las reservas quedan guardadas de forma permanente).
"""
import os
import datetime
from flask import Flask, render_template, request, jsonify, g

app = Flask(__name__)

# ---- ¿Postgres (nube) o SQLite (local)? ----
DATABASE_URL = os.getenv("DATABASE_URL")
IS_PG = bool(DATABASE_URL)
if IS_PG:
    import psycopg
    from psycopg.rows import dict_row
else:
    import sqlite3
    DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "regalos.db"))

# Clave para el modo anfitrión (agregar/eliminar regalos). Cámbiala en producción.
HOST_KEY = os.getenv("HOST_KEY", "mama2026")

# Datos de la invitación (se pueden sobrescribir con variables de entorno)
EVENT = {
    "title":    os.getenv("EVENT_TITLE", "Baby Shower"),
    "baby":     os.getenv("EVENT_BABY", "Baby Apellido"),
    "subtitle": os.getenv("EVENT_SUBTITLE", "Aparta tu regalo y evitemos repetidos 💙"),
    "date":     os.getenv("EVENT_DATE", "Sábado 15 de Agosto · 4:00 PM"),
    "place":    os.getenv("EVENT_PLACE", "Salón Las Nubes · Ciudad"),
}

SEED_GIFTS = [
    ("Pañales talla 1",         "Marca preferida: cualquiera 🙏", "🧷", ""),
    ("Body / mamelucos 0-3m",   "En tonos celeste o neutro",      "👶", ""),
    ("Manta de algodón",        "Suave para envolverlo",          "🧸", ""),
    ("Biberones anticólico",    "Set de 2 o 3",                   "🍼", ""),
    ("Toallitas húmedas",       "Pack grande, siempre útiles",    "🧻", ""),
    ("Set de baño para bebé",   "Bañera, shampoo y toallas",      "🛁", ""),
    ("Monitor de bebé",         "Para vigilarlo mientras duerme", "📡", ""),
    ("Cobija / saco de dormir", "Para noches frescas",            "🌙", ""),
    ("Juguetes de estimulación","Sonajeros y mordedores",         "🪀", ""),
    ("Cuna portátil / corral",  "Para la sala o viajes",          "🛏️", ""),
    ("Coche / carriola",        "Color azul o gris",              "🚼", ""),
    ("Tarjeta de regalo",       "Si prefieres dejarlo a su gusto","🎁", ""),
]


# ====================================================================
#  Capa de base de datos (funciona igual con SQLite y con PostgreSQL)
# ====================================================================
def connect():
    if IS_PG:
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_db():
    if "db" not in g:
        g.db = connect()
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def ph(sql):
    """Traduce los marcadores '?' a '%s' cuando usamos PostgreSQL."""
    return sql.replace("?", "%s") if IS_PG else sql


def run(sql, params=(), *, fetch=None, commit=False, db=None):
    """Ejecuta una consulta. fetch='one'|'all'|None. Devuelve filas tipo dict."""
    own = db is None
    db = db or get_db()
    cur = db.cursor()
    cur.execute(ph(sql), params)
    out, rowcount = None, cur.rowcount
    if fetch == "one":
        out = cur.fetchone()
    elif fetch == "all":
        out = cur.fetchall()
    if commit:
        db.commit()
    return out if fetch else rowcount


def init_db():
    db = connect()
    cur = db.cursor()
    id_col = "id SERIAL PRIMARY KEY" if IS_PG else "id INTEGER PRIMARY KEY AUTOINCREMENT"
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS gifts(
            {id_col},
            name TEXT NOT NULL,
            note TEXT DEFAULT '',
            emoji TEXT DEFAULT '🎁',
            image_url TEXT DEFAULT '',
            reserved_by TEXT,
            reserved_at TEXT,
            sort INTEGER DEFAULT 0
        )
    """)
    cur.execute("SELECT COUNT(*) AS c FROM gifts")
    if cur.fetchone()["c"] == 0:
        for i, (name, note, emoji, img) in enumerate(SEED_GIFTS):
            cur.execute(ph("INSERT INTO gifts(name,note,emoji,image_url,sort) VALUES(?,?,?,?,?)"),
                        (name, note, emoji, img, i))
    db.commit()
    db.close()


# ====================================================================
#  Utilidades
# ====================================================================
def clean(s, maxlen=120):
    """Sanea texto del usuario: recorta y escapa caracteres peligrosos."""
    if not s:
        return ""
    s = str(s).strip()[:maxlen]
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "&#x27;"))


def gift_to_dict(r):
    return {
        "id": r["id"], "name": r["name"], "note": r["note"],
        "emoji": r["emoji"], "image_url": r["image_url"],
        "reserved_by": r["reserved_by"], "reserved": bool(r["reserved_by"]),
    }


# ====================================================================
#  Rutas
# ====================================================================
@app.route("/")
def index():
    return render_template("index.html", event=EVENT)


@app.route("/api/gifts")
def list_gifts():
    rows = run("SELECT * FROM gifts ORDER BY (reserved_by IS NOT NULL), sort, id", fetch="all")
    gifts = [gift_to_dict(r) for r in rows]
    taken = sum(1 for g_ in gifts if g_["reserved"])
    return jsonify({"gifts": gifts, "total": len(gifts), "taken": taken})


@app.route("/api/reserve", methods=["POST"])
def reserve():
    data = request.get_json(silent=True) or {}
    gid = data.get("id")
    name = clean(data.get("name"), 40)
    if not gid or not name:
        return jsonify({"ok": False, "error": "Falta tu nombre."}), 400
    now = datetime.datetime.now().isoformat(timespec="seconds")
    db = get_db()
    # UPDATE condicional: solo reserva si sigue libre (evita choques entre 2 personas)
    changed = run("UPDATE gifts SET reserved_by=?, reserved_at=? WHERE id=? AND reserved_by IS NULL",
                  (name, now, gid), commit=True, db=db)
    if changed == 0:
        row = run("SELECT * FROM gifts WHERE id=?", (gid,), fetch="one", db=db)
        if row is None:
            return jsonify({"ok": False, "error": "Ese regalo ya no existe."}), 404
        return jsonify({"ok": False, "error": f"Justo lo apartó {row['reserved_by']}. Elige otro 💙",
                        "gift": gift_to_dict(row)}), 409
    row = run("SELECT * FROM gifts WHERE id=?", (gid,), fetch="one", db=db)
    return jsonify({"ok": True, "gift": gift_to_dict(row)})


@app.route("/api/release", methods=["POST"])
def release():
    data = request.get_json(silent=True) or {}
    gid = data.get("id")
    name = clean(data.get("name"), 40)
    host = data.get("host_key", "")
    db = get_db()
    row = run("SELECT * FROM gifts WHERE id=?", (gid,), fetch="one", db=db)
    if row is None:
        return jsonify({"ok": False, "error": "Ese regalo no existe."}), 404
    is_host = host and host == HOST_KEY
    if not is_host and (row["reserved_by"] or "").lower() != name.lower():
        return jsonify({"ok": False, "error": "Solo quien lo apartó puede liberarlo."}), 403
    run("UPDATE gifts SET reserved_by=NULL, reserved_at=NULL WHERE id=?", (gid,), commit=True, db=db)
    row = run("SELECT * FROM gifts WHERE id=?", (gid,), fetch="one", db=db)
    return jsonify({"ok": True, "gift": gift_to_dict(row)})


# ---------- Modo anfitrión: agregar / eliminar regalos ----------
@app.route("/api/gifts", methods=["POST"])
def add_gift():
    data = request.get_json(silent=True) or {}
    if data.get("host_key") != HOST_KEY:
        return jsonify({"ok": False, "error": "Clave de anfitrión incorrecta."}), 403
    name = clean(data.get("name"), 80)
    if not name:
        return jsonify({"ok": False, "error": "El regalo necesita un nombre."}), 400
    note = clean(data.get("note"), 120)
    emoji = clean(data.get("emoji") or "🎁", 8)
    image_url = clean(data.get("image_url"), 300)
    db = get_db()
    mx = run("SELECT COALESCE(MAX(sort),0)+1 AS s FROM gifts", fetch="one", db=db)["s"]
    row = run("INSERT INTO gifts(name,note,emoji,image_url,sort) VALUES(?,?,?,?,?) RETURNING *",
              (name, note, emoji, image_url, mx), fetch="one", commit=True, db=db)
    return jsonify({"ok": True, "gift": gift_to_dict(row)})


@app.route("/api/gifts/<int:gid>", methods=["DELETE"])
def delete_gift(gid):
    data = request.get_json(silent=True) or {}
    if data.get("host_key") != HOST_KEY:
        return jsonify({"ok": False, "error": "Clave de anfitrión incorrecta."}), 403
    run("DELETE FROM gifts WHERE id=?", (gid,), commit=True)
    return jsonify({"ok": True})


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
