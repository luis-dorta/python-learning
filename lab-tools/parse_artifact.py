#!/usr/bin/env python3
"""Turn a "Luis's AI Brief" HTML page (the Claude artifact) into issue.json.

Usage: python3 parse_artifact.py brief.html issue.json
The JSON it writes is then edited for the public edition and fed to build_issue.py.
"""
import json, re, sys
from bs4 import BeautifulSoup, NavigableString

KEEP = {"b": "strong", "strong": "strong", "i": "em", "em": "em", "a": "a", "code": "code"}

def inner(el, drop_first_bold=False):
    """Inline HTML limited to strong/em/a/code. Everything else becomes text."""
    out = []
    first = True
    for c in el.children:
        if isinstance(c, NavigableString):
            out.append(esc(str(c)))
        else:
            name = c.name.lower()
            if name in ("button", "script", "style", "svg"):
                continue
            if "dl" in (c.get("class") or []):
                out.append("<strong>%s.</strong> " % esc(c.get_text().strip().rstrip(".")))
            elif name == "a" and c.get("href"):
                out.append('<a href="%s">%s</a>' % (esc(c["href"]), esc(c.get_text())))
            elif name in KEEP and name != "a":
                out.append("<%s>%s</%s>" % (KEEP[name], inner(c), KEEP[name]))
            else:
                out.append(inner(c))
        first = False
    return re.sub(r"\s+", " ", "".join(out)).strip()

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def txt(el):
    return re.sub(r"\s+", " ", el.get_text()).strip() if el else ""

def labelled(el):
    """A box like <div class=analysis><b>Label</b>text</div> -> text without the label."""
    if not el:
        return ""
    b = el.find(["b", "h4"])
    if b:
        b.extract()
    return inner(el)

def sources(el):
    if not el:
        return ""
    s = inner(el)
    return re.sub(r"^(Sources?( for the recap)?:)\s*", "", s)

def figure(fig):
    rows = []
    for ch in fig.children:
        if isinstance(ch, NavigableString):
            continue
        cls = ch.get("class") or []
        if "row" in cls:
            fill = ch.select_one(".fill")
            w = re.search(r"width:\s*([\d.]+)%", fill.get("style", "")) if fill else None
            rows.append({"label": txt(ch.find("span")), "pct": float(w.group(1)) if w else 0,
                         "value": txt(ch.find("output")), "hi": bool(fill and "hi" in (fill.get("class") or []))})
        elif "gap" in cls:
            rows.append({"gap": True})
    return {"title": txt(fig.find("h4")), "rows": rows, "note": txt(fig.select_one(".cap"))}

def story(art, lead):
    d = {}
    body = art.select_one(".card.story") if lead else art
    if lead:
        hero = art.select_one(".hero")
        svg = hero.find("svg")
        d["hero"] = {"headline": txt(hero.find("h3")), "svg": str(svg) if svg else "",
                     "stats": [{"value": txt(s.find("b")), "label": txt(s.find("span"))} for s in hero.select(".stat")]}
        d["headline"] = d["hero"]["headline"]
        d["kicker"] = ""
    else:
        d["headline"] = txt(body.find("h3"))
        d["kicker"] = ""
    dl = body.select_one(".dl")
    if dl:
        d["kicker"] = txt(dl).rstrip(".")
    d["paragraphs"] = [inner(p) for p in body.find_all("p", recursive=False) if not (set(p.get("class") or []) & {"src", "cap"})]
    fig = body.select_one("figure.fig")
    d["fig"] = figure(fig) if fig else None
    d["means"] = labelled(body.select_one(".analysis"))
    d["clip"] = labelled(body.select_one(".clip"))
    det = body.find("details")
    d["deeper"] = [inner(li) for li in det.find_all("li")] if det else []
    d["sources"] = sources(body.select_one("p.src"))
    return d

def items(container):
    out = []
    for it in container.select(".item"):
        d = {"tags": [txt(t) for t in it.select(".tag")], "title": txt(it.find("h3")),
             "paragraphs": [inner(p) for p in it.find_all("p") if "src" not in (p.get("class") or [])],
             "sources": sources(it.select_one(".src"))}
        out.append(d)
    return out

def next_tag(el):
    n = el.find_next_sibling()
    return n

def parse(html):
    s = BeautifulSoup(html, "html.parser")
    d = {}
    spans = [txt(x) for x in s.select(".topbar span")]
    m = re.search(r"Vol\.\s*(\d+),\s*No\.\s*(\d+)", spans[0])
    d["vol"], d["no"] = int(m.group(1)), int(m.group(2))
    d["date_long"] = spans[1]  # e.g. Tuesday, November 10, 2026
    tiles = s.select("section.issue .tile")
    d["tiles"] = [{"label": txt(t.select_one(".lab")), "title": txt(t.find("b")), "line": txt(t.select_one(".s"))} for t in tiles]
    d["stories"] = [story(s.select_one("#story-%d" % i), i == 1) for i in (1, 2, 3)]
    for i, st in enumerate(d["stories"]):
        if i < len(d["tiles"]):
            st["teaser_title"], st["teaser_line"] = d["tiles"][i]["title"], d["tiles"][i]["line"]
    # New AI
    sec = s.select_one("#newai")
    d["newai"] = items(next_tag(sec))
    # Connectors
    sec = s.select_one("#conn")
    grid = next_tag(sec)
    d["connectors_label"] = txt(sec.select_one(".chip"))
    d["connectors"] = items(grid)
    d["worth"] = None
    nxt = next_tag(grid)
    if nxt is not None and nxt.select_one(".chip") and "worth" in txt(nxt.select_one(".chip")).lower():
        nxt.select_one(".chip").extract()
        d["worth"] = {"title": txt(nxt.find("h3")),
                      "paragraphs": [inner(p) for p in nxt.find_all("p") if "src" not in (p.get("class") or [])],
                      "sources": sources(nxt.select_one(".src"))}
    # Prompt
    pb = s.select_one(".promptbox")
    pre = pb.select_one("pre")
    d["prompt"] = {"title": txt(pb.select_one(".phead h3")), "intro": inner(pb.select_one(".phead p")),
                   "weak": labelled(pb.select_one(".pb.weak")), "strong": pre.get_text().strip("\n"),
                   "why": [{"title": txt(li.find("b")).rstrip("."), "text": labelled(li)} for li in pb.select("ul.why li")],
                   "try": labelled(pb.select_one(".clip")), "sources": sources(pb.select_one("p.src"))}
    # In brief
    d["brief"] = []
    for h in s.select(".brief .hit"):
        src = h.select_one(".src")
        srch = sources(src) if src else ""
        if src:
            src.extract()
        name = txt(h.find("b")).rstrip(".")
        d["brief"].append({"name": name, "text": labelled(h), "sources": srch})
    # Friday quiz
    d["quiz"] = None
    qz = s.select_one(".quiz")
    if qz:
        qs = []
        for q in qz.select(".q"):
            opts = [txt(o) for o in q.select(".opt")]
            fb = q.select_one(".fb")
            qs.append({"question": txt(q.select_one(".t")), "options": opts, "answer": int(q.get("data-answer", 0)),
                       "explain": re.sub(r"^Right\.\s*", "", fb.get("data-right", "")) if fb else ""})
        recap = []
        hdr = s.select_one("#quiz-sec, #recap")
        p = qz.find_previous_sibling()
        while p is not None and p.name == "p":
            recap.insert(0, inner(p)); p = p.find_previous_sibling()
        nx = qz.find_next_sibling("p", class_="src")
        d["quiz"] = {"recap": recap, "questions": qs, "sources": sources(nx) if nx else ""}
    # Fields the editor (the task) fills in for the public edition
    d["subject_hook"] = ""      # short two-topic hook for the email subject
    d["subtitle"] = ""          # one plain sentence
    d["your_turn"] = ""         # one easy opinion question
    d["prev_url"] = ""          # previous issue url, or ""
    d["prev_label"] = "Read yesterday's issue"
    d["slug"] = ""
    return d

if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    data = parse(open(src, encoding="utf-8").read())
    json.dump(data, open(dst, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("wrote", dst, "| stories", len(data["stories"]), "| newai", len(data["newai"]), "| connectors", len(data["connectors"]),
          "| worth", bool(data["worth"]), "| brief", len(data["brief"]), "| quiz", bool(data["quiz"]))
