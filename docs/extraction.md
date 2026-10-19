# 独立repoへの切り出し

このrepoは2026-10-19に、rdsh内で開発した`plugins/rdsh-harness2`から切り出しました。
ソルバー・採点器・Pythonアダプターの実装は、掲載した拡大実験のものを維持しています。
独立repo用の文書、パッケージ情報、CI、オフライン分析と保存成果物を追加しました。

掲載JSON内の`$WORKSPACE`や`$USER_HOME`は元実験のパスを置換した記録上の表現です。
その場所のファイルが公開repoに存在するという意味ではありません。
元の会話・nativeセッション・認証・ローカルモデル設定は収録していません。

- ソース成果物の対応とハッシュ: [artifacts/index.json](../evaluation/artifacts/index.json)
- 採用した合成指示の対応とハッシュ: [harnesses/index.json](../evaluation/harnesses/index.json)
- 成績の再集計とカーソルケースの再実行: [分析手順](../analysis/README.md)
- 本家の固定commitと外部依存: [帰属表示](../THIRD_PARTY.md)

元の実験のmanifestは実験開始時点の記録を保持しています。
このrepoのalphaバージョンや公開用メタデータに合わせて履歴のハッシュを書き換えていません。
統計の再集計と保存されたコードの検査は、同じモデル出力をもう一度生成できたことの証明ではありません。
