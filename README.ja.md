# MXReady

[![CI](https://github.com/shuljyli/MXReady/actions/workflows/ci.yml/badge.svg)](https://github.com/shuljyli/MXReady/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-1.0.1-blue)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)

[中文](README.md) | [English](README.en.md) | **日本語** | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt-BR.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

NVIDIA の GPU で動いている PyTorch のコードを、MetaX（沐曦）の GPU に移したい。どこでつまずくのか、まだ分かっていない。

MXReady はコードを実行せずに読むだけで、問題になりそうな箇所を一覧にします：NVIDIA のコンパイラを直接呼び出している箇所、「32 スレッドで 1 グループ」と決め打ちしている箇所（MetaX は 64 スレッド）、NVIDIA 専用のインラインアセンブラを使っている箇所、新しいカードでは動かないライブラリに依存している箇所。各項目には「どのファイルの何行目か」「なぜ問題なのか」「どう直せばよいか」が明記されます。

コードを書き換えることも、「互換性 87%」のような数字を出すこともしません——ルールに何件当たったかから互換の確率を導けるわけではありません。静的チェックが通っても、それは「明らかな問題が見つからなかった」だけです。本当の結論は MetaX の実機で動かして初めて出ます。

> MXReady はコミュニティのプロトタイプであり、MetaX（沐曦）公式の互換性認証ではありません。静的チェックが通過しても、プロジェクトがすでに MXMACA で動作することを意味するものではありません。最終的な結論は、同じコミットを統制された MetaX GPU 環境で検証して得る必要があります。

## できること

- GitHub / Gitee の公開 HTTPS リポジトリを受け付ける。ブランチ、タグ、または 40 桁のコミットを指定できる；
- Python、C/C++、CUDA、CMake、Shell、TOML、YAML などのテキストファイルをスキャンする；
- **35 個のルール**（`MXR-*`）を内蔵。各結果にはファイル、行番号、ヒットしたコード、修正の提案、権威ある一次資料が付く；
- テスト、サンプル、ドキュメント中のヒットは参考情報扱い：レポートには載るが、プロジェクト全体をブロック判定にはしない；
- JSON、Markdown、SVG バッジ、印刷可能な HTML レポート（ブラウザの印刷で PDF 化）、および標準ライブラリのみに依存するリモート検証パッケージを出力する；
- 静的な結論と実機検証の結論は分けて表示し、混ぜない；
- 読み取り専用のローカルディレクトリ CLI を提供し、オフラインの回帰テストやサンプルレポートの作成を容易にする；
- オプションの `mxready-mcp`：スキャン、ジョブ状態、レポート、ルール照会を 5 つの MCP ツールとして公開し、Model Context Protocol に対応したコーディングエージェントから呼び出せる；
- React のシングルページ UI と FastAPI サービスは、1 つのデプロイ単位としてパッケージできる。

Web UI には「ソースコード診断」「一括スキャン」「スキャン履歴」「移行進捗」「ルールライブラリ」「MCP 接続」「コマンドライン利用」のページがあります。
レポートは優先ファイルの特定、ページング検索、比較共有、手動レビューのチェックリスト、HTML 印刷エクスポートに対応します。MCP と Web が互いのレポートを
読み込む場合は、明示的に同じローカルデータディレクトリを共有する必要があります。

MVP には、非公開リポジトリ、ソースコードの自動修正、リモート GPU サーバーの Docker オーケストレーション、クラウド GPU のスケジューリング、ユーザー管理、パーセント表記の「互換スコア」は含まれません。

## 実際のプロジェクトで見つかったこと

[`NVIDIA/apex`](https://github.com/NVIDIA/apex) をコミット `575968bc1f9127ccd61003a681472a83af4ff1a1` で診断した結果：
**ブロック 12 · 警告 65 · 参考情報 140**。完全なレポートは [examples/reports/nvidia-apex.md](examples/reports/nvidia-apex.md) を参照。

12 件のブロックのうち、代表的な 4 件：

| 場所 | ヒット | なぜ MetaX で壊れるのか |
| --- | --- | --- |
| `csrc/welford.cu:36` | `#define WARP_SIZE 32` | ワープ幅を 32 に決め打ち。MetaX は 64 |
| `nhwc_batch_norm_kernel.h:1245` | `int lane_id = threadIdx.x & 31;` | lane 0 と lane 32 が同じ lane と判定されてしまう |
| `group_norm_nhwc.h:40` | `asm volatile("red.release.gpu.global.add.s32 …")` | インライン PTX が NVIDIA バックエンドに固定される |
| `setup.py:65` | `subprocess.check_output([cuda_dir + "/bin/nvcc", "-V"])` | `nvcc` を直接呼び出してバージョンを取得しようとする。MetaX 環境にこのコマンドはない |

4 件のうち 2 件はコンパイル自体は通りますが、lane の計算とワープ幅が幅 64 の wave では誤った結果を出し、テストでも検出できない可能性があります。
残り 2 件は MetaX ではそもそもコンパイルが通りません。どちらの種類の問題も、1 回の移行を数週間遅らせることになります。

さらに、コミットを固定した 2 つのケースが、ブロックと修正の両側の証拠を補います：

- [`bitsandbytes`](https://github.com/bitsandbytes-foundation/bitsandbytes)（`a616886`）：27 件の指摘、7 件のブロック。
  レポートは [examples/reports/bitsandbytes.md](examples/reports/bitsandbytes.md) を参照。
- [`causal-conv1d`](https://github.com/Dao-AILab/causal-conv1d)（`cd81f04`）：レポートに基づいて修正したところ指摘数が減少し、
  MetaX C500 の実機検証ですべて `passed`。詳細は[移行ケース記録](docs/migration-case-2026-11.md)（中国語）を参照。

## アーキテクチャ

```text
React/Vite UI
      │ /api
      ▼
FastAPI ── SQLite 永続ジョブキューとレポート
   │
   ├─ 原子的取得 / リースハートビート ── 制限付き Git 取得 ── 読み取り専用ファイル索引 ── YAML ルールエンジン
   ├─ JSON / Markdown / SVG レポート
   └─ 検証 ZIP ◀── ユーザー管理下の MetaX ホストで実行 ── result.json
```

Web サービスは、スキャン対象リポジトリのコードをインポート・インストール・ビルド・実行しません。リモート runner はユーザーが管理するマシンでのみ動き、プロジェクトコマンドの実行前に手動での確認を要求します。

Python コードはすべて `src/` に置きます。デフォルトルールと検証スキーマはインストールパッケージに同梱されます。ディレクトリ規約、ジョブキュー、アップグレード手順は
[アーキテクチャ説明](docs/architecture.md)（中国語）を参照。モデルを変更したら `make contracts` でインターフェイス契約を再生成してください。

## 機能マトリクス

| 機能 | 状態 | 検証方法 |
| --- | --- | --- |
| 公開リポジトリの静的スキャン（GitHub / Gitee、ブランチ・タグ・40 桁コミット指定可） | 利用可能 | E2E テスト + サンプルレポート |
| 35 個の `MXR-*` チェックルール | 利用可能 | 各ルールに正例と類似の反例フィクスチャを含む |
| レポート出力：JSON / Markdown / HTML / SVG バッジ | 利用可能 | 契約テスト + `generate_contracts.py --check` |
| 移行進捗ダッシュボード（リポジトリ横断の集計、ブロック項目の傾向） | 利用可能 | バックエンド集計テスト + Vitest |
| リモート検証パッケージと標準ライブラリのみの runner | 利用可能 | インストールパッケージの回帰テスト + セキュリティ境界テスト |
| 3 プラットフォームのインストール ZIP と Web UI 同梱の wheel/sdist | 利用可能 | リリースワークフローで Windows / Linux / macOS に実際にインストールして起動 |
| React シングルページ UI | 利用可能 | Vitest + TypeScript strict モード |
| 一括評価（`mxready-scan-batch`） | 利用可能 | CLI 回帰テスト |
| MCP ツール（`mxready-mcp`、`.[mcp]` が必要） | 利用可能 | バックエンドテスト + 実際の stdio ハンドシェイク |
| MetaX GPU の実機検証 | 匿名化した検証を 2 回完了（MetaX C500：`pytorch/extension-cpp` @ `1c325b2`、`causal-conv1d` @ `cd81f04`） | runner `inspect` の 5 項目の環境チェックとシングルカード smoke がすべて `passed`。causal-conv1d のビルドには upstream 未提出の一時パッチを使用しており、他のプロジェクトはそれぞれの検証が必要 |

工程状態：`ruff`、`mypy`、契約チェック、`pytest` はすべてグリーン（540 件超のテスト、ブランチカバレッジ 90%）。
CI は Python 3.11 / 3.12 / 3.13 × Windows / Linux / macOS をカバーし、加えて Python 3.10 の runner ジョブがあります。

## 既知の制限

- **互換性の結論は提供しません**。すべての出力は静的なリスクの指摘と手動レビューの提案までです。「MetaX 環境で検証済み」と言えるのは、
  具体的なコミットに紐づき、統制された MetaX GPU 上で `verified` の結果を得て、かつ 30 日以内である場合に限られます。
- **ルールの精度はまだ大規模な実プロジェクトでの統計がありません**。正例・反例は統制されたフィクスチャによるもので、公開リポジトリ上で
  再確認済み（誤検出 0）ですが、システマティックな誤検出率・見逃し率にはより多くの実プロジェクトでの統計が必要です。[ルール説明](docs/rules.md)（中国語）を参照。
- **実機検証の結果には 30 日の有効期限があります**。期限切れになるとレポートの状態は `stale` に変わり、再アップロードが必要です。
- **MVP の範囲**：非公開リポジトリには対応せず、ソースコードの自動修正はせず、クラウド GPU のスケジューリングは行わず、ユーザー管理はなく、パーセント表記の互換スコアは出しません。

> 公開プロジェクトのサンプルレポートは [examples/reports](examples/reports) にあります：`pytorch-extension-cpp` はすべて通過（参考情報 4 件）、
> `nvidia-apex`（ブロック 12 件）と `bitsandbytes`（ブロック 7 件）はブロック状態、`causal-conv1d` は修正前後の 2 本を残しています。
> 併置しているのは、レポートが本当にグリーンにもレッドにもなることを示すためです。リモート検証の流れは
> [examples/verification/README.md](examples/verification/README.md) を参照。

## インストールと起動

一般のユーザーは Web UI 同梱のリリースパッケージをそのままインストールしてください。Node.js は不要で、PyTorch や GPU ドライバのインストールも不要です。
3 プラットフォームすべてで **Python 3.11+（pip/venv 含む）と Git** を事前に用意してください。初回インストールでは Python 依存パッケージをネットワークからダウンロードします。

| プラットフォーム | パッケージ | 展開後、パッケージのディレクトリで実行 |
| --- | --- | --- |
| Windows 10/11 | `mxready-1.0.1-windows.zip` | PowerShell：`.\install.ps1`、次に `.\start.ps1` |
| Linux | `mxready-1.0.1-linux.zip` | `bash install.sh`、次に `bash start.sh` |
| macOS（Apple Silicon / Intel） | `mxready-1.0.1-macos.zip` | `bash install.sh`、次に `bash start.sh` |
| Python 環境を自分で管理 | PyPI の `mxready` | `python -m pip install mxready`、次に `mxready-serve` |
| 既存の Python 環境 | `mxready-1.0.1-py3-none-any.whl` | 専用 venv 内で `python -m pip install <wheel のパス>`、次に `mxready-serve` |

起動後 <http://127.0.0.1:8000> を開き、ターミナルで `Ctrl+C` を押してサービスを停止します。ZIP は Python アプリケーションのインストールパッケージであり、
Python/Git は同梱していません。ネイティブの EXE、DMG、システムのパッケージマネージャー用インストーラでもありません。公開済みの添付ファイルは
[GitHub Releases](https://github.com/shuljyli/MXReady/releases) を参照。オフライン準備、ハッシュ検証、アップグレード、
アンインストール、Windows のトラブルシューティングは[インストールとリリース手順](docs/installation.md)（中国語）を参照。

メンテナーがインストールパッケージをビルドするには、開発依存をインストールした上で `make release`（Windows：`.\scripts\make.ps1 release`）を実行します。
成果物は Git 無視対象の `dist/` に出ます。サーバーデプロイ（ベアメタル / systemd / Docker / nginx）と `MXREADY_*` 設定項目は
[デプロイドキュメント](docs/deployment.md)（中国語）と [.env.example](.env.example) を参照。

### ソースからの開発

必要環境：Python 3.11+、Git、Node.js 22+（フロントエンドの開発・ビルド時のみ必要）。

```bash
make install                # .venv 作成、開発依存のインストール、npm ci（Windows：.\scripts\make.ps1 install）
bash ./scripts/dev.sh       # フロントエンドとバックエンドを一括起動（Windows：.\scripts\dev.ps1）
```

`dev.sh` / `dev.ps1` はフロントエンド <http://localhost:5173>（`/api` はバックエンドへプロキシ）とバックエンド
<http://127.0.0.1:8000>（`--reload` でホットリロード）を同時に起動します。開発時は 5173 を開いてください。
バックエンドは `frontend/dist` が存在する場合に完全な UI を提供し、API ドキュメントは `/docs` にあります。中国語の API マニュアルは [docs/api.md](docs/api.md)（中国語）を参照。

統一されたコマンドエントリ（`install` / `dev` / `frontend` / `test` / `lint` / `typecheck` / `build` / `release` / `clean`）：

| 目的 | Windows (PowerShell) | Linux / macOS | 役割 |
| --- | --- | --- | --- |
| 依存関係のインストール | `.\scripts\make.ps1 install` | `make install` | venv + バックエンド依存 + `npm ci` |
| バックエンド起動 | `.\scripts\make.ps1 dev` | `make dev` | uvicorn `--reload`、ポート 8000 |
| フロントエンド起動 | `.\scripts\make.ps1 frontend` | `make frontend` | Vite dev、ポート 5173 |
| テスト実行 | `.\scripts\make.ps1 test` | `make test` | バックエンド pytest（カバレッジしきい値付き） |
| コードチェック | `.\scripts\make.ps1 lint` | `make lint` | ruff で src / scripts / tests / packaging をチェック |
| 型チェック | `.\scripts\make.ps1 typecheck` | `make typecheck` | mypy で src / scripts をチェック |
| フロントエンドビルド | `.\scripts\make.ps1 build` | `make build` | `npm run build` で `frontend/dist` を生成 |
| パッケージ生成 | `.\scripts\make.ps1 release` | `make release` | Web UI + wheel/sdist + 3 プラットフォーム ZIP、`dist/` に出力 |
| クリーンアップ | `.\scripts\make.ps1 clean` | `make clean` | `.pytest-temp` を削除 |

## コマンドラインツール

`mxready-scan`（ローカルディレクトリ）、`mxready-scan-public`（公開リポジトリの証跡）、`mxready-build-bundle`（検証パッケージ）、
`mxready-scan-batch`（一括評価）、`mxready-mcp`（コーディングエージェント向け）の詳細な使い方と終了コードの規約は
[コマンドライン利用](docs/cli.md)（中国語）を参照。すべての CLI は読み取り専用の分析のみを行い、スキャン対象のコードは実行しません。

## 状態の意味

| 状態 | 意味 |
| --- | --- |
| `passed` | ブロック項目にも警告にも該当しないが、実機検証はまだ必要 |
| `warnings` | 手動レビューが必要な移行リスクがある |
| `blocked` | リモート計算資源の申請前に解消すべきブロック項目がある |
| `not-run` | MetaX 環境の検証結果がまだアップロードされていない |
| `verified` | 同じコミットでの `mx-smi` と PyTorch デバイスチェックが成功し、すべての環境チェックが通り、結果が 30 日以内。プロジェクト全体の認証と同義ではない |
| `failed` | 検証コマンドが失敗した |
| `stale` | 検証結果が 30 日を超過し、再実行が必要 |

レポートは意図的にパーセント表記の互換スコアを提供しません。ルールのヒット数はプロジェクトの互換確率を表せないからです。

## テスト

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

負荷テストスクリプト（locust、ローカルの mock Git、インターネット不要）は [tests/load/](tests/load/) を参照。

## ドキュメント案内

（`docs/` 配下のドキュメントは中国語で書かれています。）

| ドキュメント | 内容 |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | ディレクトリ階層、依存方向、ジョブライフサイクル、パッケージリソース規約 |
| [docs/deployment.md](docs/deployment.md) | 本番デプロイ：ベアメタル / systemd / Docker / nginx / バックアップ / ログ / 設定項目 |
| [docs/api.md](docs/api.md) | 中国語の API マニュアル（curl の例付き） |
| [docs/cli.md](docs/cli.md) | コマンドラインツールと MCP の詳細な使い方 |
| [docs/installation.md](docs/installation.md) | 3 プラットフォームのインストールパッケージ、オフライン準備、アップグレード、リリースビルド、Windows のトラブルシューティング |
| [docs/report-workflow.md](docs/report-workflow.md) | 完全なヒット、スキャン範囲、レポート比較、SARIF、CI 連携 |
| [docs/security.md](docs/security.md) | セキュリティモデル |
| [docs/rules.md](docs/rules.md) | ルール開発ガイド |
| [docs/runner.md](docs/runner.md) | リモート検証 runner ガイド |
| [docs/migration-case-2026-11.md](docs/migration-case-2026-11.md) | 実リポジトリのケース：ブロックの診断、修正、実機での再検証 |
| [examples/verification/README.md](examples/verification/README.md) | 実機検証の引き継ぎ SOP |
| [CHANGELOG.md](CHANGELOG.md) | バージョン変更履歴 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | コントリビュートの流れと品質ゲート |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | コミュニティ行動規範 |

## セキュリティ境界

- `github.com` と `gitee.com` の公開 HTTPS リポジトリのみ許可。Git は認証情報を読み取らず、LFS を取得せず、サブモジュールを初期化せず、取得にはタイムアウトとサイズ・エントリ数の上限がある；
- Web スキャンはリポジトリのコードを決して実行しない。検証結果は 1 MiB が上限で、スキャンしたコミットに紐づく；
- runner は `sudo` を使わず、ソフトウェアをインストールせず、コマンドは `shell=False` で実行し、プロジェクトコマンドの実行前に手動確認を要求する；
- 公開デプロイの前に、レート制限とリクエストボディのサイズ制限を有効にすること。

デプロイ前に[セキュリティモデル](docs/security.md)（中国語）と [runner ガイド](docs/runner.md)（中国語）を熟読してください。

## コントリビュート

新しいルールには、正例・類似の反例・一次技術資料をすべて提供してください。以下を読んでください：

- [コントリビュートガイド](CONTRIBUTING.md)
- [ルール開発ガイド](docs/rules.md)（中国語）
- [リモート検証ガイド](docs/runner.md)（中国語）
- [セキュリティモデル](docs/security.md)（中国語）

## MVP ロードマップ

1. 3 つの公開 CUDA 拡張プロジェクトで再現可能なレポートを生成し、ルールの精度を較正する；
2. より多くの公開プロジェクトで、同じコミットによる匿名化した実機検証を完了する（`pytorch/extension-cpp` @ `1c325b2` と `causal-conv1d` @ `cd81f04` は完了）；
3. 1 つの upstream プロジェクトを選んで、小さくレビュー可能な移行 PR を提出する；
4. 実際の適応作業のフィードバックに基づいて、ルールと最小検証テンプレートを拡充する。

## 主要貢献者

- **shuli-黍黎** —— プロジェクトの創始者および主要開発者。

## ライセンス

本プロジェクトは [Apache License 2.0](LICENSE) の下で提供されます。ライセンスの条項に従った使用、改変、再配布を歓迎します。

## お問い合わせ

ご質問、ご提案、協力のご相談は GitHub Issue を作成いただくか、メールでお問い合わせください：

- shuli_ljy@outlook.com
- 2199553510@qq.com
