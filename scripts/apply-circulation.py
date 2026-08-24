#!/usr/bin/env python3
"""目視確認済みのTSVを public/data/source/circulation.json にマージする。

  python3 scripts/apply-circulation.py reviewed.tsv [--force]

TSVの列は fetch-circulation.py の出力と同じ:
  workId / title / copies / asOf / scope / kind / sourceText / wikipediaUrl

kind が franchise の行は「関連書籍・漫画込みの合計かもしれない」印なので**拒否する**。
記事を読んで作品本体の数字に直し、kind を series / original に書き換えてから通すこと。

apply_batch.py と同じく**既存キーは上書きせずスキップ**する(--force で上書き)。
確認の過程で行ごと消したものは当然反映されない。asOf を空欄のままにした行は
「時点不明の発行部数」になってしまうので受け付けない(generate-manifest.mjs 側でも弾かれる)。
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "public" / "data" / "source"
TODAY = datetime.date.today().isoformat()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tsv", help="目視確認済みTSV")
    ap.add_argument("--force", action="store_true", help="既存エントリも上書きする")
    args = ap.parse_args()

    works = json.loads((SRC / "works.json").read_text(encoding="utf-8"))
    known = {w["id"] for w in works}

    circ_path = SRC / "circulation.json"
    circ = json.loads(circ_path.read_text(encoding="utf-8")) if circ_path.exists() else {}
    # 確認したが値を入れられなかった作品。記録しないと fetch-circulation.py --refill が
    # 毎回また候補に出してきて、同じ行を何度も却下し続けることになる。
    miss_path = SRC / "circulation-misses.json"
    misses = json.loads(miss_path.read_text(encoding="utf-8")) if miss_path.exists() else {}

    added = skipped = 0
    errors = []
    lines = Path(args.tsv).read_text(encoding="utf-8").splitlines()
    if not lines:
        print("apply-circulation: 空のTSV", file=sys.stderr)
        sys.exit(1)
    # **列は位置ではなく名前で引く。** 収集スクリプトごとに補助列(state/match/note等)が
    # 増えるので、位置決め打ちだと列を足しただけで sourceUrl が別の列を指すようになる。
    header = [c.strip() for c in lines[0].split("\t")]
    idx = {name: i for i, name in enumerate(header)}
    for required in ("workId", "copies", "asOf", "scope"):
        if required not in idx:
            print(f"apply-circulation: ヘッダに \"{required}\" 列がない: {header}", file=sys.stderr)
            sys.exit(1)

    def cell(cols, name):
        i = idx.get(name)
        return cols[i].strip() if i is not None and i < len(cols) else ""

    for lineno, line in enumerate(lines[1:], start=2):  # 1行目はヘッダ
        if not line.strip():
            continue
        cols = line.split("\t")
        work_id = cell(cols, "workId")
        copies = cell(cols, "copies")
        as_of = cell(cols, "asOf")
        scope = cell(cols, "scope")
        kind = cell(cols, "kind")
        source_url = cell(cols, "sourceUrl")
        note = cell(cols, "note")
        if not work_id:
            errors.append(f"L{lineno}: workId が空")
            continue

        if kind == "franchise":
            errors.append(f"L{lineno} ({work_id}): kind=franchise のまま。関連書籍込みの合計でないか"
                          f"記事で確認し、作品本体の数字に直してから通すこと")
            misses[work_id] = {"reason": "franchise", "checkedAt": TODAY}
            continue
        if work_id not in known:
            errors.append(f"L{lineno}: 未知の work id \"{work_id}\"")
            continue
        if not copies.isdigit() or int(copies) <= 0:
            errors.append(f"L{lineno} ({work_id}): copies が正の整数でない \"{copies}\"")
            continue
        if not as_of:
            errors.append(f"L{lineno} ({work_id}): asOf が空欄(発行部数は時点とセットでないと意味を持たない)")
            misses[work_id] = {"reason": "no-date", "checkedAt": TODAY}
            continue
        if scope not in ("domestic", "worldwide"):
            errors.append(f"L{lineno} ({work_id}): scope は domestic / worldwide のいずれか \"{scope}\"")
            continue
        if work_id in circ and not args.force:
            skipped += 1
            continue

        entry = {"copies": int(copies), "asOf": as_of, "scope": scope}
        if source_url:
            entry["sourceUrl"] = source_url
        if note:
            entry["note"] = note
        circ[work_id] = entry
        misses.pop(work_id, None)  # 値が入ったら miss ではなくなる
        added += 1

    if errors:
        print("apply-circulation: 反映できない行があります:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)

    # 差分を読みやすく保つため id 順に並べて書き出す
    circ_path.write_text(
        json.dumps(dict(sorted(circ.items())), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    miss_path.write_text(
        json.dumps(dict(sorted(misses.items())), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"apply-circulation: {added}件を反映、{skipped}件を既存としてスキップ"
          f"(合計 {len(circ)}件) → {circ_path}")
    print(f"apply-circulation: 確認済みだが値なし {len(misses)}件 → {miss_path}")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
