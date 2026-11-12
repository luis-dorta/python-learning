#!/usr/bin/env python3
"""Build one issue of Luis's AI Brief for beehiiv from issue.json.

  python3 build_issue.py check  issue.json            validate text (dashes, privacy words, required fields)
  python3 build_issue.py images issue.json OUTDIR     render the issue's JPG images into OUTDIR
  python3 build_issue.py static OUTDIR                render the six section-header images (only needed once)
  python3 build_issue.py html   issue.json urls.json OUTDIR [both|web|email]
                                                      write part1.html, part2.html ... (beehiiv editor HTML)
  python3 build_issue.py verify issue.json urls.json SAVED_POST_FILE
                                                      check a saved post (get_post_content editor_html output)

urls.json maps image names (mast, thumb, bento, hero, fig1, fig2, fig3, newai, prompt) to beehiiv-hosted URLs.
Section header URLs come from static_urls.json next to this script.
The layout is fixed here so every issue looks the same. Only the words and numbers come from issue.json.
"""
import html as H
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = "https://luiss-newsletter.beehiiv.com"
FOOTER = ("Independent weekday AI brief for marketers and students. Researched with AI help and reviewed by the editor. "
          "Figures marked vendor-reported come from the company itself, not an independent test.")
MOTTO = "All the AI news worth your time, and one skill to practice."

HARD_WORDS = ["JWU", "Johnson & Wales", "Johnson and Wales", "Sherwin", "Dorta", "luisdorta", "Prompt Library",
              "your Notion", "your Gmail", "your Drive", "your Prompt", "Reply in Claude", "Fits your work",
              "Worth adding", "my applications", "my job search", "Resident Assistant", "reviewed by Luis"]
SOFT_WORDS = ["Charlotte", "Raleigh", "graduat", "student at", "Practiced", "job search", "resume", "daily",
              "newsletter", "The Rundown", "The Neuron", "Techpresso"]

# ----------------------------------------------------------------------------- helpers

def e(s):
    return H.escape(str(s), quote=True)

def plain(s):
    return H.unescape(re.sub(r"<[^>]+>", "", s or ""))

def all_strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for k, v in o.items():
            if k == "svg":
                continue
            yield from all_strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from all_strings(v)

def date_parts(d):
    m = re.match(r"(\w+),\s+(\w+)\s+(\d+),\s+(\d{4})", d["date_long"])
    if not m:
        raise SystemExit("date_long must look like 'Tuesday, November 10, 2026'")
    return m.group(1), m.group(2), int(m.group(3)), int(m.group(4))

def slug_for(d):
    if d.get("slug"):
        return d["slug"]
    _, mon, day, yr = date_parts(d)
    return "luis-s-ai-brief-%s-%d-%d" % (mon.lower(), day, yr)

def post_url(d):
    return "%s/p/%s" % (SITE, slug_for(d))

def title_for(d):
    _, mon, day, yr = date_parts(d)
    return "Luis's AI Brief: %s %d, %d" % (mon, day, yr)

def figs(d):
    """[(name, story_index, fig)] in order."""
    out = []
    for i, st in enumerate(d["stories"]):
        if st.get("fig") and st["fig"].get("rows"):
            out.append(("fig%d" % (len(out) + 1), i, st["fig"]))
    return out

def image_names(d):
    return ["mast", "thumb", "bento", "hero"] + [f[0] for f in figs(d)] + ["newai", "prompt"]

# ----------------------------------------------------------------------------- check

def check(d, quiet=False):
    errs, warns = [], []
    for k in ("vol", "no", "date_long", "stories", "newai", "connectors", "prompt", "brief", "subject_hook", "subtitle", "your_turn"):
        if not d.get(k):
            errs.append("missing field: %s" % k)
    if len(d.get("stories", [])) != 3:
        errs.append("need exactly 3 stories")
    for i, st in enumerate(d.get("stories", [])):
        for k in ("headline", "paragraphs", "means", "clip", "sources", "teaser_title", "teaser_line"):
            if not st.get(k):
                errs.append("story %d missing %s" % (i + 1, k))
    if d.get("stories") and not d["stories"][0].get("hero", {}).get("stats"):
        errs.append("lead story needs hero.stats")
    wd = date_parts(d)[0]
    if wd != "Friday" and d.get("quiz"):
        errs.append("quiz is for Fridays only: set quiz to null")
    for s in all_strings(d):
        if "—" in s or "–" in s:
            errs.append("em or en dash in: %r" % s[:80])
        for w in HARD_WORDS:
            if w.lower() in s.lower():
                errs.append("personal or banned phrase %r in: %r" % (w, s[:90]))
        t = s.replace("Luis's AI Brief", "")
        if re.search(r"\bLuis\b", t):
            errs.append("'Luis' outside the publication name in: %r" % s[:90])
        for w in SOFT_WORDS:
            if re.search(r"\b%s" % re.escape(w), s, flags=re.I):
                warns.append("check the word %r in: %r" % (w, s[:90]))
    if not quiet:
        for w in warns:
            print("WARN", w)
        for x in errs:
            print("ERROR", x)
        print("check:", "FAILED" if errs else "ok", "| %d errors, %d warnings" % (len(errs), len(warns)))
    return errs

# ----------------------------------------------------------------------------- images

CSS = """
@font-face{font-family:BG;font-weight:700;src:url(FONTS/bricolage-grotesque-latin-700-normal.woff2)}
@font-face{font-family:BG;font-weight:800;src:url(FONTS/bricolage-grotesque-latin-800-normal.woff2)}
@font-face{font-family:FT;font-weight:400;src:url(FONTS/figtree-latin-400-normal.woff2)}
@font-face{font-family:FT;font-weight:600;src:url(FONTS/figtree-latin-600-normal.woff2)}
@font-face{font-family:FT;font-weight:700;src:url(FONTS/figtree-latin-700-normal.woff2)}
@font-face{font-family:Figtree;font-weight:400 500;src:url(FONTS/figtree-latin-400-normal.woff2)}
@font-face{font-family:Figtree;font-weight:600;src:url(FONTS/figtree-latin-600-normal.woff2)}
@font-face{font-family:Figtree;font-weight:700 900;src:url(FONTS/figtree-latin-700-normal.woff2)}
@font-face{font-family:"Bricolage Grotesque";font-weight:600 900;src:url(FONTS/bricolage-grotesque-latin-800-normal.woff2)}
*{box-sizing:border-box;margin:0}
body{background:#fff;font-family:FT;color:#1D1D1F;width:800px}
.c{width:800px;position:relative;overflow:hidden;margin-bottom:40px}
h1,h2,h3,.d{font-family:BG;font-weight:800;letter-spacing:-.03em}
.ai{background:linear-gradient(90deg,#7C3AED,#2C5BFF 60%,#19C79A);-webkit-background-clip:text;color:transparent}
.pill{display:inline-block;font:700 24px FT;letter-spacing:.08em;text-transform:uppercase;color:#fff;padding:12px 26px;border-radius:40px}
.hl{padding:0 16px;border-radius:18px;color:#fff;display:inline-block}
/* masthead */
#mast{padding:28px 6px 22px;background:#F5F5F7}
.top{display:flex;justify-content:space-between;font:600 24px FT;color:#6E6E73}
#mast h1{font-size:112px;line-height:1;margin:26px 0 14px;color:#1D1D1F}
.motto{font:400 32px/1.35 FT;color:#515154}
.nav{margin-top:26px;border:1.5px solid #E5E5E9;background:#fff;border-radius:60px;padding:20px 26px;display:flex;justify-content:space-between;font:600 24px FT}
.nav i{display:inline-block;width:16px;height:16px;border-radius:50%;margin-right:9px;vertical-align:0}
/* bento */
#bento{padding:6px 0;background:#F5F5F7;display:flex;flex-direction:column;gap:16px}
.t{border-radius:34px;padding:32px 34px}
.t small{font:700 24px FT;letter-spacing:.1em;text-transform:uppercase;display:block}
.lead{background:linear-gradient(160deg,#C93A22,#E4573A);color:#fff}
.lead h2{font-size:60px;line-height:1.03;margin:14px 0}.lead p{font:400 30px/1.35 FT}
.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.s{background:#fff;border:1.5px solid #E5E5E9}.s small{color:#D92D20}.s h2{font-size:40px;line-height:1.06;margin:10px 0}.s p{font:400 27px/1.35 FT;color:#6E6E73}
.sk{background:linear-gradient(135deg,#C6F432,#A9F04F);color:#101406}.sk h2{font-size:46px;line-height:1.05;margin:10px 0}.sk p{font:400 28px/1.35 FT}
/* hero */
#hero{background:#0B0B0F;border-radius:40px;color:#fff;padding:44px}
#hero:before{content:"";position:absolute;right:-140px;top:-140px;width:600px;height:600px;background:radial-gradient(circle,#D9532F 0,transparent 65%);opacity:.75}
#hero:after{content:"";position:absolute;left:-160px;bottom:-220px;width:620px;height:560px;background:radial-gradient(circle,#2C6CA8 0,transparent 65%);opacity:.5}
#hero>*{position:relative;z-index:2}
.tag{display:inline-block;background:#2B2B31;border-radius:30px;padding:12px 26px;font:700 24px FT;letter-spacing:.1em}
#hero h2{line-height:1.03;margin:28px 0 0}
.art{margin:30px auto 0;width:520px}.art svg{width:520px;height:auto;display:block}
.stats{margin-top:34px;display:flex;flex-direction:column;gap:14px}
.stat{background:#ffffff14;border:2px solid #ffffff26;border-radius:28px;padding:22px 28px;display:grid;grid-template-columns:270px 1fr;align-items:center;gap:22px}
.stat b{font:800 62px BG;letter-spacing:-.03em;line-height:1}.stat b.sm{font-size:44px}.stat span{font:400 27px/1.3 FT;color:#E1E1EB}
/* charts */
.fig{background:#EEEEF2;border-radius:34px;padding:36px 38px}
.fig h3{font:700 30px/1.25 FT;letter-spacing:0;margin-bottom:22px}
.row{margin:18px 0}
.row .l{display:flex;justify-content:space-between;align-items:baseline;font:600 28px FT;margin-bottom:8px}
.row .l em{font:700 30px FT;font-style:normal;white-space:nowrap;margin-left:16px}
.row u{display:block;height:30px;border-radius:20px;background:#fff;text-decoration:none;overflow:hidden}
.row u s{display:block;height:100%;border-radius:20px;background:#6E6E73;text-decoration:none;min-width:8px}
.row u s.r{background:linear-gradient(90deg,#C93A22,#E4573A)}
.note{font:400 24px/1.4 FT;color:#6E6E73;margin-top:22px}
.gap{height:22px}
/* section headers */
.hd{padding:14px 6px 6px;background:#F5F5F7}
.hd h2{font-size:84px;line-height:1.12;margin-top:18px}
/* feature cards */
.feat{border-radius:36px;padding:40px 38px;color:#fff}
.feat .tags{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:22px}
.feat .tags span{font:700 22px FT;letter-spacing:.06em;text-transform:uppercase;background:#ffffff2e;border-radius:30px;padding:9px 20px}
.feat h2{font-size:58px;line-height:1.04}.feat p{font:400 30px/1.35 FT;margin-top:16px}
#newai{background:linear-gradient(135deg,#0A6CFF,#2C5BFF 55%,#7C3AED)}
#prompt{background:linear-gradient(135deg,#C6F432,#A9F04F 60%,#19C79A);color:#101406}
#prompt .tags span{background:#10140622}
/* thumbnail */
#thumb{width:600px;height:315px;background:#0B0B0F;color:#fff;padding:26px 30px;margin-bottom:40px}
#thumb:before{content:"";position:absolute;right:-120px;top:-150px;width:440px;height:440px;background:radial-gradient(circle,#D9532F 0,transparent 65%);opacity:.8}
#thumb>*{position:relative;z-index:2}
#thumb .w{font:800 26px BG;letter-spacing:-.02em}#thumb .w span{color:#D8F86C}
#thumb .dt{font:600 14px FT;color:#FF6F5E;letter-spacing:.08em;text-transform:uppercase;margin-top:4px}
#thumb h2{line-height:1.05;position:absolute;left:30px;right:30px;bottom:26px}
"""

def head():
    return "<!doctype html><meta charset='utf-8'><style>" + CSS.replace("FONTS", "file://" + os.path.join(HERE, "fonts")) + "</style>"

def fit(text, sizes):
    """Pick a font size by text length. sizes = [(max_len, px), ...] ascending."""
    n = len(text)
    for mx, px in sizes:
        if n <= mx:
            return px
    return sizes[-1][1]

def fig_html(name, fig):
    rows = []
    for r in fig["rows"]:
        if r.get("gap"):
            rows.append('<div class="gap"></div>')
            continue
        pct = max(0.0, min(100.0, float(r.get("pct", 0))))
        rows.append('<div class="row"><div class="l"><span>%s</span><em>%s</em></div><u><s class="%s" style="width:%s%%"></s></u></div>'
                    % (e(r["label"]), e(r["value"]), "r" if r.get("hi") else "", pct))
    return '<div class="c fig" id="%s"><h3>%s</h3>%s<p class="note">%s</p></div>' % (name, e(fig["title"]), "".join(rows), e(fig.get("note", "")))

def cards_html(d):
    wd, mon, day, yr = date_parts(d)
    st = d["stories"]
    hero = st[0]["hero"]
    skill = d["prompt"]["title"]
    parts = [head()]
    parts.append('<div class="c" id="mast"><div class="top"><span>Vol. %d, No. %d</span><span>%s</span><span>Free to read</span></div>'
                 '<h1>Luis\'s <span class="ai">AI</span> Brief</h1><p class="motto">%s</p>'
                 '<div class="nav"><span><i style="background:#E4573A"></i>Top stories</span><span><i style="background:#2C5BFF"></i>New AI</span>'
                 '<span><i style="background:#19C79A"></i>Tools</span><span><i style="background:#C6F432"></i>Prompt</span>'
                 '<span><i style="background:#9333EA"></i>In brief</span></div></div>' % (d["vol"], d["no"], e(d["date_long"]), MOTTO))
    parts.append('<div class="c" id="bento"><div class="t lead"><small>Lead story</small><h2 style="font-size:%dpx">%s</h2><p>%s</p></div>'
                 '<div class="two"><div class="t s"><small>Story 2</small><h2>%s</h2><p>%s</p></div>'
                 '<div class="t s"><small>Story 3</small><h2>%s</h2><p>%s</p></div></div>'
                 '<div class="t sk"><small>Skill of the day</small><h2>%s</h2><p>Copy today\'s prompt and try it in 5 minutes.</p></div></div>'
                 % (fit(st[0]["teaser_title"], [(50, 64), (75, 56), (999, 48)]), e(st[0]["teaser_title"]), e(st[0]["teaser_line"]),
                    e(st[1]["teaser_title"]), e(st[1]["teaser_line"]), e(st[2]["teaser_title"]), e(st[2]["teaser_line"]), e(skill)))
    stats = "".join('<div class="stat"><b class="%s">%s</b><span>%s</span></div>'
                    % ("sm" if len(s["value"]) > 6 else "", e(s["value"]), e(s["label"])) for s in hero["stats"][:3])
    art = '<div class="art">%s</div>' % (hero.get("svg") or DEFAULT_ART)
    parts.append('<div class="c" id="hero"><span class="tag">LEAD STORY</span><h2 style="font-size:%dpx">%s</h2>%s<div class="stats">%s</div></div>'
                 % (fit(hero["headline"], [(45, 78), (70, 66), (999, 56)]), e(hero["headline"]), art, stats))
    for name, _, fig in figs(d):
        parts.append(fig_html(name, fig))
    top = d["newai"][0]
    parts.append('<div class="c feat" id="newai"><div class="tags">%s</div><h2 style="font-size:%dpx">%s</h2></div>'
                 % ("".join("<span>%s</span>" % e(t) for t in (top.get("tags") or ["New"])[:3]),
                    fit(top["title"], [(45, 64), (70, 56), (999, 48)]), e(top["title"])))
    parts.append('<div class="c feat" id="prompt"><div class="tags"><span>Today\'s technique</span></div><h2 style="font-size:%dpx">%s</h2><p>%s</p></div>'
                 % (fit(skill, [(35, 68), (55, 58), (999, 50)]), e(skill), e(plain(d["prompt"].get("one_line") or first_sentence(plain(d["prompt"]["intro"]))))))
    lead_t = st[0]["teaser_title"]
    parts.append('<div class="c" id="thumb"><div class="w">Luis\'s <span>AI</span> Brief</div><div class="dt">%s %d, %d</div><h2 style="font-size:%dpx">%s</h2></div>'
                 % (mon, day, yr, fit(lead_t, [(40, 44), (60, 38), (85, 32), (999, 27)]), e(lead_t)))
    return "".join(parts)

DEFAULT_ART = ('<svg viewBox="0 0 320 150" role="img" aria-label="Abstract chart illustration">'
               '<rect x="6" y="6" width="308" height="138" rx="20" fill="rgba(255,255,255,.08)" stroke="rgba(255,255,255,.35)" stroke-width="1.5"/>'
               + "".join('<rect x="%d" y="%d" width="22" height="%d" rx="8" fill="%s"/>' % (34 + i * 38, 122 - h, h, "#F0885B" if i == 6 else "rgba(255,255,255,.55)")
                         for i, h in enumerate([24, 36, 30, 48, 58, 52, 88]))
               + '<circle cx="273" cy="22" r="6" fill="#D8F86C"/></svg>')

def cap(s):
    return s[:1].upper() + s[1:]

def first_sentence(s, lo=45, hi=240):
    """First full sentence. Adds the next one when the first is very short. Never cuts mid-sentence."""
    s = re.sub(r"^(What it is|Who can use it|Good for):\s*", "", s.strip())
    ends = [m.end() for m in re.finditer(r"[.!?](?=\s|$)", s)]
    for x in ends:
        if x >= lo:
            return s[:x] if x <= hi else s[:hi].rsplit(" ", 1)[0] + "..."
    return s if len(s) <= hi else s[:hi].rsplit(" ", 1)[0] + "..."

STATIC = [
    ("h_stories", "Top stories", "#D14B2F", "#fff", "What <span class='hl' style='background:#D14B2F'>moved</span> today"),
    ("h_newai", "New AI", "#2C5BFF", "#fff", "Fresh <span class='hl' style='background:#2C6CF0'>tools</span> to try"),
    ("h_conn", "Tools and connectors", "#19A57F", "#fff", "Tools that <span class='hl' style='background:#19A57F'>work</span> together"),
    ("h_prompt", "Prompt of the day", "#A9F04F", "#101406", "Level up <span class='hl' style='background:#B8F34C;color:#101406'>one skill</span>"),
    ("h_brief", "In brief", "#7C3AED", "#fff", "Three more, <span class='hl' style='background:#8B3FE8'>fast</span>"),
    ("h_quiz", "The Friday recap", "#FFC043", "#2A1B00", "Test <span class='hl' style='background:#FFC043;color:#2A1B00'>yourself</span>"),
]

def static_html():
    parts = [head()]
    for name, pill, bg, fg, h in STATIC:
        parts.append('<div class="c hd" id="%s"><span class="pill" style="background:%s;color:%s">%s</span><h2>%s</h2></div>' % (name, bg, fg, pill, h))
    return "".join(parts)

def shoot(page_html, names, outdir):
    from playwright.sync_api import sync_playwright
    os.makedirs(outdir, exist_ok=True)
    src = os.path.join(outdir, "_cards.html")
    open(src, "w", encoding="utf-8").write(page_html)
    with sync_playwright() as p:
        kw = {"args": ["--no-sandbox"]}
        if os.path.exists("/usr/bin/google-chrome"):
            kw["executable_path"] = "/usr/bin/google-chrome"
        b = p.chromium.launch(**kw)
        pg = b.new_page(viewport={"width": 800, "height": 900}, device_scale_factor=2)
        pg.goto("file://" + os.path.abspath(src))
        pg.wait_for_timeout(1200)
        pg.evaluate("document.fonts.ready")
        for n in names:
            pg.locator("#" + n).screenshot(path=os.path.join(outdir, n + ".jpg"), type="jpeg", quality=90)
        b.close()
    print("rendered:", " ".join(n + ".jpg" for n in names), "->", outdir)

# ----------------------------------------------------------------------------- beehiiv HTML

def inline(s):
    """issue.json inline HTML (strong, em, a, code) -> beehiiv marks."""
    s = s or ""
    s = re.sub(r'<a href="([^"]+)">', r'<a target="_blank" rel="noopener noreferrer nofollow" class="link" href="\1">', s)
    return s

def sec(body, bg=None, fg=None, radius=0, mt=14, pad=(0, 0, 0, 0), web=True, border=None, anchor=None):
    a = []
    if anchor:
        a.append('data-anchor="true" data-anchor-id="%s" data-anchor-title="%s"' % (anchor[0], e(anchor[1])))
    if bg:
        a.append('data-background-color="%s"' % bg)
    if radius:
        for corner in ("bottom-left", "bottom-right", "top-left", "top-right"):
            a.append('data-border-%s-radius="%d"' % (corner, radius))
    if border:
        a.append('data-border-style="solid" data-border-color="%s" data-border-width-top="1" data-border-width-right="1" '
                 'data-border-width-bottom="1" data-border-width-left="1"' % border)
    if fg:
        a.append('data-color="%s"' % fg)
    a.append('data-margin-top="%d" data-padding-top="%d" data-padding-right="%d" data-padding-bottom="%d" data-padding-left="%d"'
             % (mt, pad[0], pad[1], pad[2], pad[3]))
    a.append('data-show-in-email="%s" data-show-on-website="%s"' % (("false", "true") if web else ("true", "false")))
    return '<div %s data-type="section" class="node-section">%s</div>' % (" ".join(a), body)

REM = {12: "0.75rem", 14: "0.875rem", 15: "0.9375rem", 16: "1rem", 17: "1.0625rem", 18: "1.125rem", 20: "1.25rem",
       24: "1.5rem", 26: "1.625rem", 28: "1.75rem", 30: "1.875rem", 32: "2rem", 48: "3rem"}

def run(t, color, px, bold=False, italic=False):
    t = e(t)
    if italic:
        t = "<em>%s</em>" % t
    if bold:
        return '<span style="color: %s; font-weight: 700; font-size: %s;"><strong>%s</strong></span>' % (color, REM[px], t)
    return '<span style="color: %s; font-size: %s;">%s</span>' % (color, REM[px], t)

def mark(t, bg, fg, px):
    return '<span style="font-size: %s;"><mark data-color="%s" style="background-color: %s; color: %s;"><span style="color: %s; font-weight: 700;"><strong>%s</strong></span></mark></span>' % (REM[px], bg, bg, fg, fg, e(t))

def link(t, url, color, px=14, same_tab=False):
    tgt = 'target="_self" rel=""' if same_tab else 'target="_blank" rel="noopener noreferrer nofollow"'
    return '<a %s class="link" href="%s">%s</a>' % (tgt, e(url), run(t, color, px, bold=True))

def p(inner_html, align=None):
    return "<p%s>%s</p>" % (' style="text-align: %s;"' % align if align else "", inner_html)

def img(url, alt, href=None):
    extra = ' data-url="%s" data-target="_self"' % e(href) if href else ' data-url=""'
    return ('<figure data-align="center" data-alt="%s" data-src="%s"%s data-width="100%%" data-type="imageBlock"><figcaption></figcaption></figure>'
            % (e(alt), e(url), extra))

def button(t, url, bg, fg, align="center"):
    return ('<div><a data-alignment="%s" data-custom-background-color="%s" data-custom-text-color="%s" data-full-width="false" '
            'href="%s" data-size="large" data-type="button">%s</a></div>' % (align, bg, fg, e(url), e(t)))

def label(t, color):
    return p(run(t.upper(), color, 12, bold=True))

def box(lbl, body_html, bg, lbl_color):
    return sec(label(lbl, lbl_color) + body_html, bg=bg, fg="#1D1D1F", radius=14, mt=12, pad=(16, 16, 16, 16))

def headline_with_hl(text, hl, color, px, hl_bg, hl_fg):
    if hl and hl in text:
        a, b = text.split(hl, 1)
        return (run(a, color, px, bold=True) if a else "") + mark(hl, hl_bg, hl_fg, px) + (run(b, color, px, bold=True) if b else "")
    return run(text, color, px, bold=True)

def strong_prompt_html(text):
    """Multi-line prompt text -> paragraphs and bullet lists."""
    out, bullets = [], []
    def flush():
        if bullets:
            out.append("<ul>%s</ul>" % "".join("<li><p>%s</p></li>" % e(b) for b in bullets))
            bullets.clear()
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            flush()
            continue
        m = re.match(r"^[-*•]\s+(.*)", s)
        if m:
            bullets.append(m.group(1))
        else:
            flush()
            # beehiiv rejects bare entity-encoded tags, so XML-style tag lines go in a code mark
            out.append(p("<code>%s</code>" % e(s)) if re.match(r"^</?[\w-]+>$", s) else p(e(s)))
    flush()
    return "".join(out)

def email_layer(d, U):
    url = post_url(d)
    wd, mon, day, yr = date_parts(d)
    st = d["stories"]
    W, CARD = "#FFFFFF", dict(radius=26, mt=10, pad=(18, 20, 18, 20), web=False)
    out = []
    out.append(sec(
        p(run("VOL. %d, NO. %d | %s, %s %d, %d | FREE" % (d["vol"], d["no"], wd.upper(), mon.upper(), day, yr), "#FF6F5E", 12, bold=True))
        + "<h1>%s%s%s</h1>" % (run("Luis's ", W, 48, bold=True), run("AI", "#D8F86C", 48, bold=True), run(" Brief", W, 48, bold=True))
        + p(run(MOTTO, "#E1E1EB", 18))
        + p(run("About 1 minute here. ", "#D8F86C", 14, bold=True) + link("Read the full brief on the web", url, W)),
        bg="#0B0B0F", fg=W, radius=26, mt=10, pad=(22, 18, 22, 18), web=False))
    out.append(sec(
        label("Lead story", W)
        + "<h2>%s</h2>" % headline_with_hl(st[0]["teaser_title"], st[0].get("highlight"), W, 30, "#FFE9E5", "#D92D20")
        + p(run(st[0]["teaser_line"], W, 16, italic=True))
        + p(link("Read the full story →", url + "#story-1", W)),
        bg="#DD3A21", fg=W, **CARD))
    for i in (1, 2):
        out.append(sec(
            label("Story %d" % (i + 1), "#D92D20")
            + "<h2>%s</h2>" % run(st[i]["teaser_title"], "#1D1D1F", 24, bold=True)
            + p(run(st[i]["teaser_line"], "#6E6E73", 16, italic=True))
            + p(link("Read more →", url + "#story-%d" % (i + 1), "#D92D20")),
            bg=W, fg="#1D1D1F", border="#E5E5E9", **CARD))
    fl = figs(d)
    if fl:
        fig = fl[0][2]
        rows = "".join(p(run(r["value"] + " ", "#1D1D1F", 20, bold=True) + run(r["label"], "#1D1D1F", 14))
                       for r in fig["rows"] if not r.get("gap"))
        out.append(sec(p(run(fig["title"], "#1D1D1F", 15, bold=True)) + rows + p(run(fig.get("note", ""), "#6E6E73", 12)),
                       bg="#F0F0F4", fg="#1D1D1F", radius=22, mt=10, pad=(10, 12, 10, 12), web=False))

    def hdr(pill, a, hl, b, bg, fg):
        return sec(p(mark(" %s " % pill.upper(), bg, fg, 12))
                   + "<h2>%s%s%s</h2>" % (run(a, "#1D1D1F", 32, bold=True) if a else "", mark(hl, bg, fg, 32), run(b, "#1D1D1F", 32, bold=True) if b else ""),
                   mt=10, pad=(14, 0, 0, 0), web=False)
    CARD8 = dict(CARD, mt=8)
    top = d["newai"][0]
    also = [x["title"] for x in d["newai"][1:]]
    out.append(hdr("New AI", "Fresh ", "tools", " to try", "#0A6CFF", W))
    out.append(sec(
        (label(" | ".join(top.get("tags") or []), W) if top.get("tags") else "")
        + "<h2>%s</h2>" % run(top["title"], W, 24, bold=True)
        + p(run(first_sentence(plain(top["paragraphs"][0])), W, 16))
        + (p(run("Also: %s." % "; ".join(a.rstrip(".") for a in also), W, 15, italic=True)) if also else "")
        + p(link("See all new tools →", url + "#newai", W)),
        bg="#0A6CFF", fg=W, **CARD8))
    c0 = d["connectors"][0]
    out.append(hdr("Tools and connectors", "Tools that ", "work", " together", "#19C79A", "#06251D"))
    out.append(sec(
        "<h2>%s</h2>" % run(c0["title"], "#06251D", 24, bold=True)
        + p(run(first_sentence(plain(c0["paragraphs"][0])), "#06251D", 16))
        + p(link("How to use it →", url + "#conn", "#06251D")),
        bg="#19C79A", fg="#06251D", **CARD8))
    if d.get("worth"):
        out.append(sec(
            label("Worth a look", "#2A1B00")
            + "<h2>%s</h2>" % run(d["worth"]["title"], "#2A1B00", 24, bold=True)
            + p(run(cap(first_sentence(plain(d["worth"]["paragraphs"][0]))), "#2A1B00", 16))
            + p(link("See the details →", url + "#conn", "#2A1B00")),
            bg="#FFC043", fg="#2A1B00", **CARD8))
    pr = d["prompt"]
    out.append(hdr("Prompt of the day", "Level up ", "one skill", "", "#A9F04F", "#101406"))
    out.append(sec(
        "<h2>%s</h2>" % run(pr["title"], "#101406", 26, bold=True)
        + p(run(pr.get("one_line") or first_sentence(plain(pr["intro"])), "#101406", 16))
        + p(link("Get the prompt →", url + "#prompt", "#101406")),
        bg="#A9F04F", fg="#101406", **CARD8))
    out.append(hdr("In brief", "Three more, ", "fast", "", "#9333EA", W))
    out.append(sec(
        "".join(p(run(b["name"] + " ", "#9333EA", 17, bold=True) + run(first_sentence(plain(b["text"])), "#1D1D1F", 15, italic=True)) for b in d["brief"])
        + p(link("More detail →", url + "#hits", "#9333EA")),
        bg=W, fg="#1D1D1F", border="#E5E5E9", **CARD8))
    if d.get("quiz"):
        out.append(hdr("The Friday recap", "Test ", "yourself", "", "#FFC043", "#2A1B00"))
        out.append(sec(p(run("Three quick questions on this week's stories. Answers are at the end.", "#2A1B00", 16))
                       + p(link("Take the quiz on the web →", url + "#quiz", "#2A1B00")), bg="#FFC043", fg="#2A1B00", **CARD8))
    out.append(sec(
        label("Your turn", "#D92D20")
        + "<h2>%s</h2>" % run(d["your_turn"], "#1D1D1F", 24, bold=True)
        + p(run("One line is plenty. See what other readers say, and add your own.", "#6E6E73", 16))
        + p(link("Join the conversation →", url + "#comments", "#D92D20", 16)),
        bg=W, fg="#1D1D1F", border="#E5E5E9", **CARD))
    out.append(sec(button("Read the full brief", url, "#1D1D1F", W), mt=10, web=False))
    out.append(sec(p(run(FOOTER, "#6E6E73", 12)), mt=0, web=False))
    return out

CARDW = dict(bg="#FFFFFF", fg="#1D1D1F", radius=20, mt=14, pad=(22, 16, 22, 16))
IMGSEC = dict(bg="#F5F5F7", mt=14, pad=(0, 0, 0, 0))

def story_web(d, U, i):
    st = d["stories"][i]
    fmap = {si: (name, fig) for name, si, fig in figs(d)}
    body = []
    kick = "STORY %d%s" % (i + 1, " | " + st["kicker"].upper() if st.get("kicker") else "")
    paras = [p(inline(x)) for x in st["paragraphs"]]
    figimg = ""
    if i in fmap:
        name, fig = fmap[i]
        alt = "%s %s" % (fig["title"], "; ".join("%s: %s" % (r["label"], r["value"]) for r in fig["rows"] if not r.get("gap")))
        figimg = img(U[name], alt)
    if i == 0:
        hero = st["hero"]
        alt = "Lead story: %s. %s" % (hero["headline"], "; ".join("%s %s" % (s["value"], s["label"]) for s in hero["stats"]))
        body.append(sec(img(U["hero"], alt) + figimg, mt=0))
        body += paras
    else:
        body.append(label(kick, "#DD3A21"))
        body.append("<h2>%s</h2>" % e(st["headline"]))
        body += paras[:1]
        if figimg:
            body.append(sec(figimg, mt=0))
        body += paras[1:]
    body.append(box("What it means for you", p(inline(st["means"])), "#FFE9E5", "#DD3A21"))
    body.append(box("Clip and try today", p(inline(st["clip"])), "#EAF8B8", "#1D1D1F"))
    if st.get("deeper"):
        body.append(p("<strong>Go deeper</strong>"))
        body.append("<ul>%s</ul>" % "".join("<li><p>%s</p></li>" % inline(x) for x in st["deeper"]))
    body.append(p("<strong>Sources: </strong>" + inline(st["sources"])))
    return sec("".join(body), anchor=("story-%d" % (i + 1), "Lead story" if i == 0 else "Story %d" % (i + 1)), **CARDW)

def item_web(it, how_label=None):
    b = ["<h2>%s</h2>" % e(it["title"])]
    if it.get("tags"):
        b.append(p("<em>%s</em>" % e(" | ".join(it["tags"]))))
    b += [p(inline(x)) for x in it["paragraphs"]]
    if it.get("sources"):
        b.append(p("<strong>Sources: </strong>" + inline(it["sources"])))
    return "".join(b)

def web_layer(d, U, S):
    wd, mon, day, yr = date_parts(d)
    st = d["stories"]
    out = []
    nav = [("Lead story", "#story-1"), ("Story 2", "#story-2"), ("Story 3", "#story-3"), ("New AI", "#newai"), ("Prompt", "#prompt"), ("In brief", "#hits")]
    out.append(sec(
        img(U["mast"], "Luis's AI Brief, Vol. %d, No. %d, %s" % (d["vol"], d["no"], d["date_long"]))
        + p(" &nbsp;|&nbsp; ".join(link(t, h, "#1D1D1F", 14, same_tab=True) for t, h in nav), align="center"),
        bg="#F5F5F7", mt=0))
    out.append(sec(img(U["bento"], "In this issue: %s" % "; ".join(s["teaser_title"].rstrip(".") for s in st), href="#story-1"), **dict(IMGSEC, mt=10)))
    if d.get("interactive_url"):
        out.append(sec(p("<strong>Want the full experience?</strong> The interactive version has a copy button for the prompt and tap-to-open sections.")
                       + button("Open the interactive version", d["interactive_url"], "#1D1D1F", "#FFFFFF", align="left"),
                       bg="#D8F86C", fg="#1D1D1F", radius=20, mt=14, pad=(20, 20, 20, 20)))
    out.append(sec(img(S["h_stories"], "Top stories: What moved today"), **IMGSEC))
    for i in range(3):
        out.append(story_web(d, U, i))
    # New AI
    out.append(sec(img(S["h_newai"], "New AI: Fresh tools to try"), anchor=("newai", "New AI"), **IMGSEC))
    top = d["newai"][0]
    body = [sec(img(U["newai"], "New: %s" % top["title"]), mt=0)]
    for n, it in enumerate(d["newai"]):
        if n:
            body.append("<hr>")
        body.append(item_web(it))
    out.append(sec("".join(body), **CARDW))
    # Connectors
    out.append(sec(img(S["h_conn"], "Tools and connectors: Tools that work together"), anchor=("conn", "Tools"), **IMGSEC))
    body = []
    for n, it in enumerate(d["connectors"]):
        if n:
            body.append("<hr>")
        body.append(item_web(it))
    if d.get("worth"):
        w = d["worth"]
        body.append(sec(label("Worth a look", "#8A5A00") + "<h3>%s</h3>" % e(w["title"]) + "".join(p(inline(x)) for x in w["paragraphs"])
                        + (p("<strong>Sources: </strong>" + inline(w["sources"])) if w.get("sources") else ""),
                        bg="#FFF6E0", fg="#1D1D1F", radius=14, mt=14, pad=(16, 16, 16, 16), border="#F2C46B"))
    out.append(sec("".join(body), **CARDW))
    # Prompt
    pr = d["prompt"]
    out.append(sec(img(S["h_prompt"], "Prompt of the day: Level up one skill"), anchor=("prompt", "Prompt of the day"), **IMGSEC))
    body = [sec(img(U["prompt"], "Prompt of the day: %s" % pr["title"]), mt=0), p(inline(pr["intro"]))]
    body.append(box("Weak", p(inline(pr["weak"])), "#F5F5F7", "#6E6E73"))
    body.append(box("Strong. Copy and paste this", strong_prompt_html(pr["strong"]), "#EAF8B8", "#1D1D1F"))
    if pr.get("why"):
        body.append(p("<strong>Why the strong one works</strong>"))
        body.append("<ul>%s</ul>" % "".join("<li><p><strong>%s.</strong> %s</p></li>" % (e(w["title"].rstrip(".")), inline(w["text"])) for w in pr["why"]))
    if pr.get("try"):
        body.append(box("Clip and try today. 5 minutes", p(inline(pr["try"])), "#EAF8B8", "#1D1D1F"))
    if pr.get("sources"):
        body.append(p("<strong>Sources: </strong>" + inline(pr["sources"])))
    out.append(sec("".join(body), **CARDW))
    # In brief
    out.append(sec(img(S["h_brief"], "In brief: Three more, fast"), anchor=("hits", "In brief"), **IMGSEC))
    out.append(sec("".join(p('<span style="color: #7C3AED; font-weight: 700; font-size: 1.0625rem;"><strong>%s.</strong></span> %s%s'
                             % (e(b["name"]), inline(b["text"]), " " + inline(b["sources"]) if b.get("sources") else "")) for b in d["brief"]), **CARDW))
    # Friday quiz
    if d.get("quiz"):
        q = d["quiz"]
        out.append(sec(img(S["h_quiz"], "The Friday recap: Test yourself"), anchor=("quiz", "Friday quiz"), **IMGSEC))
        body = [p(inline(x)) for x in q.get("recap", [])]
        L = "ABCDE"
        for n, qq in enumerate(q["questions"]):
            body.append(p("<strong>Question %d. %s</strong>" % (n + 1, e(qq["question"]))))
            body.append("<ul>%s</ul>" % "".join("<li><p>%s. %s</p></li>" % (L[k], e(o)) for k, o in enumerate(qq["options"])))
        ans = "".join(p("<strong>%d: %s.</strong> %s" % (n + 1, L[qq["answer"]], e(qq.get("explain", "")))) for n, qq in enumerate(q["questions"]))
        body.append(box("Answers. No peeking", ans, "#FFF0CC", "#8A5A00"))
        if q.get("sources"):
            body.append(p("<strong>Sources: </strong>" + inline(q["sources"])))
        out.append(sec("".join(body), **CARDW))
    # Your turn, missed an issue, subscribe, footer
    out.append(sec(label("Your turn", "#D92D20") + "<h2>%s</h2>" % run(d["your_turn"], "#1D1D1F", 24, bold=True)
                   + p(run("One line is plenty. Add yours in the comments below.", "#6E6E73", 16)),
                   bg="#FFFFFF", fg="#1D1D1F", radius=26, mt=24, pad=(22, 20, 22, 20), border="#E5E5E9"))
    links = ""
    if d.get("prev_url"):
        links += p(link("%s →" % d.get("prev_label", "Read the previous issue"), d["prev_url"], "#0A6CFF", 16, same_tab=True))
    links += p(link("See all past issues →", SITE + "/archive", "#0A6CFF", 16, same_tab=True))
    out.append(sec(label("Missed an issue?", "#0A6CFF") + "<h2>%s</h2>" % run("Catch up anytime", "#1D1D1F", 28, bold=True) + links,
                   bg="#FFFFFF", fg="#1D1D1F", radius=26, mt=14, pad=(22, 20, 22, 20), border="#E5E5E9"))
    out.append(sec(label("Enjoyed this brief?", "#D8F86C") + "<h2>%s</h2>" % run("Get the next one in your inbox", "#FFFFFF", 28, bold=True)
                   + p(run("Free every weekday morning. Reading on the web stays free too. Unsubscribe anytime.", "#E1E1EB", 16))
                   + button("Subscribe for free", SITE + "/subscribe", "#D8F86C", "#1D1D1F", align="left"),
                   bg="#1D1D1F", fg="#FFFFFF", radius=26, mt=14, pad=(28, 22, 28, 22)))
    out.append(sec(p(run(FOOTER, "#6E6E73", 12)), bg="#F5F5F7", radius=20, mt=14, pad=(16, 16, 16, 16)))
    return out

def load_static():
    f = os.path.join(HERE, "static_urls.json")
    return json.load(open(f)) if os.path.exists(f) else {}

def build_blocks(d, U, layer="both"):
    S = load_static()
    for n in [s[0] for s in STATIC]:
        if n not in S:
            raise SystemExit("static_urls.json is missing %s" % n)
    for n in image_names(d):
        if n != "thumb" and n not in U:
            raise SystemExit("urls.json is missing %s" % n)
    if layer == "web":
        return web_layer(d, U, S)
    if layer == "email":
        return email_layer(d, U)
    return email_layer(d, U) + web_layer(d, U, S)

def cmd_html(d, U, outdir, limit=14000, layer="both"):
    if check(d):
        raise SystemExit("fix the errors above first")
    blocks = build_blocks(d, U, layer)
    os.makedirs(outdir, exist_ok=True)
    for f in os.listdir(outdir):
        if re.match(r"part\d+\.html$", f):
            os.remove(os.path.join(outdir, f))
    parts, cur = [], ""
    for b in blocks:
        if cur and len(cur) + len(b) > limit:
            parts.append(cur); cur = ""
        cur += b
    if cur:
        parts.append(cur)
    for i, t in enumerate(parts):
        open(os.path.join(outdir, "part%d.html" % (i + 1)), "w", encoding="utf-8").write(t)
    meta = {"title": title_for(d), "slug": slug_for(d), "url": post_url(d),
            "subject_line": "Luis's AI Brief: %s" % d["subject_hook"], "subtitle": d["subtitle"],
            "preview_text": MOTTO, "parts": len(parts), "images_in_post": len(re.findall("imageBlock", "".join(parts)))}
    json.dump(meta, open(os.path.join(outdir, "meta.json"), "w"), indent=1)
    print(json.dumps(meta, indent=1))
    print("parts:", [len(t) for t in parts])

def cmd_verify(d, U, saved):
    raw = open(saved, encoding="utf-8").read()
    try:
        j = json.loads(raw)
        if isinstance(j, list):
            j = json.loads(j[0]["text"])
        raw = j.get("body", raw)
    except Exception:
        pass
    text = re.sub(r"\s+", " ", plain(raw))
    bad = []
    want = []
    for s in d["stories"]:
        want += [s["teaser_title"], s["means"], s["clip"], s["sources"]] + s["paragraphs"] + s.get("deeper", [])
    want += [d["prompt"]["title"], d["prompt"]["weak"], d["your_turn"], FOOTER, "Subscribe for free", "Get the next one in your inbox"]
    want += [x["title"] for x in d["newai"] + d["connectors"]] + [b["text"] for b in d["brief"]]
    want += [l for l in d["prompt"]["strong"].split("\n") if l.strip() and "<" not in l]
    for w in want:
        k = re.sub(r"\s+", " ", plain(w)).strip()
        k = re.sub(r"^[-*•]\s+", "", k)[:60]
        if k and k not in text:
            bad.append("missing text: %r" % k)
    n_img = len(re.findall(r'data-type="imageBlock"', raw))
    exp = len(re.findall("imageBlock", "".join(build_blocks(d, U))))
    if n_img != exp:
        bad.append("expected %d images, found %d" % (exp, n_img))
    if "htmlSnippet" in raw:
        bad.append("an htmlSnippet block is present: remove it")
    if "—" in text or "–" in text:
        bad.append("em or en dash found")
    for w in HARD_WORDS:
        if w.lower() in text.lower():
            bad.append("banned phrase: %s" % w)
    if post_url(d) not in raw:
        bad.append("post url %s not found in links" % post_url(d))
    for b in bad:
        print("ERROR", b)
    print("verify:", "FAILED (%d)" % len(bad) if bad else "ok")
    return 1 if bad else 0

def main(a):
    if len(a) < 2:
        raise SystemExit(__doc__)
    c = a[1]
    if c == "static":
        shoot(static_html(), [s[0] for s in STATIC], a[2]); return 0
    d = json.load(open(a[2], encoding="utf-8"))
    if c == "check":
        return 1 if check(d) else 0
    if c == "images":
        if check(d):
            raise SystemExit("fix the errors above first")
        shoot(cards_html(d), image_names(d), a[3]); return 0
    if c == "html":
        cmd_html(d, json.load(open(a[3])), a[4], layer=a[5] if len(a) > 5 else "both"); return 0
    if c == "verify":
        return cmd_verify(d, json.load(open(a[3])), a[4])
    raise SystemExit(__doc__)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
