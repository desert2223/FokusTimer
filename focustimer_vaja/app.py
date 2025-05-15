from flask import Flask, render_template, request, redirect, session, g
import sqlite3

app = Flask(__name__)
app.secret_key = "skrivna_ključ"  # safe sasions
DATABASE = 'baza.db'


# Pomožna funkcija za povezavo z bazo
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


# Inicializacija baze
def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS seje (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uporabnik_id INTEGER NOT NULL,
                trajanje INTEGER NOT NULL,
                datum DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS uporabniki (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                geslo TEXT NOT NULL,
                nickname TEXT NOT NULL UNIQUE
            );
        ''')

        db.commit()

# baza podatkov
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Prijava
@app.route("/")
def prijava():
    return render_template("prijava.html")


@app.route("/prijava", methods=["POST"])
def prijava_uporabnika():
    email = request.form["email"]
    geslo = request.form["geslo"]
    db = get_db()
    uporabnik = db.execute(
        "SELECT * FROM uporabniki WHERE email = ? AND geslo = ?",
        (email, geslo)
    ).fetchone()

    if uporabnik:
        session["uporabnik_id"] = uporabnik[0]
        return redirect("/dashboard")  
    else:
        napaka = "Napačni podatki. Poskusi znova."
        return render_template("prijava.html", napaka=napaka)


# Registracija
@app.route("/registracija")
def registracija():
    return render_template("registracija.html")


@app.route("/registracija", methods=["POST"])
def registracija_uporabnika():
    nickname = request.form["nickname"]
    email = request.form["email"]
    geslo = request.form["geslo"]
    db = get_db()
    try:
        db.execute(
            "INSERT INTO uporabniki (email, geslo, nickname) VALUES (?, ?, ?)",
            (email, geslo, nickname)
        )
        db.commit()
        return redirect("/")
    except sqlite3.IntegrityError:
        napaka = "Email ali nickname je že v uporabi."
        return render_template("registracija.html", napaka=napaka)


# Odjava
@app.route("/odjava")
def odjava():
    session.pop("uporabnik_id", None)
    return redirect("/")

@app.route("/izbris", methods=["POST"])
def izbris():
    if "uporabnik_id" not in session:
        return redirect("/")
    db = get_db()
    uporabnik_id = session["uporabnik_id"]
    # Izbriši uporabnika in vse njegove seje
    db.execute("DELETE FROM seje WHERE uporabnik_id = ?", (uporabnik_id,))
    db.execute("DELETE FROM uporabniki WHERE id = ?", (uporabnik_id,))
    db.commit()
    session.pop("uporabnik_id", None)
    return redirect("/")

# Ploščica
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "uporabnik_id" not in session:
        return redirect("/")

    db = get_db()
    uporabnik_id = session["uporabnik_id"]

    seje = db.execute('''
        SELECT trajanje, datum FROM seje
        WHERE uporabnik_id = ?
        ORDER BY datum DESC
    ''', (uporabnik_id,)).fetchall()

    skupni_cas = sum([s[0] for s in seje])
    st_sej = len(seje)
    zadnja = seje[0][1] if seje else "Ni podatkov"

    rezultati = None
    sporocilo = None
    if request.method == "POST":
        iskani_nickname = request.form["nickname"]
        rezultati = db.execute(
            "SELECT * FROM uporabniki WHERE nickname LIKE ? AND id != ?",
            ('%' + iskani_nickname + '%', uporabnik_id)
        ).fetchall()
        if not rezultati:
            sporocilo = "Ni najdenih uporabnikov."

    return render_template(
        "dashboard.html",
        skupni_cas=skupni_cas,
        st_sej=st_sej,
        zadnja=zadnja,
        rezultati=rezultati,
        sporocilo=sporocilo
    )

# Iskanje Prijateljev
@app.route("/iskanje_prijateljev", methods=["POST"])
def iskanje_prijateljev():
    nickname = request.form["nickname"]
    db = get_db()
    cur = db.execute("SELECT * FROM uporabniki WHERE nickname LIKE ?", ('%' + nickname + '%',))
    rezultati = cur.fetchall()

    if rezultati:
        return render_template("dashboard.html", rezultati=rezultati)
    else:
        sporocilo = "Uporabnik s tem vzdevkom ne obstaja."
        return render_template("dashboard.html", sporocilo="Ni zadetkov za ta vzdevek.")
    

#Fokus
@app.route('/seja')
def seja():
    return render_template('seja.html')

@app.route("/seja")
def fokus():
    if "uporabnik_id" not in session:
        return redirect("/")

    db = get_db()
    db.execute('''
        INSERT INTO seje (uporabnik_id, trajanje)
        VALUES (?, ?)
    ''', (session["uporabnik_id"], 25))  # simul pomodoro 25 min
    db.commit()
    return redirect("/dashboard")


#Konec seji
@app.route('/konec')
def konec():
    if "uporabnik_id" not in session:
        return redirect("/")
    db = get_db()
    uporabnik_id = session["uporabnik_id"]
    # nov zapis seansa (25 min)
    db.execute('''
        INSERT INTO seje (uporabnik_id, trajanje)
        VALUES (?, ?)
    ''', (uporabnik_id, 25))
    db.commit()
    return render_template('konec_seje.html')

# občasni konec seje —streak
@app.route('/preklicana_seja')
def preklicana_seja():
    if "uporabnik_id" not in session:
        return redirect("/")
    db = get_db()
    uporabnik_id = session["uporabnik_id"]
    # -streak
    db.execute("DELETE FROM seje WHERE uporabnik_id = ?", (uporabnik_id,))
    db.commit()
    return redirect("/dashboard")


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)

