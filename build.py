"""Build the ChromaChaos site and its Pinterest RSS feed into _site/.

Standard library only, so GitHub Actions needs no installs. Runs on every push
and once a day: a pin in data/pins.json appears on the site and in feed.xml on
its `release` date, and Pinterest's RSS auto-publish turns each new feed item
into a pin. Nothing here talks to Pinterest or Etsy.
"""
import datetime as dt
import html
import json
import os
import re
import shutil
from email.utils import format_datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "_site"
BASE = "https://chromachaos.kafkami.nl"
SHOP = "https://www.etsy.com/shop/ChromaChaos"
UTM = "utm_source=pinterest&utm_medium=social&utm_campaign=launch"
PATHS = {"a-hero": "", "b-pieces": "pieces/", "c-lifestyle": "journal/"}
FEED_MAX = 150
e = html.escape


def today() -> dt.date:
    forced = os.environ.get("BUILD_DATE")
    return dt.date.fromisoformat(forced) if forced else dt.datetime.now(dt.timezone.utc).date()


def path_of(p) -> str:
    return f"/{p['slug']}/{PATHS.get(p['variant'], p['variant'] + '/')}"


def etsy(p) -> str:
    return f"https://www.etsy.com/listing/{p['listing_id']}?{UTM}"


def prose(p) -> str:
    """Pin description without the trailing hashtags."""
    return re.sub(r"(\s*#\w+)+\s*$", "", p["description"]).strip()


def page(title, desc, canonical, body, image=None) -> str:
    og = f'<meta property="og:image" content="{e(image)}">' if image else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(canonical)}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(canonical)}"><meta property="og:type" content="website">{og}
<link rel="alternate" type="application/rss+xml" title="ChromaChaos new sets" href="/feed.xml">
<link rel="stylesheet" href="/style.css">
</head><body>
<header class="wrap"><a href="/"><img src="/img/logo.png" alt="ChromaChaos digital arts"></a></header>
<nav><a href="/#latest">Latest</a><a href="/#destinations">Favourites</a><a href="/#about">About</a><a href="{SHOP}">Shop on Etsy</a></nav>
<main class="wrap">
{body}
</main>
<footer class="wrap">© {today().year} ChromaChaos · <a href="/privacy.html">Privacy policy</a> · <a href="{SHOP}">Etsy shop</a></footer>
</body></html>
"""


def card(p) -> str:
    return (f'<a class="card" href="{path_of(p)}"><img src="/{p["image"]}" alt="{e(p["name"])} watercolour clipart" '
            f'loading="lazy" width="1000" height="1500"><span>{e(p["name"])}</span></a>')


def write(rel: str, text: str) -> None:
    f = OUT / rel.lstrip("/")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")


def main() -> None:
    pins = json.loads((HERE / "data" / "pins.json").read_text(encoding="utf-8"))
    now = today()
    live = sorted([p for p in pins if dt.date.fromisoformat(p["release"]) <= now],
                  key=lambda p: (p["release"], p["slug"], p["variant"]), reverse=True)
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    for d in ("fonts", "img"):
        shutil.copytree(HERE / d, OUT / d)
    shutil.copy2(HERE / "style.css", OUT / "style.css")
    (OUT / "pins").mkdir()
    for p in live:                                   # future pins stay off the site
        shutil.copy2(HERE / p["image"], OUT / p["image"])
    write("CNAME", BASE.split("//")[1] + "\n")
    write(".nojekyll", "")

    # one card per bundle on the home page: its most recent released pin
    first = {}
    for p in live:
        first.setdefault(p["slug"], p)
    latest = list(first.values())

    for p in live:
        sibs = [q for q in live if q["slug"] == p["slug"] and q is not p]
        more = [q for q in latest if q["slug"] != p["slug"]][:8]
        sib_html = ('<section><h2>More from this set</h2><div class="grid tall">'
                    + "".join(card(q) for q in sibs) + "</div></section>") if sibs else ""
        more_html = ('<section><h2>More destinations</h2><div class="grid tall">'
                     + "".join(card(q) for q in more) + "</div></section>") if more else ""
        body = f"""<p class="crumb"><a href="/">ChromaChaos</a> · {e(p['name'])}</p>
<div class="pin">
<img src="/{p['image']}" alt="{e(p['title'])}" width="1000" height="1500">
<div>
<h1>{e(p['title'])}</h1>
<p>{e(prose(p))}</p>
<ul><li>Instant digital download from our Etsy shop</li><li>Transparent PNG files at 300 DPI</li><li>Works in Canva, Procreate, Goodnotes and print</li></ul>
<p><a class="btn" href="{e(etsy(p))}" rel="noopener">Get this set on Etsy</a></p>
<p style="color:var(--muted);font-size:15px">Checkout and delivery are handled by Etsy.</p>
</div></div>
{sib_html}{more_html}"""
        write(path_of(p) + "index.html",
              page(f"{p['title']} | ChromaChaos", prose(p)[:155], BASE + path_of(p), body, f"{BASE}/{p['image']}"))

    featured = json.loads((HERE / "img" / "featured.json").read_text(encoding="utf-8"))
    fav = "".join(f'<a class="card" href="{e(f["url"])}"><img src="/img/{f["key"]}.jpg" alt="{e(f["name"])} watercolour clipart" '
                  f'loading="lazy" width="1000" height="800"><span>{e(f["name"])}</span></a>' for f in featured)
    latest_html = (f'<section id="latest"><h2>Latest sets</h2><div class="grid tall">{"".join(card(p) for p in latest[:24])}</div></section>'
                   if latest else "")
    home = f"""<h1>Watercolour travel clipart for every trip worth remembering</h1>
<p class="lead">Hand-finished destination sets — landmarks, food, streets and the little details — made for travel journals, scrapbooks, photo books, cards and trip-themed parties.</p>
<p class="center"><a class="btn" href="{SHOP}">Browse the shop on Etsy</a></p>
{latest_html}
<section id="destinations"><h2>Favourites</h2>
<p style="color:var(--muted);margin-top:0">Over a hundred cities and regions, each in the same matching style, so a whole trip stays on one page.</p>
<div class="grid">{fav}</div>
<p class="center" style="margin-top:28px"><a href="{SHOP}">See every destination →</a></p></section>
<section id="about"><div class="three">
<div><h3>Drawn to look like the place</h3><p>Landmarks are painted to be recognised — the real castle, the real bridge — not generic scenery, so your page reads as the trip you took.</p></div>
<div><h3>Ready to use</h3><p>Transparent PNG files at 300 DPI, delivered instantly as a digital download. Drop them into Canva, Procreate, Goodnotes or a print.</p></div>
<div><h3>Made to match</h3><p>City sets, vintage stamps, luggage labels and papers share one palette, so every destination pairs with the rest.</p></div>
</div>
<p class="center script" style="margin:40px 0 0">made for memory keepers</p>
<p class="center" style="color:var(--muted);max-width:640px;margin:8px auto 0">ChromaChaos is a small independent studio. Every set is sold through our Etsy shop, which handles checkout and delivery, and comes with a commercial use licence.</p></section>
<section id="contact" class="center"><h2>Contact</h2>
<p>Questions about a set, a custom destination or licensing? Message us through <a href="{SHOP}">our Etsy shop</a>.</p></section>"""
    write("index.html", page("ChromaChaos — Watercolour Travel Clipart",
          "Watercolour travel clipart for journals, scrapbooks and photo books: recognisable landmarks, stamps and luggage labels as transparent PNGs.",
          BASE + "/", home))
    write("privacy.html", page("Privacy policy | ChromaChaos", "ChromaChaos privacy policy.", BASE + "/privacy.html",
          '<div class="policy">' + (HERE / "data" / "privacy_body.html").read_text(encoding="utf-8") + "</div>"))
    write("404.html", page("Page not found | ChromaChaos", "Page not found.", BASE + "/",
          '<h1>That page has moved</h1><p class="center"><a class="btn" href="/">Back to ChromaChaos</a></p>'))

    # RSS 2.0 (Pinterest does not read Atom). Every link sits on the claimed domain.
    items = []
    for p in live[:FEED_MAX]:
        d = dt.date.fromisoformat(p["release"])
        when = format_datetime(dt.datetime(d.year, d.month, d.day, 5, 0, tzinfo=dt.timezone.utc))
        url, img = BASE + path_of(p), f"{BASE}/{p['image']}"
        size = (HERE / p["image"]).stat().st_size
        items.append(f"""<item>
<title>{e(p['title'])}</title>
<link>{e(url)}</link>
<guid isPermaLink="true">{e(url)}</guid>
<pubDate>{when}</pubDate>
<description><![CDATA[<img src="{img}" alt="{e(p['title'])}"><p>{e(p['description'])}</p>]]></description>
<enclosure url="{e(img)}" length="{size}" type="image/jpeg"/>
<media:content url="{e(img)}" medium="image" type="image/jpeg" width="1000" height="1500"/>
</item>""")
    built = format_datetime(dt.datetime.now(dt.timezone.utc))
    write("feed.xml", f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
<title>ChromaChaos — new watercolour travel clipart</title>
<link>{BASE}/</link>
<description>New watercolour travel clipart sets for journals, scrapbooks and photo books.</description>
<language>en</language>
<lastBuildDate>{built}</lastBuildDate>
<atom:link href="{BASE}/feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
</channel>
</rss>
""")
    urls = ["/", "/privacy.html"] + [path_of(p) for p in live]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"<url><loc>{BASE}{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    print(f"[build] {now}: {len(live)} of {len(pins)} pins released, {len(latest)} bundles, feed items {min(len(live), FEED_MAX)}")


if __name__ == "__main__":
    main()
