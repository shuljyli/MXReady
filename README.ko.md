# MXReady

[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md) | **한국어** | [Español](README.es.md) | [Português](README.pt-BR.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

NVIDIA GPU에서 돌아가던 PyTorch 코드를 MetaX(沐曦) GPU로 옮기려고 합니다. 어디서 깨질지는 아직 모릅니다.

MXReady는 코드를 실행하지 않고 읽기만 해서, 문제가 될 만한 곳을 찾아 목록으로 보여 줍니다.

- NVIDIA 컴파일러를 직접 호출하는 곳
- "스레드 32개를 한 그룹"으로 고정한 곳 (MetaX는 64개입니다)
- NVIDIA 전용 인라인 어셈블리를 쓰는 곳
- 새 카드에 없는 라이브러리에 의존하는 곳

각 항목에는 어떤 파일의 몇 번째 줄인지, 왜 문제인지, 어떻게 고치면 되는지가 함께 나옵니다.

## 사용 방법

사용하는 운영체제에 맞는 ZIP을 내려받아 압축을 풀고 설치 스크립트를 실행합니다.

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

그다음 <http://127.0.0.1:8000> 을 열고 저장소 주소를 넣으면 결과가 나옵니다.

명령줄에서도 쓸 수 있습니다.

```bash
mxready-scan ./my-repo \
  --repo-url https://github.com/example/my-repo \
  --commit <40자리 커밋> \
  --output reports
```

## 하지 않는 일

- 코드를 대신 고쳐 주지 않습니다.
- "호환성 87%" 같은 숫자를 만들지 않습니다. 규칙에 몇 개 걸렸는지와 실제로 동작하는지는 다른 문제입니다.
- 정적 검사를 통과해도 "뚜렷한 문제를 못 찾았다"는 뜻일 뿐입니다. 진짜 답은 같은 커밋을 MetaX 실기에서 돌려야 나옵니다.

## 더 보기

- [전체 문서(중국어)](README.md)
- [Full documentation (English)](README.en.md)
- [규칙 목록](docs/rules.md)
- [구조와 설계](docs/architecture.md)

라이선스는 [Apache-2.0](LICENSE)입니다.
