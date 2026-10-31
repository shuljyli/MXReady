# MXReady

[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | **Português** | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

Você tem código PyTorch rodando em placas NVIDIA e quer levá-lo para uma GPU MetaX. Ainda não sabe o que vai quebrar.

O MXReady lê o código sem executá-lo e lista os pontos que provavelmente vão dar problema:

- onde o compilador da NVIDIA é chamado diretamente;
- onde se assume um grupo de 32 threads (na MetaX são 64);
- onde se usa assembly inline exclusivo da NVIDIA;
- onde há dependência de uma biblioteca que não existe na placa nova.

Cada achado informa o arquivo, a linha, por que aquilo importa e o que mudar.

## Como usar

Baixe o ZIP do seu sistema, descompacte e rode o instalador.

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

Depois abra <http://127.0.0.1:8000> e cole o endereço do repositório.

Também funciona pelo terminal:

```bash
mxready-scan ./my-repo \
  --repo-url https://github.com/example/my-repo \
  --commit <commit de 40 caracteres> \
  --output reports
```

## O que ele não faz

- Não reescreve o seu código.
- Não inventa uma "porcentagem de compatibilidade". Quantas regras um projeto dispara não diz nada sobre ele funcionar.
- Uma verificação estática limpa significa apenas que nada óbvio foi encontrado. A resposta real vem de rodar o mesmo commit numa máquina MetaX.

## Mais informações

- [Documentação completa (chinês)](README.md)
- [Full documentation (English)](README.en.md)
- [Lista de regras](docs/rules.md)
- [Arquitetura](docs/architecture.md)

Licença [Apache-2.0](LICENSE).
