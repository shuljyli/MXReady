# MXReady

[![CI](https://github.com/shuljyli/MXReady/actions/workflows/ci.yml/badge.svg)](https://github.com/shuljyli/MXReady/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-1.0.1-blue)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)

[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | **Español** | [Português](README.pt-BR.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

Tienes código de PyTorch funcionando en tarjetas NVIDIA y quieres pasarlo a una GPU MetaX, pero no sabes con qué problemas te vas a encontrar.

MXReady lee el código primero (solo lectura, sin ejecutarlo) y lista los puntos que probablemente den problemas: dónde se llama directamente al compilador de NVIDIA, dónde se da por hecho que "un grupo tiene 32 hilos" (en MetaX son 64), dónde se usa ensamblador en línea exclusivo de NVIDIA, dónde se depende de librerías que no funcionan en la tarjeta nueva. Cada hallazgo indica qué archivo, qué línea, por qué es un problema y qué se recomienda cambiar.

No reescribe tu código por ti, ni ofrece cifras como un "porcentaje de compatibilidad" — el número de reglas que activa un proyecto no permite deducir la probabilidad de compatibilidad. Que la revisión estática pase solo significa que no se encontró nada evidente; la conclusión real sale de ejecutar el código en una máquina MetaX.

> MXReady es un prototipo comunitario, no una certificación oficial de compatibilidad de MetaX. Que la revisión estática pase no significa que el proyecto ya sea compatible con MXMACA; la conclusión final debe verificarse en el mismo commit y en un entorno MetaX GPU controlado.

## Qué puede hacer

- Acepta repositorios HTTPS públicos de GitHub y Gitee, con posibilidad de indicar rama, etiqueta o un commit de 40 caracteres;
- Escanea archivos de texto como Python, C/C++, CUDA, CMake, Shell, TOML, YAML, etc.;
- Incorpora **35 reglas** (`MXR-*`); cada resultado incluye archivo, línea, el código que activa la regla, una sugerencia y una referencia autorizada;
- Los hallazgos en pruebas, ejemplos y documentación solo se toman como avisos: se incluyen en el informe, pero no hacen que todo el proyecto se marque como bloqueado;
- Genera informes en JSON, Markdown, insignias SVG e HTML imprimible (el navegador lo convierte a PDF), además de un paquete de verificación remota que solo depende de la biblioteca estándar;
- Las conclusiones estáticas y las de verificación en hardware real se muestran por separado, sin mezclarse;
- Ofrece un CLI local de solo lectura para directorios, útil para regresiones sin conexión y para generar informes de ejemplo;
- Opcional `mxready-mcp`: expone escaneo, estado de tareas, informes y consulta de reglas como 5 herramientas MCP, para que los agentes de codificación compatibles con Model Context Protocol las usen;
- La interfaz React de página única y el servicio FastAPI se pueden empaquetar como una sola unidad de despliegue.

La interfaz web ofrece las páginas "Chequeo de código fuente", "Escaneo por lotes", "Historial de escaneos", "Progreso de migración", "Biblioteca de reglas", "Integración MCP" y "Uso desde la línea de comandos";
los informes admiten localización de archivos prioritarios, búsqueda con paginación, comparación para compartir, listas de revisión manual y exportación e impresión HTML. Al leer informes entre sí, MCP y Web deben compartir
explícitamente el mismo directorio de datos local.

El MVP no incluye repositorios privados, modificación automática del código fuente, orquestación Docker de servidores GPU remotos, programación de GPU en la nube, sistema de usuarios ni "puntuaciones de compatibilidad" porcentuales.

## Qué se encontró en proyectos reales

Resultados del chequeo de [`NVIDIA/apex`](https://github.com/NVIDIA/apex) en el commit `575968bc1f9127ccd61003a681472a83af4ff1a1`:
**12 bloqueos · 65 avisos · 140 notas**. El informe completo está en [examples/reports/nvidia-apex.md](examples/reports/nvidia-apex.md).

Los cuatro más representativos de los 12 bloqueos:

| Ubicación | Activación | Por qué falla en MetaX |
| --- | --- | --- |
| `csrc/welford.cu:36` | `#define WARP_SIZE 32` | El ancho del warp está fijado en 32; en MetaX es 64 |
| `nhwc_batch_norm_kernel.h:1245` | `int lane_id = threadIdx.x & 31;` | lane 0 y lane 32 se calculan como la misma lane |
| `group_norm_nhwc.h:40` | `asm volatile("red.release.gpu.global.add.s32 …")` | El PTX en línea queda atado al backend de NVIDIA |
| `setup.py:65` | `subprocess.check_output([cuda_dir + "/bin/nvcc", "-V"])` | Llama a `nvcc` para detectar la versión; en el entorno MetaX ese comando no existe |

Dos de los cuatro **compilan sin error**, pero el cálculo de lanes y el ancho del warp producen resultados incorrectos en una wave de ancho 64, y las pruebas no siempre los cubren;
los otros dos no compilan en MetaX. Ambos tipos de problemas pueden retrasar una migración semanas.

Otros dos casos con commit fijo aportan evidencia de ambos lados del ciclo de bloqueo y corrección:

- [`bitsandbytes`](https://github.com/bitsandbytes-foundation/bitsandbytes) (`a616886`): 27 hallazgos, 7 bloqueos;
  informe en [examples/reports/bitsandbytes.md](examples/reports/bitsandbytes.md).
- [`causal-conv1d`](https://github.com/Dao-AILab/causal-conv1d) (`cd81f04`): tras aplicar las correcciones del informe el número de hallazgos bajó, y
  la verificación en hardware real sobre MetaX C500 dio `passed` en todo; ver [registro del caso de migración](docs/migration-case-2026-11.md).

## Arquitectura

```text
React/Vite UI
      │ /api
      ▼
FastAPI ── SQLite: cola de tareas e informes persistentes
   │
   ├─ Asignación atómica / latido de concesión ── Git restringido ── Índice de archivos de solo lectura ── Motor de reglas YAML
   ├─ Informes JSON / Markdown / SVG
   └─ ZIP de verificación ◀── Se ejecuta en el host MetaX controlado por el usuario ── result.json
```

El servicio web nunca importa, instala, compila ni ejecuta código del repositorio analizado. El runner remoto solo se ejecuta en máquinas controladas por el usuario y exige confirmación humana antes de ejecutar los comandos del proyecto.

El código Python se agrupa de forma uniforme en `src/`; las reglas por defecto y el esquema de verificación se publican junto con el paquete de instalación. Las convenciones de directorios, la cola de tareas y las notas de actualización están en
[documentación de arquitectura](docs/architecture.md). Tras modificar los modelos, usa `make contracts` para sincronizar los contratos de interfaz generados.

## Matriz de funcionalidades

| Capacidad | Estado | Cómo se verifica |
| --- | --- | --- |
| Escaneo estático de repositorios públicos (GitHub / Gitee, con rama, etiqueta o commit de 40 caracteres) | Disponible | Pruebas de extremo a extremo + informes de ejemplo |
| 35 reglas de comprobación `MXR-*` | Disponible | Cada regla con fixtures de ejemplos positivos y negativos similares |
| Salida de informes: JSON / Markdown / HTML / insignias SVG | Disponible | Pruebas de contrato + `generate_contracts.py --check` |
| Panel de progreso de migración (agregación entre repositorios, tendencia de bloqueos) | Disponible | Pruebas de agregación del backend + Vitest |
| Paquete de verificación remota y runner de biblioteca estándar | Disponible | Regresión del paquete de instalación + pruebas de límites de seguridad |
| ZIP de instalación para tres plataformas y wheel/sdist con interfaz web | Disponible | El flujo de publicación instala y arranca realmente en Windows / Linux / macOS |
| Interfaz React de página única | Disponible | Vitest + modo estricto de TypeScript |
| Evaluación por lotes (`mxready-scan-batch`) | Disponible | Regresión de CLI |
| Herramientas MCP (`mxready-mcp`, requiere `.[mcp]`) | Disponible | Pruebas de backend + handshake stdio real |
| Verificación en GPU MetaX real | Dos verificaciones anonimizadas completadas (MetaX C500: `pytorch/extension-cpp` @ `1c325b2`, `causal-conv1d` @ `cd81f04`) | Las cinco comprobaciones de entorno del `inspect` del runner y el smoke de una sola tarjeta dieron todos `passed`; la compilación de causal-conv1d usó un parche temporal no enviado upstream; los demás proyectos aún requieren su propia verificación |

Estado de ingeniería: `ruff`, `mypy`, la validación de contratos y `pytest` están todos en verde (más de 540 casos, 90 % de cobertura de ramas);
la CI cubre Python 3.11 / 3.12 / 3.13 × Windows / Linux / macOS, además de un job de runner con Python 3.10.

## Limitaciones conocidas

- **No ofrece conclusiones de compatibilidad**. Todas las salidas se limitan a avisos de riesgo estático y sugerencias de revisión manual; "verificado en entorno MetaX" debe estar ligado a un commit concreto,
  haberse ejecutado en una GPU MetaX controlada con resultado `verified`, y no tener más de 30 días.
- **La precisión de las reglas aún no se ha medido estadísticamente sobre proyectos reales a gran escala**. Los ejemplos positivos y negativos provienen de fixtures controlados y se han revisado en repositorios públicos (0 falsos positivos);
  las tasas sistemáticas de falsos positivos y falsos negativos requieren más proyectos reales, ver [guía de reglas](docs/rules.md).
- **Los resultados de la verificación en hardware real tienen 30 días de validez**; al expirar, el estado del informe pasa a `stale` y hay que volver a subirlo.
- **Límites del MVP**: no se admiten repositorios privados, no se modifica el código fuente automáticamente, no hay programación de GPU en la nube, no hay sistema de usuarios ni puntuaciones de compatibilidad porcentuales.

> Los informes de ejemplo de proyectos públicos están en [examples/reports](examples/reports): `pytorch-extension-cpp` pasa todo (4 notas),
> `nvidia-apex` (12 bloqueos) y `bitsandbytes` (7 bloqueos) están en estado de bloqueo, y `causal-conv1d` conserva las dos versiones, antes y después de la corrección.
> Están juntos para mostrar que los informes realmente pueden dar luz verde, y también luz roja. El flujo de verificación remota se describe en
> [examples/verification/README.md](examples/verification/README.md).

## Instalación y puesta en marcha

Los usuarios normales solo tienen que instalar el paquete de publicación con interfaz web incluida: no necesitan Node.js, ni instalar PyTorch ni controladores de GPU;
en las tres plataformas hace falta tener preinstalados **Python 3.11+ (con pip/venv) y Git**; la primera instalación descarga por defecto las dependencias de Python desde internet.

| Plataforma | Paquete | Tras descomprimir por completo, ejecutar en el directorio del paquete |
| --- | --- | --- |
| Windows 10/11 | `mxready-1.0.1-windows.zip` | PowerShell: `.\install.ps1` y luego `.\start.ps1` |
| Linux | `mxready-1.0.1-linux.zip` | `bash install.sh` y luego `bash start.sh` |
| macOS (Apple Silicon / Intel) | `mxready-1.0.1-macos.zip` | `bash install.sh` y luego `bash start.sh` |
| Si gestionas tu propio entorno Python | `mxready` en PyPI | `python -m pip install mxready` y luego `mxready-serve` |
| Si ya tienes un entorno Python | `mxready-1.0.1-py3-none-any.whl` | En un venv dedicado, `python -m pip install <ruta_del_wheel>` y luego `mxready-serve` |

Tras el arranque abre <http://127.0.0.1:8000>; para detener el servicio pulsa `Ctrl+C` en la terminal. El ZIP es un paquete de instalación de una aplicación Python:
no incluye Python/Git, ni es un ejecutable nativo, un DMG o un instalador del gestor de paquetes del sistema. Los adjuntos publicados están en
[GitHub Releases](https://github.com/shuljyli/MXReady/releases); la preparación sin conexión, la verificación de resúmenes, la actualización,
la desinstalación y la solución de problemas en Windows se describen en [plan de instalación y publicación](docs/installation.md).

Para que los mantenedores construyan los paquetes: instala las dependencias de desarrollo y ejecuta `make release` (Windows: `.\scripts\make.ps1 release`);
los artefactos quedan en `dist/`, que Git ignora. El despliegue del servidor (bare metal / systemd / Docker / nginx) y las opciones de configuración `MXREADY_*`
están en [documentación de despliegue](docs/deployment.md) y en [.env.example](.env.example).

### Desarrollo desde el código fuente

Requisitos: Python 3.11+, Git, Node.js 22+ (solo hace falta para desarrollar o construir el frontend).

```bash
make install                # Crea .venv, instala dependencias de desarrollo, npm ci (Windows: .\scripts\make.ps1 install)
bash ./scripts/dev.sh       # Arranca frontend y backend a la vez (Windows: .\scripts\dev.ps1)
```

`dev.sh` / `dev.ps1` arrancan a la vez el frontend <http://localhost:5173> (con proxy `/api` al backend) y el backend
<http://127.0.0.1:8000> (con recarga en caliente `--reload`). En modo desarrollo abre el 5173; cuando ya existe
`frontend/dist`, el backend sirve la interfaz completa, la documentación de la API está en `/docs` y el manual de la API en chino está en [docs/api.md](docs/api.md).

Puntos de entrada de comandos unificados (`install` / `dev` / `frontend` / `test` / `lint` / `typecheck` / `build` / `release` / `clean`):

| Objetivo | Windows (PowerShell) | Linux / macOS | Función |
| --- | --- | --- | --- |
| Instalar dependencias | `.\scripts\make.ps1 install` | `make install` | venv + dependencias del backend + `npm ci` |
| Arrancar backend | `.\scripts\make.ps1 dev` | `make dev` | uvicorn `--reload`, puerto 8000 |
| Arrancar frontend | `.\scripts\make.ps1 frontend` | `make frontend` | Vite dev, puerto 5173 |
| Ejecutar pruebas | `.\scripts\make.ps1 test` | `make test` | pytest del backend (con umbral de cobertura) |
| Comprobación de código | `.\scripts\make.ps1 lint` | `make lint` | ruff sobre src / scripts / tests / packaging |
| Comprobación de tipos | `.\scripts\make.ps1 typecheck` | `make typecheck` | mypy sobre src / scripts |
| Construir frontend | `.\scripts\make.ps1 build` | `make build` | `npm run build` produce `frontend/dist` |
| Generar paquetes | `.\scripts\make.ps1 release` | `make release` | web + wheel/sdist + ZIP para tres plataformas, en `dist/` |
| Limpiar | `.\scripts\make.ps1 clean` | `make clean` | Elimina `.pytest-temp` |

## Herramientas de línea de comandos

El uso detallado y las convenciones de códigos de salida de `mxready-scan` (directorio local), `mxready-scan-public` (evidencia de repositorios públicos), `mxready-build-bundle` (paquete de verificación),
`mxready-scan-batch` (evaluación por lotes) y `mxready-mcp` (para agentes de codificación) están en
[Uso de la línea de comandos](docs/cli.md). Todos los CLI analizan en modo de solo lectura y no ejecutan el código analizado.

## Significado de los estados

| Estado | Significado |
| --- | --- |
| `passed` | No se activaron bloqueos ni avisos; aún requiere verificación en hardware real |
| `warnings` | Hay riesgos de migración que requieren revisión manual |
| `blocked` | Hay bloqueos que deberían resolverse antes de solicitar capacidad de cómputo remota |
| `not-run` | Aún no se han subido resultados de verificación del entorno MetaX |
| `verified` | Las comprobaciones de dispositivo `mx-smi` y PyTorch del mismo commit pasaron, todas las comprobaciones de entorno tuvieron éxito y el resultado no tiene más de 30 días; no equivale a la certificación completa del proyecto |
| `failed` | El comando de verificación falló |
| `stale` | El resultado de verificación tiene más de 30 días y debe volver a ejecutarse |

A propósito, los informes no ofrecen puntuaciones de compatibilidad porcentuales, porque el número de reglas activadas no representa la probabilidad de compatibilidad de un proyecto.

## Pruebas

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

Los scripts de pruebas de carga (locust, con Git simulado local, sin depender de la red pública) están en [tests/load/](tests/load/).

## Navegación de documentación

| Documento | Contenido |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | Jerarquía de directorios, direcciones de dependencias, ciclo de vida de las tareas y convenciones de recursos del paquete |
| [docs/deployment.md](docs/deployment.md) | Despliegue en producción: bare metal / systemd / Docker / nginx / copias de seguridad / registros / opciones de configuración |
| [docs/api.md](docs/api.md) | Manual de API en chino (con ejemplos curl) |
| [docs/cli.md](docs/cli.md) | Uso detallado de las herramientas de línea de comandos y de MCP |
| [docs/installation.md](docs/installation.md) | Paquetes para tres plataformas, preparación sin conexión, actualización, construcción de publicaciones y solución de problemas en Windows |
| [docs/report-workflow.md](docs/report-workflow.md) | Hallazgos completos, alcance del escaneo, comparación de informes, SARIF e integración con CI |
| [docs/security.md](docs/security.md) | Modelo de seguridad |
| [docs/rules.md](docs/rules.md) | Guía de desarrollo de reglas |
| [docs/runner.md](docs/runner.md) | Guía del runner de verificación remota |
| [docs/migration-case-2026-11.md](docs/migration-case-2026-11.md) | Caso con repositorio real: diagnóstico de bloqueos, corrección y reverificación en hardware real |
| [examples/verification/README.md](examples/verification/README.md) | SOP de entrega de la verificación en hardware real |
| [CHANGELOG.md](CHANGELOG.md) | Registro de cambios por versión |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Proceso de contribución y controles de calidad |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Código de conducta de la comunidad |

## Límites de seguridad

- Solo se permiten repositorios HTTPS públicos de `github.com` y `gitee.com`; Git no lee credenciales, no descarga LFS ni inicializa submódulos, y la descarga tiene límites de tiempo y de tamaño/número de elementos;
- El escaneo web nunca ejecuta código del repositorio; los resultados de verificación tienen un tope de 1 MiB y quedan ligados al commit analizado;
- El runner no usa `sudo` ni instala software; los comandos se ejecutan con `shell=False` y los comandos del proyecto exigen confirmación humana antes de ejecutarse;
- Antes de un despliegue público deben activarse el limitador de peticiones y los límites de tamaño del cuerpo de las solicitudes.

Antes de desplegar, lee por completo el [modelo de seguridad](docs/security.md) y la [guía del runner](docs/runner.md).

## Cómo contribuir

Las reglas nuevas deben incluir a la vez ejemplos positivos, ejemplos negativos similares y documentación técnica de primera fuente. Por favor, lee:

- [Guía de contribución](CONTRIBUTING.md)
- [Guía de desarrollo de reglas](docs/rules.md)
- [Guía de verificación remota](docs/runner.md)
- [Modelo de seguridad](docs/security.md)

## Hoja de ruta MVP

1. Generar informes reproducibles con tres proyectos públicos de extensiones CUDA y calibrar la precisión de las reglas;
2. Completar en más proyectos públicos verificaciones anonimizadas en hardware real del mismo commit (ya completados `pytorch/extension-cpp` @ `1c325b2` y `causal-conv1d` @ `cd81f04`);
3. Enviar a un proyecto upstream un PR de migración acotado y fácil de revisar;
4. Ampliar las reglas y las plantillas mínimas de verificación según la retroalimentación de adaptación real.

## Contribuidor principal

- **shuli-黍黎** — Iniciador del proyecto y desarrollador principal.

## Licencia

Este proyecto se distribuye bajo la [Licencia Apache 2.0](LICENSE). Puedes usarlo, modificarlo y distribuirlo respetando los términos de la licencia.

## Contacto

Para preguntas, sugerencias y colaboración, te invitamos a abrir un Issue en GitHub o escribir por correo a:

- shuli_ljy@outlook.com
- 2199553510@qq.com
