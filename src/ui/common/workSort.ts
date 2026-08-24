import type { WorkGenerated } from "../../types";

/**
 * 作品リストの並べ替えと、発行部数まわりの絞り込み・整形。
 *
 * 並べ替えの選択肢と比較関数は WorkListPage(作品一覧)と useWorkFilter(テーマ/著者/レーベル等の
 * 詳細ページ)に**同一のものが2つ**あった。片方にだけ選択肢を足すと、同じサイト内で並べ替えメニューの
 * 中身が違うという分かりにくい壊れ方をするので、ここに1本化している。
 * 「そのページでしか意味のない絞り込み」(レーベル・テーマ等)は各ページに置いたままにする。
 */

export const SORT_OPTIONS: { value: string; label: string }[] = [
  { value: "year-desc", label: "刊行年が新しい順" },
  { value: "year-asc", label: "刊行年が古い順" },
  { value: "kana", label: "五十音順" },
  { value: "copies-desc", label: "発行部数が多い順" },
];

/** 未判明を -1 にして常に末尾へ送る。0 だと「0部と公表された作品」と区別が付かなくなる。 */
const copiesOf = (w: WorkGenerated) => w.circulation?.copies ?? -1;

export function sortWorks(works: WorkGenerated[], sort: string): WorkGenerated[] {
  if (sort === "year-asc") return [...works].sort((a, b) => a.firstPublishedYear - b.firstPublishedYear);
  if (sort === "year-desc") return [...works].sort((a, b) => b.firstPublishedYear - a.firstPublishedYear);
  if (sort === "kana") return [...works].sort((a, b) => a.titleKana.localeCompare(b.titleKana, "ja"));
  if (sort === "copies-desc") {
    // 公表値は「500万部」「1000万部」のようなキリのいい数字に集中するので同数がとても多い。
    // かなでタイブレークして、ビルドごとにプリレンダーHTMLの並びが揺れないようにする
    // (generate-manifest.mjs の relatedWorkIds を id でタイブレークしているのと同じ理由)。
    return [...works].sort(
      (a, b) => copiesOf(b) - copiesOf(a) || a.titleKana.localeCompare(b.titleKana, "ja"),
    );
  }
  return works;
}

export const COPIES_FILTER_OPTIONS: { value: string; label: string }[] = [
  { value: "known", label: "部数判明分のみ" },
  { value: "1m", label: "100万部以上" },
  { value: "10m", label: "1000万部以上" },
];

const COPIES_THRESHOLD: Record<string, number> = { known: 1, "1m": 1_000_000, "10m": 10_000_000 };

export function matchesCopies(w: WorkGenerated, filter: string) {
  if (!filter) return true;
  const min = COPIES_THRESHOLD[filter];
  if (!min) return true; // 知らない値がURLに入っていたら絞り込まない
  return (w.circulation?.copies ?? 0) >= min;
}

/** 30000000 → 「3000万部」、120000000 → 「1億2000万部」、8000 → 「8000部」。
 *  公表値は万部単位で発表されるので、万未満の端数が出ることはまずない。 */
export function formatCopies(copies: number): string {
  if (copies >= 100_000_000) {
    const oku = Math.floor(copies / 100_000_000);
    const man = Math.floor((copies % 100_000_000) / 10_000);
    return man > 0 ? `${oku}億${man}万部` : `${oku}億部`;
  }
  // 万の位に桁区切りは入れない。部数は「3000万部」と書くのが普通で、toLocaleString を
  // 通すと4桁から区切られて「3,000万部」になる(1000万部以上の作品で実際にそうなった)。
  if (copies >= 10_000) return `${Math.floor(copies / 10_000)}万部`;
  return `${copies.toLocaleString("ja-JP")}部`;
}

/** 「2017-04」→「2017年4月時点」、「2017」→「2017年時点」。 */
export function formatAsOf(asOf: string): string {
  const [year, month] = asOf.split("-");
  return month ? `${year}年${Number(month)}月時点` : `${year}年時点`;
}

export const SCOPE_LABEL: Record<string, string> = { domestic: "国内", worldwide: "全世界" };
