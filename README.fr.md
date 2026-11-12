# MXReady

[![CI](https://github.com/shuljyli/MXReady/actions/workflows/ci.yml/badge.svg)](https://github.com/shuljyli/MXReady/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-1.0.1-blue)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)

[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt-BR.md) | **Français** | [Deutsch](README.de.md) | [Русский](README.ru.md)

Vous avez du code PyTorch qui tourne sur des cartes NVIDIA et vous voulez le porter sur un GPU MetaX. Vous ne savez
pas encore ce qui va casser.

MXReady lit d'abord le code (en lecture seule, sans l'exécuter) et liste les endroits susceptibles de poser problème :
là où le compilateur NVIDIA est appelé directement, là où l'on suppose des groupes de 32 threads (MetaX en utilise 64),
là où l'on utilise de l'assembleur en ligne propre à NVIDIA, là où l'on dépend de bibliothèques qui ne tourneront pas.
Chaque résultat indique le fichier, la ligne, la raison du problème et la correction suggérée.

Il ne réécrit pas votre code et n'affiche pas de « pourcentage de compatibilité » — le nombre de règles déclenchées ne
dit rien sur la probabilité de compatibilité. Une analyse statique propre signifie seulement que rien d'évident n'a été
trouvé ; la vraie réponse vient de l'exécution sur une machine MetaX.

> MXReady est un prototype communautaire, pas une certification de compatibilité officielle de MetaX. Une analyse
> statique réussie ne signifie **pas** qu'un projet fonctionne déjà sur MXMACA ; la réponse définitive doit encore venir
> de l'exécution du même commit dans un environnement GPU MetaX contrôlé.

## Ce qu'il fait

- Accepte les dépôts HTTPS publics sur GitHub et Gitee, éventuellement à une branche, un tag ou un
  commit de 40 caractères ;
- Analyse les fichiers texte Python, C/C++, CUDA, CMake, Shell, TOML, YAML et autres ;
- Fournit **35 règles** (`MXR-*`) ; chaque résultat indique le chemin du fichier, les numéros de ligne, le code
  concerné, une recommandation et une référence à la source primaire ;
- Les correspondances dans les tests, les exemples et la documentation ne comptent que comme des indications : elles
  apparaissent quand même dans le rapport, mais ne font pas juger le projet entier comme bloqué ;
- Produit des sorties JSON, Markdown, un badge SVG et un rapport HTML imprimable (impression en PDF depuis le
  navigateur), ainsi qu'un paquet de vérification à distance ne dépendant que de la bibliothèque standard ;
- Garde les conclusions statiques strictement séparées des conclusions de vérification matérielle ;
- Fournit un CLI en lecture seule pour les répertoires locaux, utile pour les régressions hors ligne et les rapports
  d'exemple ;
- `mxready-mcp` optionnel : expose l'analyse, l'état des tâches, les rapports et la consultation des règles sous la
  forme de 5 outils Model Context Protocol pour les agents de codage ;
- Empaquette l'interface React en page unique et le service FastAPI comme une seule unité déployable.

L'interface web fournit les pages « Bilan du code source », « Analyse par lots », « Historique des analyses »,
« Progression de la migration », « Bibliothèque de règles », « Accès MCP » et « Utilisation du CLI » ;
les rapports prennent en charge la navigation par fichiers prioritaires, la recherche paginée, la comparaison et le
partage, une liste de vérification manuelle et l'export HTML imprimable. MCP et le Web doivent explicitement partager
le même répertoire de données local pour lire les rapports l'un de l'autre.

Le MVP ne comprend pas les dépôts privés, la réécriture automatique du code source, l'orchestration Docker de serveurs
GPU distants, l'ordonnancement de GPU cloud, les comptes utilisateurs, ni de « score de compatibilité » en pourcentage.

## Ce qu'il a trouvé sur des projets réels

Bilan de [`NVIDIA/apex`](https://github.com/NVIDIA/apex) au commit
`575968bc1f9127ccd61003a681472a83af4ff1a1` : **12 bloquants · 65 avertissements · 140 indications**. Le rapport
complet se trouve dans [examples/reports/nvidia-apex.md](examples/reports/nvidia-apex.md).

Les quatre plus représentatifs des 12 bloquants :

| Emplacement | Correspondance | Pourquoi ça casse sur MetaX |
| --- | --- | --- |
| `csrc/welford.cu:36` | `#define WARP_SIZE 32` | Largeur de warp codée en dur à 32 ; MetaX utilise 64 |
| `nhwc_batch_norm_kernel.h:1245` | `int lane_id = threadIdx.x & 31;` | lane 0 et lane 32 sont calculés comme la même lane |
| `group_norm_nhwc.h:40` | `asm volatile("red.release.gpu.global.add.s32 …")` | Le PTX en ligne lie le code au backend NVIDIA |
| `setup.py:65` | `subprocess.check_output([cuda_dir + "/bin/nvcc", "-V"])` | Appelle directement `nvcc` pour détecter la version ; cette commande n'existe pas dans un environnement MetaX |

Deux des quatre **compilent sans erreur**, mais les calculs de lane et la largeur de warp produisent de mauvais
résultats sur des waves de largeur 64, et les tests ne le couvrent pas forcément ; les deux autres échouent tout
simplement à la compilation sur MetaX. Ces deux types de problèmes peuvent retarder une migration de plusieurs semaines.

Deux autres cas à commit fixé complètent les preuves de part et d'autre du cycle diagnostic des bloquants et correction :

- [`bitsandbytes`](https://github.com/bitsandbytes-foundation/bitsandbytes) (`a616886`) : 27 résultats, 7 bloquants,
  rapport dans [examples/reports/bitsandbytes.md](examples/reports/bitsandbytes.md).
- [`causal-conv1d`](https://github.com/Dao-AILab/causal-conv1d) (`cd81f04`) : après correction selon le rapport, le
  nombre de résultats a diminué et la vérification matérielle sur un MetaX C500 est revenue entièrement `passed`,
  voir les [notes de cas de migration](docs/migration-case-2026-11.md).

## Architecture

```text
React/Vite UI
      │ /api
      ▼
FastAPI ── file de tâches et rapports sur SQLite
   │
   ├─ attribution atomique / battement de bail ── récupération git restreinte ── index de fichiers en lecture seule ── moteur de règles YAML
   ├─ rapports JSON / Markdown / SVG
   └─ ZIP de vérification ◀── exécuté sur votre propre hôte MetaX ── result.json
```

Le service web n'importe, n'installe, ne compile et n'exécute jamais le code du dépôt analysé. Le runner distant ne
s'exécute que sur une machine que vous contrôlez et exige une confirmation explicite avant toute commande du projet.

Le code Python se trouve uniformément sous `src/` ; les règles par défaut et le schéma de vérification sont livrés avec
le paquet installé. Les conventions de répertoire, la file de tâches et les notes de mise à niveau sont décrites dans le
[guide d'architecture](docs/architecture.md). Après avoir modifié les modèles, lancez `make contracts` pour régénérer
les contrats d'interface.

## Matrice des fonctionnalités

| Fonctionnalité | État | Mode de vérification |
| --- | --- | --- |
| Analyse statique de dépôts publics (GitHub / Gitee, éventuellement à une branche, un tag ou un commit de 40 caractères) | Disponible | Tests de bout en bout + rapports d'exemple |
| 35 règles `MXR-*` | Disponible | Chaque règle possède un cas positif et un cas négatif similaire |
| Sortie de rapports : JSON / Markdown / HTML / badge SVG | Disponible | Tests de contrat + `generate_contracts.py --check` |
| Tableau de bord de progression de la migration (agrégation inter-dépôts, tendance des bloquants) | Disponible | Tests d'agrégation backend + Vitest |
| Paquet de vérification et runner dépendant uniquement de la bibliothèque standard | Disponible | Régression d'installation + tests des limites de sécurité |
| ZIP d'installation pour les trois plateformes et wheel/sdist avec interface web | Disponible | Le workflow de publication installe et démarre réellement sur Windows / Linux / macOS |
| Interface React en page unique | Disponible | Vitest + mode strict TypeScript |
| Évaluation par lots (`mxready-scan-batch`) | Disponible | Régression CLI |
| Outils MCP (`mxready-mcp`, nécessite `.[mcp]`) | Disponible | Tests backend et une vraie poignée de main stdio |
| Vérification sur GPU MetaX réel | Deux exécutions anonymisées terminées (MetaX C500 : `pytorch/extension-cpp` @ `1c325b2`, `causal-conv1d` @ `cd81f04`) | Les cinq vérifications d'environnement du runner `inspect` et le smoke sur une seule carte sont toutes `passed` ; la construction de causal-conv1d a utilisé un correctif temporaire non soumis en amont, et chaque autre projet doit encore faire l'objet de sa propre exécution |

État d'ingénierie : `ruff`, `mypy`, les vérifications de contrats et `pytest` sont tous au vert (plus de 540 cas de
test, 90 % de couverture de branches) ;
la CI couvre Python 3.11 / 3.12 / 3.13 × Windows / Linux / macOS, ainsi qu'un job runner sur Python 3.10.

## Limites connues

- **Aucun verdict de compatibilité.** Toute sortie s'arrête aux signaux de risque statiques et aux recommandations de
  revue manuelle ; une affirmation du type « vérifié dans un environnement MetaX » doit être liée à un commit précis,
  produite comme résultat `verified` sur un GPU MetaX contrôlé, et ne pas avoir plus de 30 jours.
- **La précision des règles n'a pas été calibrée statistiquement sur un grand nombre de projets réels.** Les cas
  positifs et négatifs proviennent de cas de test contrôlés et ont été revérifiés sur des dépôts publics (0 faux
  positifs) ; les taux systématiques de faux positifs et de faux négatifs nécessitent encore des statistiques sur
  davantage de projets réels, voir le [guide des règles](docs/rules.md).
- **Les résultats de vérification sont valables 30 jours** ; une fois expirés, l'état du rapport devient `stale` et le
  résultat doit être téléversé à nouveau.
- **Périmètre du MVP** : pas de dépôts privés, pas de réécriture automatique du code source, pas d'ordonnancement de
  GPU cloud, pas de comptes utilisateurs, pas de score de compatibilité en pourcentage.

> Les rapports d'exemple pour les projets publics se trouvent dans [examples/reports](examples/reports) :
> `pytorch-extension-cpp` passe tout (4 indications), `nvidia-apex` (12 bloquants) et `bitsandbytes` (7 bloquants)
> sont en état bloqué, et `causal-conv1d` conserve les rapports d'avant et d'après correction. Ils sont présentés côte
> à côte pour montrer que les rapports passent réellement au vert, et passent réellement au rouge. Le flux de
> vérification à distance est décrit dans [examples/verification/README.md](examples/verification/README.md).

## Installation et démarrage

Les utilisateurs courants peuvent simplement installer le paquet de publication avec interface web : ni Node.js, ni
PyTorch, ni pilote GPU nécessaires. Les trois plateformes exigent que **Python 3.11+ (avec pip/venv) et Git** soient
préinstallés ; la première installation télécharge par défaut les dépendances Python depuis le réseau.

| Plateforme | Artefact | Après extraction, exécutez dans le répertoire du paquet |
| --- | --- | --- |
| Windows 10/11 | `mxready-1.0.1-windows.zip` | PowerShell : `.\install.ps1`, puis `.\start.ps1` |
| Linux | `mxready-1.0.1-linux.zip` | `bash install.sh`, puis `bash start.sh` |
| macOS (Apple Silicon / Intel) | `mxready-1.0.1-macos.zip` | `bash install.sh`, puis `bash start.sh` |
| Environnement Python géré | `mxready` sur PyPI | `python -m pip install mxready`, puis `mxready-serve` |
| Environnement Python existant | `mxready-1.0.1-py3-none-any.whl` | dans un venv dédié : `python -m pip install <chemin du wheel>`, puis `mxready-serve` |

Après le démarrage, ouvrez <http://127.0.0.1:8000> ; appuyez sur `Ctrl+C` dans le terminal pour arrêter le service.
Les ZIP sont des paquets d'applications Python : ils n'incluent ni Python ni Git, et ne sont ni des exécutables natifs
EXE/DMG, ni des installateurs de gestionnaires de paquets système. Les artefacts publiés se trouvent sur
[GitHub Releases](https://github.com/shuljyli/MXReady/releases) ; la préparation hors ligne, la vérification des sommes
de contrôle, la mise à niveau, la désinstallation et le dépannage sous Windows sont couverts par les
[notes d'installation et de publication](docs/installation.md) (en chinois).

Mainteneurs construisant les paquets de publication : installez les dépendances de développement, puis lancez
`make release` (Windows : `.\scripts\make.ps1 release`) ; les artefacts atterrissent dans le `dist/` ignoré par git.
Le déploiement serveur (bare metal / systemd / Docker / nginx) et les options de configuration `MXREADY_*` sont
décrits dans le [guide de déploiement](docs/deployment.md) et [.env.example](.env.example).

### Développement depuis les sources

Prérequis : Python 3.11+, Git et Node.js 22+ (nécessaire uniquement pour développer/construire le frontend).

```bash
make install                # crée .venv, installe les dépendances de dev, npm ci (Windows : .\scripts\make.ps1 install)
bash ./scripts/dev.sh       # démarre frontend et backend en une étape (Windows : .\scripts\dev.ps1)
```

`dev.sh` / `dev.ps1` démarrent en même temps le frontend <http://localhost:5173> (`/api` proxifié vers le backend) et
le backend <http://127.0.0.1:8000> (rechargement à chaud `--reload`). Utilisez le port 5173 en mode développement ; le
backend sert l'interface complète lorsque `frontend/dist` existe déjà, la documentation de l'API se trouve à `/docs`,
et le manuel d'API en chinois est à [docs/api.md](docs/api.md).

Points d'entrée de commandes unifiés (`install` / `dev` / `frontend` / `test` / `lint` / `typecheck` /
`build` / `release` / `clean`) :

| Tâche | Windows (PowerShell) | Linux / macOS | Rôle |
| --- | --- | --- | --- |
| Installer les dépendances | `.\scripts\make.ps1 install` | `make install` | venv + dépendances backend + `npm ci` |
| Démarrer le backend | `.\scripts\make.ps1 dev` | `make dev` | uvicorn `--reload`, port 8000 |
| Démarrer le frontend | `.\scripts\make.ps1 frontend` | `make frontend` | Vite dev, port 5173 |
| Exécuter les tests | `.\scripts\make.ps1 test` | `make test` | pytest backend (avec seuil de couverture) |
| Vérification de style | `.\scripts\make.ps1 lint` | `make lint` | ruff sur src / scripts / tests / packaging |
| Vérification de types | `.\scripts\make.ps1 typecheck` | `make typecheck` | mypy sur src / scripts |
| Construire le frontend | `.\scripts\make.ps1 build` | `make build` | `npm run build` produit `frontend/dist` |
| Générer les paquets | `.\scripts\make.ps1 release` | `make release` | interface + wheel/sdist + ZIP des trois plateformes dans `dist/` |
| Nettoyer | `.\scripts\make.ps1 clean` | `make clean` | supprime `.pytest-temp` |

## Outils en ligne de commande

L'utilisation détaillée et les conventions de codes de sortie de `mxready-scan` (répertoires locaux),
`mxready-scan-public` (preuves sur dépôt public), `mxready-build-bundle` (paquet de vérification),
`mxready-scan-batch` (évaluation par lots) et `mxready-mcp` (pour les agents de codage) sont décrites dans le
[guide du CLI](docs/cli.md). Tous les CLI analysent en lecture seule et n'exécutent jamais le code analysé.

## Signification des statuts

| Statut | Signification |
| --- | --- |
| `passed` | Aucun bloquant ni avertissement détecté ; la vérification matérielle reste requise |
| `warnings` | Risques de migration nécessitant une revue manuelle |
| `blocked` | Bloquants à traiter avant de demander des ressources de calcul distantes |
| `not-run` | Aucun résultat de vérification en environnement MetaX n'a encore été téléversé |
| `verified` | `mx-smi` et le contrôle de périphérique PyTorch sont passés pour le même commit, toutes les vérifications d'environnement ont réussi et le résultat n'a pas plus de 30 jours ; cela ne vaut pas certification complète du projet |
| `failed` | La commande de vérification a échoué |
| `stale` | Le résultat de vérification a plus de 30 jours et doit être relancé |

Les rapports ne fournissent volontairement pas de score de compatibilité en pourcentage, car le nombre de règles
déclenchées ne peut pas représenter la probabilité de compatibilité d'un projet.

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

Les scripts de tests de charge (locust, avec un Git mock local et sans dépendance à l'internet public) se trouvent dans
[tests/load/](tests/load/).

## Documentation

| Document | Contenu |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | Arborescence, directions des dépendances, cycle de vie des tâches et conventions des ressources du paquet |
| [docs/deployment.md](docs/deployment.md) | Déploiement en production : bare metal / systemd / Docker / nginx / sauvegarde / journaux / options de configuration |
| [docs/api.md](docs/api.md) | Manuel d'API en chinois (avec exemples `curl`) |
| [docs/cli.md](docs/cli.md) | Utilisation détaillée du CLI et de MCP |
| [docs/installation.md](docs/installation.md) | Installateurs des trois plateformes, préparation hors ligne, mise à niveau, construction des publications et dépannage Windows |
| [docs/report-workflow.md](docs/report-workflow.md) | Résultats complets, périmètre d'analyse, comparaison de rapports, SARIF et intégration CI |
| [docs/security.md](docs/security.md) | Modèle de sécurité |
| [docs/rules.md](docs/rules.md) | Guide de création de règles |
| [docs/runner.md](docs/runner.md) | Guide du runner de vérification à distance |
| [docs/migration-case-2026-11.md](docs/migration-case-2026-11.md) | Cas sur dépôts réels : diagnostic des bloquants, correction et revérification matérielle |
| [examples/verification/README.md](examples/verification/README.md) | SOP de passation de la vérification matérielle |
| [CHANGELOG.md](CHANGELOG.md) | Historique des versions |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Processus de contribution et portes de qualité |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Code de conduite communautaire |

## Limites de sécurité

- Seuls les dépôts HTTPS publics sur `github.com` et `gitee.com` sont autorisés ; Git ne lit jamais les identifiants,
  ne télécharge jamais d'objets LFS et n'initialise jamais les sous-modules, et les récupérations ont des délais
  d'attente et des limites de taille/entrées ;
- Les analyses web n'exécutent jamais le code des dépôts ; les résultats de vérification sont limités à 1 Mio et liés
  au commit analysé ;
- Le runner n'utilise jamais `sudo` et n'installe jamais de logiciels ; les commandes s'exécutent avec `shell=False`,
  et les commandes du projet exigent une confirmation manuelle avant exécution ;
- Activez la limitation de débit et une limite de taille de corps de requête avant d'exposer publiquement un
  déploiement.

Avant de déployer, lisez intégralement le [modèle de sécurité](docs/security.md) et le [guide du runner](docs/runner.md).

## Contribuer

Les nouvelles règles doivent inclure des cas positifs, des cas négatifs similaires et des références techniques
primaires. Veuillez lire :

- [Guide de contribution](CONTRIBUTING.md)
- [Guide de création de règles](docs/rules.md)
- [Guide de vérification à distance](docs/runner.md)
- [Modèle de sécurité](docs/security.md)

## Feuille de route MVP

1. Générer des rapports reproductibles sur trois projets publics d'extensions CUDA et calibrer la précision des
   règles ;
2. Terminer la vérification matérielle anonymisée sur davantage de projets publics aux mêmes commits (fait pour
   `pytorch/extension-cpp` @ `1c325b2` et `causal-conv1d` @ `cd81f04`) ;
3. Soumettre à un projet amont une petite PR de migration, limitée et facile à relire ;
4. Étendre l'ensemble de règles et le modèle de vérification minimal à partir des retours d'adaptation réels.

## Contributeurs principaux

- **shuli-黍黎** — initiateur du projet et développeur principal.

## Licence

Ce projet est sous licence [Apache License 2.0](LICENSE). Vous êtes libre de l'utiliser, de le modifier et de le
distribuer conformément aux termes de la licence.

## Contact

Questions, suggestions et collaborations bienvenues — ouvrez une GitHub Issue, ou contactez-nous par e-mail :

- shuli_ljy@outlook.com
- 2199553510@qq.com
