# rdsh Harness² adapter

[Harness²](https://github.com/google-research/harness2)を
[rdsh](https://github.com/jimoto-no-llm/rustdsh)で実行する、研究・評価用のalphaです。
本家のPropose–Probe–Composeを使ってMarkdownの指示を改善し、通常版と固定した改善版を同条件で比較します。
Google Researchの公式アダプターではありません。

品質向上を保証するものではありません。公開した8課題×3回の比較では成功が9/24から13/24に増えましたが、課題による悪化と別のカーソル衝突も見つかりました。
全訓練込みの追加時間は、成功の純増1件当たり約7.5分です。
[比較結果](evaluation/coding-expanded-RESULTS.md)には失敗・追試・事後分析も含めています。

## 対応範囲

| 項目 | 条件 |
| --- | --- |
| リリース状態 | `0.1.0-alpha.1`、GitHubからソースで導入 |
| 読取比較 | native rdsh / DSH headless、固定JSON採点 |
| コード修正比較 | macOSの`/usr/bin/sandbox-exec`が必須。他OSでは拒否 |
| 検証した実行環境 | Node.js 26.12.0、Python 3.12、macOS |
| 本家Harness² | commit `1cfe254e8d25b15f37048c3730134686abe60335`に固定 |
| DSH | `0.2.0-rc.2`で検証 |
| モデル | 明示指定した既存プロバイダー。掲載実験は`cursor-sdk / composer-2.5` |

本家の内部APIを使う互換層があるため、Harness²の任意の最新版へ差し替えることはできません。
Nodeのパッケージ条件は22以上ですが、コード採点の動作確認とCIは26.12.0です。
このrepoだけではrdsh・DSH・モデルの認証は導入されません。npmレジストリへの公開も行っていません。

## セットアップ

Node.js 26.12.0とPython 3.12を用意してから実行します。

```sh
git clone https://github.com/jimoto-no-llm/rdsh-harness2.git
cd rdsh-harness2
npm ci --ignore-scripts
mkdir -p .local/upstream
git clone https://github.com/google-research/harness2.git .local/upstream/harness2
git -C .local/upstream/harness2 checkout 1cfe254e8d25b15f37048c3730134686abe60335
python3.12 -m venv .venv
.venv/bin/python -m pip install -e .local/upstream/harness2
```

本家チェックアウトの`harness2/`以下は変更せず使用してください。実行時にcommitと変更の有無を検査します。

## モデルを呼ばずに結果を再確認

掲載した成績は同梱JSONから再集計できます。新しいモデル処理や追加のAPI利用はありません。

```sh
PYTHONPATH=python .venv/bin/python analysis/reaggregate.py --verify
```

macOSでは保存済みの生成ソースを固定テストへかけ直し、既知カーソル反例と事後の26文字列を検査できます。

```sh
node analysis/replay-cursor.mjs
```

手順と分析の位置付けは[分析README](analysis/README.md)を参照してください。
保存データによる再集計と、新たなモデル生成による再現は区別します。同じモデル出力の再生成は保証しません。

## 実モデルで比較する

まず[rdsh](https://github.com/jimoto-no-llm/rustdsh)とDSHを導入し、利用するプロバイダーの認証を済ませます。
既存のCursor SDKログインを使う例では、別途[rdsh-direct-models](https://github.com/jimoto-no-llm/rustdsh/tree/main/plugins/rdsh-direct-models)を導入し、
[overlay例](examples/model.patch.example.json)のパスを自分の環境へ合わせます。認証情報はこのrepoへ配置しません。

```sh
export RDSH_HARNESS2_BIN=/absolute/path/to/rdsh
export RDSH_HARNESS2_DSH_PACKAGE=/absolute/path/to/node_modules/@deepseek-ai/dsh
export RDSH_HARNESS2_MODEL_PATCH=/absolute/path/to/your/model.patch.json

PYTHONPATH=python .venv/bin/python python/rdsh_coding_repeated.py \
  --suite evaluation/coding-expanded-tasks.json \
  --runner "$PWD/runner.mjs" \
  --provider cursor-sdk --model composer-2.5 \
  --output "$PWD/runs/new-comparison" \
  --rounds 3 --workers 2 --seed 271828 \
  --timeout-ms 600000 --max-steps 24
```

このコマンドは実モデルを使います。名目上は訓練21・比較48の計69 nativeセッションで、本家規定の提案修正が加わる場合があります。
プロバイダー内部のAPI呼び出し数とは異なります。保存済みハーネスを使う場合や小規模な読取比較は[詳細手順](USAGE.md)を参照してください。

主評価の設定マージ課題には仕様解釈の曖昧さがあり、[明確化した別プロンプトによる追試](evaluation/coding-expanded-RESULTS.md#仕様の曖昧さと追試)を併記しています。
元のスイートと成績は追試で置き換えていません。seedは実行順・集計用で、モデル生成のseedではありません。

通常プロファイルへの追加だけでは比較を開始しません。runnerが明示した読取・限定編集・固定テストのみに制限します。
改善した指示の既定プロファイルへの自動反映はありません。生成コードと採点テストは同じJavaScript環境で動くため、任意の敵対的コードを完全に隔離する仕組みではありません。

## 開発と検証

公開DSHモジュールをテスト専用ディレクトリへ導入します。認証やモデルAPIは不要です。

```sh
npm install --prefix .local/native-tests --ignore-scripts --no-audit --no-fund \
  @deepseek-ai/dsh@0.2.0-rc.2 @deepseek-ai/cordis@4.0.4 \
  @deepseek-ai/dsh-tools@0.2.0-rc.2 @deepseek-ai/dsh-system-prompt@0.2.0-rc.2
RDSH_PUBLIC_DSH_MODULES="$PWD/.local/native-tests/node_modules" npm test
PYTHONPATH=python .venv/bin/python -m unittest discover -s python/tests -v
PYTHONPATH=python .venv/bin/python -m unittest discover -s analysis/tests -v
```

専用CIはmacOS上で実際のsandbox・Cordis統合を含めて検証します。
macOS以外やDSH公開モジュールがない環境では一部テストがSKIPされます。SKIPを対応確認済みとは扱いません。
変更時の確認範囲は[CONTRIBUTING.md](CONTRIBUTING.md)に記載しています。

## ライセンスと由来

アダプターは[MIT](LICENSE)です。rdsh内で開発したプラグインから切り出し、元の著作権表示を保持しています。
Harness²は別途導入するApache-2.0の依存プロジェクトです。[依存と帰属表示](THIRD_PARTY.md)、[切り出し時の履歴とパスの説明](docs/extraction.md)を参照してください。
