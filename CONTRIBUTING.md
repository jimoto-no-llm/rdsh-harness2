# 開発手順

セットアップは[README](README.md#セットアップ)を参照してください。
本家Harness²は固定commitを用意し、同プロジェクトのソースを変更せず使用します。

## 変更後の確認

macOSとNode.js 26.12.0で、READMEの公開DSHモジュールを用意してから実行します。

```sh
npm ci --ignore-scripts
RDSH_PUBLIC_DSH_MODULES="$PWD/.local/native-tests/node_modules" npm test
PYTHONPATH=python .venv/bin/python -m unittest discover -s python/tests -v
PYTHONPATH=python .venv/bin/python -m unittest discover -s analysis/tests -v
PYTHONPATH=python .venv/bin/python analysis/reaggregate.py --verify
node analysis/replay-cursor.mjs
git diff --check
```

これらはモデルを呼びません。既存の実験データと契約テストを検証します。
実モデル比較は明示して実行し、追加セッション数と時間、失敗、モデル・upstreamの設定を記録してください。
モデルを実行するテストをCIへ追加しないでください。

コード課題のOS sandboxがない環境では該当検証ができません。SKIPをPASSへ置き換えず、確認した層を報告してください。
プロバイダーのトークン使用量や費用が得られないときは`null`を保持します。

## 評価結果を更新するとき

元の実験・固定スイート・ハッシュを保存してください。新しい結果で既存成績を上書きしません。
事前に決めた評価と、生成ソースを見てから追加した反例・追試を区別します。
同じ課題の反復や同じハーネスの再利用を、独立した新規課題の数へ水増ししません。
非公開テストを改善や候補の選択へ渡さないでください。

runディレクトリと生ログはローカルに置きます。公開するデータは合成課題と必要な成果物に絞り、個人パスや認証情報が混ざっていないか確認してください。
安全なsandbox対応を追加するときは、外部I/O・子プロセス・timeoutの契約を実環境で検証してください。
