# MXReady

[中文](README.md) | [English](README.en.md) | **日本語** | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt-BR.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

NVIDIA の GPU で動いている PyTorch のコードを、MetaX（沐曦）の GPU に移したい。どこで壊れるのか、まだ分かっていない。

MXReady はコードを実行せずに読むだけで、問題になりそうな箇所を一覧にします。

- NVIDIA のコンパイラを直接呼び出している箇所
- 「32 スレッドで 1 グループ」と決め打ちしている箇所（MetaX は 64 スレッド）
- NVIDIA 専用のインラインアセンブラを使っている箇所
- 新しいカードには存在しないライブラリに依存している箇所

各項目には「どのファイルの何行目か」「なぜ問題なのか」「どう直せばよいか」が付きます。

## 使い方

お使いのシステム用の ZIP をダウンロードして解凍し、インストーラを実行します。

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

起動したら <http://127.0.0.1:8000> を開いてください。リポジトリの URL を入れると結果が出ます。

コマンドラインからも使えます。

```bash
mxready-scan ./my-repo \
  --repo-url https://github.com/example/my-repo \
  --commit <40 桁のコミット> \
  --output reports
```

## やらないこと

- コードを書き換えることはしません。
- 「互換性 87%」のような数字は出しません。ルールに何件当たったかと、実際に動くかどうかは別の話です。
- 静的チェックが通っても、それは「明らかな問題が見つからなかった」だけです。本当の結論は MetaX の実機で同じコミットを動かして初めて出ます。

## もっと詳しく

- [完全なドキュメント（中国語）](README.md)
- [Full documentation (English)](README.en.md)
- [ルール一覧](docs/rules.md)
- [設計と構成](docs/architecture.md)

ライセンスは [Apache-2.0](LICENSE) です。
