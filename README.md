# ミステリDB

国内外の推理小説・ミステリ作品を著者・名探偵・翻訳者・出版社・受賞歴・テーマから検索できるファンデータベースです。姉妹サイト [らのべDB](https://izenmi.github.io/ranobe-db/) のミステリ版として作成しました。**シリーズ探偵を独立した軸として持ち、探偵ごとに登場作品を刊行年順で辿れる**のが特徴です。

https://izenmi.github.io/mystery-db/

## ネタバレについて

推理小説を扱うサイトなので、**あらすじ・探偵紹介には真相・犯人・トリックの核心を書かない**方針で運用しています。「叙述トリック」のように、そのタグが付いていること自体が推理の手がかりになってしまうテーマタグには `spoiler` フラグを付けており、作品一覧には表示せず、作品詳細ページでもボタンを押して初めて表示されます。

## データについて

`public/data/source/*.json` が一次データです。Wikipedia日本語版などの公開情報を参考に、あらすじ等は独自の文章で要約して作成しています。各ページから参照元のWikipedia記事へリンクしているので、詳細はそちらをご確認ください。データの誤りに気づいた場合はIssueでお知らせください。

`public/data/generated/*.json` はビルド時に `scripts/generate-manifest.mjs` が `source/*.json` から自動生成する非正規化データです(`.gitignore`対象、手で編集しないでください)。

## 開発

```sh
npm install
npm run dev       # http://localhost:5173/mystery-db/
npm run build      # 型チェック + データ整合性チェック + ビルド
npm run preview
```

`npm run dev` / `npm run build` の前に `scripts/generate-manifest.mjs` が自動実行され、`source/*.json` 内のid参照(著者・探偵・翻訳者・出版社・テーマ・アワード)に誤りがあるとビルドが失敗します。

## デプロイ

`main` ブランチへのpushで GitHub Actions (`.github/workflows/deploy.yml`) が自動的にビルドしてGitHub Pagesへ公開します。リポジトリ名を変更する場合は `vite.config.ts` の `base` も合わせて変更してください。
