# 依存と帰属表示

## アダプターの由来

このアダプターは[jimoto-no-llm/rustdsh](https://github.com/jimoto-no-llm/rustdsh)の
`plugins/rdsh-harness2`として開発し、独立repoへ切り出しました。
元repoのMIT License全文と`Copyright (c) 2026 sahenjp`の表示を[LICENSE](LICENSE)に保持しています。

## 外部プロジェクト

| プロジェクト | 使用方法 | 確認したライセンス |
| --- | --- | --- |
| [Harness²](https://github.com/google-research/harness2) | 固定commitを別途checkoutしPythonでimport | Apache-2.0 |
| [rdsh](https://github.com/jimoto-no-llm/rustdsh) | 別途導入した実行ファイルを呼び出す | MIT |
| [DSH / Cordis](https://github.com/deepseek-ai/deepseek-harness) | 別途導入した公開Nodeパッケージを使用 | MIT |
| [Acorn](https://github.com/acornjs/acorn) | `acorn@8.19.0`をnpm依存として導入 | MIT |

Harness²の再帰・提案・選択アルゴリズムはupstreamを直接呼び出します。そのソースツリーや第三者ベンチマークはこのrepoへ同梱していません。
互換層はupstreamの内部プロンプト表へrdshの説明を追加します。固定commitは`1cfe254e8d25b15f37048c3730134686abe60335`です。

プロバイダーSDKや認証は別途導入します。掲載実験のCursor SDKブリッジはrdsh側の任意導入プラグインです。
これらの利用にはそれぞれの配布元の条件が適用されます。このrepoを各プロジェクトの公式版や推奨と称しません。

## 同梱した評価データ

`evaluation/`の課題はこのアダプター用の小規模な合成課題です。
実行結果には失敗と事後分析を含め、生成コードは分析を再現するための保存データとして収録しています。
会話・認証情報・プロバイダーの生セッション記録は含めません。
