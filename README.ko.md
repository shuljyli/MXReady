# MXReady

[![CI](https://github.com/shuljyli/MXReady/actions/workflows/ci.yml/badge.svg)](https://github.com/shuljyli/MXReady/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-1.0.1-blue)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)

[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md) | **한국어** | [Español](README.es.md) | [Português](README.pt-BR.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

NVIDIA GPU에서 돌아가는 PyTorch 코드를 MetaX(沐曦) GPU로 옮기려고 하는데, 어디서 문제가 생길지 모릅니다.

MXReady는 코드를 한 번 읽어 봅니다(읽기만 하고, 실행하지 않습니다). 문제가 될 만한 곳을 목록으로 뽑아 줍니다: 어디서 NVIDIA 컴파일러를 직접 호출하는지, 어디서 "스레드 32개 한 그룹"으로 고정했는지(MetaX는 64입니다), 어디서 NVIDIA 전용 인라인 어셈블리를 넣었는지, 어디서 실행되지 않는 라이브러리에 의존하는지. 각 항목마다 어느 파일의 몇 번째 줄인지, 왜 문제인지, 어떻게 고치면 되는지 명확히 알려 줍니다.

코드를 대신 고쳐 주지도 않고, "호환성 퍼센트" 같은 숫자도 주지 않습니다—규칙에 몇 개 걸렸다고 호환 확률을 도출할 수는 없습니다. 정적 검사를 통과했다는 것은 뚜렷한 문제를 찾지 못했다는 뜻일 뿐이며, 진짜 결론은 MetaX 기계에서 실행해 봐야 나옵니다.

> MXReady는 커뮤니티 프로토타입이며 MetaX 공식 호환성 인증이 아닙니다. 정적 검사를 통과해도 프로젝트가 MXMACA와 호환된다는 뜻은 아니며, 최종 결론은 동일한 커밋과 통제된 MetaX GPU 환경에서 검증해야 합니다.

## 무엇을 할 수 있나요

- GitHub, Gitee의 공개 HTTPS 저장소를 받으며, 브랜치·태그 또는 40자리 커밋을 지정할 수 있습니다;
- Python, C/C++, CUDA, CMake, Shell, TOML, YAML 등의 텍스트 파일을 스캔합니다;
- **35개 규칙**(`MXR-*`)이 내장되어 있으며, 각 결과에는 파일, 행 번호, 매칭된 코드, 제안, 권위 있는 참고 자료가 함께 들어 있습니다;
- 테스트, 예제, 문서에서 나온 매칭은 힌트로만 취급합니다: 보고서에는 여전히 기록되지만 전체 프로젝트가 차단 판정을 받지는 않습니다;
- JSON, Markdown, SVG 배지, 인쇄 가능한 HTML 보고서(브라우저 인쇄로 PDF 변환), 그리고 표준 라이브러리에만 의존하는 원격 검증 번들을 출력합니다;
- 정적 결론과 실기 검증 결론을 분리해서 표시하며, 섞지 않습니다;
- 읽기 전용 로컬 디렉터리 CLI를 제공하여 오프라인 회귀와 예제 보고서 생성에 편리합니다;
- 선택적인 `mxready-mcp`: 스캔, 작업 상태, 보고서, 규칙 조회를 5개 MCP 도구로 노출하여 Model Context Protocol을 지원하는 코딩 Agent가 호출할 수 있게 합니다;
- React 단일 페이지 인터페이스와 FastAPI 서비스를 하나의 배포 단위로 패키징할 수 있습니다.

웹 인터페이스는 "소스 코드 검진", "일괄 스캔", "스캔 기록", "마이그레이션 진행 상황", "규칙 라이브러리", "MCP 연동", "명령줄 사용" 페이지를 제공합니다.
보고서는 우선 파일 위치 지정, 페이지 분할 검색, 비교 공유, 인적 검토 체크리스트, HTML 인쇄 내보내기를 지원합니다. MCP와 Web이 서로의 보고서를 읽을 때는 명시적으로 동일한 로컬 데이터 디렉터리를 공유해야 합니다.

MVP에는 비공개 저장소, 소스 코드 자동 수정, 원격 GPU 서버의 Docker 오케스트레이션, 클라우드 GPU 스케줄링, 사용자 시스템, 백분율 "호환성 점수"가 포함되지 않습니다.

## 실제 프로젝트에서 발견한 것

[`NVIDIA/apex`](https://github.com/NVIDIA/apex)를 커밋 `575968bc1f9127ccd61003a681472a83af4ff1a1`에서 검진한 결과:
**차단 12 · 경고 65 · 힌트 140**. 전체 보고서는 [examples/reports/nvidia-apex.md](examples/reports/nvidia-apex.md)를 참조하세요.

12개 차단 중 가장 대표적인 네 가지:

| 위치 | 매칭 | MetaX에서 깨지는 이유 |
| --- | --- | --- |
| `csrc/welford.cu:36` | `#define WARP_SIZE 32` | 워프 크기가 32로 고정되어 있는데, MetaX는 64입니다 |
| `nhwc_batch_norm_kernel.h:1245` | `int lane_id = threadIdx.x & 31;` | lane 0과 lane 32가 같은 lane으로 계산됩니다 |
| `group_norm_nhwc.h:40` | `asm volatile("red.release.gpu.global.add.s32 …")` | 인라인 PTX가 NVIDIA 백엔드에 결합되어 있습니다 |
| `setup.py:65` | `subprocess.check_output([cuda_dir + "/bin/nvcc", "-V"])` | `nvcc`를 직접 호출해 버전을 탐지하는데, MetaX 환경에는 이 명령이 없습니다 |

네 가지 중 두 가지는 **컴파일은 통과하지만**, lane 계산과 워프 크기가 64 너비의 wave에서 잘못된 결과를 계산하며, 테스트가 이를 꼭 커버하는 것도 아닙니다;
나머지 두 가지는 MetaX에서 아예 컴파일되지 않습니다. 이 두 종류의 문제 모두 마이그레이션을 몇 주씩 끌게 만듭니다.

또한 두 개의 고정 커밋 사례가 차단과 수정 루프 양쪽의 증거를 보충합니다:

- [`bitsandbytes`](https://github.com/bitsandbytes-foundation/bitsandbytes)（`a616886`）: 27개 발견, 7개 차단,
  보고서는 [examples/reports/bitsandbytes.md](examples/reports/bitsandbytes.md)를 참조하세요.
- [`causal-conv1d`](https://github.com/Dao-AILab/causal-conv1d)（`cd81f04`）: 보고서대로 수정한 뒤 발견 수가 줄었고,
  MetaX C500에서 실기 검증이 모두 `passed`입니다. 자세한 내용은 [마이그레이션 사례 기록](docs/migration-case-2026-11.md)을 참조하세요.

## 아키텍처

```text
React/Vite UI
      │ /api
      ▼
FastAPI ── SQLite 영속 작업 큐와 보고서
   │
   ├─ 원자적 할당 / 리스 하트비트 ── 제한된 Git 가져오기 ── 읽기 전용 파일 인덱스 ── YAML 규칙 엔진
   ├─ JSON / Markdown / SVG 보고서
   └─ 검증 ZIP ◀── 사용자가 제어하는 MetaX 호스트에서 실행 ── result.json
```

Web 서비스는 스캔 대상 저장소의 코드를 절대 import, 설치, 빌드, 실행하지 않습니다. 원격 runner는 사용자가 제어하는 기기에서만 실행되며, 프로젝트 명령을 실행하기 전에 인적 확인을 요구합니다.

Python 코드는 `src/`에 통합되어 있습니다; 기본 규칙과 검증 schema는 설치 패키지와 함께 배포됩니다. 디렉터리 규약, 작업 큐, 업그레이드 설명은
[아키텍처 설명](docs/architecture.md)을 참조하세요. 모델을 수정한 뒤에는 `make contracts`로 인터페이스 계약을 동기화하세요.

## 기능 매트릭스

| 기능 | 상태 | 검증 방법 |
| --- | --- | --- |
| 공개 저장소 정적 스캔 (GitHub / Gitee, 브랜치·태그 또는 40자리 커밋 지정 가능) | 사용 가능 | 엔드투엔드 테스트 + 예제 보고서 |
| 35개 `MXR-*` 검사 규칙 | 사용 가능 | 각 규칙에 양례와 유사한 반례 픽스처 포함 |
| 보고서 출력: JSON / Markdown / HTML / SVG 배지 | 사용 가능 | 계약 테스트 + `generate_contracts.py --check` |
| 마이그레이션 진행 대시보드(저장소 간 집계, 차단 항목 추이) | 사용 가능 | 백엔드 집계 테스트 + Vitest |
| 원격 검증 번들과 표준 라이브러리 runner | 사용 가능 | 설치 패키지 회귀 + 보안 경계 테스트 |
| 3플랫폼 설치 ZIP과 웹 포함 wheel/sdist | 사용 가능 | 릴리스 워크플로가 Windows / Linux / macOS에 실제로 설치하고 실행함 |
| React 단일 페이지 인터페이스 | 사용 가능 | Vitest + TypeScript 엄격 모드 |
| 일괄 평가(`mxready-scan-batch`) | 사용 가능 | CLI 회귀 |
| MCP 도구(`mxready-mcp`, `.[mcp]` 필요) | 사용 가능 | 백엔드 테스트 + 실제 stdio 핸드셰이크 |
| 실기 MetaX GPU 검증 | 비식별화 검증 두 번 완료(MetaX C500: `pytorch/extension-cpp` @ `1c325b2`, `causal-conv1d` @ `cd81f04`) | runner `inspect`의 다섯 가지 환경 검사와 단일 카드 smoke가 모두 `passed`; causal-conv1d의 빌드에는 업스트림에 커밋되지 않은 임시 패치가 사용되었으며, 다른 프로젝트는 각각 검증이 필요합니다 |

엔지니어링 상태: `ruff`, `mypy`, 계약 검증, `pytest`가 모두 녹색입니다(540여 개 테스트 케이스, 분기 커버리지 90%);
CI는 Python 3.11 / 3.12 / 3.13 × Windows / Linux / macOS를 커버하며, Python 3.10 runner 작업도 따로 있습니다.

## 알려진 제한 사항

- **호환성 결론을 제공하지 않습니다**. 모든 출력은 정적 위험 힌트와 인적 검토 제안까집니다; "MetaX 환경에서 검증됨"은 특정 커밋에 결부되어야 하고,
  통제된 MetaX GPU에서 `verified` 결과를 내야 하며, 30일을 넘지 않아야 합니다.
- **규칙 정확도는 아직 대규모 실제 프로젝트로 통계되지 않았습니다**. 양반례는 통제된 픽스처에서 나왔고 공개 저장소에서 재검토했습니다(오탐 0건);
  체계적인 오탐률과 미탐률은 더 많은 실제 프로젝트 통계가 필요합니다. [규칙 설명](docs/rules.md)을 참조하세요.
- **실기 검증 결과에는 30일 유효기간이 있으며**, 만료되면 보고서 상태가 `stale`로 전환되어 다시 업로드해야 합니다.
- **MVP 범위**: 비공개 저장소 미지원, 소스 코드 자동 수정 없음, 클라우드 GPU 스케줄링 없음, 사용자 시스템 없음, 백분율 호환성 점수 없음.

> 공개 프로젝트 예제 보고서는 [examples/reports](examples/reports)를 참조하세요: `pytorch-extension-cpp`는 모두 통과(4개 힌트),
> `nvidia-apex`(12개 차단)와 `bitsandbytes`(7개 차단)는 차단 상태이며, `causal-conv1d`는 수정 전/후 두 벌을 보관합니다.
> 함께 보여 주는 이유는, 보고서가 정말로 초록색 판정도 내고 정말로 빨간색 판정도 내기 때문입니다. 원격 검증 절차는
> [examples/verification/README.md](examples/verification/README.md)를 참조하세요.

## 설치 및 시작

일반 사용자는 웹이 포함된 릴리스 패키지를 바로 설치하면 되며, Node.js도 PyTorch나 GPU 드라이버도 필요 없습니다;
세 플랫폼 모두 **Python 3.11+(pip/venv 포함)과 Git**을 사전에 설치해야 하며, 최초 설치 시 기본적으로 네트워크에 연결해 Python 의존성을 내려받습니다.

| 플랫폼 | 설치 패키지 | 압축을 완전히 푼 뒤, 패키지 디렉터리에서 실행 |
| --- | --- | --- |
| Windows 10/11 | `mxready-1.0.1-windows.zip` | PowerShell: `.\install.ps1`, 그다음 `.\start.ps1` |
| Linux | `mxready-1.0.1-linux.zip` | `bash install.sh`, 그다음 `bash start.sh` |
| macOS (Apple Silicon / Intel) | `mxready-1.0.1-macos.zip` | `bash install.sh`, 그다음 `bash start.sh` |
| Python 환경을 직접 관리 | PyPI의 `mxready` | `python -m pip install mxready`, 그다음 `mxready-serve` |
| Python 환경 보유 | `mxready-1.0.1-py3-none-any.whl` | 전용 venv에서 `python -m pip install <wheel 경로>`, 그다음 `mxready-serve` |

실행 후 <http://127.0.0.1:8000>을 열고, 터미널에서 `Ctrl+C`로 서비스를 중지합니다. ZIP은 Python 애플리케이션 설치 패키지이며,
Python/Git이 붙어 있지 않고, 네이티브 EXE, DMG, 시스템 패키지 관리자 설치 프로그램도 아닙니다. 게시된 첨부 파일은
[GitHub Releases](https://github.com/shuljyli/MXReady/releases)를 참조하세요; 오프라인 준비, 요약 검증, 업그레이드,
제거와 Windows 문제 해결은 [설치 및 릴리스 방안](docs/installation.md)을 참조하세요.

메인테이너가 설치 패키지를 빌드하려면 개발 의존성을 설치한 뒤 `make release`를 실행합니다(Windows: `.\scripts\make.ps1 release`).
산출물은 Git이 무시하는 `dist/`에 있습니다. 서버 배포(베어 메탈 / systemd / Docker / nginx)와 `MXREADY_*` 설정 항목은
[배포 문서](docs/deployment.md)와 [.env.example](.env.example)을 참조하세요.

### 소스 코드 개발

환경 요구 사항: Python 3.11+, Git, Node.js 22+(프론트엔드 개발/빌드 시에만 필요).

```bash
make install                # .venv 생성, 개발 의존성 설치, npm ci (Windows: .\scripts\make.ps1 install)
bash ./scripts/dev.sh       # 프론트/백엔드 원터치 실행 (Windows: .\scripts\dev.ps1)
```

`dev.sh` / `dev.ps1`는 프론트엔드 <http://localhost:5173>(`/api`가 백엔드로 프록시)과 백엔드
<http://127.0.0.1:8000>(`--reload` 핫 리로드)을 동시에 실행합니다. 개발 모드에서는 5173을 여세요; 백엔드는
`frontend/dist`가 있을 때 전체 인터페이스를 제공하며, API 문서는 `/docs`에 있고, 중국어 인터페이스 매뉴얼은 [docs/api.md](docs/api.md)를 참조하세요.

통합 명령 진입점(`install` / `dev` / `frontend` / `test` / `lint` / `typecheck` / `build` / `release` / `clean`):

| 목표 | Windows (PowerShell) | Linux / macOS | 동작 |
| --- | --- | --- | --- |
| 의존성 설치 | `.\scripts\make.ps1 install` | `make install` | venv + 백엔드 의존성 + `npm ci` |
| 백엔드 실행 | `.\scripts\make.ps1 dev` | `make dev` | uvicorn `--reload`, 포트 8000 |
| 프론트엔드 실행 | `.\scripts\make.ps1 frontend` | `make frontend` | Vite dev, 포트 5173 |
| 테스트 실행 | `.\scripts\make.ps1 test` | `make test` | 백엔드 pytest(커버리지 임계값 포함) |
| 코드 검사 | `.\scripts\make.ps1 lint` | `make lint` | ruff가 src / scripts / tests / packaging 검사 |
| 타입 검사 | `.\scripts\make.ps1 typecheck` | `make typecheck` | mypy가 src / scripts 검사 |
| 프론트엔드 빌드 | `.\scripts\make.ps1 build` | `make build` | `npm run build`로 `frontend/dist` 생성 |
| 설치 패키지 생성 | `.\scripts\make.ps1 release` | `make release` | 웹 + wheel/sdist + 3플랫폼 ZIP, `dist/`에 생성 |
| 정리 | `.\scripts\make.ps1 clean` | `make clean` | `.pytest-temp` 삭제 |

## 명령줄 도구

`mxready-scan`(로컬 디렉터리), `mxready-scan-public`(공개 저장소 증거), `mxready-build-bundle`(검증 번들),
`mxready-scan-batch`(일괄 평가), `mxready-mcp`(코딩 Agent용)의 상세 사용법과 종료 코드 규약은
[명령줄 사용](docs/cli.md)을 참조하세요. 모든 CLI는 읽기 전용 분석만 수행하며, 스캔 대상 코드를 실행하지 않습니다.

## 상태 의미

| 상태 | 의미 |
| --- | --- |
| `passed` | 차단 항목이나 경고가 매칭되지 않았으며, 여전히 실기 검증이 필요합니다 |
| `warnings` | 인적 검토가 필요한 마이그레이션 위험이 있습니다 |
| `blocked` | 원격 컴퓨팅 자원을 신청하기 전에 처리해야 할 차단 항목이 있습니다 |
| `not-run` | 아직 MetaX 환경 검증 결과를 업로드하지 않았습니다 |
| `verified` | 동일 커밋의 `mx-smi`와 PyTorch 장치 검사가 통과했고, 모든 환경 검사가 성공했으며, 결과가 30일 이내입니다; 전체 프로젝트 인증과 동일하지 않습니다 |
| `failed` | 검증 명령이 실패했습니다 |
| `stale` | 검증 결과가 30일을 넘겨 다시 실행해야 합니다 |

보고서는 의도적으로 백분율 호환성 점수를 제공하지 않습니다. 규칙 매칭 수가 프로젝트의 호환 확률을 대표할 수 없기 때문입니다.

## 테스트

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

부하 테스트 스크립트(locust, 로컬 mock Git, 공용 네트워크 불필요)는 [tests/load/](tests/load/)를 참조하세요.

## 문서 안내

| 문서 | 내용 |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | 디렉터리 계층, 의존성 방향, 작업 수명주기와 패키지 리소스 규약 |
| [docs/deployment.md](docs/deployment.md) | 프로덕션 배포: 베어 메탈 / systemd / Docker / nginx / 백업 / 로그 / 설정 항목 |
| [docs/api.md](docs/api.md) | 중국어 API 매뉴얼(curl 예제 포함) |
| [docs/cli.md](docs/cli.md) | 명령줄 도구와 MCP 상세 사용법 |
| [docs/installation.md](docs/installation.md) | 3플랫폼 설치 패키지, 오프라인 준비, 업그레이드, 릴리스 빌드와 Windows 문제 해결 |
| [docs/report-workflow.md](docs/report-workflow.md) | 전체 매칭, 스캔 범위, 보고서 비교, SARIF와 CI 연동 |
| [docs/security.md](docs/security.md) | 보안 모델 |
| [docs/rules.md](docs/rules.md) | 규칙 개발 가이드 |
| [docs/runner.md](docs/runner.md) | 원격 검증 runner 가이드 |
| [docs/migration-case-2026-11.md](docs/migration-case-2026-11.md) | 실제 저장소 사례: 차단 진단, 수정과 실기 재검증 |
| [examples/verification/README.md](examples/verification/README.md) | 실기 검증 인수인계 SOP |
| [CHANGELOG.md](CHANGELOG.md) | 버전 변경 기록 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 기여 절차와 품질 게이트 |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | 커뮤니티 행동 강령 |

## 보안 경계

- `github.com`와 `gitee.com`의 공개 HTTPS 저장소만 허용합니다; Git은 자격 증명을 읽지 않고, LFS를 내려받지 않고, 서브모듈을 초기화하지 않으며, 가져오기에 시간 제한과 크기/항목 상한이 있습니다;
- Web 스캔은 저장소 코드를 절대 실행하지 않습니다; 검증 결과 상한은 1 MiB이며 스캔 커밋에 결부됩니다;
- runner는 `sudo`를 쓰지 않고, 소프트웨어를 설치하지 않으며, 명령은 `shell=False`로 실행하고, 프로젝트 명령 실행 전에 인적 확인을 요구합니다;
- 공개 배포 전에는 속도 제한과 요청 본문 크기 제한을 켜야 합니다.

배포 전에 [보안 모델](docs/security.md)과 [runner 가이드](docs/runner.md)를 완전히 읽어 주세요.

## 기여하기

새 규칙은 양례, 유사한 반례, 1차 기술 자료를 함께 제공해야 합니다. 다음을 읽어 주세요:

- [기여 가이드](CONTRIBUTING.md)
- [규칙 개발 가이드](docs/rules.md)
- [원격 검증 가이드](docs/runner.md)
- [보안 모델](docs/security.md)

## MVP 로드맵

1. 세 개의 공개 CUDA 확장 프로젝트로 재현 가능한 보고서를 만들고 규칙 정확도를 보정합니다;
2. 더 많은 공개 프로젝트에서 동일 커밋의 비식별화 실기 검증을 완료합니다(`pytorch/extension-cpp` @ `1c325b2`와 `causal-conv1d` @ `cd81f04` 완료);
3. 하나의 업스트림 프로젝트를 골라 작고 리뷰 가능한 마이그레이션 PR을 제출합니다;
4. 실제 적응 피드백을 바탕으로 규칙과 최소 검증 템플릿을 확장합니다.

## 주요 기여자

- **shuli-黍黎** —— 프로젝트 창시자이자 주요 개발자.

## 라이선스

이 프로젝트는 [Apache License 2.0](LICENSE) 라이선스를 따릅니다. 라이선스 조건을 준수하는 한 사용, 수정, 배포를 환영합니다.

## 연락처

질문, 제안, 협업은 GitHub Issue로 남겨 주시거나 이메일로 연락 주세요:

- shuli_ljy@outlook.com
- 2199553510@qq.com
