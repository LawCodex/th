#!/usr/bin/env python3
"""Convert cached OCS law JSON (see th_fetch.py) to LawCodex Markdown.

Usage: th_convert.py [RAW_DIR] [OUT_DIR]
"""
import glob
import json
import os
import re
import sys
from datetime import date

from bs4 import BeautifulSoup, NavigableString, Tag

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "_raw", "th")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..")
RETRIEVED = date.today().isoformat()

TYPE = {"constitution": "constitution", "organic-acts": "organic_act", "acts": "act",
        "codes": "code", "revolutionary": "announcement", "other": "act"}
CATTYPE = {"1B": "act", "1C": "emergency_decree", "1I": "revolutionary_council_announcement",
           "1J": "revolutionary_party_announcement", "1K": "cdrm_announcement",
           "1L": "ncpo_announcement", "1F": "palace_law", "1G": "royal_proclamation",
           "1H": "other_law", "1A": "organic_act", "10": "constitution", "1D": "code"}

# Thai consonants -> Latin (RTGS initial value) for ASCII file names
TR = dict(zip("กขฃคฅฆงจฉชซฌญฎฏฐฑฒณดตถทธนบปผฝพฟภมยรลวศษสหฬอฮ",
              ["k", "kh", "kh", "kh", "kh", "kh", "ng", "ch", "ch", "ch", "s", "ch", "y", "d", "t",
               "th", "th", "th", "n", "d", "t", "th", "th", "th", "n", "b", "p", "ph", "f", "ph",
               "f", "ph", "m", "y", "r", "l", "w", "s", "s", "s", "h", "l", "o", "h"]))
THDIG = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")

STRUCT_RANK = {"5": 0, "6": 0, "22": 0, "7": 1, "8": 2, "12": 2, "13": 2, "9": 3}
ARTICLE = {"4", "10"}
ART_RE = re.compile(r"^((?:มาตรา|ข้อ)\s*[๐-๙0-9]+(?:\s*/\s*[๐-๙0-9]+)?"
                    r"(?:\s*(?:ทวิ|ตรี|จัตวา|เบญจ|ฉ|สัตต|อัฏฐ|นว|ทศ|เอกาทศ|ทวาทศ|เตรส|จตุทศ|ปัณรส|โสฬส)\S*)?)\s*")


def translit(code):
    return "".join(TR.get(ch, ch) for ch in code).lower()


def clean_ws(s):
    s = s.replace(" ", " ").replace("​", "")
    return re.sub(r"\s+", " ", s).strip()


def esc(line):
    if re.match(r"^(\d+[.)]\s|[#>*+\-|]|=+\s*$)", line):
        return "\\" + line
    return line


def blocks(html, fnmap):
    """Return list of markdown blocks (paragraph strings or HTML tables)."""
    soup = BeautifulSoup(html or "", "html.parser")
    for img in soup.find_all("img"):
        img.decompose()
    for sp in soup.select("span.footnote-detect"):
        ref = (sp.get("href") or "").replace("#foot-", "")
        if ref in fnmap:
            sp.append(NavigableString(f"[^{fnmap[ref]}]"))
    out = []

    def table_html(t):
        for tag in t.find_all(True):
            for a in list(tag.attrs):
                if a not in ("colspan", "rowspan"):
                    del tag.attrs[a]
        for tag in t.find_all(["span", "font", "o:p", "b", "i", "u", "strong", "em", "a"]):
            tag.unwrap()
        for cell in t.find_all(["td", "th"]):
            paras = [clean_ws(p.get_text("")) for p in cell.find_all("p")] or [clean_ws(cell.get_text(""))]
            cell.clear()
            cell.append(NavigableString(" <br> ".join(x for x in paras if x)))
        h = str(t)
        h = re.sub(r"\s*\n\s*", "", h)
        return h.replace("&lt;br&gt;", "<br>")

    def walk(node):
        buf = []

        def flush():
            txt = clean_ws("".join(buf))
            if txt:
                out.append(esc(txt))
            buf.clear()
        for ch in node.children:
            if isinstance(ch, NavigableString):
                buf.append(str(ch))
            elif isinstance(ch, Tag):
                if ch.name == "table":
                    flush()
                    out.append(table_html(ch))
                elif ch.name in ("p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote",
                                 "ol", "ul", "tbody", "thead", "tr"):
                    flush()
                    if ch.find("table"):
                        walk(ch)
                    else:
                        txt = clean_ws(ch.get_text(""))
                        if txt:
                            out.append(esc(txt))
                elif ch.name == "br":
                    flush()
                else:
                    if ch.find(["p", "table", "div"]):
                        flush()
                        walk(ch)
                    else:
                        buf.append(ch.get_text(""))
        flush()
    walk(soup)
    return out


def yq(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def convert(d, used):
    info = d["lawInfo"]
    name = clean_ws(info.get("lawNameTh") or d["_list"]["lawNameTh"])
    code = info["lawCode"]
    cat = code.split("-")[1] if code.count("-") >= 2 else ""
    group = d["_category"]
    repealed = "(ยกเลิก)" in name
    status = {"01": "in_force", "02": "not_yet_in_force", "00": "repealed"}.get(info.get("stateId"), "unknown")
    if repealed:
        status = "repealed"
    pub = info.get("publishDateAd") or ""
    year_be = str(int(pub[:4]) + 543) if pub[:4].isdigit() else "unknown"
    cur = [t for t in d.get("timelines") or [] if t["timelineId"] == info["timelineId"]]
    last = cur[-1].get("timelineDateAd") if cur else info.get("effectiveDateStartAd")

    fn = translit(code)
    if group == "constitution":
        sub = "constitution" if not repealed else "constitution/historical"
        rel = f"{sub}/{year_be}-{fn}.md"
    elif group in ("acts", "revolutionary"):
        rel = f"{group}/{year_be}/{fn}.md"
    else:
        rel = f"{group}/{fn}.md"
    base = rel
    k = 2
    while rel in used:
        rel = base[:-3] + f"-{k}.md"
        k += 1
    used.add(rel)

    fns = d.get("footnoteList") or []
    fnmap = {f["footnoteUuid"]: i + 1 for i, f in enumerate(fns)}

    secs = sorted(d.get("lawSections") or [], key=lambda s: s.get("sectionSeq", 0))
    present = sorted({STRUCT_RANK[s["sectionTypeId"]] for s in secs if s["sectionTypeId"] in STRUCT_RANK})
    lvl = {r: i + 2 for i, r in enumerate(present)}
    art_level = min(6, 2 + len(present))

    lines = []
    first_title = True
    for s in secs:
        t = s["sectionTypeId"]
        bl = blocks(s.get("sectionContent"), fnmap)
        if t == "1":
            if first_title:
                first_title = False
                # the law name itself (already the H1) - keep its footnote refs as a paragraph if any
                extra = [b for b in bl if "[^" in b]
                lines += extra
                continue
            head = " ".join(re.sub(r"^\\", "", b) for b in bl if not b.startswith("<table")) or s.get("sectionName") or ""
            lines.append("## " + clean_ws(head))
            continue
        if t in STRUCT_RANK:
            heads = [re.sub(r"^\\", "", b) for b in bl if not b.startswith("<table")]
            head = " — ".join(heads) if heads else clean_ws(s.get("sectionLabel") or "")
            lines.append("#" * lvl[STRUCT_RANK[t]] + " " + head)
            continue
        if t in ARTICLE:
            label = None
            if bl and not bl[0].startswith("<table"):
                m = ART_RE.match(bl[0])
                if m:
                    label = clean_ws(m.group(1))
                    rest = bl[0][m.end():].strip()
                    bl = ([esc(rest)] if rest else []) + bl[1:]
            if not label:
                label = clean_ws(s.get("sectionLabel") or "")
            lines.append("#" * art_level + " " + label)
            lines += bl
            continue
        lines += bl

    fm = ["---", f"title: {yq(name)}"]
    if info.get("lawNameEn"):
        fm.append(f"title_en: {yq(clean_ws(info['lawNameEn']))}")
    fm += [f"identifier: {yq(code)}", f"type: {CATTYPE.get(cat, TYPE[group])}", "jurisdiction: th",
           "language: th"]
    if pub:
        fm.append(f"date: {pub}")
    if last:
        fm.append(f"last_amended: {last}")
    fm += [f"status: {status}",
           f"source: {yq('https://searchlaw.ocs.go.th/council-of-state/#/public/doc/' + info['timelineId'])}",
           f"retrieved: {RETRIEVED}", "---", "", f"# {name}", ""]
    body = "\n\n".join(x for x in lines if x.strip())
    notes = ""
    if fns:
        notes = "\n\n" + "\n".join(f"[^{i + 1}]: {clean_ws(BeautifulSoup(f.get('footnoteContent') or '', 'html.parser').get_text(' '))}"
                                    for i, f in enumerate(fns))
    text = "\n".join(fm) + "\n" + body + notes + "\n"
    path = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return rel, group, status


def main():
    used = set()
    stats = {}
    files = sorted(glob.glob(os.path.join(RAW, "docs", "*.json")))
    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        if not d.get("lawSections"):
            print("no sections:", f)
            continue
        name = d["lawInfo"].get("lawNameTh") or ""
        if d["_category"] != "constitution" and ("(ยกเลิก)" in name or d["lawInfo"].get("stateId") == "00"):
            stats[("skipped-repealed", d["_category"])] = stats.get(("skipped-repealed", d["_category"]), 0) + 1
            continue
        rel, group, status = convert(d, used)
        stats[(group, status)] = stats.get((group, status), 0) + 1
    for k in sorted(stats):
        print(k, stats[k])


if __name__ == "__main__":
    main()
