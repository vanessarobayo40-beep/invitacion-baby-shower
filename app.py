"""
Invitación Baby Shower · Tarjeta + Confirmar asistencia + Lista de regalos
--------------------------------------------------------------------------
Todo en una sola página:
  • Tarjeta de invitación (con foto, fecha y lugar)
  • Confirmar asistencia (RSVP)
  • Lista de regalos con reserva y CANTIDADES (varios pueden apartar el mismo
    regalo si tiene cantidad 2, 3, etc.)

Almacenamiento:
  • Local (tu PC): SQLite -> regalos.db
  • Nube (producción): PostgreSQL si existe DATABASE_URL
"""
import os
import datetime
from flask import Flask, render_template, request, jsonify, g

app = Flask(__name__)

# ---- ¿Postgres (nube) o SQLite (local)? ----
DATABASE_URL = os.getenv("DATABASE_URL")
IS_PG = bool(DATABASE_URL)
if IS_PG:
    import time
    import psycopg
    from psycopg.rows import dict_row
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]
else:
    import sqlite3
    DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "regalos.db"))

# Clave del modo anfitrión (agregar/eliminar regalos). Cámbiala en producción.
HOST_KEY = os.getenv("HOST_KEY", "mama2026")

# Datos de la invitación (configurables por variables de entorno)
EVENT = {
    "title":    os.getenv("EVENT_TITLE", "Baby Shower"),
    "baby":     os.getenv("EVENT_BABY", "Bienvenido, bebé"),
    "subtitle": os.getenv("EVENT_SUBTITLE", "Con todo nuestro amor, te esperamos 💙"),
    "date":     os.getenv("EVENT_DATE", "Sábado 15 de Agosto · 4:00 PM"),
    "place":    os.getenv("EVENT_PLACE", "Salón Las Nubes · Ciudad"),
    "hosts":    os.getenv("EVENT_HOSTS", "Los futuros papás"),
    "photo":    os.getenv("EVENT_PHOTO", "/static/img/portada.jpg"),
}

# Sube este número cuando cambies la lista de regalos para forzar la recarga en la nube.
SEED_VERSION = "3"

# Lista real de regalos: (nombre, nota, emoji, cantidad)
SEED_GIFTS = [
    ("Tina plegable + Pañales etapa 2",          "", "🛁", 1),
    ("Toallas + Pañales etapa 3",                "", "🧻", 2),
    ("Kit de aseo + pañales etapa 0",            "", "🧴", 2),
    ("Set de body + semanario 0 - 3 meses",      "", "👶", 2),
    ("Set de body + semanario 3 - 6 meses",      "", "👶", 3),
    ("Set de body + semanario 6 - 9 meses",      "", "👶", 3),
    ("Cobijas + pañal etapa 5",                  "", "🧸", 1),
    ("Gorro y ruana",                            "", "🧢", 2),
    ("Almohada de lactancia + Pañales etapa 4",  "", "🤱", 1),
    ("Extractor de leche eléctrico",             "", "🍼", 1),
    ("Pañalera + cambiador",                     "", "🎒", 1),
    ("Muda de ropa 0 - 3 meses",                 "", "👕", 3),
    ("Muda de ropa 3 - 6 meses",                 "", "👕", 3),
    ("Muda de ropa 6 - 9 meses",                 "", "👕", 3),
    ("Sleeping (saco para dormir)",              "", "🐻", 2),
    ("Set de pijamas 0 - 3 meses + pañales etapa 2", "", "🌙", 3),
    ("Set de pijama 3 - 6 meses + pañales etapa 0",  "", "🌙", 3),
    ("Set de pijama 6 - 9 meses + pañales etapa 1",  "", "🌙", 3),
    ("Nido para bebé",                           "", "🛏️", 1),
    ("Coche",                                    "", "🚼", 1),
    ("Gimnasio para bebé",                       "", "🪀", 1),
    ("Tetero Avent 11 oz + babero en silicona",  "", "🍼", 1),
]


# ====================================================================
#  Base de datos (funciona con SQLite y con PostgreSQL)
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
    return sql.replace("?", "%s") if IS_PG else sql


def run(sql, params=(), *, fetch=None, commit=False, db=None):
    db = db or get_db()
    cur = db.cursor()
    cur.execute(ph(sql), params)
    out = None
    if fetch == "one":
        out = cur.fetchone()
    elif fetch == "all":
        out = cur.fetchall()
    rc = cur.rowcount
    if commit:
        db.commit()
    return out if fetch else rc


def init_db():
    if IS_PG:
        last = None
        for intento in range(15):
            try:
                _create_schema()
                return
            except Exception as e:  # noqa: BLE001
                last = e
                print(f"[init_db] base de datos aún no lista (intento {intento+1}/15): {e}", flush=True)
                time.sleep(3)
        raise last
    _create_schema()


def _create_schema():
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
            qty INTEGER DEFAULT 1,
            sort INTEGER DEFAULT 0
        )
    """)
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS reservations(
            {id_col},
            gift_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT
        )
    """)
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS rsvps(
            {id_col},
            name TEXT NOT NULL,
            guests INTEGER DEFAULT 0,
            message TEXT DEFAULT '',
            created_at TEXT
        )
    """)
    cur.execute("CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT)")

    # --- Migración: asegurar la columna qty en bases con esquema viejo ---
    if IS_PG:
        cur.execute("ALTER TABLE gifts ADD COLUMN IF NOT EXISTS qty INTEGER DEFAULT 1")
    else:
        cols = [row["name"] for row in cur.execute("PRAGMA table_info(gifts)").fetchall()]
        if "qty" not in cols:
            cur.execute("ALTER TABLE gifts ADD COLUMN qty INTEGER DEFAULT 1")

    # --- Sembrar / recargar la lista cuando cambia SEED_VERSION ---
    cur.execute(ph("SELECT value FROM settings WHERE key=?"), ("seed_version",))
    rowv = cur.fetchone()
    current = rowv["value"] if rowv else None
    cur.execute("SELECT COUNT(*) AS c FROM gifts")
    empty = cur.fetchone()["c"] == 0
    if empty or current != SEED_VERSION:
        cur.execute("DELETE FROM reservations")
        cur.execute("DELETE FROM gifts")
        for i, (name, note, emoji, qty) in enumerate(SEED_GIFTS):
            cur.execute(ph("INSERT INTO gifts(name,note,emoji,qty,sort) VALUES(?,?,?,?,?)"),
                        (name, note, emoji, qty, i))
        cur.execute(ph("INSERT INTO settings(key,value) VALUES(?,?) "
                       "ON CONFLICT(key) DO UPDATE SET value=?"),
                    ("seed_version", SEED_VERSION, SEED_VERSION))
    db.commit()
    db.close()


# ====================================================================
#  Utilidades
# ====================================================================
def clean(s, maxlen=120):
    if not s:
        return ""
    s = str(s).strip()[:maxlen]
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "&#x27;"))


def gift_state(r, reservers):
    """reservers: lista de nombres que apartaron este regalo."""
    qty = int(r["qty"] or 1)
    count = len(reservers)
    return {
        "id": r["id"], "name": r["name"], "note": r["note"],
        "emoji": r["emoji"], "image_url": r["image_url"],
        "qty": qty, "count": count, "left": max(0, qty - count),
        "reserved": count >= qty, "reservers": reservers,
    }


def all_gifts():
    gifts = run("SELECT * FROM gifts ORDER BY sort, id", fetch="all")
    res = run("SELECT gift_id, name FROM reservations ORDER BY id", fetch="all")
    by_gift = {}
    for r in res:
        by_gift.setdefault(r["gift_id"], []).append(r["name"])
    out = [gift_state(gobj, by_gift.get(gobj["id"], [])) for gobj in gifts]
    # disponibles primero, agotados al final
    out.sort(key=lambda g_: (g_["reserved"], g_["id"]))
    return out


# ====================================================================
#  Rutas
# ====================================================================
@app.route("/")
def index():
    return render_template("index.html", event=EVENT)


@app.route("/api/gifts")
def list_gifts():
    gifts = all_gifts()
    total = sum(g_["qty"] for g_ in gifts)
    taken = sum(g_["count"] for g_ in gifts)
    return jsonify({"gifts": gifts, "total": total, "taken": taken})


@app.route("/api/reserve", methods=["POST"])
def reserve():
    data = request.get_json(silent=True) or {}
    gid = data.get("id")
    name = clean(data.get("name"), 40)
    if not gid or not name:
        return jsonify({"ok": False, "error": "Falta tu nombre."}), 400
    db = get_db()
    gobj = run("SELECT * FROM gifts WHERE id=?", (gid,), fetch="one", db=db)
    if gobj is None:
        return jsonify({"ok": False, "error": "Ese regalo ya no existe."}), 404
    reservers = [x["name"] for x in run("SELECT name FROM reservations WHERE gift_id=?", (gid,), fetch="all", db=db)]
    if any(n.lower() == name.lower() for n in reservers):
        return jsonify({"ok": True, "gift": gift_state(gobj, reservers)})  # ya lo tenía: idempotente
    if len(reservers) >= int(gobj["qty"] or 1):
        return jsonify({"ok": False, "error": "Ese regalo ya está completo. Elige otro 💙",
                        "gift": gift_state(gobj, reservers)}), 409
    now = datetime.datetime.now().isoformat(timespec="seconds")
    run("INSERT INTO reservations(gift_id,name,created_at) VALUES(?,?,?)", (gid, name, now), commit=True, db=db)
    reservers.append(name)
    return jsonify({"ok": True, "gift": gift_state(gobj, reservers)})


@app.route("/api/release", methods=["POST"])
def release():
    data = request.get_json(silent=True) or {}
    gid = data.get("id")
    name = clean(data.get("name"), 40)
    host = data.get("host_key", "")
    db = get_db()
    gobj = run("SELECT * FROM gifts WHERE id=?", (gid,), fetch="one", db=db)
    if gobj is None:
        return jsonify({"ok": False, "error": "Ese regalo no existe."}), 404
    is_host = host and host == HOST_KEY
    if is_host:
        run("DELETE FROM reservations WHERE gift_id=? AND LOWER(name)=LOWER(?)", (gid, name), commit=True, db=db)
    else:
        n = run("DELETE FROM reservations WHERE gift_id=? AND LOWER(name)=LOWER(?)", (gid, name), commit=True, db=db)
        if n == 0:
            return jsonify({"ok": False, "error": "Solo quien lo apartó puede liberarlo."}), 403
    reservers = [x["name"] for x in run("SELECT name FROM reservations WHERE gift_id=?", (gid,), fetch="all", db=db)]
    return jsonify({"ok": True, "gift": gift_state(gobj, reservers)})


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
    try:
        qty = max(1, min(20, int(data.get("qty") or 1)))
    except (TypeError, ValueError):
        qty = 1
    db = get_db()
    mx = run("SELECT COALESCE(MAX(sort),0)+1 AS s FROM gifts", fetch="one", db=db)["s"]
    gobj = run("INSERT INTO gifts(name,note,emoji,qty,sort) VALUES(?,?,?,?,?) RETURNING *",
               (name, note, emoji, qty, mx), fetch="one", commit=True, db=db)
    return jsonify({"ok": True, "gift": gift_state(gobj, [])})


@app.route("/api/gifts/<int:gid>", methods=["DELETE"])
def delete_gift(gid):
    data = request.get_json(silent=True) or {}
    if data.get("host_key") != HOST_KEY:
        return jsonify({"ok": False, "error": "Clave de anfitrión incorrecta."}), 403
    db = get_db()
    run("DELETE FROM reservations WHERE gift_id=?", (gid,), commit=True, db=db)
    run("DELETE FROM gifts WHERE id=?", (gid,), commit=True, db=db)
    return jsonify({"ok": True})


# ====================================================================
#  Confirmar asistencia (RSVP)
# ====================================================================
def rsvp_summary(include_details=False):
    rows = run("SELECT * FROM rsvps ORDER BY id DESC", fetch="all")
    people = len(rows)
    total = people + sum(int(r["guests"] or 0) for r in rows)
    data = {"people": people, "total": total, "names": [r["name"] for r in rows]}
    if include_details:
        data["items"] = [{"name": r["name"], "guests": int(r["guests"] or 0),
                          "message": r["message"] or ""} for r in rows]
    return data


@app.route("/api/rsvp", methods=["GET"])
def rsvp_list():
    is_host = request.args.get("host_key", "") == HOST_KEY
    return jsonify(rsvp_summary(include_details=is_host))


@app.route("/api/rsvp", methods=["POST"])
def rsvp_add():
    data = request.get_json(silent=True) or {}
    name = clean(data.get("name"), 40)
    if not name:
        return jsonify({"ok": False, "error": "Escribe tu nombre."}), 400
    try:
        guests = max(0, min(20, int(data.get("guests") or 0)))
    except (TypeError, ValueError):
        guests = 0
    message = clean(data.get("message"), 200)
    now = datetime.datetime.now().isoformat(timespec="seconds")
    db = get_db()
    existing = run("SELECT id FROM rsvps WHERE LOWER(name)=LOWER(?)", (name,), fetch="one", db=db)
    if existing:
        run("UPDATE rsvps SET guests=?, message=?, created_at=? WHERE id=?",
            (guests, message, now, existing["id"]), commit=True, db=db)
    else:
        run("INSERT INTO rsvps(name,guests,message,created_at) VALUES(?,?,?,?)",
            (name, guests, message, now), commit=True, db=db)
    return jsonify({"ok": True, **rsvp_summary()})


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
