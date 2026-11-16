# MXReady

[![CI](https://github.com/shuljyli/MXReady/actions/workflows/ci.yml/badge.svg)](https://github.com/shuljyli/MXReady/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-1.0.1-blue)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)

[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | **Português** | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

Você tem código PyTorch rodando em placas NVIDIA e quer levá-lo para uma GPU MetaX. Ainda não sabe o que vai quebrar.

O MXReady lê o código primeiro (somente leitura, sem executá-lo) e lista os pontos que provavelmente vão dar problema: onde o compilador da NVIDIA é chamado diretamente, onde se assume "um grupo de 32 threads" fixo (na MetaX são 64), onde se usa assembly inline exclusivo da NVIDIA, onde há dependência de bibliotecas que não rodam na nova plataforma. Cada achado informa qual arquivo, qual linha, por que há problema e o que mudar.

Ele não reescreve o seu código nem fornece números como "porcentagem de compatibilidade" — a quantidade de regras atingidas não permite inferir a probabilidade de compatibilidade. Uma verificação estática limpa significa apenas que nada óbvio foi encontrado; a conclusão real precisa ser obtida rodando na máquina da MetaX.

> O MXReady é um protótipo da comunidade, não uma certificação oficial de compatibilidade da MetaX. Uma verificação estática aprovada não significa que o projeto já é compatível com MXMACA; a conclusão final ainda precisa ser validada no mesmo commit e em um ambiente controlado de GPU MetaX.

## O que ele faz

- Recebe repositórios HTTPS públicos do GitHub e do Gitee, com opção de branch, tag ou commit de 40 caracteres;
- Varre arquivos de texto em Python, C/C++, CUDA, CMake, Shell, TOML, YAML etc.;
- Inclui **35 regras** (`MXR-*`); cada resultado traz arquivo, linha, código atingido, recomendação e referência de fonte primária;
- Ocorrências em testes, exemplos e documentação contam apenas como avisos: continuam listadas no relatório, mas não fazem o projeto inteiro ser considerado bloqueado;
- Gera relatórios em JSON, Markdown, badge SVG e HTML imprimível (impressão do navegador para PDF), além de um pacote de verificação remota que depende apenas da biblioteca padrão;
- Conclusões estáticas e conclusões de verificação em hardware real são exibidas separadamente, sem se misturar;
- Oferece um CLI de diretório local somente leitura, útil para regressão offline e geração de relatórios de exemplo;
- Opcional `mxready-mcp`: expõe varredura, status de tarefas, relatórios e consulta de regras como 5 ferramentas MCP para agentes de codificação compatíveis com o Model Context Protocol;
- A interface React (SPA) e o serviço FastAPI podem ser empacotados em uma única unidade de implantação.

A interface web oferece as páginas "check-up do código-fonte", "varredura em lote", "histórico de varreduras", "progresso da migração", "biblioteca de regras", "integração MCP" e "uso por linha de comando"; os relatórios oferecem navegação por arquivos prioritários, busca paginada, comparação e compartilhamento, checklist de revisão manual e exportação/impressão em HTML. MCP e Web, ao lerem relatórios um do outro, precisam compartilhar explicitamente o mesmo diretório de dados local.

O MVP não inclui repositórios privados, modificação automática de código-fonte, orquestração Docker para servidores GPU remotos, agendamento de GPU em nuvem, sistema de usuários nem "pontuação de compatibilidade" em porcentagem.

## O que foi encontrado em projetos reais

Resultados do check-up do [`NVIDIA/apex`](https://github.com/NVIDIA/apex) no commit `575968bc1f9127ccd61003a681472a83af4ff1a1`:
**12 bloqueios · 65 avisos · 140 alertas**. Relatório completo em [examples/reports/nvidia-apex.md](examples/reports/nvidia-apex.md).

Os quatro mais representativos dos 12 bloqueios:

| Local | Ocorrência | Por que quebra na MetaX |
| --- | --- | --- |
| `csrc/welford.cu:36` | `#define WARP_SIZE 32` | Largura da warp fixada em 32; na MetaX é 64 |
| `nhwc_batch_norm_kernel.h:1245` | `int lane_id = threadIdx.x & 31;` | A lane 0 e a lane 32 são calculadas como a mesma lane |
| `group_norm_nhwc.h:40` | `asm volatile("red.release.gpu.global.add.s32 …")` | PTX inline amarrado ao backend da NVIDIA |
| `setup.py:65` | `subprocess.check_output([cuda_dir + "/bin/nvcc", "-V"])` | Chama `nvcc` diretamente para detectar a versão; esse comando não existe no ambiente MetaX |

Dos quatro, dois **compilam sem erro**, mas o cálculo de lane e a largura da warp produzem resultados errados em uma wave de largura 64, e os testes também podem não cobrir esses casos; os outros dois nem compilam na MetaX. Os dois tipos de problema podem atrasar uma migração em semanas.

Outros dois casos, em commits fixos, completam as evidências dos dois lados do ciclo de bloqueio e correção:

- [`bitsandbytes`](https://github.com/bitsandbytes-foundation/bitsandbytes) (`a616886`): 27 achados, 7 bloqueios;
  relatório em [examples/reports/bitsandbytes.md](examples/reports/bitsandbytes.md).
- [`causal-conv1d`](https://github.com/Dao-AILab/causal-conv1d) (`cd81f04`): após as correções descritas no relatório, o número de achados diminuiu e a verificação em hardware real na MetaX C500 ficou toda `passed`; detalhes em [registro do caso de migração](docs/migration-case-2026-11.md).

## Arquitetura

```text
React/Vite UI
      │ /api
      ▼
FastAPI ── SQLite: fila de tarefas persistente e relatórios
   │
   ├─ claim atômico / heartbeat de lease ── git fetch restrito ── índice de arquivos somente leitura ── motor de regras YAML
   ├─ relatórios JSON / Markdown / SVG
   └─ ZIP de verificação ◀── roda no host MetaX controlado pelo usuário ── result.json
```

O serviço web nunca importa, instala, compila nem executa código do repositório varrido. O runner remoto só roda em máquinas controladas pelo usuário e exige confirmação humana antes de executar comandos do projeto.

O código Python fica unificado em `src/`; as regras padrão e o schema de verificação são publicados junto com o pacote de instalação. Convenções de diretório, fila de tarefas e instruções de upgrade: [guia de arquitetura](docs/architecture.md). Após alterar modelos, use `make contracts` para sincronizar os contratos de interface gerados.

## Matriz de funcionalidades

| Capacidade | Status | Como é verificado |
| --- | --- | --- |
| Varredura estática de repositórios públicos (GitHub / Gitee, com opção de branch, tag ou commit de 40 caracteres) | Disponível | Testes de ponta a ponta + relatórios de exemplo |
| 35 regras `MXR-*` | Disponível | Cada regra inclui fixtures positivos e negativos semelhantes |
| Relatórios: JSON / Markdown / HTML / badge SVG | Disponível | Testes de contrato + `generate_contracts.py --check` |
| Painel de progresso da migração (agregação entre repositórios, tendência de bloqueios) | Disponível | Testes de agregação do backend + Vitest |
| Pacote de verificação remota e runner só com biblioteca padrão | Disponível | Regressão do instalador + testes de fronteiras de segurança |
| ZIPs de instalação para três plataformas e wheel/sdist com interface web | Disponível | O workflow de release instala e inicia de fato em Windows / Linux / macOS |
| Interface React (SPA) | Disponível | Vitest + modo strict do TypeScript |
| Avaliação em lote (`mxready-scan-batch`) | Disponível | Regressão de CLI |
| Ferramentas MCP (`mxready-mcp`, requer `.[mcp]`) | Disponível | Testes de backend + handshake real de stdio |
| Verificação em GPU MetaX real | Concluídas duas execuções anonimizadas (MetaX C500: `pytorch/extension-cpp` @ `1c325b2`, `causal-conv1d` @ `cd81f04`) | As cinco verificações de ambiente do `inspect` do runner e o smoke de GPU única ficaram todas `passed`; o build do causal-conv1d usou um patch temporário não enviado upstream, e os demais projetos ainda precisam de verificação própria |

Estado de engenharia: `ruff`, `mypy`, validação de contratos e `pytest` todos verdes (mais de 540 casos de teste, 90% de cobertura de branches);
a CI cobre Python 3.11 / 3.12 / 3.13 × Windows / Linux / macOS, mais um job do runner em Python 3.10.

## Limitações conhecidas

- **Não oferece conclusão de compatibilidade**. Toda saída se limita a alertas de risco estático e recomendações de revisão manual; "verificado em ambiente MetaX" precisa estar vinculado a um commit específico, com resultado `verified` obtido em uma GPU MetaX controlada, com no máximo 30 dias.
- **A precisão das regras ainda não foi medida estatisticamente em projetos reais em larga escala**. Os casos positivos e negativos vêm de fixtures controlados e foram conferidos em repositórios públicos (0 falsos positivos); as taxas sistemáticas de falso positivo e falso negativo ainda precisam de mais estatísticas de projetos reais — ver [guia de regras](docs/rules.md).
- **Resultados de verificação em hardware real têm validade de 30 dias**; após expirar, o status do relatório passa a `stale` e é preciso reenviar.
- **Fronteiras do MVP**: sem repositórios privados, sem modificação automática de código-fonte, sem agendamento de GPU em nuvem, sem sistema de usuários, sem pontuação de compatibilidade em porcentagem.

> Relatórios de exemplo de projetos públicos: [examples/reports](examples/reports) — `pytorch-extension-cpp` passa em tudo (4 alertas);
> `nvidia-apex` (12 bloqueios) e `bitsandbytes` (7 bloqueios) ficam em estado de bloqueio, e `causal-conv1d` mantém as duas versões, antes/depois da correção.
> Estão juntos para mostrar que o relatório realmente reprova quando precisa e realmente aprova quando pode. Fluxo de verificação remota:
> [examples/verification/README.md](examples/verification/README.md).

## Instalação e inicialização

Usuários finais só precisam instalar o pacote de release com interface web; não é necessário Node.js nem instalar PyTorch ou drivers de GPU;
nas três plataformas é preciso ter **Python 3.11+ (com pip/venv) e Git** pré-instalados, e a primeira instalação baixa as dependências Python da internet por padrão.

| Plataforma | Pacote | Após extrair completamente, execute no diretório do pacote |
| --- | --- | --- |
| Windows 10/11 | `mxready-1.0.1-windows.zip` | PowerShell: `.\install.ps1`, depois `.\start.ps1` |
| Linux | `mxready-1.0.1-linux.zip` | `bash install.sh`, depois `bash start.sh` |
| macOS (Apple Silicon / Intel) | `mxready-1.0.1-macos.zip` | `bash install.sh`, depois `bash start.sh` |
| Gerencia o próprio ambiente Python | `mxready` no PyPI | `python -m pip install mxready`, depois `mxready-serve` |
| Já tem ambiente Python | `mxready-1.0.1-py3-none-any.whl` | em um venv dedicado: `python -m pip install <caminho-do-wheel>`, depois `mxready-serve` |

Após iniciar, abra <http://127.0.0.1:8000> e pressione `Ctrl+C` no terminal para parar o serviço. O ZIP é um pacote de instalação de aplicação Python,
não inclui Python/Git e não é um EXE, DMG nativo nem instalador de gerenciador de pacotes do sistema. Os anexos publicados:
[GitHub Releases](https://github.com/shuljyli/MXReady/releases); preparação offline, verificação de checksum, upgrade,
desinstalação e solução de problemas no Windows: [guia de instalação e release](docs/installation.md).

Para os mantenedores construírem os pacotes: instale as dependências de desenvolvimento e execute `make release` (Windows: `.\scripts\make.ps1 release`);
os artefatos ficam em `dist/`, ignorado pelo Git. Implantação de servidor (bare metal / systemd / Docker / nginx) e as opções de configuração `MXREADY_*`:
[guia de implantação](docs/deployment.md) e [.env.example](.env.example).

### Desenvolvimento a partir do código-fonte

Requisitos: Python 3.11+, Git, Node.js 22+ (apenas para desenvolver/compilar o frontend).

```bash
make install                # cria .venv, instala dependências de desenvolvimento, npm ci (Windows: .\scripts\make.ps1 install)
bash ./scripts/dev.sh       # sobe frontend e backend de uma vez (Windows: .\scripts\dev.ps1)
```

O `dev.sh` / `dev.ps1` sobe ao mesmo tempo o frontend <http://localhost:5173> (com proxy de `/api` para o backend) e o backend
<http://127.0.0.1:8000> (com hot reload via `--reload`). Em modo de desenvolvimento, use a porta 5173; o backend serve a interface
completa quando já existe `frontend/dist`, a documentação da API fica em `/docs` e o manual de interfaces em chinês está em [docs/api.md](docs/api.md).

Entrada unificada de comandos (`install` / `dev` / `frontend` / `test` / `lint` / `typecheck` / `build` / `release` / `clean`):

| Alvo | Windows (PowerShell) | Linux / macOS | Função |
| --- | --- | --- | --- |
| Instalar dependências | `.\scripts\make.ps1 install` | `make install` | venv + dependências do backend + `npm ci` |
| Subir o backend | `.\scripts\make.ps1 dev` | `make dev` | uvicorn `--reload`, porta 8000 |
| Subir o frontend | `.\scripts\make.ps1 frontend` | `make frontend` | Vite dev, porta 5173 |
| Rodar testes | `.\scripts\make.ps1 test` | `make test` | pytest do backend (com limite de cobertura) |
| Checagem de código | `.\scripts\make.ps1 lint` | `make lint` | ruff em src / scripts / tests / packaging |
| Checagem de tipos | `.\scripts\make.ps1 typecheck` | `make typecheck` | mypy em src / scripts |
| Compilar o frontend | `.\scripts\make.ps1 build` | `make build` | `npm run build` gerando `frontend/dist` |
| Gerar pacotes de instalação | `.\scripts\make.ps1 release` | `make release` | web + wheel/sdist + ZIPs das três plataformas, em `dist/` |
| Limpar | `.\scripts\make.ps1 clean` | `make clean` | remove `.pytest-temp` |

## Ferramentas de linha de comando

Uso detalhado e convenções de código de saída de `mxready-scan` (diretório local), `mxready-scan-public` (evidência de repositórios públicos), `mxready-build-bundle` (pacote de verificação),
`mxready-scan-batch` (avaliação em lote) e `mxready-mcp` (para agentes de codificação): [uso por linha de comando](docs/cli.md). Todos os CLIs fazem análise somente leitura e não executam o código varrido.

## Significado dos status

| Status | Significado |
| --- | --- |
| `passed` | Nenhum bloqueio ou aviso atingido; ainda exige verificação em hardware real |
| `warnings` | Há riscos de migração que precisam de revisão manual |
| `blocked` | Há bloqueios que devem ser tratados antes de solicitar capacidade de computação remota |
| `not-run` | Resultados da verificação em ambiente MetaX ainda não foram enviados |
| `verified` | As verificações de dispositivo `mx-smi` e PyTorch passaram no mesmo commit, todas as verificações de ambiente tiveram sucesso e o resultado tem no máximo 30 dias; não equivale à certificação completa do projeto |
| `failed` | Os comandos de verificação falharam |
| `stale` | O resultado de verificação tem mais de 30 dias e precisa ser reexecutado |

O relatório deliberadamente não oferece pontuação de compatibilidade em porcentagem, porque o número de regras atingidas não representa a probabilidade de compatibilidade do projeto.

## Testes

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

Scripts de testes de carga (locust, com Git mock local, sem depender da internet): [tests/load/](tests/load/).

## Navegação pela documentação

| Documento | Conteúdo |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | Hierarquia de diretórios, direções de dependência, ciclo de vida das tarefas e convenções de recursos do pacote |
| [docs/deployment.md](docs/deployment.md) | Implantação em produção: bare metal / systemd / Docker / nginx / backup / logs / opções de configuração |
| [docs/api.md](docs/api.md) | Manual da API em chinês (com exemplos em curl) |
| [docs/cli.md](docs/cli.md) | Uso detalhado das ferramentas de linha de comando e do MCP |
| [docs/installation.md](docs/installation.md) | Pacotes de instalação das três plataformas, preparação offline, upgrade, build de release e solução de problemas no Windows |
| [docs/report-workflow.md](docs/report-workflow.md) | Ocorrências completas, escopo da varredura, comparação de relatórios, SARIF e integração com CI |
| [docs/security.md](docs/security.md) | Modelo de segurança |
| [docs/rules.md](docs/rules.md) | Guia de desenvolvimento de regras |
| [docs/runner.md](docs/runner.md) | Guia do runner de verificação remota |
| [docs/migration-case-2026-11.md](docs/migration-case-2026-11.md) | Casos em repositórios reais: diagnóstico de bloqueios, correção e reverificação em hardware real |
| [examples/verification/README.md](examples/verification/README.md) | SOP de transferência da verificação em hardware real |
| [CHANGELOG.md](CHANGELOG.md) | Histórico de versões |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Fluxo de contribuição e portões de qualidade |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Código de conduta da comunidade |

## Fronteiras de segurança

- São permitidos apenas repositórios HTTPS públicos em `github.com` e `gitee.com`; o Git não lê credenciais, não baixa LFS e não inicializa submódulos; a busca tem timeout e limites de tamanho/quantidade de itens;
- A varredura web nunca executa código do repositório; resultados de verificação têm limite de 1 MiB e ficam vinculados ao commit varrido;
- O runner não usa `sudo` nem instala software; os comandos são executados com `shell=False` e exigem confirmação humana antes de rodar comandos do projeto;
- Antes de uma implantação pública, ative o rate limiting e o limite de tamanho do corpo das requisições.

Antes de implantar, leia integralmente o [modelo de segurança](docs/security.md) e o [guia do runner](docs/runner.md).

## Como contribuir

Regras novas devem incluir exemplos positivos, exemplos negativos semelhantes e material técnico de fonte primária. Leia:

- [Guia de contribuição](CONTRIBUTING.md)
- [Guia de desenvolvimento de regras](docs/rules.md)
- [Guia de verificação remota](docs/runner.md)
- [Modelo de segurança](docs/security.md)

## Roadmap do MVP

1. Gerar relatórios reproduzíveis em três projetos públicos de extensões CUDA e calibrar a precisão das regras;
2. Concluir verificações anonimizadas em hardware real com o mesmo commit em mais projetos públicos (concluído para `pytorch/extension-cpp` @ `1c325b2` e `causal-conv1d` @ `cd81f04`);
3. Enviar a um projeto upstream um PR de migração pequeno e fácil de revisar;
4. Expandir as regras e o template mínimo de verificação com base no feedback real de adaptação.

## Principais colaboradores

- **shuli-黍黎** — idealizador e principal desenvolvedor do projeto.

## Licença

Este projeto é licenciado sob a [Apache License 2.0](LICENSE). Você pode usar, modificar e distribuir desde que respeite os termos da licença.

## Contato

Problemas, sugestões e colaborações: abra uma GitHub Issue ou envie um e-mail:

- shuli_ljy@outlook.com
- 2199553510@qq.com
