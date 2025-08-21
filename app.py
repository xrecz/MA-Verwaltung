# Flask-Basismodule importieren
from flask import Flask, render_template, request, url_for, session

# Flask-MySQLdb für die Verbindung zu MySQL importieren
from flask_mysqldb import MySQL

# MySQLdb-Cursors erlauben uns, die Datenbank-Ergebnisse als Dict (Spaltennamen -> Wert) zu bekommen
import MySQLdb.cursors

# Reguläre Ausdrücke (regex), aktuell nicht genutzt, könnten aber z. B. für Validierung dienen
import re

# Flask-App erstellen
app = Flask(__name__)

# Geheimschlüssel für Sessions (muss geheim bleiben in echten Projekten!)
app.secret_key = "HalloDasistunserKey!"

# MySQL-Konfiguration: Verbindungsdaten zur Datenbank
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'MyTestServer2025!'  # Dein MySQL-Passwort
app.config['MYSQL_DB'] = 'ttma'  # Name der Datenbank

# MySQL-Objekt erstellen, das mit Flask verbunden ist
mysql = MySQL(app)


# ---- LOGIN-ROUTE ----
@app.route("/")  # Aufruf über Haupt-URL
@app.route("/login", methods=["GET", "POST"])  # Oder explizit über /login
def login():
    msg = ""  # Variable für Fehlermeldungen oder Infos

    # Prüfen, ob ein Formular per POST geschickt wurde UND ob Username & Passwort-Felder ausgefüllt sind
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:

        # Werte aus dem Formular abholen
        username = request.form["username"]
        password = request.form["password"]

        # Cursor erstellen, DictCursor liefert Ergebnis als Dictionary (z. B. {"id":1, "benutzername":"max"})
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # SQL-Abfrage: nach einem passenden Benutzer suchen
        # ACHTUNG: Hier wird noch Klartext-Passwort verglichen → unsicher in echten Projekten!
        cursor.execute(
            "SELECT * FROM benutzer WHERE benutzername = %s AND passwort = %s",
            (username, password)
        )

        # Ergebnis holen: entweder ein Account oder None
        account = cursor.fetchone()

        # Wenn Account existiert → Login erfolgreich
        if account:
            # Werte in Session speichern (bleiben so lange, bis Browser geschlossen oder logout)
            session["loggedin"] = True
            session["id"] = account["id"]
            session["username"] = account["benutzername"]

            # Weiterleiten auf index.html mit Meldung
            return render_template("landing.html", msg="Logged in!")
        else:
            # Kein Benutzer gefunden → Fehlermeldung
            msg = "Falscher Benutzername oder Passwort!"

    # GET-Anfrage oder Login fehlgeschlagen → Login-Seite anzeigen
    return render_template("login.html", msg=msg)


# ---- LOGOUT-ROUTE ----
@app.route("/logout", methods=["POST"])
def logout():
    # Session komplett leeren → User ist ausgeloggt
    session.clear()

    # Zurück auf die Login-Seite mit Nachricht
    return render_template("login.html", msg="Du wurdest ausgeloggt!")


@app.route("/Kalender")
def kalender():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        "SELECT name, geburtstag FROM mitarbeiter ORDER BY MONTH(geburtstag), DAY(geburtstag)"
    )
    birthdays = cursor.fetchall()
    return render_template("kalender.html",  birthdays = birthdays)

@app.route("/mitarbeiter_neu", methods=["GET", "POST"])
def mitarbeiter_neu():
    msg = ""
    if request.method == "POST":
        # Daten aus Formular holen
        name = request.form["name"]
        nachname = request.form["nachname"]
        abteilung = request.form["abteilung"]
        telefonnummer = request.form["telefonnummer"]
        gearbeitet_von = request.form["gearbeitet_von"]
        geburtstag = request.form["geburtstag"]

        # E-Mail automatisch generieren
        email = name.lower() + "." + nachname.lower() + "@terratrans.de"

        # DB-Cursor öffnen
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Prüfen, ob Mitarbeiter schon existiert
        cursor.execute(
            "SELECT * FROM mitarbeiter WHERE name = %s AND nachname = %s",
            (name, nachname)
        )
        neuer_mitarbeiter = cursor.fetchone()

        if neuer_mitarbeiter:
            msg = "Mitarbeiter wurde bereits angelegt!"
        else:
            # Mitarbeiter einfügen
            cursor.execute(
                "INSERT INTO mitarbeiter (name, nachname, abteilung, email, telefonnummer, gearbeitet_von, geburtstag) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (name, nachname, abteilung, email, telefonnummer, gearbeitet_von, geburtstag)
            )
            mysql.connection.commit()
            msg = "Mitarbeiter erfolgreich angelegt!"

    return render_template("mitarbeiter_neu.html", msg=msg)

@app.route("/mitarbeiter", methods=["GET", "POST"])
def mitarbeiter():
    msg = ""
    daten = None   # Variable für Ergebnissatz
    if request.method == "POST":
        name = request.form["name"]         # () → [] ändern!
        nachname = request.form["nachname"] # () → [] ändern!

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        # Doppeltes WHERE entfernt
        cursor.execute("SELECT * FROM mitarbeiter WHERE name = %s AND nachname = %s", (name, nachname))
        daten = cursor.fetchone()  # fetchone, wenn nur 1 Mitarbeiter erwartet

        if not daten:
            msg = "Mitarbeiter existiert nicht. Bitte überprüfe deine Eingabe!"

    return render_template("mitarbeiter.html", msg=msg, daten=daten)

@app.route("/mitarbeiter_edit/<int:id>", methods=["GET", "POST"])
def mitarbeiter_edit(id):
    msg = ""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == "POST":
        # Neue Daten aus Formular holen
        name = request.form["name"]
        nachname = request.form["nachname"]
        abteilung = request.form["abteilung"]
        telefonnummer = request.form["telefonnummer"]
        geburtstag = request.form["geburtstag"]

        # Update in der DB
        cursor.execute("""
            UPDATE mitarbeiter
            SET name = %s, nachname = %s, abteilung = %s, telefonnummer = %s, geburtstag = %s
            WHERE id = %s
        """, (name, nachname, abteilung, telefonnummer, geburtstag, id))
        mysql.connection.commit()
        msg = "Mitarbeiterdaten erfolgreich geändert!"

    # Aktuelle Daten neu holen, damit Formular befüllt wird
    cursor.execute("SELECT * FROM mitarbeiter WHERE id = %s", (id,))
    daten = cursor.fetchone()

    return render_template("mitarbeiter_edit.html", daten=daten, msg=msg)

# ---- START DER APP ----
if __name__ == '__main__':
    # Debug=True: Server startet im Entwicklungsmodus (zeigt Fehler im Browser, Auto-Reload bei Codeänderung)
    app.run(debug=True)
