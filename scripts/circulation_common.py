#!/usr/bin/env python3
"""累計発行部数の収集スクリプトが共有する語彙とヘルパー。

fetch-circulation.py(Wikipedia本文)と fetch-circulation-rakuten.py(楽天ブックス/Koboの
商品説明)は情報源が違うだけで、**「その数字は作品本体のものか」を見分ける語彙は同じ**。
別々に持つと片方だけ直したときに静かにずれるので(UIのSORT_OPTIONSで同じ失敗をした)、
ここに1本化する。ファイル名にハイフンが入っていて import できないので、
共有分だけをこのモジュールに置いている。
"""
import re

# **「1億4000万部」のような複合表記を1つの数として掴むこと。**
# 「万部」だけを見ていると『進撃の巨人』の「1億4000万部」から4000万部を、
# 『名探偵コナン』の「2億7000万部」から7000万部を拾う(漫画DBへの移植時に発覚)。
# ラノベは最大でも6200万部で1億に届いていなかったため、それまで表に出なかった。
NUMBER = re.compile(r"((?:[\d,]+(?:\.\d+)?\s*[億万]\s*)+)部")
_UNIT = re.compile(r"([\d,]+(?:\.\d+)?)\s*([億万])")

# 罠4: フランチャイズ合計と作品本体の見分け。日本語版Wikipediaも出版社の宣伝文も
# ほぼ同じ言い回しをするので、同じ語彙で判定できる。
# 「コミカライズ」は「コミック」を部分文字列に持たない(コ-ミ-カ vs コ-ミ-ッ-ク)ので個別に要る。
# **「本体」と「フランチャイズ」は媒体によって入れ替わる。** 小説DBでは漫画の部数が除外対象だが、
# 漫画DBでは漫画こそが本体で、ノベライズのほうが除外対象になる。姉妹サイトへ移植するとき
# ここを共通のままにすると、漫画DBで正しい数字を franchise として弾いてしまう。
MEDIUM = {
    "novel": {
        "original": re.compile(r"原作(?:小説)?|小説版"),
        "franchise": re.compile(
            r"関連(?:書籍|作品|シリーズ)|スピンオフ|漫画|コミック|コミカライズ|メディアミックス"
            r"|(?:書籍|シリーズ)全体"),
    },
    "manga": {
        "original": re.compile(r"単行本|コミックス|原作漫画"),
        "franchise": re.compile(
            r"関連(?:書籍|作品|シリーズ)|スピンオフ|小説版|ノベライズ|novelize|メディアミックス"
            r"|(?:書籍|シリーズ)全体"),
    },
}
WORLDWIDE = re.compile(r"全世界|世界累計|世界[のでは]?累計|海外|翻訳版")

# 累計ではない部数(初版・単巻)、および全体の内訳を述べているだけの文。
# 『鬼滅の刃』の「そのうち5600万部は海外での発行部数である」を総数として拾ってしまった。
EXCLUDE = re.compile(
    r"初版|単巻|重版|第\s*\d+\s*巻|\d+\s*巻(?:目)?の|1巻(?:のみ)?[はがで]"
    r"|そのうち|のうち\s*\d|内訳"
    # 国・言語ごとの部数は全体の数字ではない。『NARUTO』の記事には
    # 「フランス語版の累計出版部数は3300万部」があり、時点が新しいぶんだけ
    # 本来の国内1億5300万部に勝ってしまう。
    r"|[^\s、。]{1,8}語版"
    r"|(?:ドイツ|フランス|イタリア|スペイン|タイ|中国|韓国|台湾|北米|米国|アメリカ|欧州|ロシア|ブラジル)[での]"
    # 雑誌の発行部数。『ドラゴンボール』の記事の「『週刊少年ジャンプ』発行部数600万部」は
    # 掲載誌の部数であって作品の部数ではない。
    r"|(?:週刊|月刊|季刊)[^\s、。]{0,12}(?:の)?発行部数"
    # **著者の生涯累計**。「著作の国内累計発行部数が1億部を突破した」は東野圭吾個人の
    # 通算部数で、その作家の全作品の記事に同じ文が入っている。mystery-db では18作品が
    # 揃って1億部になり、放置するとランキングの上位を1人の作家が占める。
    r"|著作(?:の|は|が)|著者の(?:累計|通算)|作家生活|通算(?:の)?発行部数|全作品|刊行作品"
    # 作家の通算部数は記念イベント名の形でも出てくる。『境界のRINNE』の記事の
    # 「2017年の『高橋留美子作品全世界2億部突破記念』に初公開された…」を本作の部数として
    # 拾っていた(実際は約1000万部)。「本作品は100万部突破した」は本作の話なので消さない。
    r"|突破記念|作品全世界|作品累計")

# 巻の範囲を合計した数字。**範囲が既刊全体を覆っているなら正しい値**なので、EXCLUDE に
# 入れて一律に捨ててはいけない。『銀の匙』の「1 - 3巻合わせて250万部」は全15巻中3巻ぶんの
# 部分値だが、『逃げ上手の若君』の「単行本1〜24巻までの累計500万部」は全24巻=シリーズ累計。
# 上限を volumeCount と比べて判断する(呼び出し側が巻数を渡す)。
VOLUME_RANGE = re.compile(r"(\d+)\s*[-−–—~〜]\s*(\d+)\s*巻")


WHOLE_SERIES_RATIO = 0.8


def covers_whole_series(text: str, volume_count: int) -> bool:
    """巻範囲の記述が実質シリーズ全体を覆っているか。範囲表記が無ければ True(判断不要)。

    完全一致では厳しすぎる。『逃げ上手の若君』の「単行本1〜24巻までの累計500万部(2025年3月時点)」は
    全26巻のうち24巻ぶんで、**その時点ではほぼ全巻**なので正当な累計値。一方『銀の匙』の
    「1 - 3巻合わせて250万部」は全15巻のうち3巻ぶんで、初期巻の販促値にすぎない。
    記事が書かれた時点の巻数は分からないので、現在の既刊数に対する割合で代用する。
    """
    m = VOLUME_RANGE.search(text or "")
    if not m:
        return True
    if not volume_count:
        return False  # 巻数が分からないなら部分値の疑いを残す
    start, end = int(m.group(1)), int(m.group(2))
    if start > 1:
        return False  # 途中の巻から数えた範囲は累計ではない
    return end >= volume_count * WHOLE_SERIES_RATIO

RANK_ORIGINAL, RANK_PLAIN, RANK_FRANCHISE = 0, 1, 2
RANK_NAME = {RANK_ORIGINAL: "original", RANK_PLAIN: "series", RANK_FRANCHISE: "franchise"}


def to_copies(text: str) -> int | None:
    """NUMBER の第1グループ(「1億4000万」「1,200万」「6億」)を部数に直す。
    万・億が付かない裸の数字は部数の桁として信用しない(NUMBER が単位を必須にしている)。
    宣伝文には「1,200万部」のように桁区切り入りで書かれることがある。"""
    total = 0
    for m in _UNIT.finditer(text or ""):
        try:
            value = float(m.group(1).replace(",", ""))
        except ValueError:
            return None
        total += value * (100_000_000 if m.group(2) == "億" else 10_000)
    return int(total) or None


def rank_of(text: str, medium: str = "novel") -> int:
    """その一節が作品本体を指しているか、フランチャイズ合計を指しているか。
    `medium` は "novel"(小説DB) / "manga"(漫画DB)。判定語彙が入れ替わる。"""
    vocab = MEDIUM[medium]
    if vocab["franchise"].search(text):
        return RANK_FRANCHISE
    if vocab["original"].search(text):
        return RANK_ORIGINAL
    return RANK_PLAIN


DOMESTIC = re.compile(r"国内|日本国内")


def scope_of(clause: str, sentence: str = "") -> str:
    """**節に書いてあることを文より優先する。** 『NARUTO』の
    「単行本の国内累計発行部数は…1億5300万部、全世界累計発行部数は2億5000万部」では、
    文全体を見ると「全世界」が入っているので、国内の数字に全世界の印が付いてしまう。"""
    if DOMESTIC.search(clause or ""):
        return "domestic"
    if WORLDWIDE.search(clause or ""):
        return "worldwide"
    return "worldwide" if WORLDWIDE.search(sentence or "") else "domestic"


TSV_HEADER = ["workId", "title", "copies", "asOf", "scope", "kind", "sourceText", "sourceUrl"]
