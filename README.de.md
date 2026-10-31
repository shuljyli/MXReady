# MXReady

[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt-BR.md) | [Français](README.fr.md) | **Deutsch** | [Русский](README.ru.md)

PyTorch-Code läuft auf NVIDIA-Karten und soll auf eine MetaX-GPU umziehen. Was dabei kaputtgeht, ist noch offen.

MXReady liest den Code, ohne ihn auszuführen, und listet die Stellen auf, die wahrscheinlich Ärger machen:

- wo der NVIDIA-Compiler direkt aufgerufen wird;
- wo fest mit 32 Threads pro Gruppe gerechnet wird (bei MetaX sind es 64);
- wo NVIDIA-spezifischer Inline-Assembler verwendet wird;
- wo eine Bibliothek vorausgesetzt wird, die es auf der neuen Karte nicht gibt.

Jeder Fund nennt Datei, Zeile, den Grund und einen Vorschlag zur Änderung.

## Benutzung

Laden Sie das ZIP für Ihr System herunter, entpacken Sie es und starten Sie das Installationsskript.

```bash
# Linux / macOS
bash install.sh
bash start.sh
```

```powershell
# Windows
.\install.ps1
.\start.ps1
```

Danach <http://127.0.0.1:8000> öffnen und die Repository-Adresse einfügen.

Es geht auch auf der Kommandozeile:

```bash
mxready-scan ./my-repo \
  --repo-url https://github.com/example/my-repo \
  --commit <40-stelliger Commit> \
  --output reports
```

## Was es nicht tut

- Es schreibt den Code nicht um.
- Es liefert keinen „Kompatibilitätsprozentsatz“. Wie viele Regeln ein Projekt auslöst, sagt nichts darüber aus, ob es läuft.
- Eine saubere statische Prüfung heißt nur, dass nichts Offensichtliches gefunden wurde. Die eigentliche Antwort kommt erst, wenn derselbe Commit auf einer MetaX-Maschine läuft.

## Weiterlesen

- [Vollständige Dokumentation (Chinesisch)](README.md)
- [Full documentation (English)](README.en.md)
- [Regelliste](docs/rules.md)
- [Architektur](docs/architecture.md)

Lizenz [Apache-2.0](LICENSE).
