# ---------------------------------------------------------
# BENÖTIGTE MODULE
# ---------------------------------------------------------

# Flask-Basismodule importieren
from flask import Flask, render_template, request, url_for, session
# -> Flask = Hauptklasse für die Web-App
# -> render_template = lädt HTML-Dateien aus /templates
# -> request = verarbeitet eingehende HTTP-Requests (Formulardaten, GET/POST)
# -> url_for = baut dynamisch URLs auf Basis von Routen
# -> session = speichert Informationen über eingeloggte Nutzer zwischen Requests (Cookies)

# Flask-MySQLdb für die Verbindung zu MySQL importieren
from flask_mysqldb import MySQL
# -> erleichtert die Arbeit mit einer MySQL-Datenbank aus Flask heraus

# MySQLdb-Cursors erlauben uns, die Datenbank-Ergebnisse als Dict (Spaltennamen -> Wert) zu bekommen
import MySQLdb.cursors
# -> DictCursor = liefert Ergebnisse als { "spalte": wert } statt als einfache Tupel

import json  # für Umwandlung von Python-Listen in JSON-Strings (z. B. Checkboxen)
import re    # reguläre Ausdrücke (noch nicht genutzt, könnte z. B. für Validierung dienen)


# ---------------------------------------------------------
# GRUNDKONFIGURATION
# ---------------------------------------------------------

# Flask-App erstellen
app = Flask(__name__)

# Geheimschlüssel für Sessions (muss geheim bleiben in echten Projekten!)
app.secret_key = "HalloDasistunserKey!"
# -> Dieser Key wird intern von Flask genutzt, um Session-Daten zu signieren
# -> niemals in GitHub hochladen → in echten Projekten über Umgebungsvariablen setzen

# MySQL-Konfiguration: Verbindungsdaten zur Datenbank
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'MyTestServer2025!'  # Dein MySQL-Passwort
app.config['MYSQL_DB'] = 'ttma'                     # Name der Datenbank

# MySQL-Objekt erstellen, das mit Flask verbunden ist
mysql = MySQL(app)


# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------

@app.route("/")
@app.route("/login", methods=["GET", "POST"])
def login():
    msg = ""  # Variable für Rückmeldungen (z. B. Fehlermeldungen, Infos)

    # Prüfen, ob ein Formular per POST geschickt wurde UND ob Username & Passwort-Felder ausgefüllt sind
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:

        # Werte aus dem Formular abholen
        username = request.form["username"]
        password = request.form["password"]

        # Cursor erstellen (DictCursor = Ergebnis als Dictionary)
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # SQL-Abfrage: Benutzer suchen (⚠️ unsicher, da Passwort im Klartext!)
        cursor.execute(
            "SELECT * FROM benutzer WHERE benutzername = %s AND passwort = %s",
            (username, password)
        )
        account = cursor.fetchone()  # Ergebnis holen

        # Wenn Account existiert → Login erfolgreich
        if account:
            session["loggedin"] = True
            session["id"] = account["id"]
            session["username"] = account["benutzername"]
            return render_template("landing.html", msg="Logged in!")
        else:
            msg = "Falscher Benutzername oder Passwort!"

    # GET-Anfrage oder Login fehlgeschlagen → Login-Seite anzeigen
    return render_template("login.html", msg=msg)


# ---------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------

@app.route("/logout", methods=["POST"])
def logout():
    # Session komplett leeren → User ist ausgeloggt
    session.clear()
    return render_template("login.html", msg="Du wurdest ausgeloggt!")


# ---------------------------------------------------------
# KALENDER (Geburtstage)
# ---------------------------------------------------------

@app.route("/Kalender")
def kalender():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT name, geburtstag FROM mitarbeiter ORDER BY MONTH(geburtstag), DAY(geburtstag)")
    birthdays = cursor.fetchall()
    return render_template("kalender.html", birthdays=birthdays)


# ---------------------------------------------------------
# NEUEN MITARBEITER ANLEGEN
# ---------------------------------------------------------

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
            cursor.execute(
                "INSERT INTO mitarbeiter (name, nachname, abteilung, email, telefonnummer, gearbeitet_von, geburtstag) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (name, nachname, abteilung, email, telefonnummer, gearbeitet_von, geburtstag)
            )
            mysql.connection.commit()
            msg = "Mitarbeiter erfolgreich angelegt!"

    return render_template("mitarbeiter_neu.html", msg=msg)


# ---------------------------------------------------------
# MITARBEITER-SUCHE
# ---------------------------------------------------------

@app.route("/mitarbeiter", methods=["GET", "POST"])
def mitarbeiter():
    msg = ""
    daten = None

    if request.method == "POST":
        name = request.form["name"]
        nachname = request.form["nachname"]

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM mitarbeiter WHERE name = %s OR nachname = %s", (name, nachname))
        daten = cursor.fetchone()

        if not daten:
            msg = "Mitarbeiter existiert nicht. Bitte überprüfe deine Eingabe!"

    return render_template("mitarbeiter.html", msg=msg, daten=daten)


# ---------------------------------------------------------
# MITARBEITER BEARBEITEN
# ---------------------------------------------------------

@app.route("/mitarbeiter_edit/<int:id>", methods=["GET", "POST"])
def mitarbeiter_edit(id):
    msg = ""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == "POST":
        # Neue Daten holen
        name = request.form["name"]
        nachname = request.form["nachname"]
        abteilung = request.form["abteilung"]
        telefonnummer = request.form["telefonnummer"]
        geburtstag = request.form["geburtstag"]

        # Update in DB
        cursor.execute("""
            UPDATE mitarbeiter
            SET name = %s, nachname = %s, abteilung = %s, telefonnummer = %s, geburtstag = %s
            WHERE id = %s
        """, (name, nachname, abteilung, telefonnummer, geburtstag, id))
        mysql.connection.commit()
        msg = "Mitarbeiterdaten erfolgreich geändert!"

    # Aktuelle Daten holen
    cursor.execute("SELECT * FROM mitarbeiter WHERE id = %s", (id,))
    daten = cursor.fetchone()

    return render_template("mitarbeiter_edit.html", daten=daten, msg=msg)


# ---------------------------------------------------------
# ONBOARDING
# ---------------------------------------------------------

@app.route("/onboarding/<int:id>", methods=["GET", "POST"])
def onboarding(id):
    msg = ""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Mitarbeiter holen
    cursor.execute("SELECT * FROM mitarbeiter WHERE id = %s", (id,))
    mitarbeiter = cursor.fetchone()
    if not mitarbeiter:
        return render_template("mitarbeiter.html", msg="Mitarbeiter nicht gefunden!", daten=None)

    # Onboarding-Datensatz (falls schon vorhanden)
    cursor.execute("SELECT * FROM onboarding WHERE mitarbeiter_id = %s", (id,))
    onboard_start = cursor.fetchone()

    if request.method == "POST":
        abteilung = mitarbeiter["abteilung"]

        # Sonderfall: Lager/Werkstatt/Fahrer
        if abteilung in ("Lager", "Werkstatt", "Fahrer"):
            kleidung_text = request.form.get("kleidung_text") or None
            kleidung_groesse = request.form.get("kleidung_groesse")
            dokumente = request.form.getlist("dokumente")
            dokumente_json = json.dumps(dokumente) if dokumente else None

            cursor.execute("""
                INSERT INTO onboarding (mitarbeiter_id, kleidung_text, kleidung_groesse, dokumente, abgeschlossen)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    kleidung_text = VALUES(kleidung_text),
                    kleidung_groesse = VALUES(kleidung_groesse),
                    dokumente = VALUES(dokumente),
                    abgeschlossen = VALUES(abgeschlossen)
            """, (id, kleidung_text, kleidung_groesse, dokumente_json,
                  1 if request.form.get("abgeschlossen") == "1" else 0))

        # Alle anderen (Büro/IT etc.)
        else:
            arbeitsplatz_aufgebaut = 1 if request.form.get("arbeitsplatz_aufgebaut") == "1" else 0
            arbeitsplatz_art = request.form.get("arbeitsplatz_art") or None
            telefonnummer = request.form.get("telefonnummer") or None
            homeoffice = 1 if request.form.get("homeoffice") == "1" else 0
            programme = request.form.getlist("programme")
            programme_json = json.dumps(programme) if programme else None

            cursor.execute("""
                INSERT INTO onboarding (mitarbeiter_id, arbeitsplatz_aufgebaut, arbeitsplatz_art, telefonnummer, programme, homeoffice, abgeschlossen)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    arbeitsplatz_aufgebaut = VALUES(arbeitsplatz_aufgebaut),
                    arbeitsplatz_art = VALUES(arbeitsplatz_art),
                    telefonnummer = VALUES(telefonnummer),
                    programme = VALUES(programme),
                    homeoffice = VALUES(homeoffice),
                    abgeschlossen = VALUES(abgeschlossen)
            """, (id, arbeitsplatz_aufgebaut, arbeitsplatz_art, telefonnummer,
                  programme_json, homeoffice,
                  1 if request.form.get("abgeschlossen") == "1" else 0))

        # Änderungen speichern
        mysql.connection.commit()
        msg = "Onboarding gespeichert."

        # Daten nach Speichern erneut laden
        cursor.execute("SELECT * FROM onboarding WHERE mitarbeiter_id = %s", (id,))
        onboard_start = cursor.fetchone()

    return render_template("onboarding.html", mitarbeiter=mitarbeiter, onb=onboard_start, msg=msg)


# ---------------------------------------------------------
# START DER APP
# ---------------------------------------------------------

if __name__ == '__main__':
    # Debug=True: Server startet im Entwicklungsmodus
    # Vorteile:
    #  - Änderungen am Code laden automatisch neu
    #  - Fehler werden im Browser angezeigt
    # Nachteil: niemals in Produktion benutzen (zu unsicher!)
    app.run(debug=True)
