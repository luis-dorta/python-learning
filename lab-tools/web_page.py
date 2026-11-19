"""Publish one issue of Luis's AI Brief as a static page for GitHub Pages.

Usage:
  python3 lab-tools/web_page.py lab-issues/YYYY-MM-DD.json

It renders the web layer with build_issue.py, turns beehiiv editor markup into
plain HTML and CSS, and writes into docs/:
  docs/img/YYYY-MM-DD/*.jpg     the issue images (copied from lab-images/)
  docs/YYYY-MM-DD/index.html    the issue page
  docs/index.html               the newest issue (same content, links to the archive)
  docs/archive/index.html       every published issue, newest first
  docs/feed.xml                 RSS feed
  docs/issues.json              the list of published issues
Run it from the repo root. Images must already exist in lab-images/YYYY-MM-DD/.
"""
import json, os, re, shutil, subprocess, sys, tempfile, html
from datetime import datetime, timezone
from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
SITE = "https://luis-dorta.github.io/python-learning"
OLD = "https://luiss-newsletter.beehiiv.com"
NAMES = ["mast", "thumb", "bento", "hero", "fig1", "fig2", "fig3", "newai", "prompt"]


def section_style(d):
    s = []
    g = d.get
    if g("data-background-color"): s.append("background:%s" % g("data-background-color"))
    if g("data-color"): s.append("color:%s" % g("data-color"))
    r = [g("data-border-top-left-radius"), g("data-border-top-right-radius"),
         g("data-border-bottom-right-radius"), g("data-border-bottom-left-radius")]
    if any(r): s.append("border-radius:%s" % " ".join("%spx" % (x or 0) for x in r))
    if g("data-border-style"):
        w = [g("data-border-width-top"), g("data-border-width-right"),
             g("data-border-width-bottom"), g("data-border-width-left")]
        s.append("border-style:%s;border-color:%s;border-width:%s" % (
            g("data-border-style"), g("data-border-color") or "#E5E5E9",
            " ".join("%spx" % (x or 0) for x in w)))
    if g("data-margin-top"): s.append("margin-top:%spx" % g("data-margin-top"))
    p = [g("data-padding-top"), g("data-padding-right"), g("data-padding-bottom"), g("data-padding-left")]
    if any(x is not None for x in p): s.append("padding:%s" % " ".join("%spx" % (x or 0) for x in p))
    return ";".join(s)


def convert(markup, date, published):
    soup = BeautifulSoup(markup, "html.parser")
    for d in soup.find_all(attrs={"data-type": "section"}):
        st = section_style(d.attrs)
        aid = d.get("data-anchor-id")
        for k in list(d.attrs):
            del d[k]
        d["class"] = "sec"
        d["style"] = st
        if aid:
            d["id"] = aid
    for f in soup.find_all("figure", attrs={"data-type": "imageBlock"}):
        img = soup.new_tag("img", src=f.get("data-src", ""), alt=f.get("data-alt", ""), loading="lazy")
        img["class"] = "img"
        url = f.get("data-url")
        if url:
            a = soup.new_tag("a", href=url)
            a.append(img)
            img = a
        f.replace_with(img)
    for b in soup.find_all("a", attrs={"data-type": "button"}):
        st = "background:%s;color:%s" % (b.get("data-custom-background-color", "#1D1D1F"),
                                          b.get("data-custom-text-color", "#FFFFFF"))
        href = b.get("href")
        for k in list(b.attrs):
            del b[k]
        b["href"] = href
        b["class"] = "btn"
        b["style"] = st
    for a in soup.find_all("a", href=True):
        h = a["href"]
        m = re.match(re.escape(OLD) + r"/p/luis-s-ai-brief-([a-z]+)-(\d+)-(\d{4})(#.*)?$", h)
        if m:
            try:
                dt = datetime.strptime("%s %s %s" % m.group(1, 2, 3), "%B %d %Y").strftime("%Y-%m-%d")
            except ValueError:
                dt = None
            if dt and dt in published:
                a["href"] = "%s/%s/%s" % (SITE, dt, m.group(4) or "")
        elif h.rstrip("/") in (OLD, OLD + "/archive") or h.startswith(OLD + "/archive"):
            a["href"] = SITE + "/archive/"
        if a.get("target") == "_self":
            del a["target"]
        if a.get("rel") == "" or a.get("rel") == []:
            del a["rel"]
    out = str(soup)
    out = out.replace("Add yours in the comments below.",
                      "Share yours with a colleague, or repost the issue with your answer.")
    return out


def subscribe_block(markup):
    """The beehiiv subscribe button no longer fits (no emails go out from this page).
    Swap that block for a follow block: bookmark plus RSS."""
    soup = BeautifulSoup(markup, "html.parser")
    for b in soup.find_all("a", class_="btn"):
        if "subscribe" in b.get("href", ""):
            sec = b.find_parent("div", class_="sec")
            new = BeautifulSoup(
                '<div class="sec" style="%s">'
                '<p><span style="color:#D8F86C;font-weight:700;font-size:0.75rem"><strong>ENJOYED THIS BRIEF?</strong></span></p>'
                '<h2><span style="color:#FFFFFF;font-weight:700;font-size:1.5rem"><strong>A new issue every weekday morning</strong></span></h2>'
                '<p><span style="color:#E1E1EB;font-size:1rem">Free to read, no sign-up. Bookmark this page, it always opens the newest issue, '
                'or follow along in any feed reader.</span></p>'
                '<p><a class="btn" style="background:#D8F86C;color:#1D1D1F" href="%s/">Bookmark the brief</a> '
                '<a class="btn" style="background:#FFFFFF;color:#1D1D1F" href="%s/feed.xml">RSS feed</a></p></div>'
                % (sec.get("style", ""), SITE, SITE), "html.parser")
            sec.replace_with(new)
    return str(soup)


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canon}">
<link rel="alternate" type="application/rss+xml" title="Luis's AI Brief" href="{site}/feed.xml">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{thumb}">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@600;700;800&family=Figtree:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{{color-scheme:light}}
*{{box-sizing:border-box}}
html{{scroll-behavior:smooth}}
body{{margin:0;background:#F5F5F7;color:#1D1D1F;font:16px/1.55 Figtree,system-ui,-apple-system,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased}}
main{{max-width:680px;margin:0 auto;padding:16px 14px 48px}}
h1,h2,h3{{font-family:"Bricolage Grotesque",Figtree,sans-serif;line-height:1.15;margin:.35em 0 .3em;letter-spacing:-.01em}}
p{{margin:.45em 0}}
ul{{margin:.4em 0;padding-left:1.2em}} li{{margin:.25em 0}}
a{{color:inherit}}
.sec{{overflow:hidden}}
.sec>*:first-child{{margin-top:0}} .sec>*:last-child{{margin-bottom:0}}
.img{{display:block;width:100%;height:auto;border-radius:18px;margin:6px 0}}
.btn{{display:inline-block;padding:12px 20px;border-radius:999px;font-weight:700;text-decoration:none;margin:6px 6px 0 0}}
.btn:focus-visible,a:focus-visible{{outline:3px solid #0A6CFF;outline-offset:2px}}
.top{{display:flex;justify-content:space-between;align-items:center;font-size:.8rem;color:#6E6E73;margin:0 2px 10px}}
.top a{{text-decoration:none;font-weight:700;color:#1D1D1F}}
code{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.9em;background:rgba(0,0,0,.06);padding:1px 5px;border-radius:6px}}
hr{{border:0;border-top:1px solid #E5E5E9;margin:16px 0}}
@media (prefers-reduced-motion:reduce){{html{{scroll-behavior:auto}}}}
</style>
</head>
<body>
<main>
<div class="top"><a href="{site}/">Luis's AI Brief</a><a href="{site}/archive/">All issues</a></div>
{body}
</main>
</body>
</html>
"""


def list_page(issues):
    rows = "".join(
        '<div class="sec" style="background:#FFFFFF;border-radius:20px;padding:16px 18px;margin-top:10px">'
        '<p><span style="color:#6E6E73;font-size:.8rem;font-weight:700">%s</span></p>'
        '<h2 style="font-size:1.25rem"><a href="%s/%s/" style="text-decoration:none">%s</a></h2>'
        '<p style="color:#3A3A3C">%s</p></div>'
        % (html.escape(i["date_long"]).upper(), SITE, i["date"], html.escape(i["headline"]), html.escape(i["subtitle"]))
        for i in issues)
    old = ('<div class="sec" style="background:#FFFFFF;border-radius:20px;padding:16px 18px;margin-top:10px">'
           '<p style="color:#3A3A3C">Issues from November 5 to 18, 2026 are on our '
           '<a href="%s/archive">earlier site</a>.</p></div>' % OLD)
    body = ('<div class="sec" style="background:#0B0B0F;color:#FFFFFF;border-radius:26px;padding:22px 20px">'
            '<h1 style="font-size:2.4rem;margin:0">Every issue</h1>'
            '<p style="color:#E1E1EB">A free weekday brief on AI for marketers: the top stories, what they mean, and one skill to practice.</p></div>'
            + rows + old)
    return PAGE.format(title="Every issue | Luis's AI Brief", desc="Every issue of Luis's AI Brief, newest first.",
                       canon=SITE + "/archive/", site=SITE, thumb=issues[0]["thumb"] if issues else "", body=body)


def feed(issues):
    items = "".join(
        "<item><title>%s</title><link>%s/%s/</link><guid>%s/%s/</guid><pubDate>%s</pubDate><description>%s</description></item>"
        % (html.escape(i["title"]), SITE, i["date"], SITE, i["date"],
           datetime.strptime(i["date"], "%Y-%m-%d").replace(hour=12, tzinfo=timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000"),
           html.escape(i["subtitle"]))
        for i in issues[:30])
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>Luis\'s AI Brief</title>'
            '<link>%s/</link><description>A free weekday brief on AI for marketers.</description>%s</channel></rss>\n'
            % (SITE, items))


def main(issue_path):
    issue = json.load(open(issue_path))
    date = os.path.basename(issue_path)[:-5]
    src = os.path.join(ROOT, "lab-images", date)
    if not os.path.isdir(src):
        raise SystemExit("missing images: " + src)
    imgdir = os.path.join(DOCS, "img", date)
    os.makedirs(imgdir, exist_ok=True)
    urls = {}
    for n in NAMES:
        f = os.path.join(src, n + ".jpg")
        if os.path.exists(f):
            shutil.copy(f, imgdir)
            urls[n] = "%s/img/%s/%s.jpg" % (SITE, date, n)
    tmp = tempfile.mkdtemp()
    json.dump(urls, open(os.path.join(tmp, "urls.json"), "w"))
    subprocess.run([sys.executable, os.path.join(ROOT, "lab-tools", "build_issue.py"), "html", issue_path,
                    os.path.join(tmp, "urls.json"), os.path.join(tmp, "out"), "web"], check=True,
                   stdout=subprocess.DEVNULL)
    meta = json.load(open(os.path.join(tmp, "out", "meta.json")))
    parts = sorted(p for p in os.listdir(os.path.join(tmp, "out")) if p.startswith("part"))
    markup = "".join(open(os.path.join(tmp, "out", p)).read() for p in sorted(parts, key=lambda x: int(re.sub(r"\D", "", x))))

    manifest_path = os.path.join(DOCS, "issues.json")
    issues = json.load(open(manifest_path)) if os.path.exists(manifest_path) else []
    issues = [i for i in issues if i["date"] != date]
    entry = {"date": date, "date_long": issue.get("date_long", date), "title": meta["title"],
             "headline": issue["stories"][0].get("teaser_title") or meta["title"],
             "subtitle": meta["subtitle"], "thumb": urls.get("thumb", "")}
    issues.append(entry)
    issues.sort(key=lambda i: i["date"], reverse=True)
    published = {i["date"] for i in issues}

    # section header images: serve our own copies instead of beehiiv's
    st = json.load(open(os.path.join(ROOT, "lab-tools", "static_urls.json")))
    sdir = os.path.join(DOCS, "img", "static")
    os.makedirs(sdir, exist_ok=True)
    for n, u in st.items():
        f = os.path.join(ROOT, "lab-images", "static", n + ".jpg")
        if os.path.exists(f):
            shutil.copy(f, sdir)
            markup = markup.replace(u, "%s/img/static/%s.jpg" % (SITE, n))
    body = subscribe_block(convert(markup, date, published))
    # beehiiv-only email layer never reaches here (web mode), but strip any leftover data-* noise
    page = PAGE.format(title=html.escape(meta["title"]), desc=html.escape(meta["subtitle"]),
                       canon="%s/%s/" % (SITE, date), site=SITE, thumb=urls.get("thumb", ""), body=body)
    if re.search("[–—]", page):
        raise SystemExit("ERROR: en or em dash in the page")
    os.makedirs(os.path.join(DOCS, date), exist_ok=True)
    open(os.path.join(DOCS, date, "index.html"), "w").write(page)
    if issues[0]["date"] == date:
        open(os.path.join(DOCS, "index.html"), "w").write(page)
    os.makedirs(os.path.join(DOCS, "archive"), exist_ok=True)
    open(os.path.join(DOCS, "archive", "index.html"), "w").write(list_page(issues))
    open(os.path.join(DOCS, "feed.xml"), "w").write(feed(issues))
    open(manifest_path, "w").write(json.dumps(issues, indent=1) + "\n")
    open(os.path.join(DOCS, ".nojekyll"), "w").write("")
    print("page: ok | %s/%s/ | %d issues listed" % (SITE, date, len(issues)))


if __name__ == "__main__":
    main(sys.argv[1])
