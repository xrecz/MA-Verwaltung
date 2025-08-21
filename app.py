# ---------------------------------------------------------
# BENÖTIGTE MODULE
# ---------------------------------------------------------

# Flask-Basismodule importieren
from flask import Flask, render_template, request, url_for, session, redirect, send_from_directory
# -> Flask = Hauptklasse für die Web-App
# -> render_template = lädt HTML-Dateien aus /templates
# -> request = verarbeitet eingehende HTTP-Requests (Formulardaten, GET/POST)
# -> url_for = baut dynamisch URLs auf Basis von Routen
# -> session = speichert Informationen über eingeloggte Nutzer zwischen Requests (Cookies)
# -> redirect = leitet den Nutzer auf eine andere Route weiter

# Flask-MySQLdb für die Verbindung zu MySQL importieren
from flask_mysqldb import MySQL
# -> erleichtert die Arbeit mit einer MySQL-Datenbank aus Flask heraus

# MySQLdb-Cursors erlauben uns, die Datenbank-Ergebnisse als Dict (Spaltennamen -> Wert) zu bekommen
import MySQLdb.cursors
# -> DictCursor = liefert Ergebnisse als { "spalte": wert } statt als einfache Tupel

import json  # für Umwandlung von Python-Listen in JSON-Strings (z. B. Checkboxen)
import re    # reguläre Ausdrücke (noch nicht genutzt, könnte z. B. für Validierung dienen)
import os

# Optional: Anbindung an Active Directory
try:
    from ldap3 import Server, Connection, ALL, MODIFY_REPLACE
except Exception:  # Modul nicht installiert oder andere Importprobleme
    Server = Connection = None

from werkzeug.utils import secure_filename


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

# Upload-Konfiguration
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg'}
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Active-Directory-Konfiguration über Umgebungsvariablen
AD_SERVER = os.getenv("AD_SERVER")
AD_USER = os.getenv("AD_USER")
AD_PASSWORD = os.getenv("AD_PASSWORD")
AD_BASE_DN = os.getenv("AD_BASE_DN", "OU=Users,DC=example,DC=com")


def allowed_file(filename):
    """Prüft, ob die Datei eine der erlaubten Endungen besitzt."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def init_app():
    """Initialisiert Datenbankstrukturen (z. B. Tabelle für Dokumente)."""
    cursor = mysql.connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mitarbeiter_dokumente (
            id INT AUTO_INCREMENT PRIMARY KEY,
            mitarbeiter_id INT NOT NULL,
            filename VARCHAR(255) NOT NULL,
            original_name VARCHAR(255) NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mitarbeiter_id) REFERENCES mitarbeiter(id)
        )
    """)
    mysql.connection.commit()



def create_ad_user(vorname, nachname, abteilung, email):
    """Legt einen Benutzer im Active Directory an (falls konfiguriert)."""
    if Server is None or not all([AD_SERVER, AD_USER, AD_PASSWORD]):
        # Keine AD-Verbindung konfiguriert
        return

    username = (vorname[0] + nachname).lower()
    password = f"40{vorname[0].upper()}{nachname[0].lower()}28197!"

    try:
        server = Server(AD_SERVER, get_info=ALL)
        conn = Connection(server, user=AD_USER, password=AD_PASSWORD, auto_bind=True)
        dn = f"CN={vorname} {nachname},{AD_BASE_DN}"
        domain = email.split("@")[-1]
        attributes = {
            "givenName": vorname,
            "sn": nachname,
            "displayName": f"{vorname} {nachname}",
            "mail": email,
            "department": abteilung,
            "sAMAccountName": username,
            "userPrincipalName": f"{username}@{domain}",
        }
        conn.add(dn, ["top", "person", "organizationalPerson", "user"], attributes)
        conn.extend.microsoft.modify_password(dn, password)
        conn.modify(dn, {"userAccountControl": [(MODIFY_REPLACE, 512)]})
        conn.unbind()
    except Exception as exc:
        print(f"AD user creation failed: {exc}")


# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------

@app.route("/")
@app.route("/login", methods=["GET", "POST"])
def login():
    msg = ""  # Variable für Rückmeldungen (z. B. Fehlermeldungen, Infos)

    # Wenn bereits eingeloggt → direkt zur Startseite
    if session.get("loggedin"):
        return redirect(url_for("landing"))

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
            return redirect(url_for("landing"))
        else:
            msg = "Falscher Benutzername oder Passwort!"

    # GET-Anfrage oder Login fehlgeschlagen → Login-Seite anzeigen
    return render_template("login.html", msg=msg)


# ---------------------------------------------------------
# LANDINGPAGE / STARTSEITE
# ---------------------------------------------------------

@app.route("/landing")
def landing():
    if session.get("loggedin"):
        return render_template("landing.html")
    return redirect(url_for("login"))


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

            # Automatisch AD-Benutzer anlegen, wenn Abteilung nicht ausgeschlossen ist
            ausgeschlossene_abteilungen = {"Lager", "Werkstatt", "Fahrer", "LKW Fahrer"}
            if abteilung not in ausgeschlossene_abteilungen:
                create_ad_user(name, nachname, abteilung, email)

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
# MITARBEITER-DOKUMENTE UPLOAD
# ---------------------------------------------------------

@app.route("/mitarbeiter_upload/<int:id>", methods=["GET", "POST"])
def mitarbeiter_upload(id):
    """Zeigt Dokumente eines Mitarbeiters und verarbeitet neue Uploads."""
    if not session.get("loggedin"):
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    msg = ""

    if request.method == "POST":
        file = request.files.get("dokument")
        if file and allowed_file(file.filename):
            original_name = file.filename
            filename = secure_filename(original_name)
            user_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(id))
            os.makedirs(user_folder, exist_ok=True)
            file.save(os.path.join(user_folder, filename))

            cursor.execute(
                """
                INSERT INTO mitarbeiter_dokumente (mitarbeiter_id, filename, original_name, uploaded_at)
                VALUES (%s, %s, %s, NOW())
                """,
                (id, filename, original_name),
            )
            mysql.connection.commit()
            msg = "Datei gespeichert."
        else:
            msg = "Ungültige Datei."

    cursor.execute(
        "SELECT id, original_name FROM mitarbeiter_dokumente WHERE mitarbeiter_id = %s",
        (id,),
    )
    dokumente = cursor.fetchall()

    return render_template(
        "mitarbeiter_upload.html", dokumente=dokumente, mitarbeiter_id=id, msg=msg
    )


@app.route("/download/<int:doc_id>")
def download(doc_id):
    """Stellt ein gespeichertes Dokument zum Download bereit."""
    if not session.get("loggedin"):
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        "SELECT mitarbeiter_id, filename, original_name FROM mitarbeiter_dokumente WHERE id = %s",
        (doc_id,),
    )
    doc = cursor.fetchone()
    if not doc:
        return "Dokument nicht gefunden", 404

    folder = os.path.join(app.config['UPLOAD_FOLDER'], str(doc["mitarbeiter_id"]))
    return send_from_directory(
        folder, doc["filename"], as_attachment=True, download_name=doc["original_name"]
    )


@app.route("/delete_document/<int:doc_id>", methods=["POST"])
def delete_document(doc_id):
    """Löscht die Datei und den passenden Datenbankeintrag."""
    if not session.get("loggedin"):
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        "SELECT mitarbeiter_id, filename FROM mitarbeiter_dokumente WHERE id = %s",
        (doc_id,),
    )
    doc = cursor.fetchone()
    if doc:
        file_path = os.path.join(
            app.config['UPLOAD_FOLDER'], str(doc["mitarbeiter_id"]), doc["filename"]
        )
        if os.path.exists(file_path):
            os.remove(file_path)
        cursor.execute(
            "DELETE FROM mitarbeiter_dokumente WHERE id = %s",
            (doc_id,),
        )
        mysql.connection.commit()
        return redirect(url_for("mitarbeiter_upload", id=doc["mitarbeiter_id"]))

    return redirect(url_for("landing"))


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
