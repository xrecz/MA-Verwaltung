# MA-Verwaltung

Dieses Projekt ist eine einfache Verwaltungsoberfläche für Mitarbeiter auf Basis von [Flask](https://flask.palletsprojects.com/).

## Dokumenten-Upload

Die Anwendung erlaubt das Hochladen und Verwalten von Dateien für jeden Mitarbeiter. Die wichtigsten Bausteine:

1. **Konfiguration** – In `app.py` werden `UPLOAD_FOLDER` und erlaubte Dateiendungen definiert. Beim Start wird der Ordner automatisch angelegt.
2. **Datenbank** – Die Tabelle `mitarbeiter_dokumente` speichert Metadaten jeder Datei (`mitarbeiter_id`, Server-`filename`, ursprünglicher Name und Zeitstempel).
3. **Upload-Route** – Über `/mitarbeiter_upload/<id>` können Dateien hochgeladen werden. Nach erfolgreichem Upload werden sie im Ordner `uploads/<id>/` gespeichert und in der Tabelle erfasst.
4. **Download & Löschen** – Die Routen `/download/<doc_id>` und `/delete_document/<doc_id>` liefern bzw. löschen eine Datei samt Datenbankeintrag.

Im Quellcode und in den Templates sind zusätzliche Kommentare hinterlegt, die die einzelnen Schritte erläutern und so beim Lernen unterstützen.

## Entwicklung

Zum Testen der Anwendung genügt es, das Python-Modul zu kompilieren:

```bash
python -m py_compile app.py
```

