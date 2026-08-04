# mystery-db

国内外の推理小説・ミステリ作品を著者・名探偵・翻訳者・出版社・受賞歴・テーマから検索できるファンデータベース。姉妹サイト[らのべDB](https://izenmi.github.io/ranobe-db/)(`izenmi/ranobe-db`)のミステリ版として作成した。アーキテクチャ・デザインシステム・運用ノウハウの多くをranobe-dbから移植している。**シリーズ探偵を独立したエンティティとして持ち、探偵ごとに登場作品を発表年順で辿れる**のが差別化点。

- 公開URL: https://izenmi.github.io/mystery-db/
- リポジトリ: `izenmi/mystery-db`(public。GitHub Pagesは無料枠だとpublicでないと使えない)
- スタック: React 18 + TypeScript + Vite 5 + `react-router-dom`(`BrowserRouter`)。ranobe-dbと異なり最初からBrowserRouterで作っているため、旧HashRouter互換のリダイレクト処理は存在しない(manga-db/game-dbと同じ)

## ネタバレ方針(このサイト固有・最重要)

推理小説を扱う以上、これが他の姉妹サイトにない最優先ルールになる。

- **あらすじ・探偵の`description`・`sourceNote`に、犯人・真相・トリックの核心を書かない**。あらすじは「読者が本を手に取るかどうか判断できる情報」までにとどめる
- **`ThemeSource.spoiler: true` を付ける基準**: 「そのタグが作品に付いていることを知ること自体が、真相の推理に直結するもの」だけ。帯・あらすじ・レーベルの惹句で公表されている構造タグは対象外
  - spoiler扱いにする: 叙述トリック、信頼できない語り手、多重解決、意外な犯人
  - spoiler扱いにしない: 密室、館もの、クローズドサークル、読者への挑戦状、倒叙、見立て殺人、孤島(いずれも売り文句として表に出ている)
- **UI側の扱い**(実装済み):
  - `WorkCard`(作品一覧・各詳細ページの関連作品)は spoiler タグを**描画しない**。一覧をスクロールしただけで漏れるのが最悪のため、`generate-manifest.mjs` が各Workに `spoilerThemeIds` を付けて出力し、カード側でそれを除外している
  - `WorkDetailPage` は「ネタバレを含むタグを表示(N件)」ボタンを押して初めて表示する。展開状態は`useState`のみで保存せず、ページを開き直すと必ず閉じた状態に戻る
  - `WorkDetailPage` のJSON-LD `genre` からも spoiler タグを除外している(検索結果のスニペットは、誰も見ることに同意していない場所のため)
  - `ThemeListPage` は spoiler タグを別セクション「ネタバレを含むタグ」にまとめる。タグ名自体は隠さない(タグ名だけでは特定作品と結びつかないため)
  - `ThemeDetailPage` は spoiler タグのページに警告バナーを出し、meta descriptionを作品数に触れない汎用文にする
  - `HomePage` の「人気テーマ」からは spoiler タグを完全に除外する

## データフロー(source → generated)

- `public/data/source/*.json` … 手作業で作成・**コミットする**一次データ(works/authors/detectives/translators/publishers/themes/awards)
- `public/data/generated/*.json` … `scripts/generate-manifest.mjs` がビルド時に生成する非正規化データ。**`.gitignore`対象**、`predev`/`prebuild`npmスクリプトで毎回再生成するので手で編集しない
- 生成スクリプトの検証(いずれも失敗するとビルドが落ちる):
  - 全Workの`authorIds`(空配列不可)/`detectiveIds`/`translatorIds`/`publisherId`/`themeIds`/`awardResults[].awardId` の参照整合性
  - `DetectiveSource.creatorAuthorId` が `authors.json` に存在すること、`firstAppearanceWorkId` が指定されていれば `works.json` に存在すること
  - **`origin` の整合性**: `"overseas"` なら `translatorIds` が1件以上あり `originalTitle` があること / `"jp"` なら `translatorIds`・`originalTitle`・`jpPublishedYear` がいずれも空であること
- 著者・探偵・翻訳者・出版社・テーマの詳細ページは、それぞれの作品一覧を`WorkGenerated`型でフル展開して埋め込む(`WorkCard`をそのまま再利用できるようにするため)

## データモデル上の判断(ranobe-dbとの違い)

- **1作品(1タイトル)単位**で登録する。ranobe-dbはシリーズ単位だが、ミステリはシリーズものでも各巻が独立作品として認知されており、探偵軸で発表順に並べる設計とも噛み合う。副次的に、表紙取得がタイトル完全一致で効くため精度が上がる
- **`firstPublishedYear` は原著の発表年**。海外作品もこの欄に原書刊行年を入れることで、ホームズ(1887年)から現代作までを推理小説史の時系列で並べられる。邦訳初刊年は `jpPublishedYear` に分離する
- **`seriesName` はエンティティ化しない**ただの表示用テキスト(「金田一耕助シリーズ」等)。シリーズ横断のブラウズは探偵軸が担うため
- **`mediaMix` は `{ movie, drama, anime, comic }` の4種**。このジャンルは実写映画化・テレビドラマ化が主役なので、ranobe-dbのアニメ/コミカライズ2種から拡張した
- `DetectiveGenerated.works` は**`firstPublishedYear` 昇順固定**(他のエンティティ詳細ページと違いソート切替を用意していない)。「シリーズをどの順で読めばいいか」が探偵ページの存在意義のため
- `PersonKind` は `"author" | "translator" | "publisher"`。探偵は固有フィールド(生みの親・職業・初登場作)を持つため generic な `PersonListPage`/`PersonDetailPage` を使わず、`src/ui/detectives/` に専用ページを置いている(game-dbの`CompanyListPage`/`CompanyDetailPage`と同じ方針)

## データ入力ルール(ranobe-dbから踏襲)

- **出典は日本語版Wikipediaを基本とするが必須ではない**。Wikipediaに記事がない作品も登録してよく、その場合は出版社公式サイト・電子書店等の書誌情報・信頼できる他の情報源を使ってよい。ユーザーが口頭で伝えるタイトル・著者名・刊行年等はしばしば誤っているので、書き込む前に必ず何らかの情報源で裏取りする。矛盾があれば訂正し、`sourceNote`に何を確認したか・どの情報源を使ったか・何が未確認かを明記する
- **あらすじはコピペ禁止**。Wikipediaの文章表現をそのまま転記せず、150〜250字程度で必ず自分の言葉で要約する(事実自体は著作権保護対象外だが、文章表現はCC BY-SA 4.0の対象になりうるため)。加えて上記のネタバレ方針を守る
- **実在確認できない候補は無理に埋めない**。目標作品数に届かなくても、確認できたタイトルのみ収録する
- **表紙画像は`covers-cache.json`にあれば実画像、なければプレースホルダー**。直リンクの画像URLを推測・ハードコードすることはしない
- **購入リンクは検索URL形式のみ**。個別商品ページへの直リンクは使わない。理由: 1作品が単行本・文庫で別々に版を重ねるため版ごとのISBN/ASINを持てない。`amazonSearchUrl(title, extra?)`(`src/ui/common/WorkCover.tsx`)がアフィリエイトタグ`izenmi-22`(姉妹サイト共通)付きの検索URLを生成する。作品詳細ページでは第2引数に著者名を渡し、短いタイトルでも目的の本に当たるようにしている
- 新規idを追加する前に既存の`authors.json`/`detectives.json`/`translators.json`/`publishers.json`を確認し、同一人物の重複登録を避ける

## データ拡充時の作業フロー

シードデータの拡充は**必ず小バッチ(10〜15作品程度)で作業し、バッチごとに即コミット・push**する。理由: セッションのトークン/時間制限で作業が中断されても、それまでの成果を失わないため。

1. 候補作品をリストアップ
2. サブエージェントにWikipedia調査を依頼(事実確認・訂正・あらすじ要約案の作成)し、コード編集はさせない。**並列実行はしない**(ranobe-dbで2026-08-03にユーザーから明確な指示があり、姉妹サイトにも同じ方針を適用する)。1つずつ順番に起動・完了を待ってから次を起動する
3. 調査結果を `scripts/apply_batch.py` で反映する。batch.jsonのキーは `newAuthors` / `newDetectives` / `newTranslators` / `newPublishers` / `newThemes` / `newAwards` / `works`。このスクリプトは `origin` ごとの必須項目や `creatorAuthorId` の参照も `generate-manifest.mjs` と同じルールで検証し、通らない要素はレポートしてスキップする
4. `npm run build`(内部で`generate-manifest`が整合性チェックを行う)が通ることを確認
5. `git add public/data/source && git commit && git push`

## 受賞歴(awards)の方針

文学賞・新人賞に加え、ranobe-dbと同様に年間ランキング系も`awardResults`に含める。scaffold時点で登録済み: 日本推理作家協会賞、本格ミステリ大賞、直木三十五賞、山本周五郎賞、メフィスト賞、鮎川哲也賞、角川学園小説大賞、『このミステリーがすごい!』年間ランキング、週刊文春ミステリーベスト10、本格ミステリ・ベスト10、ミステリが読みたい!。

**カウントする/しないの基準:**
- 作品自体の受賞・順位が明記されているものだけを採用する。**候補・ノミネートは登録しない**(『獄門島』の探偵作家クラブ賞候補、『占星術殺人事件』の江戸川乱歩賞最終候補、『火車』の直木賞候補、『容疑者Xの献身』のエドガー賞候補などはいずれも`sourceNote`に記載するのみ)
- **映画版・ドラマ版のみが対象の賞**は小説自体の受賞ではないため対象外(『砂の器』の毎日映画コンクール大賞、『白夜行』のテレビドラマアカデミー賞など)
- **著者の別作品での受賞**と**本作自体の受賞**を明確に区別し、`sourceNote`に明記する
- 賞の名称が時代とともに変わっている場合は既存idを再利用し、`sourceNote`に当時の名称を明記する。実例: 『本陣殺人事件』の第1回受賞は当時「探偵作家クラブ賞」の名称であり、`mystery-writers-japan`(日本推理作家協会賞)のidで登録している
- ランキング系の`year`は「◯年版」の表記に合わせる(『このミステリーがすごい!2013年版』は`year: 2013`)。『週刊文春ミステリーベスト10』は発表年をそのまま使う

## テーマタグの方針

再利用可能な少数タグに絞る(1作品あたり4〜5個が目安)。scaffold時点で通常タグ30件+spoilerタグ4件。作品数0のタグがいくつか残っているのは、今後の追加で使う語彙をあらかじめ用意しているため(時代ミステリ・倒叙・読者への挑戦状・法廷ミステリ・多重解決)。新規作品を追加する際、既存タグで表現しきれない要素があれば追加してよいが、**新規タグにspoilerフラグを付けるかは上記の基準で必ず判断する**。

## デザイン方針

- パステルカラー基調、グラデーションはなるべく使わない。**メインアクセントは藤色(`--color-iris` / `--color-iris-strong` / `--color-iris-deep`)**。ranobe-dbの水色・manga-dbのオレンジ・game-dbのグリーンと区別するための独自トリオで、装飾用パステル(pink/mint/yellow/peach/blue)のローテーションとは分けている
- `--color-primary`(リンク・ブランド用の紫)とアクセントの藤色は別変数。隣り合ったときに溶けないよう色を離してある
- ページ背景は黒一色固定(`:root`で不変。`[data-theme="light"]`のパステル明テーマ定義は残しているが現状UIから到達不能=未使用のドーマント状態)
- 装飾(影・グラデーション・点線ボーダー等)は基本つけない。「真っ黒でよい」「シャドウも微妙」など過剰な装飾は嫌われる傾向
- 見出しは`M PLUS Rounded 1c`、本文は`Noto Sans JP`
- PC画面の余白を無駄にしない(`.work-grid`は`repeat(auto-fill, minmax(min(450px, 100%), 1fr))`、`.page`は`max-width: 1200px`)

## コマンド

```sh
npm install
npm run dev       # http://localhost:5173/mystery-db/
npm run build      # 型チェック + データ整合性チェック + ビルド + プリレンダー
npm run preview
npm run fetch-covers
```

`main`へのpushで`.github/workflows/deploy.yml`が自動ビルド・GitHub Pagesデプロイを行う。

## 表紙画像

`scripts/fetch-covers.mjs` は ranobe-db 版をベースに、3段フォールバック(楽天ブックス → 楽天Kobo → BOOK☆WALKER)をそのまま引き継いでいる。ミステリ向けの変更点:

- **全経路で著者名一致を必須にしている**(ranobe-dbは緩いキーワードで当たった候補にのみ課していた)。『点と線』『火車』のようにタイトルが短く一般的な作品が多く、前方一致だけでは無関係な本・同名映画のノベライズ・コミカライズが混ざるため。manga-dbが同じ理由で導入したロジックの移植
- 楽天ブックスのジャンル除外に **`001017`(ライトノベル)** を追加(`001001` コミック除外はranobe-dbから継承)。BOOK☆WALKERの `BW_REJECTED_GENRES` にも「ライトノベル」を追加
- 検索キーワードは**邦題**を使う(原題では日本の書誌に当たらない)
- **楽天の認証情報は姉妹サイトと共用できる**(現行の新gateway形式は各サイトのRefererから通ることを2026-08-04にmystery-dbでも実証済み)ので新規アプリ登録は不要。`RAKUTEN_APP_ID`/`RAKUTEN_ACCESS_KEY` を渡さずに実行すると BOOK☆WALKER のみで解決する
- **邦訳版の書影は、works.jsonに登録した版と別レーベルになることがある**。1作品1エントリの設計上、表紙はタイトルで解決するため、複数の訳者・レーベルから出ている海外古典では楽天が別の版を拾う。作品としては同一なので採用してよいが、`covers-cache.json`の`note`に食い違いを書き残すこと。実例: 『緋色の研究』(登録は新潮文庫・延原謙訳 → 書影は創元推理文庫の新訳版)、『Yの悲劇』(登録はハヤカワ・ミステリ文庫・宇野利泰訳 → 書影は角川文庫版)、『D坂の殺人事件』(登録は光文社 → 書影は創元推理文庫の江戸川乱歩全集2)
- **江戸川乱歩・横溝正史のように漫画版が多数ある作家は、書影が漫画版でないか必ず目視すること**。『D坂の殺人事件』はBOOK☆WALKERの検索上位が『漫画 D坂の殺人事件』『漫画 心理試験』で埋まるが、ジャンル判定(「マンガ（漫画）」を除外)が効いて小説版が採用された。画像を実際に開いて確認済み
- **フラグ**: `--only=id1,id2` / `--force` / `--retry-misses`。**未解決分の再挑戦には必ず`--retry-misses`を使う**こと(`--force`は手動修正済みのエントリも上書きするため)
- 古い海外古典や絶版作品は3ストアのいずれにもないことがある。その場合はプレースホルダーのままにし、無理に埋めない

## SEO / SSG

ranobe-dbの構成をそのまま移植している。

- `src/ui/common/useSeo.ts`: `document.title`・meta description・canonical・OGP/Twitterカード・JSON-LD構造化データを`useEffect`内のDOM操作で設定する。**canonical/og:urlは`window.location.origin`ではなく固定の`SITE_ORIGIN`定数から組み立てる**(`scripts/prerender.mjs`はローカルの`vite preview`からページを取得するため、`window.location.origin`を使うとプリレンダー結果のcanonicalが`localhost`になる。ranobe-dbで実際に踏んだバグ)
- JSON-LD: 作品詳細=`Book`、著者・翻訳者・探偵=`Person`、出版社=`Organization`、加えて`BreadcrumbList`。トップは`WebSite`+`SearchAction`
- `scripts/prerender.mjs`(npm `postbuild`フック): `vite build`後に`vite preview`を起動してPlaywright(Chromium)で全ルートをクロールし、`dist/<route>/index.html`を書き出す。最後に`dist/index.html`を`dist/404.html`にコピーしてGitHub Pagesのフォールバックにする。CI(`.github/workflows/deploy.yml`)では`npx playwright install --with-deps chromium`を`npm run build`の前に実行している
- `public/sitemap.xml`: `scripts/generate-manifest.mjs`の末尾で生成(`.gitignore`対象)
- `public/robots.txt`: GitHub Pagesのプロジェクトページではオリジンルートのrobots.txtが優先されうるため、確実に索引させたい場合は Google Search Console にsitemapを手動登録するのが確実(ユーザー自身のGoogleアカウント操作が必要)
- `scripts/generate-ogp.mjs`(手動実行): Playwrightで1200×630のブランドバナーを生成し`public/og-image.png`に置く
- `scripts/generate-icons.mjs`(手動実行): `public/favicon.svg`と同じ意匠で`public/favicon.ico`(16/32/48/64px)と`public/apple-touch-icon.png`(180px)を生成する。Playwrightのページ内でGoogle Fontsから`M PLUS Rounded 1c`を読み込んでから描画するのは、このコンテナに同フォントが入っていないため(ImageMagickで直接SVGを変換すると別のsans-serifにフォールバックする)。**四隅は不透明な黒で塗り、アルファを残さない**: 姉妹サイトのアイコンは角丸(`rx=16`)で四隅が透明になっており、タブストリップやICO consumer によっては白く合成される。そのためmystery-dbのアイコンだけは角丸をやめて全面塗りにし、`convert`にも`-alpha remove -alpha off`を渡している。意匠を変えるときは`favicon.svg`とこのスクリプトの両方を直すこと
- Google Analytics: `index.html`にGA4のgtagスニペットを直書きしている(測定ID `G-JM8SW0R904`)。**姉妹サイトはそれぞれ固有のプロパティを持つ**(ranobe-db `G-2NR0M8VN1N` / manga-db `G-01FCSJVHQX` / game-db `G-V6407CNZ8Y`)ので、サイト間でIDを流用しないこと

## データ規模の推移

24作品(初回、2026-08-04)。著者17・探偵14・翻訳者6・出版社9・テーマ34(うちspoiler 4)・アワード11。国内18作品・海外6作品。目標は30作品前後だったが、Wikipedia日本語版で刊行年・受賞歴・訳者を裏取りできたものだけを採用した結果24作品で区切った。

## 既知の未着手事項

- ~~**楽天ブックス経由の表紙取得が未実行**~~ → **2026-08-04に解消。24作品中24作品(100%)が解決済み**(内訳: BOOK☆WALKER 16 / 楽天ブックス 8)。最初にBOOK☆WALKERのみで16件を解決したあと、ユーザーから楽天の認証情報を受け取り`--retry-misses`で残り8件を解決した。紙の書籍が中心の古典・文庫作品(本陣殺人事件・獄門島・火車・64・満願・氷菓・Yの悲劇)は楽天ブックスの方が明確に強い。
  - **BOOK☆WALKERの誤マッチ実例(対処済み)**: 『緋色の研究』でBOOK☆WALKERが『【大活字シリーズ】英語原文で味わうSherlock Holmes1』(英語原文の学習用版)を拾っていた。著者名一致・ジャンル判定を通り抜けるタイプの誤マッチなので、`matchedTitle`の目視確認は省略しないこと。**`--force`で回すとこの種の誤マッチが復活するので、再挑戦には必ず`--retry-misses`を使う**
- **新人賞 / ランキング系のフィルター**: 受賞歴を種別で区別してフィルターする機能は未実装(ranobe-dbと同じ課題)。`awards.json`に賞の種別フィールドの追加が必要
