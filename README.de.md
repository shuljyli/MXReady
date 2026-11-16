# MXReady

[![CI](https://github.com/shuljyli/MXReady/actions/workflows/ci.yml/badge.svg)](https://github.com/shuljyli/MXReady/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-1.0.1-blue)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)

[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt-BR.md) | [Français](README.fr.md) | **Deutsch** | [Русский](README.ru.md)

Sie haben PyTorch-Code, der auf NVIDIA-Grafikkarten läuft, und wollen ihn auf eine MetaX-GPU umziehen.
Was dabei kaputtgeht, wissen Sie noch nicht.

MXReady liest den Code zuerst (nur lesend, ohne ihn auszuführen) und listet die Stellen auf, die wahrscheinlich
Ärger machen: wo direkt der NVIDIA-Compiler aufgerufen wird, wo „32 Threads pro Gruppe" fest verdrahtet ist
(bei MetaX sind es 64), wo NVIDIA-spezifischer Inline-Assembler eingebettet wird, wo Bibliotheken
vorausgesetzt werden, die nicht laufen. Jeder Fund nennt Datei, Zeile, den Grund und einen Änderungsvorschlag.

Es schreibt Ihren Code nicht um und liefert auch keine Zahl wie einen „Kompatibilitätsprozentsatz" — wie viele
Regeln ein Projekt auslöst, sagt nichts über die Wahrscheinlichkeit der Kompatibilität. Eine saubere statische
Prüfung bedeutet nur, dass nichts Offensichtliches gefunden wurde; die eigentliche Antwort kommt vom Laufen
auf einer MetaX-Maschine.

> MXReady ist ein Community-Prototyp, keine offizielle MetaX-Kompatibilitätszertifizierung. Eine bestandene
> statische Prüfung bedeutet **nicht**, dass ein Projekt bereits auf MXMACA läuft; die endgültige Aussage muss
> weiterhin durch Ausführen desselben Commits in einer kontrollierten MetaX-GPU-Umgebung erbracht werden.

## Was es kann

- Akzeptiert öffentliche HTTPS-Repositories auf GitHub und Gitee, wahlweise bei einem Branch, Tag oder
  40-stelligem Commit;
- Durchsucht Python-, C/C++-, CUDA-, CMake-, Shell-, TOML-, YAML- und weitere Textdateien;
- Enthält **35 Regeln** (`MXR-*`); jeder Fund enthält Dateipfad, Zeilennummern, den getroffenen Codeausschnitt,
  eine Empfehlung und eine Referenz auf die Primärquelle;
- Treffer in Tests, Beispielen und Dokumentation zählen nur als Hinweise: Sie erscheinen weiterhin im Bericht,
  lassen das gesamte Projekt aber nicht als blockiert bewerten;
- Gibt JSON, Markdown, ein SVG-Badge und einen druckbaren HTML-Bericht (im Browser als PDF drucken) aus, dazu
  ein Verifizierungspaket nur mit der Standardbibliothek;
- Hält die statischen Ergebnisse strikt von den Ergebnissen der Hardware-Verifizierung getrennt;
- Bietet ein nur lesendes CLI für lokale Verzeichnisse, nützlich für Offline-Regression und Beispielberichte;
- Optionales `mxready-mcp`: stellt Scan, Aufgabenstatus, Berichte und Regelsuche als 5
  Model-Context-Protocol-Werkzeuge für Coding-Agenten bereit;
- Verpackt die React-Single-Page-Oberfläche und den FastAPI-Dienst als eine auslieferbare Einheit.

Die Weboberfläche bietet die Seiten „Quellcode-Check", „Batch-Scan", „Scan-Verlauf", „Migrationsfortschritt",
„Regelbibliothek", „MCP-Anbindung" und „Kommandozeile"; Berichte unterstützen Navigation zu prioritären
Dateien, seitenweise Suche, Vergleich und Teilen, eine Checkliste zur manuellen Prüfung und HTML-Druckexport.
MCP und Web müssen beim Lesen der jeweils anderen Berichte ausdrücklich dasselbe lokale Datenverzeichnis
verwenden.

Der MVP umfasst keine privaten Repositories, keine automatische Quellcodeänderung, keine
Docker-Orchestrierung entfernter GPU-Server, kein Cloud-GPU-Scheduling, kein Benutzersystem und keine
prozentuale „Kompatibilitätsbewertung".

## Was es auf echten Projekten gefunden hat

Check von [`NVIDIA/apex`](https://github.com/NVIDIA/apex) beim Commit
`575968bc1f9127ccd61003a681472a83af4ff1a1`: **12 blockierend · 65 Warnungen · 140 Hinweise**. Der
vollständige Bericht liegt unter [examples/reports/nvidia-apex.md](examples/reports/nvidia-apex.md).

Die vier repräsentativsten der 12 Blocker:

| Fundort | Treffer | Warum es auf MetaX kaputtgeht |
| --- | --- | --- |
| `csrc/welford.cu:36` | `#define WARP_SIZE 32` | Warp-Breite fest auf 32 gesetzt; bei MetaX sind es 64 |
| `nhwc_batch_norm_kernel.h:1245` | `int lane_id = threadIdx.x & 31;` | lane 0 und lane 32 werden als dieselbe lane berechnet |
| `group_norm_nhwc.h:40` | `asm volatile("red.release.gpu.global.add.s32 …")` | Eingebettetes PTX bindet den Code an das NVIDIA-Backend |
| `setup.py:65` | `subprocess.check_output([cuda_dir + "/bin/nvcc", "-V"])` | Ruft `nvcc` direkt zur Versionsabfrage auf; diesen Befehl gibt es in einer MetaX-Umgebung nicht |

Zwei der vier **kompilieren erfolgreich**, aber lane-Arithmetik und Warp-Breite liefern auf 64-breiten waves
falsche Ergebnisse, und Tests decken das nicht unbedingt ab; die anderen beiden kompilieren auf MetaX schlicht
nicht. Beide Problemklassen können eine Migration um Wochen verlängern.

Zwei weitere Fälle mit festen Commits ergänzen die Evidenz auf beiden Seiten der Schleife aus Blocker-Diagnose
und Fix:

- [`bitsandbytes`](https://github.com/bitsandbytes-foundation/bitsandbytes) (`a616886`): 27 Funde, 7 Blocker;
  Bericht unter [examples/reports/bitsandbytes.md](examples/reports/bitsandbytes.md).
- [`causal-conv1d`](https://github.com/Dao-AILab/causal-conv1d) (`cd81f04`): nach dem Fix gemäß Bericht sank die
  Zahl der Funde, und die Hardware-Verifizierung auf einem MetaX C500 ergab durchgehend `passed`; siehe
  [Migrationsfall-Notizen](docs/migration-case-2026-11.md) (chinesisch).

## Architektur

```text
React/Vite UI
      │ /api
      ▼
FastAPI ── SQLite-gestützte persistente Aufgabenwarteschlange und Berichte
   │
   ├─ atomare Übernahme / Leasing-Herzschlag ── eingeschränkter git fetch ── nur lesender Dateiindex ── YAML-Regelwerk
   ├─ JSON / Markdown / SVG-Berichte
   └─ Verifizierungs-ZIP ◀── läuft auf Ihrem eigenen MetaX-Host ── result.json
```

Der Webdienst importiert, installiert, baut oder führt niemals Code aus dem gescannten Repository aus. Der
Remote-Runner läuft nur auf einer Maschine, die Sie kontrollieren, und verlangt vor der Ausführung von
Projektbefehlen eine ausdrückliche Bestätigung.

Python-Code liegt einheitlich unter `src/`; Standardregeln und das Verifizierungs-Schema werden mit dem
Installationspaket ausgeliefert. Verzeichnis-Konventionen, die Aufgabenwarteschlange und Upgrade-Hinweise
stehen in der [Architekturanleitung](docs/architecture.md) (chinesisch). Nach Änderungen an den Modellen
erzeugt `make contracts` die Schnittstellenverträge neu.

## Funktionsmatrix

| Fähigkeit | Status | Wie es verifiziert wird |
| --- | --- | --- |
| Statischer Scan öffentlicher Repositories (GitHub / Gitee, wahlweise bei Branch, Tag oder 40-stelligem Commit) | Verfügbar | End-to-End-Tests + Beispielberichte |
| 35 `MXR-*`-Regeln | Verfügbar | Jede Regel hat ein positives und ein ähnliches negatives Fixture |
| Berichtsausgabe: JSON / Markdown / HTML / SVG-Badge | Verfügbar | Vertragstests + `generate_contracts.py --check` |
| Migrationsfortschritts-Dashboard (reposübergreifende Aggregation, Blocker-Trends) | Verfügbar | Backend-Aggregationstests + Vitest |
| Verifizierungspaket und Runner nur mit Standardbibliothek | Verfügbar | Installer-Regression + Sicherheits-Grenztests |
| Installations-ZIPs für alle drei Plattformen und wheel/sdist mit Oberfläche | Verfügbar | Der Release-Workflow installiert und startet tatsächlich auf Windows / Linux / macOS |
| React-Single-Page-Oberfläche | Verfügbar | Vitest + TypeScript-Strict-Mode |
| Sammelbewertung (`mxready-scan-batch`) | Verfügbar | CLI-Regression |
| MCP-Werkzeuge (`mxready-mcp`, benötigt `.[mcp]`) | Verfügbar | Backend-Tests und ein echter stdio-Handshake |
| Echte MetaX-GPU-Verifizierung | Zwei geschwärzte Durchläufe abgeschlossen (MetaX C500: `pytorch/extension-cpp` @ `1c325b2`, `causal-conv1d` @ `cd81f04`) | Alle fünf runner-`inspect`-Umgebungsprüfungen und der Einzel-GPU-Smoke jeweils `passed`; der causal-conv1d-Build verwendete einen temporären Patch, der nicht upstream eingereicht wurde, und jedes andere Projekt braucht noch seinen eigenen Durchlauf |

Engineering-Status: `ruff`, `mypy`, Vertragsprüfungen und `pytest` sind alle grün (über 540 Testfälle, 90 %
Zweigabdeckung); CI deckt Python 3.11 / 3.12 / 3.13 × Windows / Linux / macOS ab, dazu ein
Python-3.10-Runner-Job.

## Bekannte Einschränkungen

- **Kein Kompatibilitätsurteil.** Jede Ausgabe endet bei statischen Risikosignalen und Empfehlungen zur
  manuellen Prüfung; eine Aussage wie „in einer MetaX-Umgebung verifiziert" muss an einen bestimmten Commit
  gebunden sein, als `verified`-Ergebnis auf einer kontrollierten MetaX-GPU erzeugt worden sein und höchstens
  30 Tage alt sein.
- **Die Regelgenauigkeit ist noch nicht anhand vieler echter Projekte statistisch kalibriert.** Die Positiv-
  und Negativbeispiele stammen aus kontrollierten Fixtures und wurden auf öffentlichen Repositories
  gegengeprüft (0 Fehlalarme); systematische Fehlalarm- und Übersehensraten brauchen noch Statistiken aus mehr
  echten Projekten, siehe [Regelhandbuch](docs/rules.md) (chinesisch).
- **Verifizierungsergebnisse sind 30 Tage gültig**; danach wechselt der Berichtsstatus auf `stale` und das
  Ergebnis muss erneut hochgeladen werden.
- **MVP-Umfang**: keine privaten Repositories, keine automatische Quellcodeänderung, kein Cloud-GPU-Scheduling,
  kein Benutzersystem, keine prozentuale Kompatibilitätsbewertung.

> Beispielberichte für öffentliche Projekte liegen unter [examples/reports](examples/reports):
> `pytorch-extension-cpp` besteht alles (4 Hinweise), `nvidia-apex` (12 Blocker) und `bitsandbytes` (7 Blocker)
> stehen auf blockiert, und `causal-conv1d` behält beide Berichte, vor und nach dem Fix. Sie stehen
> nebeneinander, um zu zeigen, dass Berichte wirklich grün und wirklich rot werden. Der Ablauf der
> Remote-Verifizierung ist in [examples/verification/README.md](examples/verification/README.md) beschrieben.

## Installation und Start

Reguläre Benutzer installieren einfach das Release-Paket mit Weboberfläche: kein Node.js, kein PyTorch und
kein GPU-Treiber nötig. Auf allen drei Plattformen müssen **Python 3.11+ (mit pip/venv) und Git**
vorinstalliert sein; die erste Installation lädt Python-Abhängigkeiten standardmäßig aus dem Netz herunter.

| Plattform | Paket | Nach dem Entpacken im Paketverzeichnis ausführen |
| --- | --- | --- |
| Windows 10/11 | `mxready-1.0.1-windows.zip` | PowerShell: `.\install.ps1`, dann `.\start.ps1` |
| Linux | `mxready-1.0.1-linux.zip` | `bash install.sh`, dann `bash start.sh` |
| macOS (Apple Silicon / Intel) | `mxready-1.0.1-macos.zip` | `bash install.sh`, dann `bash start.sh` |
| Eigenverwaltete Python-Umgebung | `mxready` auf PyPI | `python -m pip install mxready`, dann `mxready-serve` |
| Vorhandene Python-Umgebung | `mxready-1.0.1-py3-none-any.whl` | in einer eigenen venv: `python -m pip install <wheel-Pfad>`, dann `mxready-serve` |

Öffnen Sie nach dem Start <http://127.0.0.1:8000>; im Terminal beendet `Ctrl+C` den Dienst. Die ZIPs sind
Python-Anwendungspakete: Sie enthalten weder Python noch Git und sind keine nativen EXE-/DMG-Pakete oder
Installer von System-Paketmanagern. Veröffentlichte Artefakte liegen auf
[GitHub Releases](https://github.com/shuljyli/MXReady/releases); Offline-Vorbereitung, Prüfsummen-Abgleich,
Upgrade, Deinstallation und Windows-Fehlersuche stehen in den [Installations- und
Release-Hinweisen](docs/installation.md) (chinesisch).

Maintainer bauen Release-Pakete so: Entwicklungsabhängigkeiten installieren, dann `make release` ausführen
(Windows: `.\scripts\make.ps1 release`); die Artefakte landen im von Git ignorierten `dist/`.
Serverbereitstellung (Bare Metal / systemd / Docker / nginx) und die `MXREADY_*`-Konfigurationsoptionen
stehen im [Deployment-Handbuch](docs/deployment.md) (chinesisch) und in [.env.example](.env.example).

### Entwicklung aus dem Quellcode

Voraussetzungen: Python 3.11+, Git und Node.js 22+ (nur für die Frontend-Entwicklung bzw. den Frontend-Build
nötig).

```bash
make install                # .venv anlegen, Dev-Abhängigkeiten installieren, npm ci (Windows: .\scripts\make.ps1 install)
bash ./scripts/dev.sh       # Frontend und Backend in einem Schritt starten (Windows: .\scripts\dev.ps1)
```

`dev.sh` / `dev.ps1` starten das Frontend <http://localhost:5173> (`/api` wird auf das Backend proxyt) und
das Backend <http://127.0.0.1:8000> (`--reload` Hot Reload) gleichzeitig. Im Entwicklungsmodus nutzen Sie
Port 5173; das Backend liefert die vollständige Oberfläche, sobald `frontend/dist` existiert, die
API-Dokumentation liegt unter `/docs`, das chinesische API-Handbuch unter [docs/api.md](docs/api.md).

Einheitliche Befehlseinstiegspunkte (`install` / `dev` / `frontend` / `test` / `lint` / `typecheck` /
`build` / `release` / `clean`):

| Aufgabe | Windows (PowerShell) | Linux / macOS | Wirkung |
| --- | --- | --- | --- |
| Abhängigkeiten installieren | `.\scripts\make.ps1 install` | `make install` | venv + Backend-Abhängigkeiten + `npm ci` |
| Backend starten | `.\scripts\make.ps1 dev` | `make dev` | uvicorn `--reload`, Port 8000 |
| Frontend starten | `.\scripts\make.ps1 frontend` | `make frontend` | Vite-Dev, Port 5173 |
| Tests ausführen | `.\scripts\make.ps1 test` | `make test` | Backend-pytest (mit Coverage-Schwelle) |
| Lint | `.\scripts\make.ps1 lint` | `make lint` | ruff über src / scripts / tests / packaging |
| Typprüfung | `.\scripts\make.ps1 typecheck` | `make typecheck` | mypy über src / scripts |
| Frontend bauen | `.\scripts\make.ps1 build` | `make build` | `npm run build` erzeugt `frontend/dist` |
| Release-Pakete bauen | `.\scripts\make.ps1 release` | `make release` | UI + wheel/sdist + ZIPs für drei Plattformen nach `dist/` |
| Aufräumen | `.\scripts\make.ps1 clean` | `make clean` | entfernt `.pytest-temp` |

## Kommandozeilenwerkzeuge

Detaillierte Nutzung und Exit-Code-Konventionen für `mxready-scan` (lokale Verzeichnisse),
`mxready-scan-public` (Nachweise für öffentliche Repositories), `mxready-build-bundle`
(Verifizierungspaket), `mxready-scan-batch` (Sammelbewertung) und `mxready-mcp` (für Coding-Agenten) stehen
im [CLI-Handbuch](docs/cli.md) (chinesisch). Alle CLIs analysieren nur lesend und führen gescannten Code
niemals aus.

## Bedeutung der Status

| Status | Bedeutung |
| --- | --- |
| `passed` | Keine Blocker oder Warnungen getroffen; Hardware-Verifizierung weiterhin erforderlich |
| `warnings` | Migrationsrisiken, die eine manuelle Prüfung brauchen |
| `blocked` | Blocker, die vor der Beantragung entfernter Rechenleistung behandelt werden sollten |
| `not-run` | Es wurde noch kein Verifizierungsergebnis aus der MetaX-Umgebung hochgeladen |
| `verified` | `mx-smi` und die PyTorch-Geräteprüfung für denselben Commit bestanden, alle Umgebungsprüfungen erfolgreich und das Ergebnis höchstens 30 Tage alt; das ist nicht dasselbe wie eine vollständige Projektzertifizierung |
| `failed` | Der Verifizierungsbefehl ist fehlgeschlagen |
| `stale` | Das Verifizierungsergebnis ist älter als 30 Tage und muss erneut laufen |

Berichte liefern bewusst keine prozentuale Kompatibilitätsbewertung, denn die Zahl der Regel-Treffer kann die
Kompatibilitätswahrscheinlichkeit eines Projekts nicht repräsentieren.

## Tests

```bash
python -m ruff check src scripts tests packaging
python -m ruff format --check src scripts tests packaging
python -m mypy
python scripts/generate_contracts.py --check
python -m pytest --cov=mxready --cov=mxready_runner --cov-fail-under=80

cd frontend
npm test
npm run build
```

Last-Testszenarien (locust, mit lokalem Mock-Git und ohne Abhängigkeit vom öffentlichen Internet) liegen
unter [tests/load/](tests/load/).

## Dokumentation

(Hinweis: Die Dokumente unter `docs/` sind auf Chinesisch verfasst.)

| Dokument | Inhalt |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | Verzeichnisstruktur, Abhängigkeitsrichtungen, Aufgabenlebenszyklus und Paketressourcen-Konventionen |
| [docs/deployment.md](docs/deployment.md) | Produktiv-Deployment: Bare Metal / systemd / Docker / nginx / Backup / Logging / Konfigurationsoptionen |
| [docs/api.md](docs/api.md) | Chinesisches API-Handbuch (mit `curl`-Beispielen) |
| [docs/cli.md](docs/cli.md) | Detaillierte CLI- und MCP-Nutzung |
| [docs/installation.md](docs/installation.md) | Installer für drei Plattformen, Offline-Vorbereitung, Upgrade, Release-Build und Windows-Fehlersuche |
| [docs/report-workflow.md](docs/report-workflow.md) | Vollständige Funde, Scan-Umfang, Berichtsvergleich, SARIF und CI-Anbindung |
| [docs/security.md](docs/security.md) | Sicherheitsmodell |
| [docs/rules.md](docs/rules.md) | Leitfaden zur Regelentwicklung |
| [docs/runner.md](docs/runner.md) | Leitfaden für den Remote-Verifizierungs-Runner |
| [docs/migration-case-2026-11.md](docs/migration-case-2026-11.md) | Fälle aus echten Repositories: Blocker-Diagnose, Fix und Hardware-Re-Verifizierung |
| [examples/verification/README.md](examples/verification/README.md) | Übergabe-SOP für die Hardware-Verifizierung |
| [CHANGELOG.md](CHANGELOG.md) | Versionshistorie |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Mitwirkungsprozess und Qualitätstor |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Community-Verhaltenskodex |

## Sicherheitsgrenzen

- Es sind nur öffentliche HTTPS-Repositories auf `github.com` und `gitee.com` erlaubt; Git liest keine
  Zugangsdaten, lädt keine LFS-Objekte herunter und initialisiert keine Submodule, und Fetches haben
  Zeitlimits sowie Größen- und Eintragsobergrenzen;
- Web-Scans führen niemals Repository-Code aus; Verifizierungsergebnisse sind auf 1 MiB begrenzt und an den
  gescannten Commit gebunden;
- Der Runner benutzt niemals `sudo` und installiert keine Software; Befehle laufen mit `shell=False`, und
  Projektbefehle erfordern vor der Ausführung eine manuelle Bestätigung;
- Aktivieren Sie vor einer öffentlichen Bereitstellung eine Ratenbegrenzung und eine Obergrenze für die
  Anfragegröße.

Lesen Sie vor dem Deployment das [Sicherheitsmodell](docs/security.md) (chinesisch) und den
[Runner-Leitfaden](docs/runner.md) (chinesisch) vollständig.

## Mitwirken

Neue Regeln müssen Positivbeispiele, ähnliche Negativbeispiele und technische Primärquellen enthalten. Bitte
lesen Sie:

- [Mitwirkungsleitfaden](CONTRIBUTING.md)
- [Leitfaden zur Regelentwicklung](docs/rules.md) (chinesisch)
- [Leitfaden zur Remote-Verifizierung](docs/runner.md) (chinesisch)
- [Sicherheitsmodell](docs/security.md) (chinesisch)

## MVP-Roadmap

1. Reproduzierbare Berichte auf drei öffentlichen CUDA-Erweiterungsprojekten erzeugen und die
   Regelgenauigkeit kalibrieren;
2. Für weitere öffentliche Projekte geschwärzte Hardware-Verifizierungen bei denselben Commits abschließen
   (erledigt für `pytorch/extension-cpp` @ `1c325b2` und `causal-conv1d` @ `cd81f04`);
3. Einen kleinen, prüfbaren Migrations-PR an ein Upstream-Projekt einreichen;
4. Den Regelsatz und die minimale Verifizierungsvorlage auf Basis echten Anpassungs-Feedbacks erweitern.

## Hauptmitwirkende

- **shuli-黍黎** — Projektautor und Hauptentwickler.

## Lizenz

Dieses Projekt steht unter der [Apache License 2.0](LICENSE). Sie dürfen es gemäß den Bedingungen der Lizenz
nutzen, ändern und weitergeben.

## Kontakt

Fragen, Anregungen und Zusammenarbeit sind willkommen — erstellen Sie ein GitHub-Issue oder kontaktieren Sie
uns per E-Mail:

- shuli_ljy@outlook.com
- 2199553510@qq.com
