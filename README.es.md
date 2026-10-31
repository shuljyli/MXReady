# MXReady

[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | **Español** | [Português](README.pt-BR.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

Tienes código de PyTorch funcionando en tarjetas NVIDIA y quieres pasarlo a una GPU MetaX. Todavía no sabes qué se va a romper.

MXReady lee el código sin ejecutarlo y te muestra los puntos que probablemente den problemas:

- donde se llama directamente al compilador de NVIDIA;
- donde se da por hecho que un grupo tiene 32 hilos (en MetaX son 64);
- donde se usa ensamblador en línea exclusivo de NVIDIA;
- donde se depende de una librería que no existe en la tarjeta nueva.

Cada hallazgo indica el archivo, la línea, por qué importa y qué cambiar.

## Cómo se usa

Descarga el ZIP de tu sistema, descomprímelo y ejecuta el instalador.

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

Luego abre <http://127.0.0.1:8000> y pega la dirección del repositorio.

También funciona desde la terminal:

```bash
mxready-scan ./my-repo \
  --repo-url https://github.com/example/my-repo \
  --commit <commit de 40 caracteres> \
  --output reports
```

## Lo que no hace

- No reescribe tu código.
- No inventa un "porcentaje de compatibilidad". Cuántas reglas activa un proyecto no dice nada sobre si va a funcionar.
- Una revisión estática limpia solo significa que no se encontró nada evidente. La respuesta real sale de ejecutar el mismo commit en una máquina MetaX.

## Más información

- [Documentación completa (chino)](README.md)
- [Full documentation (English)](README.en.md)
- [Lista de reglas](docs/rules.md)
- [Arquitectura](docs/architecture.md)

Licencia [Apache-2.0](LICENSE).
