#!/usr/bin/env python3
"""日本語版Wikipediaの本文から「シリーズ累計発行部数」の候補を抜き出し、目視確認用のTSVを吐く。

  python3 scripts/fetch-circulation.py out.tsv [--limit 50] [--only id1,id2] [--refill]

出力は**そのまま circulation.json にはならない**。1行1作品のTSVを人間が確認し、
scripts/apply-circulation.py で反映する(award_wiki.py → award_cand.py と同じ流れ)。

列: workId / title / copies / asOf / scope / kind / 抜き出した原文 / wikipediaUrl

kind は機械が付けた見立て: original(「原作の」と明記) / series(素のシリーズ累計) /
franchise(関連書籍・漫画込みの合計かもしれない → **そのまま反映しない**)。

## 集めているのは発行部数であって実売ではない

ラノベの実売冊数は公開されていない。公表されるのは出版社発表の「刷った部数」(電子版・海外版を
含むことが多い)で、必ず「◯年◯月時点」とセットでしか意味を持たない。UIのラベルもそう表記する。

## 機械抽出の4つの罠(実データで踏んだもの。緩めると静かに壊れる)

1. <ref> と {{Cite}} を先に落とす。『ソードアート・オンライン』の記事の脚注には
   『とある魔術の禁書目録』『魔法科高校の劣等生』の部数が入っており、残したまま拾うと
   **他作品の数字をその作品の値として書き込む**
2. 初版・単巻を除く。『涼宮ハルヒの憂鬱』の「初版51万部」は累計ではない
3. 最大値ではなく最新の時点を採る。『ようこそ実力至上主義の教室へ』は
   50万→100万→200万→1160万部の推移が全部書かれている
4. フランチャイズ合計と作品本体を混同しない。「とあるシリーズ 3100万部」はスピンオフ込みで、
   原作本体は1800万部。機械には判別できないので原文をTSVに残して人間に見せる
"""
import argparse
import datetime
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

TODAY = datetime.date.today().isoformat()

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prep import get, norm  # noqa: E402
from circulation_common import (  # noqa: E402
    EXCLUDE, NUMBER, RANK_FRANCHISE, RANK_NAME, RANK_ORIGINAL, RANK_PLAIN,
    TSV_HEADER, covers_whole_series, rank_of, scope_of, to_copies,
)

WIKI_PREFIX = "https://ja.wikipedia.org/wiki/"


def title_from_url(url: str) -> str:
    """記事名は**プレフィックスを剥がして**取り出す。`rsplit("/")` で最後の要素を取ると
    『Fate/strange Fake』が「strange Fake」に化けて記事が引けない(実際に踏んだ)。"""
    path = url[len(WIKI_PREFIX):] if url.startswith(WIKI_PREFIX) else url.rsplit("/", 1)[-1]
    return urllib.parse.unquote(path).replace("_", " ")

SRC = Path(__file__).resolve().parent.parent / "public" / "data" / "source"
WIKI_API = "https://ja.wikipedia.org/w/api.php"
SLEEP = 1.5

# 罠1: 脚注・テンプレートは本文より先に落とす。ここを緩めると他作品の数字が混入する。
# テンプレートは種類を列挙せず**すべて落とす**。Cite/Sfnp だけを狙っていたときに
# 『ひぐらしのなく頃に』の「累計で約80万部売れた{{要出典|date=2021年8月}}」から
# **出典要求タグの日付を発行時点として拾った**。本文の部数記述を探すのが目的なので、
# テンプレートの中身は一律に不要。入れ子は2段まで内側から剥がす。
REF_PATTERNS = [
    re.compile(r"<ref[^>]*/>", re.I),
    re.compile(r"<ref[^>]*>.*?</ref>", re.I | re.S),
]
TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")

# 「累計」「発行部数」等の語と、数値+単位が同じ文にあるものだけを候補にする。
KEYWORD = re.compile(r"累計|発行部数|発行[はがを]|突破|出荷部数")
# 「2026年（令和8年）5月時点で」のように和暦が括弧で挟まる書き方が多いので、年と月の間の
# 短い括弧書きは読み飛ばす(挟まれると月を取り逃して asOf が年だけになる)。
ASOF = re.compile(r"(\d{4})年(?:\s*(?:[（(][^）)]{0,12}[）)])?\s*(\d{1,2})\s*月)?")
SAME_YEAR = re.compile(r"同年\s*(\d{1,2})\s*月")

# 罠2(初版・単巻の除外)・罠4(作品本体かフランチャイズ合計か)の語彙と数値変換は、
# 楽天版 fetch-circulation-rakuten.py と共有する circulation_common.py に置いてある。
# 情報源が違っても「その数字は作品本体のものか」を見分ける語彙は同じで、別々に持つと
# 片方だけ直したときに静かにずれる(UIのSORT_OPTIONSで同じ失敗をした)。


def strip_refs(wikitext: str) -> str:
    out = wikitext
    for pat in REF_PATTERNS:
        out = pat.sub(" ", out)
    for _ in range(3):  # 内側から剥がすので入れ子のぶんだけ繰り返す
        out, n = TEMPLATE.subn(" ", out)
        if not n:
            break
    # 見出し記号・強調・内部リンクの装飾だけ外す(リンク先の表示名は残す)
    out = re.sub(r"\[\[(?:[^\[\]|]*\|)?([^\[\]|]*)\]\]", r"\1", out)
    out = out.replace("'''", "").replace("''", "")
    return out


def fetch_wikitext(title: str) -> str | None:
    """記事の**全文**を取る。部数の記述は導入部だけでなく「概要」「書誌情報」節にも出るため、
    prep.py の wiki_lookup と違って rvsection=0 では絞らない。"""
    params = {
        "action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
        "format": "json", "formatversion": "2", "redirects": "1", "titles": title,
    }
    body = get(WIKI_API + "?" + urllib.parse.urlencode(params), sleep=SLEEP)
    if not body:
        return None
    try:
        pages = json.loads(body)["query"]["pages"]
    except Exception:
        return None
    if not pages or pages[0].get("missing"):
        # works.json の wikipediaUrl は記事名の表記ゆれで実在しないことがある
        # (『まよチキ！』が実際は『まよチキ!』、『Overlord』が『オーバーロード (小説)』など)。
        # NFKC正規化して一致する記事を検索で拾い直す(prep.py の wiki_lookup と同じ手当て)。
        resolved = search_title(title)
        if not resolved:
            return None
        params["titles"] = resolved
        body = get(WIKI_API + "?" + urllib.parse.urlencode(params), sleep=SLEEP)
        try:
            pages = json.loads(body)["query"]["pages"]
        except Exception:
            return None
        if not pages or pages[0].get("missing"):
            return None
    try:
        return pages[0]["revisions"][0]["slots"]["main"]["content"]
    except Exception:
        return None


def search_title(title: str) -> str | None:
    params = {"action": "query", "list": "search", "srsearch": title, "srlimit": "5",
              "format": "json", "formatversion": "2"}
    body = get(WIKI_API + "?" + urllib.parse.urlencode(params), sleep=SLEEP)
    if not body:
        return None
    try:
        hits = json.loads(body)["query"]["search"]
    except Exception:
        return None
    for h in hits:
        if norm(h["title"]) == norm(title):
            return h["title"]
    return None


def candidates(wikitext: str, medium: str = "novel", min_year: int = 0,
               volume_count: int = 0) -> list[dict]:
    """部数らしき記述を集める。選ぶのは呼び出し側(と最終的には人間)。

    **文ではなく読点区切りの節を単位にする。** 1つの文に
    「2011年6月時点で…800万部を突破し、2017年12月時点で…2000万部を突破している」のように
    時点と数字の組が複数入っていることが多く、文単位で「最大の数字」と「最初の日付」を別々に
    拾うと**2000万部に2011年6月が付く**(罠3)。節に割れば組が壊れない。
    """
    found = []
    for sid, sentence in enumerate(re.split(r"[。\n]", strip_refs(wikitext))):
        sentence = sentence.strip()
        if not sentence or not KEYWORD.search(sentence) or EXCLUDE.search(sentence):
            continue
        # wikitable の行は本文ではない。セルの主語が別カラムにあるので、そのまま読むと
        # 『ドラゴンボール』の記事で別作品の年次表(|2023年時点累計発行部数||2800万部||)を
        # 本作の数字として拾う。
        if sentence.startswith(("|", "!", "{|")) or "||" in sentence:
            continue
        last_year, last_asof = "", ""
        for clause in sentence.split("、"):
            # 「同年7月時点で」は直前の節の西暦を引き継ぐ
            asof = ""
            m = ASOF.search(clause)
            if m:
                last_year = m.group(1)
                asof = f"{m.group(1)}-{int(m.group(2)):02d}" if m.group(2) else m.group(1)
            elif last_year and (sy := SAME_YEAR.search(clause)):
                asof = f"{last_year}-{int(sy.group(1)):02d}"
            else:
                # 時点だけが別の節に切り出されている書き方がある:
                # 「2013年1月の刊行以来、2025年5月時点で、シリーズ累計発行部数は…2000万部を突破している」
                # 数字の節に日付が無いときは、同じ文で**直近に出た**時点を引き継ぐ。
                asof = last_asof
            # **作品の刊行年より古い時点はありえない。** 『疾風ロンド』(2013年刊)の記事には
            # 「1996年10月14日に…『名探偵の呪縛』以来17年ぶりとなり、発売10日で100万部を突破」
            # とあり、別の本の年を時点として引き継いでいた。古い日付は「時点なし」に落として
            # 反映側で弾かせる(誤った日付を書き込むより、空欄で人間に回すほうが安全)。
            if asof and min_year and int(asof[:4]) < min_year:
                asof = ""
            if asof:
                last_asof = asof

            # 「1〜3巻合わせて」のような部分値は捨てる(既刊全体を覆う範囲なら通す)
            if not covers_whole_series(clause, volume_count):
                continue

            best = None
            for nm in NUMBER.finditer(clause):
                copies = to_copies(nm.group(1))
                if copies and (best is None or copies > best):
                    best = copies
            if best is None:
                continue

            rank = rank_of(clause, medium)
            found.append({
                "copies": best,
                "asOf": asof,
                "scope": scope_of(clause, sentence),
                "rank": rank,
                "sid": sid,
                "text": clause[:160],
            })
    return found


def _newest(pool: list[dict]) -> dict:
    """時点付きを優先し、そのなかで最も新しいものを採る(罠3: 最大値ではない)。
    時点付きが1つも無ければ最大値に落とす — その場合 asOf が空欄のままTSVに出るので、
    人間が記事を見て埋めることになる。

    **同じ時点に複数の数字があるときは、大きい方ではなくランクの低い(=作品本体に近い)方を採る。**
    『灼眼のシャナ』の「2022年1月時点でシリーズ累計860万部、関連書籍を含めた累計1080万部」は
    どちらの節も同じ時点になるので、数字の大小で選ぶと関連書籍込みの1080万部を掴む。
    """
    dated = [f for f in pool if f["asOf"]]
    if dated:
        return max(dated, key=lambda f: (f["asOf"], -f["rank"], f["copies"]))
    return max(pool, key=lambda f: (-f["rank"], f["copies"]))


def pick(found: list[dict]) -> dict | None:
    """**まず新しさで選び、ランクは同じ文の中の曖昧さを解くためだけに使う。**

    ランクを新しさより優先すると、『涼宮ハルヒの憂鬱』で2011年の「文庫本800万部」が
    2017年の「全世界2000万部」に勝ってしまうし、『ようこそ実力至上主義の教室へ』では
    2017年の「原作100万部」が2026年の「1160万部」に勝ってしまう(実際に踏んだ)。
    一方、『とある魔術の禁書目録』の「原作1800万部(2019年6月)」と
    「とあるシリーズ3100万部(同年7月)」のように**同じ文が本体と全体を並べている**ときだけは、
    新しさで選ぶと全体の数字を掴む。そこで「原作」と明記された節が同じ文にあれば、
    その文の他の節を落とす。
    """
    if not found:
        return None

    # 全体で最も新しいものがフランチャイズ合計しかないなら、印を付けたまま人間に渡す。
    # ここで合計を捨てて古い別の数字に落ちると、『転生したらスライムだった件』で
    # 記事の別の箇所にある無関係な50万部を拾ってしまう(実際に踏んだ)。
    top = _newest(found)
    if top["rank"] == RANK_FRANCHISE:
        return top

    pool = [f for f in found if f["rank"] != RANK_FRANCHISE]
    original_sentences = {f["sid"] for f in pool if f["rank"] == RANK_ORIGINAL}
    narrowed = [f for f in pool if f["sid"] not in original_sentences or f["rank"] == RANK_ORIGINAL]
    return _newest(narrowed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", help="出力TSV(目視確認用)")
    ap.add_argument("--limit", type=int, default=0, help="処理する作品数の上限(0で無制限)")
    ap.add_argument("--only", default="", help="work id をカンマ区切りで指定")
    ap.add_argument("--refill", action="store_true",
                    help="解決済み・確認済みの作品を飛ばす(欠損の埋め直し用)")
    ap.add_argument("--medium", default="novel", choices=["novel", "manga"],
                    help="判定語彙の切り替え。漫画DBでは漫画が本体、小説版が除外対象になる")
    ap.add_argument("--retry-misses", action="store_true",
                    help="--refill でも circulation-misses.json の作品は再度対象にする")
    args = ap.parse_args()

    works = json.loads((SRC / "works.json").read_text(encoding="utf-8"))
    circ_path = SRC / "circulation.json"
    existing = json.loads(circ_path.read_text(encoding="utf-8")) if circ_path.exists() else {}
    # 確認済みだが値を入れられなかった作品(フランチャイズ合計しか無い・時点が無い等)。
    # ここに記録しておかないと、却下した作品が毎バッチ候補に出てきて永久に片付かない。
    # fetch-covers.mjs が coverUrl:null を残して --retry-misses で拾い直すのと同じ作り。
    miss_path = SRC / "circulation-misses.json"
    misses = json.loads(miss_path.read_text(encoding="utf-8")) if miss_path.exists() else {}
    if not args.retry_misses:
        existing = {**existing, **misses}

    only = {s.strip() for s in args.only.split(",") if s.strip()}
    targets = []
    for w in works:
        url = (w.get("externalLinks") or {}).get("wikipediaUrl")
        if not url:
            continue
        if only and w["id"] not in only:
            continue
        if args.refill and w["id"] in existing:
            continue
        targets.append((w, url))
    if args.limit:
        targets = targets[: args.limit]

    print(f"fetch-circulation: {len(targets)} works to probe", file=sys.stderr)
    rows, hits = [], 0
    no_figure = []
    for i, (w, url) in enumerate(targets, 1):
        wikitext = fetch_wikitext(title_from_url(url))
        if wikitext:
            # 刊行年は sf-db が jpPublishedYear、他は firstPublishedYear を持つ
            year = w.get("firstPublishedYear") or w.get("jpPublishedYear") or 0
            best = pick(candidates(wikitext, args.medium, year, w.get("volumeCount") or 0))
            if not best:
                # 記事は取れたが部数の記述が無かった。記録しないと --refill が毎回また
                # 同じ記事を引きに行き、**未調査件数がいつまでも減らない**(実際にそうなった)。
                # 記事は更新されるので、拾い直したいときは --retry-misses を使う。
                no_figure.append(w["id"])
            if best:
                hits += 1
                # kind 列は人間への注意書き。franchise は「作品本体の数字ではないかもしれない」印で、
                # そのまま反映せず記事を読んで判断すること(機械では原作分を分離できない)。
                kind = RANK_NAME[best["rank"]]
                rows.append([w["id"], w["title"], str(best["copies"]), best["asOf"],
                             best["scope"], kind, best["text"].replace("\t", " "), url])
        if i % 25 == 0 or i == len(targets):
            print(f"  {i}/{len(targets)} done ({hits} with a figure)", file=sys.stderr)
        time.sleep(SLEEP)

    header = TSV_HEADER
    Path(args.out).write_text(
        "\n".join(["\t".join(header)] + ["\t".join(r) for r in rows]) + "\n", encoding="utf-8")
    print(f"fetch-circulation: wrote {len(rows)} candidate rows to {args.out}", file=sys.stderr)

    if no_figure:
        # 走らせるたびに書き足す(apply-circulation.py も同じファイルを触るので読み直してから書く)
        current = json.loads(miss_path.read_text(encoding="utf-8")) if miss_path.exists() else {}
        for work_id in no_figure:
            current.setdefault(work_id, {"reason": "no-figure", "checkedAt": TODAY})
        miss_path.write_text(
            json.dumps(dict(sorted(current.items())), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        print(f"fetch-circulation: {len(no_figure)}件は記述なしとして記録 → {miss_path}", file=sys.stderr)
    print("確認してから scripts/apply-circulation.py で反映すること"
          "(フランチャイズ合計・時点の取り違えは機械では弾けない)", file=sys.stderr)


if __name__ == "__main__":
    main()
