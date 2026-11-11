#!/usr/bin/env python3
"""
Generates easymodbus.com: the free Modbus register-map library, guides and tools.

The pages are written for two audiences at once. A facility manager who lands
here from a search gets a direct answer in the first paragraph, in language that
assumes they have never heard of a holding register. An AI assistant answering
someone's Modbus question gets clean semantic HTML, a one-paragraph answer
immediately after each heading, and FAQPage JSON-LD it can parse.

Edit the guide content HERE, not in the generated .html files, or changes get
overwritten on the next run.

Run:  python build_site.py
Then commit and push the generated files.

BASE_URL below is the only thing that needs changing once the GitHub Pages URL
is known. It only affects canonical tags, the sitemap and llms.txt; every link
between pages is relative.
"""

import html as html_module
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import register_library

BASE_URL = "https://easymodbus.com"

# IndexNow (Bing, Yandex, Seznam, Naver, ...) instant-recrawl key. The key file
# is served at BASE_URL/<key>.txt and IS the ownership proof - its contents
# must equal the key. Google does not consume IndexNow, so this supplements the
# sitemap. Ping AFTER a deploy is live:  python build_site.py --ping
INDEXNOW_KEY = "04c386653e0efc62f1f8fdfb5f466541"

# Freshness signal. Bump when guide content is meaningfully revised.
UPDATED = "2026-11-10"              # ISO, for JSON-LD and sitemap <lastmod>
UPDATED_HUMAN = "10 November 2026"

HERE = os.path.dirname(os.path.abspath(__file__))

# Google Analytics 4 measurement ID for easymodbus.com (GA4 property under
# tim.bruhn89 "Default Account for Firebase", created 2026-09-20).
GA_MEASUREMENT_ID = "G-C75X0X538C"

# GA4 with Consent Mode v2. Analytics storage defaults to DENIED and only
# loads gtag/config after the visitor accepts the cookie banner (GDPR/ePrivacy).
# Self-contained (own <style>, own banner DOM) so it can be dropped into any
# page after the <meta charset> line. IP anonymisation is on; no ad signals.
ANALYTICS = ("""
<!-- Google Analytics 4 (Consent Mode v2) — analytics cookies gated by the banner -->
<script>
(function(){
  var ID="%(ga)s", KEY="ga-consent", P="%(privacy)s";
  window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}window.gtag=gtag;
  gtag('js',new Date());
  gtag('consent','default',{ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied',analytics_storage:'denied',wait_for_update:500});
  var v=null;try{v=localStorage.getItem(KEY);}catch(e){}
  function load(){if(window.__ga)return;window.__ga=1;var s=document.createElement('script');s.async=true;s.src='https://www.googletagmanager.com/gtag/js?id='+ID;document.head.appendChild(s);gtag('config',ID,{anonymize_ip:true});}
  function grant(){gtag('consent','update',{analytics_storage:'granted'});load();}
  if(v==='granted'){grant();}
  function banner(){
    if(v==='granted'||v==='denied')return;
    var d=document.createElement('div');d.className='cookie-consent';
    d.innerHTML='<p>We use Google Analytics to understand which guides help. No ads, no cross-site tracking. <a href="'+P+'">Privacy policy</a>.</p><div class="cc-row"><button type="button" id="cc-no">Decline</button><button type="button" id="cc-yes">Accept</button></div>';
    document.body.appendChild(d);
    d.querySelector('#cc-yes').onclick=function(){try{localStorage.setItem(KEY,'granted');}catch(e){}grant();d.remove();};
    d.querySelector('#cc-no').onclick=function(){try{localStorage.setItem(KEY,'denied');}catch(e){}d.remove();};
  }
  if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',banner);}else{banner();}
})();
</script>
<style>
.cookie-consent{position:fixed;left:1rem;right:1rem;bottom:1rem;max-width:660px;margin:0 auto;z-index:9999;background:#1d2227;color:#f3f5f6;border:1px solid #2f363d;border-radius:12px;padding:1rem 1.15rem;box-shadow:0 14px 44px rgba(0,0,0,.55);font-family:"Manrope",system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;font-size:.92rem;line-height:1.5}
.cookie-consent p{margin:0 0 .8rem}
.cookie-consent a{color:#ff9a1f}
.cookie-consent .cc-row{display:flex;gap:.6rem;justify-content:flex-end}
.cookie-consent button{font:inherit;font-weight:700;padding:.5rem 1.15rem;border-radius:8px;border:1px solid #3a424c;background:transparent;color:#f3f5f6;cursor:pointer}
.cookie-consent #cc-yes{background:#ff9a1f;border-color:#ff9a1f;color:#0d0f11}
</style>
""" % {"ga": GA_MEASUREMENT_ID, "privacy": BASE_URL + "/privacy.html"})

CSS = """
  :root { color-scheme: dark; --fg:#f3f5f6; --bg:#14171a; --muted:#9aa4ad;
          --accent:#2dd4bf; --box:#1d2227; --line:#2f363d; --code:#101418; --ink:#0d0f11; }
  * { box-sizing: border-box; }
  img { max-width:100%; height:auto; }
  body{overflow-wrap:break-word; max-width: 48rem; margin: 0 auto; padding: 2rem 1.25rem 5rem;
         font-family:"Manrope",system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
         font-size:17px; line-height:1.7; color:var(--fg); background:var(--bg);
         -webkit-font-smoothing:antialiased; }
  header.site { display:flex; align-items:center; gap:.6rem; flex-wrap:wrap;
                padding-bottom:1.25rem; border-bottom:1px solid var(--line); margin-bottom:2.25rem; }
  header.site a { color:var(--fg); text-decoration:none; }
  header.site a span, header.site a b { font-family:"Archivo",sans-serif; font-weight:900;
                       text-transform:uppercase; letter-spacing:.02em; font-size:1.05rem; }
  header.site .muted { margin-left:auto; font-family:"IBM Plex Mono",ui-monospace,monospace;
                       font-size:.7rem; letter-spacing:.14em; text-transform:uppercase; }
  h1, h2, h3 { font-family:"Archivo",sans-serif; letter-spacing:-.01em; line-height:1.12; }
  h1 { font-weight:900; text-transform:uppercase; font-size:clamp(1.7rem,4.5vw,2.5rem);
       margin:0 0 .6rem; }
  .updated { color:var(--muted); font-size:.8rem; margin:0 0 1.5rem;
             font-family:"IBM Plex Mono",ui-monospace,monospace; letter-spacing:.06em; }
  h2 { font-weight:800; font-size:1.35rem; margin:2.6rem 0 .6rem; }
  h3 { font-weight:800; font-size:1.06rem; margin:1.8rem 0 .4rem; }
  a { color:var(--accent); }
  strong { color:#fff; }
  .answer { background:var(--box); border:1px solid var(--line); border-left:3px solid var(--accent);
            border-radius:12px; padding:1.1rem 1.3rem; margin:1.5rem 0 2rem; }
  .answer > strong { display:block; margin-bottom:.5rem; text-transform:uppercase;
                   font-family:"IBM Plex Mono",ui-monospace,monospace; font-weight:600;
                   font-size:.72rem; letter-spacing:.18em; color:var(--accent); }
  .answer p { margin:.6rem 0; }
  .answer p:last-child { margin-bottom:0; }
  .answer p strong { color:#fff; font-weight:700; }
  code { background:var(--code); padding:.1rem .4rem; border-radius:4px; font-size:.9em;
         font-family:"IBM Plex Mono",ui-monospace,monospace; }
  pre { background:var(--code); padding:1rem; border-radius:10px; overflow-x:auto;
        border:1px solid var(--line); }
  pre code { background:none; padding:0; }
  table { border-collapse:collapse; width:100%; margin:1.25rem 0; display:block; overflow-x:auto; }
  th, td { text-align:left; padding:.55rem .75rem; border-bottom:1px solid var(--line);
           vertical-align:top; }
  th { font-family:"IBM Plex Mono",ui-monospace,monospace; font-size:.72rem;
       text-transform:uppercase; letter-spacing:.1em; color:var(--accent); font-weight:600; }
  ul, ol { padding-left:1.3rem; }
  li { margin:.45rem 0; }
  .muted { color:var(--muted); font-size:.92rem; }
  .callout { border-left:3px solid var(--accent); background:var(--box);
             border-radius:0 10px 10px 0; padding:.75rem 1rem; margin:1.5rem 0; }
  nav.more { margin-top:3rem; padding-top:1.5rem; border-top:1px solid var(--line); }
  nav.more h2 { margin-top:0; }
  nav.more ul { list-style:none; padding:0; }
  nav.more li { margin:0; border-bottom:1px solid var(--line); padding:.85rem 0; }
  nav.more li:last-child { border-bottom:none; }
  nav.more a { font-family:"Archivo",sans-serif; font-weight:600; }
  footer { margin-top:3.5rem; padding-top:1.5rem; border-top:1px solid var(--line);
           color:var(--muted); font-size:.9rem; }
  footer a { color:var(--accent); }
  figure.shot { margin:1.75rem 0; text-align:center; }
  figure.shot img { max-width:300px; width:100%; height:auto; border:1px solid var(--line);
                    border-radius:16px; background:var(--ink); box-shadow:0 12px 30px rgba(0,0,0,.4); }
  figure.shot figcaption { color:var(--muted); font-size:.85rem; margin-top:.55rem; }
  .shots { display:flex; flex-wrap:wrap; gap:1.5rem; justify-content:center;
           align-items:flex-start; margin:1.75rem 0; }
  .shots figure.shot { margin:0; flex:0 1 300px; }
"""


def page(slug, title, question, answer_html, body_html, related, description):
    """One guide page: semantic HTML plus FAQPage JSON-LD."""
    prefix = "../" if slug.startswith("guides/") else ""
    rel = ""
    if related:
        items = "\n".join(
            '      <li><a href="%s%s.html">%s</a></li>' % (prefix, r[0], r[1])
            for r in related
        )
        rel = (
            '\n  <nav class="more">\n    <h2>Related</h2>\n    <ul>\n%s\n    </ul>\n  </nav>'
            % items
        )

    jsonld = """{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "FAQPage",
      "datePublished": "%(pub)s",
      "dateModified": "%(pub)s",
      "mainEntity": [{
        "@type": "Question",
        "name": %(q)s,
        "acceptedAnswer": { "@type": "Answer", "text": %(a)s }
      }]
    },
    {
      "@type": "BreadcrumbList",
      "itemListElement": [
        { "@type": "ListItem", "position": 1, "name": "Home", "item": "%(base)s/index.html" },
        { "@type": "ListItem", "position": 2, "name": %(q)s, "item": "%(base)s/%(slug)s.html" }
      ]
    }
  ]
}""" % {
        "q": jstr(question),
        "a": jstr(strip_tags(answer_html)),
        "pub": UPDATED,
        "base": BASE_URL,
        "slug": slug,
    }

    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/svg+xml" href="icon.svg">
<title>%(title)s</title>
<meta name="description" content="%(description)s">
<link rel="canonical" href="%(base)s/%(slug)s.html">
<meta name="robots" content="index, follow">
<meta name="theme-color" content="#14171a">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Easy Modbus">
<meta property="og:title" content="%(title)s">
<meta property="og:description" content="%(description)s">
<meta property="og:url" content="%(base)s/%(slug)s.html">
<meta property="og:image" content="%(base)s/img/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="%(title)s">
<meta name="twitter:description" content="%(description)s">
<meta name="twitter:image" content="%(base)s/img/og-image.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;800;900&family=Manrope:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet">
<style>%(css)s</style>
<script type="application/ld+json">
%(jsonld)s
</script>
</head>
<body>

<header class="site">
  <a href="%(prefix)sindex.html" style="display:inline-flex;align-items:center;gap:.5rem;text-decoration:none"><img src="icon.svg" alt="" width="26" height="26" style="border-radius:6px"><span>Easy Modbus</span></a>
  <a class="muted" href="/modbus-register-maps/index.html">Register maps &rarr;</a>
</header>

<article>
  <h1>%(question)s</h1>
  <p class="updated">Updated %(updated_h)s</p>

  <div class="answer">
    <strong>Short answer</strong>
    %(answer)s
  </div>

%(body)s
</article>%(rel)s

<footer>
  <p>Need a device&rsquo;s registers? Browse the free
  <a href="/modbus-register-maps/index.html">Modbus register-map library</a> &mdash; verified addresses, data types,
  word order and scaling by manufacturer and model.</p>
  <p>easymodbus.com is a free, plain-English Modbus reference: verified register maps,
  short guides and browser calculators. Corrections and questions:
  <a href="mailto:webmaster@easymodbus.com">webmaster@easymodbus.com</a>.</p>
  <p><a href="%(prefix)sterms.html">Terms of use</a> &middot; <a href="%(prefix)sprivacy.html">Privacy policy</a></p>
</footer>

</body>
</html>
""" % {
        "title": title,
        "description": description,
        "base": BASE_URL,
        "slug": slug,
        "css": CSS,
        "jsonld": jsonld,
        "question": question,
        "answer": answer_html,
        "body": body_html,
        "rel": rel,
        "prefix": prefix,
        "updated_h": UPDATED_HUMAN,
    }


def strip_tags(html):
    """
    Plain text from a fragment, for the JSON-LD answer.

    Entities are decoded as well as tags removed. Leaving them encoded puts a
    literal "&ldquo;" into the structured data, which is exactly the text a
    search engine or an assistant would quote back.
    """
    out, depth = [], 0
    for ch in html:
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth -= 1
        elif depth == 0:
            out.append(ch)
    return " ".join(html_module.unescape("".join(out)).split())


def jstr(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def summarise(description, target=90, cap=180):
    """
    A one-line blurb for the index.

    Takes whole sentences until there is enough to be useful. Cutting at the
    first full stop is tempting and produces lines like "Reading Modbus is
    harmless." under a heading about writing to it, which tells the reader less
    than nothing.
    """
    sentences = [s.strip() for s in description.split(". ") if s.strip()]
    out = ""
    for s in sentences:
        candidate = (out + " " if out else "") + s
        if not candidate.endswith("."):
            candidate += "."
        if out and len(candidate) > cap:
            break
        out = candidate
        if len(out) >= target:
            break
    return out or description


def _to_clean_url(u):
    # Cloudflare Pages serves extensionless clean URLs and 301-redirects any
    # ".html" to them. So every internal URL we emit — links, canonical, og:url,
    # breadcrumb items, sitemap <loc> — must be the extensionless form, or it
    # points at a redirect (Google Search Central: link consistently to the
    # canonical URL and keep sitemaps/canonicals in agreement). Same-site and
    # relative URLs only; external hosts (e.g. easybacnet.com) are left alone.
    if u.startswith(("http://", "https://")) and "easymodbus.com" not in u:
        return u
    if u.startswith(("mailto:", "tel:", "#", "javascript:", "data:")):
        return u
    u = re.sub(r'index\.html(?=$|[#?])', "", u)   # ".../index.html" -> ".../"
    u = re.sub(r'\.html(?=$|[#?])', "", u)          # ".../page.html"  -> ".../page"
    return u or "/"                                  # bare "index.html" -> "/"


def _clean_internal_urls(text):
    text = re.sub(r'href="([^"]*)"',
                  lambda m: 'href="%s"' % _to_clean_url(m.group(1)), text)
    text = re.sub(r'(<meta property="og:url" content=")([^"]*)(")',
                  lambda m: m.group(1) + _to_clean_url(m.group(2)) + m.group(3), text)
    text = re.sub(r'("item":\s*")([^"]*)(")',
                  lambda m: m.group(1) + _to_clean_url(m.group(2)) + m.group(3), text)
    text = re.sub(r'(<loc>)([^<]*)(</loc>)',
                  lambda m: m.group(1) + _to_clean_url(m.group(2)) + m.group(3), text)
    return text


def write(relpath, content):
    # Inject the analytics + consent banner into every HTML page, right after
    # the charset meta so it never pushes charset past the first 1 KB.
    if "<head>" in content and "googletagmanager" not in content:
        marker = '<meta charset="utf-8">'
        if marker in content:
            content = content.replace(marker, marker + ANALYTICS, 1)
        else:
            content = content.replace("<head>", "<head>" + ANALYTICS, 1)
    content = _clean_internal_urls(content)
    full = os.path.join(HERE, relpath)
    directory = os.path.dirname(full)
    if directory:
        os.makedirs(directory, exist_ok=True)
    io.open(full, "w", encoding="utf-8", newline="\n").write(content)
    print("wrote", relpath)


# ---------------------------------------------------------------------------
# Guides
# ---------------------------------------------------------------------------

GUIDES = []

GUIDES.append(dict(
    slug="guides/what-is-modbus",
    title="What is Modbus? A plain-English explanation | Easy Modbus",
    question="What is Modbus?",
    description="Modbus is a simple protocol for reading and writing numbered registers on industrial and building equipment. What it is, in plain English.",
    answer_html="""<p>Modbus is a way for one machine to ask another machine for
    numbers. It was published in 1979, it is deliberately simple, and it is in an
    enormous amount of building and industrial equipment: meters, variable-speed
    drives, chillers, boilers, rooftop units, generators, UPSs, and sensors of
    every kind. A Modbus request says, in effect, &ldquo;give me the contents of
    sixteen-bit slot number 7&rdquo;. The equipment answers with sixteen bits. It
    does <em>not</em> say what those bits mean &mdash; that information lives only
    in the manufacturer's documentation, and that single fact is the source of
    almost every difficulty people have with Modbus.</p>""",
    body_html="""
  <h2>What a Modbus device actually gives you</h2>
  <p>Picture the equipment as having four numbered lists inside it, and nothing
  else:</p>
  <table>
    <tr><th>List</th><th>What it holds</th><th>Can you change it?</th></tr>
    <tr><td>Coils</td><td>Single on/off values &mdash; a start command, an enable, a reset</td><td>Yes</td></tr>
    <tr><td>Discrete inputs</td><td>Single on/off values the equipment reports &mdash; running, alarm</td><td>No</td></tr>
    <tr><td>Input registers</td><td>Numbers the equipment measures &mdash; temperatures, pressures</td><td>No</td></tr>
    <tr><td>Holding registers</td><td>Numbers you can read and usually write &mdash; setpoints, modes, and on many devices the readings too</td><td>Usually</td></tr>
  </table>

  <p>Each list is just numbered slots. Slot 0, slot 1, slot 2, and so on. A
  register slot holds exactly sixteen bits, which is a whole number from 0 to
  65535, or &minus;32768 to 32767 if the manufacturer decided it was a signed
  number. There are no names, no units, and no descriptions anywhere in the
  protocol.</p>

  <div class="callout">
  <p>This is the part that surprises people coming from BACnet, or from almost any
  modern system. A BACnet controller will tell you what it has: you ask for its
  object list and it replies with names and units. A Modbus device will never do
  this. It answers exactly the question you asked and volunteers nothing.</p>
  </div>

  <h2>What that means in practice</h2>
  <p>To get one useful number out of a Modbus device you need to know four things,
  and the protocol supplies none of them:</p>
  <ol>
    <li><strong>Which list</strong> the value is in.</li>
    <li><strong>Which slot number</strong> &mdash; and there are several rival ways
    of writing that number down. See
    <a href="modbus-address-off-by-one.html">why your Modbus address is off by one</a>.</li>
    <li><strong>How to interpret the bits</strong> &mdash; is it a whole number, a
    decimal, a number spread across two slots, one bit of a status word? See
    <a href="modbus-value-wrong-scaling-byte-order.html">why your Modbus value looks wrong</a>.</li>
    <li><strong>What it means</strong> &mdash; that slot 7 is the leaving water
    temperature, in tenths of a degree Fahrenheit.</li>
  </ol>
  <p>All four live in a document called a register map, which your equipment
  vendor has and you probably do not. See
  <a href="what-is-a-modbus-register-map.html">what a Modbus register map is</a>.</p>

  <h2>The flavours you will run into</h2>
  <ul>
    <li><strong>Modbus TCP</strong> &mdash; runs over an ordinary Ethernet network,
    normally on port 502. If the equipment has an Ethernet socket, this is probably
    what it speaks.</li>
    <li><strong>Modbus RTU</strong> &mdash; runs over a two- or three-wire serial
    cable, usually RS-485, with devices daisy-chained along it. Far more common in
    the field than Modbus TCP, and much older.</li>
    <li><strong>Modbus RTU over TCP</strong> &mdash; serial Modbus stuffed inside a
    network connection by a small box called a gateway. Extremely common, and a
    frequent source of &ldquo;the device is not responding&rdquo;.</li>
  </ul>
  <p><a href="modbus-tcp-vs-rtu-vs-rs485.html">Which kind do I have?</a> covers how
  to tell them apart.</p>

  <h2>Why it is still everywhere</h2>
  <p>Because it is simple enough to implement in a few hundred bytes of code, it
  is not owned by anybody, and it works. A protocol that reads sixteen bits out of
  a numbered slot has essentially nothing to go wrong or go out of date. The cost
  of that simplicity is that all the meaning has to be documented somewhere else,
  by humans, and kept up to date by humans.</p>

  <h2>Is reading from it safe?</h2>
  <p>Reading is harmless. A read request cannot change anything; the equipment
  looks up a number and sends it. <strong>Writing is a different matter
  entirely</strong> &mdash; Modbus has no undo, no timeout, and no concept of
  priority. A value you write is simply the value now, until something else writes
  over it. Read
  <a href="is-it-safe-to-write-to-modbus.html">is it safe to write to a Modbus register?</a>
  before changing anything on live equipment.</p>
""",
    related=[
        ("guides/what-is-a-modbus-register-map", "What is a Modbus register map?"),
        ("guides/modbus-address-off-by-one", "Why is my Modbus address off by one?"),
        ("guides/modbus-tcp-vs-rtu-vs-rs485", "Modbus TCP, RTU or RS-485 &mdash; which do I have?"),
        ("guides/modbus-vs-bacnet", "What is the difference between Modbus and BACnet?"),
    ],
))

GUIDES.append(dict(
    slug="guides/what-is-a-modbus-register-map",
    title="What is a Modbus register map? | Easy Modbus",
    question="What is a Modbus register map?",
    description="A Modbus register map ties each address to what it means: data type, scaling, word order and units. What it contains and why you need one.",
    answer_html="""<p>A Modbus register map &mdash; also called a register list,
    address list, point list, or Modbus table &mdash; is the document that says
    what each numbered slot inside a piece of equipment actually means. A row of it
    says something like &ldquo;holding register 40007, 16-bit signed, multiply by
    0.1, degrees Fahrenheit, leaving water temperature&rdquo;. Without it, a Modbus
    device is a list of meaningless numbers; the protocol itself carries no names,
    no units and no data types. It is the single most important document in any
    Modbus integration, and it comes from the equipment manufacturer.</p>""",
    body_html="""
  <p>Verified maps for many common devices are in the free
  <a href="../modbus-register-maps/index.html">Modbus register-map library</a>,
  organised by manufacturer and equipment type.</p>

  <h2>What a usable register map contains</h2>
  <p>A map that someone can actually work from has at least these columns. If a
  vendor sends you one missing the middle three, send it back.</p>
  <table>
    <tr><th>Column</th><th>Why it matters</th></tr>
    <tr><td>Description / name</td><td>What the value is. &ldquo;Supply air temperature&rdquo;, not &ldquo;AI_07&rdquo;.</td></tr>
    <tr><td>Register type</td><td>Holding register, input register, coil, or discrete input. Decides which request is used and whether it can be written.</td></tr>
    <tr><td>Address</td><td>The slot number &mdash; and ideally a note about which numbering convention is being used, because there are three. See <a href="modbus-address-off-by-one.html">the addressing guide</a>.</td></tr>
    <tr><td>Data type</td><td>16-bit signed, 16-bit unsigned, 32-bit float, 32-bit integer, ASCII text, one bit of a word. Guessing wrong produces a wrong number, not an error.</td></tr>
    <tr><td>Word order</td><td>Only for values spanning two or more registers. Usually written as ABCD or CDAB. Getting it wrong produces wild nonsense.</td></tr>
    <tr><td>Multiplier / scaling</td><td>Many devices report tenths or hundredths. A raw 725 with a multiplier of 0.1 is 72.5.</td></tr>
    <tr><td>Units</td><td>Degrees F, degrees C, percent, kW, kWh, ppm, PSI. A number without units is not information.</td></tr>
    <tr><td>Read / write</td><td>Whether you are allowed to change it, and what range is acceptable.</td></tr>
    <tr><td>Enumerations</td><td>For mode registers: 0 = Off, 1 = Heat, 2 = Cool. Otherwise &ldquo;2&rdquo; tells you nothing.</td></tr>
  </table>

  <h2>A worked example</h2>
  <p>Three rows from a realistic map, and what each one is telling you:</p>
  <table>
    <tr><th>Description</th><th>Type</th><th>Address</th><th>Data type</th><th>Scale</th><th>Units</th></tr>
    <tr><td>Supply air temperature</td><td>Holding</td><td>40001</td><td>INT16</td><td>0.1</td><td>&deg;F</td></tr>
    <tr><td>Fan power</td><td>Holding</td><td>40007</td><td>FLOAT32 CDAB</td><td>1</td><td>kW</td></tr>
    <tr><td>Filter alarm</td><td>Holding</td><td>40006 bit 2</td><td>Bit</td><td>&mdash;</td><td>0 = clear, 1 = dirty</td></tr>
  </table>
  <ul>
    <li><strong>Row one.</strong> Read holding register address 0 (40001 means the
    first holding register, counting from one). You get back a whole number like
    552. Multiply by 0.1 and you have 55.2&deg;F. <em>INT16</em> means it is signed,
    so the value can go below zero &mdash; which matters for an outside air sensor
    in January.</li>
    <li><strong>Row two.</strong> Read <em>two</em> registers starting at 40007,
    because a 32-bit float does not fit in one. <em>CDAB</em> means the two halves
    arrive in the opposite order to the obvious one; read it the other way and you
    get something like 3.6&times;10<sup>-41</sup> instead of 12.75.</li>
    <li><strong>Row three.</strong> Read one register and look at a single bit of
    it. Devices routinely pack a dozen unrelated alarms into the sixteen bits of
    one register.</li>
  </ul>

  <h2>Why everybody keeps asking you for one</h2>
  <p>Because nothing can be done without it. An analytics platform, a new building
  management system, a tenant billing system, a monitoring service, or a
  contractor replacing a controller all need to know what exists before they can
  read anything. And unlike a BACnet system, nobody can simply ask the equipment.
  See <a href="vendor-asking-for-modbus-information.html">a vendor asked for my
  Modbus information &mdash; what do I send?</a></p>

  <h2>If you do not have one</h2>
  <p><a href="how-to-find-modbus-register-map.html">How do I find my Modbus
  register map?</a> covers the four places to look, in order of how likely they
  are to work, and what to do when all four fail.</p>
""",
    related=[
        ("guides/how-to-find-modbus-register-map", "How do I find my Modbus register map?"),
        ("guides/vendor-asking-for-modbus-information", "A vendor asked for my Modbus information &mdash; what do I send?"),
        ("guides/modbus-address-off-by-one", "Why is my Modbus address off by one?"),
        ("guides/modbus-value-wrong-scaling-byte-order", "Why does my Modbus value look wrong?"),
    ],
))

GUIDES.append(dict(
    slug="guides/how-to-find-modbus-register-map",
    title="How do I find my Modbus register map? | Easy Modbus",
    question="How do I find my Modbus register map?",
    description="Build a Modbus register map from a live device: read blocks, decode each value's type and scaling, name it, and export the map as a CSV.",
    answer_html="""<p>Four routes, easiest first: search the manufacturer's site for
    the model number plus &ldquo;Modbus&rdquo;, look in the installation or
    integration manual rather than the user manual, ask your controls contractor
    for the submittal documents, or connect to the device and work backwards from
    the values it reports. The last one sounds hardest but is often fastest,
    because it is the only method that does not depend on someone else answering an
    email.</p>
    <p>Before any of that, check the free
    <a href="../modbus-register-maps/index.html">Modbus register-map library</a>: it has
    verified maps for common meters, drives, generator controllers, inverters and HVAC
    equipment, each checked against the manufacturer&rsquo;s own document.</p>""",
    body_html="""
  <h2>1. The manufacturer's website</h2>
  <p>Search for the exact model number from the equipment label plus the word
  Modbus. The document you want is usually called one of:</p>
  <ul>
    <li><em>Modbus register map</em> or <em>Modbus point list</em></li>
    <li><em>Integration guide</em> or <em>Integration manual</em></li>
    <li><em>BMS interface manual</em> or <em>Communications manual</em></li>
    <li><em>Installation and operation manual</em> &mdash; the Modbus table is
    frequently an appendix at the back</li>
  </ul>
  <p>Two things worth knowing. The <strong>user manual almost never has it</strong>
  &mdash; you want the installer or integrator document. And the map is often
  specific to a firmware version, so check the revision against the label on the
  equipment.</p>

  <h2>2. The equipment label and the controller itself</h2>
  <p>Get the model number, serial number and firmware version off the nameplate
  before you start searching. On equipment with a display, the Modbus settings
  screen is also worth finding: it usually shows the baud rate, the unit ID, and
  sometimes the protocol, all of which you will need anyway and none of which can
  be guessed reliably.</p>

  <h2>3. Your controls contractor</h2>
  <p>Whoever installed or maintains the building automation system normally holds
  the submittals, which include integration documents. This is the fastest route
  when it works. The caveat is the usual one: the documents describe the design,
  and the installed system may have moved on.</p>

  <h2>4. Read the device and work backwards</h2>
  <p>This is more practical than it sounds, and for undocumented equipment it is
  the only option. The method:</p>
  <ol>
    <li>Read a block of holding registers &mdash; addresses 0 to 32 is a good first
    try &mdash; and look at what comes back.</li>
    <li>Ignore everything reading zero and everything reading 0xFFFF. Those are
    usually unused or faulted.</li>
    <li>For the rest, compare against what the equipment's own display says. If the
    unit shows 72.4&deg;F and a register reads 724, you have found it and you have
    found the multiplier at the same time.</li>
    <li>Look for pairs of registers where one half is zero &mdash; that pattern is
    a 32-bit value, usually a running total like energy or hours.</li>
    <li>Look for runs of registers holding printable characters. That is the model
    number or serial number in text, and it is a useful landmark for where the map
    begins.</li>
  </ol>
  <p>Values that change when you change something physical are the most reliable
  evidence of all. Turn the fan up and see which register moves.</p>

  <h2>Write it down as you go</h2>
  <p>Each time a number makes sense, record the whole interpretation, not just the
  address: the table, the 0-based wire address, the data type, the word order, the
  multiplier and the units. A spreadsheet with those columns <em>is</em> a register
  map, and filing it with the equipment means nobody has to work it out again. The
  <a href="../modbus-float-decoder.html">float and byte-order decoder</a> shows a pair
  of registers in all four word orders at once, and the
  <a href="../modbus-address-converter.html">address converter</a> settles which
  register a 40001-style address really is on the wire.</p>

  <h2>When none of it works</h2>
  <p>Ask the vendor directly, with the model and firmware version, for the Modbus
  register map. It is a normal request and they have the document. If the equipment
  is out of support and the manufacturer is gone, the reverse-engineering route
  above is what remains &mdash; and a map you build yourself, exported and filed
  somewhere, is worth more to the next person than anything else you could leave
  them.</p>
""",
    related=[
        ("guides/what-is-a-modbus-register-map", "What is a Modbus register map?"),
        ("guides/cannot-find-modbus-devices", "Why can't I find my Modbus devices?"),
        ("guides/modbus-value-wrong-scaling-byte-order", "Why does my Modbus value look wrong?"),
    ],
))

GUIDES.append(dict(
    slug="guides/modbus-address-off-by-one",
    title="Modbus address off by one? 40001 vs 0 | Easy Modbus",
    question="Why is my Modbus address off by one?",
    description="40001, 4x00001, register 1 and address 0 are all the same Modbus register. Here is why the conventions conflict, and how to tell which one your document uses.",
    answer_html="""<p>Because the same register is legitimately called four
    different things. <code>40001</code>, <code>4x00001</code>, &ldquo;holding
    register 1&rdquo; and &ldquo;address 0&rdquo; all refer to the identical slot
    in the identical device. The number that actually travels in the Modbus packet
    is the last one, counting from zero; most vendor documentation uses one of the
    first three, counting from one. If your value is one register out &mdash;
    you asked for the supply temperature and got the return temperature &mdash;
    this is almost always why.</p>""",
    body_html="""
  <h2>The four ways to write one address</h2>
  <table>
    <tr><th>Written as</th><th>Called</th><th>Counts from</th><th>What goes on the wire</th></tr>
    <tr><td><code>40001</code></td><td>Modicon five-digit</td><td>1</td><td>0</td></tr>
    <tr><td><code>4x00001</code></td><td>Prefixed, explicit</td><td>1</td><td>0</td></tr>
    <tr><td>&ldquo;Holding register 1&rdquo;</td><td>One-based register number</td><td>1</td><td>0</td></tr>
    <tr><td>&ldquo;Address 0&rdquo;</td><td>Protocol address</td><td>0</td><td>0</td></tr>
  </table>

  <p>The leading digit in the first two forms is not part of the number &mdash; it
  says which of the four lists the value is in:</p>
  <table>
    <tr><th>Prefix</th><th>List</th><th>Example</th></tr>
    <tr><td>0</td><td>Coils</td><td><code>00001</code> or <code>0x00001</code></td></tr>
    <tr><td>1</td><td>Discrete inputs</td><td><code>10001</code> or <code>1x00001</code></td></tr>
    <tr><td>3</td><td>Input registers</td><td><code>30001</code> or <code>3x00001</code></td></tr>
    <tr><td>4</td><td>Holding registers</td><td><code>40001</code> or <code>4x00001</code></td></tr>
  </table>

  <div class="callout">
  <p><strong>A trap for programmers.</strong> In Modbus documentation
  <code>0x</code> means the coil table. It is not hexadecimal. Hexadecimal
  addresses are vanishingly rare in device manuals, so <code>0x10</code> in a
  Modbus table almost certainly means coil number 10, not the number 16.</p>
  </div>

  <h2>How to tell which convention a document uses</h2>
  <ul>
    <li><strong>Addresses in the 40001&ndash;49999 range</strong> &mdash; Modicon
    five-digit, counting from one. Subtract 40001 to get the wire address.</li>
    <li><strong>Addresses starting at 1</strong> with a separate &ldquo;register
    type&rdquo; column &mdash; one-based. Subtract one.</li>
    <li><strong>Addresses starting at 0</strong> &mdash; protocol addresses. Use
    them as they are.</li>
    <li><strong>A column headed &ldquo;offset&rdquo;</strong> &mdash; almost always
    zero-based.</li>
    <li><strong>Both a &ldquo;register&rdquo; and an &ldquo;address&rdquo; column,
    differing by one</strong> &mdash; the document is being helpful. Use the one
    your tool asks for.</li>
  </ul>

  <h2>How to confirm it without guessing</h2>
  <p>Read three registers in a row and compare all three against what the
  equipment's own display shows. If the value you wanted appears one slot earlier
  or later than the document says, you now know the convention and every other row
  in that document falls into place at once.</p>

  <p>Some equipment documents are simply wrong about this, including from large
  manufacturers. Trusting the reading over the document is the right instinct.</p>

  <h2>Why it ended up like this</h2>
  <p>The five-digit notation comes from the original Modicon PLCs, where memory
  references were written that way and counted from one. The protocol itself always
  counted from zero. Forty-five years of documents later, both conventions are
  still in active use, often in the same building, sometimes in the same PDF.</p>

  <p>The quickest way to settle it is the
  <a href="../modbus-address-converter.html">Modbus address converter</a>: type the
  address however your manual writes it &mdash; <code>40007</code>,
  <code>4x00007</code> or <code>6</code> &mdash; and it shows the table, the function
  code and the 0-based wire address. Every map in the
  <a href="../modbus-register-maps/index.html">register-map library</a> lists the wire
  address, with the documented number beside it when the two differ.</p>
""",
    related=[
        ("modbus-register-maps/index", "Modbus register maps with both printed and 0-based wire addresses"),
        ("guides/modbus-value-wrong-scaling-byte-order", "Why does my Modbus value look wrong?"),
        ("guides/what-is-a-modbus-register-map", "What is a Modbus register map?"),
        ("guides/modbus-function-codes-explained", "Modbus function codes in plain English"),
    ],
))

GUIDES.append(dict(
    slug="guides/modbus-value-wrong-scaling-byte-order",
    title="Why does my Modbus value look wrong? | Easy Modbus",
    question="Why does my Modbus value look wrong?",
    description="A Modbus value that reads wrong is usually scaling or byte/word order. How to spot 32-bit floats, word swaps and multipliers, and fix them.",
    answer_html="""<p>Almost always one of four things. If it is exactly ten or a
    hundred times too big, the device reports tenths or hundredths and you need a
    multiplier. If it is a huge number like 65524 where you expected a small
    negative one, it is a signed value being read as unsigned. If it is wild
    nonsense &mdash; 3.6&times;10<sup>-41</sup> or 2.4&times;10<sup>31</sup> &mdash;
    it is a 32-bit value whose two halves are in the other order, and switching
    ABCD to CDAB will fix it. If it is a sensible-looking number belonging to
    something else entirely, your address is off by one.</p>""",
    body_html="""
  <h2>Ten or a hundred times too big</h2>
  <p>You expected 72.4 and got 724. The device is reporting tenths, which is the
  most widespread convention in Modbus equipment: it gives one decimal place
  without needing floating-point maths, which mattered a great deal in 1985 and
  still matters on cheap hardware.</p>
  <p>The fix is a multiplier of 0.1 (or 0.01 for hundredths). Occasionally it goes
  the other way &mdash; a device reporting kilowatts where you wanted watts needs a
  multiplier of 1000.</p>

  <h2>A huge number where you expected a small negative one</h2>
  <p>You expected &minus;11.8 and got 6541.8, or you expected &minus;12 and got
  65524. A sixteen-bit register can hold 0 to 65535 as an unsigned number, or
  &minus;32768 to 32767 as a signed one, and the protocol does not say which.
  Read it as signed &mdash; INT16 rather than UINT16 &mdash; and it comes right.</p>
  <p>Outside-air temperature sensors are where this bites, because everything looks
  fine until the first cold morning.</p>

  <h2>Wild nonsense</h2>
  <p>You expected something like 12.75 and got 3.6&times;10<sup>-41</sup>. This is
  a 32-bit value &mdash; a float or a big integer spread across two registers
  &mdash; and the two halves are arriving in the opposite order to the one you
  assumed.</p>
  <p>Vendor documents name the orders with four letters, where the 32-bit value's
  four bytes are A, B, C and D:</p>
  <table>
    <tr><th>Order</th><th>Also called</th><th>How common</th></tr>
    <tr><td><code>ABCD</code></td><td>Big endian, high word first</td><td>The standard choice. Try it first.</td></tr>
    <tr><td><code>CDAB</code></td><td>Word swapped, mid-little endian</td><td>Very common &mdash; a large share of power meters and variable-speed drives.</td></tr>
    <tr><td><code>BADC</code></td><td>Byte swapped</td><td>Rare.</td></tr>
    <tr><td><code>DCBA</code></td><td>Little endian</td><td>Occasional, usually PLC-hosted maps.</td></tr>
  </table>
  <p>With only four possibilities and an obvious right answer, trying each one is a
  perfectly respectable method. The giveaway is magnitude: real engineering values
  live roughly between a thousandth and a few million. A float decoding to
  10<sup>-41</sup> or 10<sup>28</sup> is not a weak guess, it is a wrong one.</p>

  <h2>A sensible number, but the wrong thing</h2>
  <p>The value is plausible but it is clearly the return air temperature rather
  than the supply. That is an addressing problem, not an interpretation one: see
  <a href="modbus-address-off-by-one.html">why is my Modbus address off by one</a>.</p>

  <h2>A number that never changes, or reads 65535</h2>
  <ul>
    <li><strong>Always 0xFFFF (65535)</strong> &mdash; on most equipment this means
    &ldquo;no value&rdquo; or &ldquo;sensor fault&rdquo;, not sixty-five thousand.
    Check whether that sensor is connected.</li>
    <li><strong>Always 0</strong> &mdash; often an unused register, or a feature the
    equipment does not have fitted.</li>
    <li><strong>Never changes but looks plausible</strong> &mdash; you may be
    reading a configuration register rather than a live measurement.</li>
  </ul>

  <h2>A value that jumps around impossibly</h2>
  <p>A temperature reading 72, then 4096, then 71 is usually a 32-bit value being
  read as two separate 16-bit ones, or a reply arriving one register out of step
  after a timeout. If the jumping started when you added more readings, try asking
  for fewer registers at a time.</p>

  <h2>The systematic way through it</h2>
  <ol>
    <li>Look at the raw register in hex, not just the decoded number.</li>
    <li>Compare against what the equipment's own display says. That is ground
    truth, and it settles scaling and addressing in one move.</li>
    <li>Change one thing at a time: signedness, then multiplier, then word order.</li>
  </ol>
  <p>For a 32-bit value, the <a href="../modbus-float-decoder.html">float and
  byte-order decoder</a> does the arithmetic for you: paste the two raw registers and
  it shows the result in all four word orders, highlighting the ones that land on a
  sensible engineering magnitude. Then ask whether the number is physically possible
  &mdash; a humidity of 452% is the obvious case of one that is not.</p>
""",
    related=[
        ("modbus-register-maps/index", "Modbus register maps with word order and scaling, by manufacturer"),
        ("guides/modbus-address-off-by-one", "Why is my Modbus address off by one?"),
        ("guides/what-is-a-modbus-register-map", "What is a Modbus register map?"),
        ("guides/how-to-find-modbus-register-map", "How do I find my Modbus register map?"),
    ],
))

GUIDES.append(dict(
    slug="guides/cannot-find-modbus-devices",
    title="Can't find Modbus devices? 6 things to check | Easy Modbus",
    question="Why can't I find my Modbus devices on the network?",
    description="Modbus has no discovery at all — devices never announce themselves. Here is why scanning is the only option, and the six things to check when nothing answers.",
    answer_html="""<p>Start with the thing that surprises everyone: <strong>Modbus
    has no discovery mechanism whatsoever</strong>. There is no broadcast, no
    announcement, no equivalent of asking &ldquo;who is out there?&rdquo;. A Modbus
    device is completely silent until something asks it a direct question at its
    exact address. So finding equipment means trying every address on the network
    and seeing which ones answer on port 502 &mdash; which is what every Modbus
    scanning tool does. When that finds nothing, the cause is usually the network,
    the port, the unit ID, or the framing.</p>""",
    body_html="""
  <h2>Why there is nothing to discover</h2>
  <p>BACnet has a <em>Who-Is</em> broadcast: shout into the network and every
  controller answers. Modbus has no such thing, by design &mdash; it was built for
  a single serial cable with one master that already knew what was on it. Nothing
  was ever added for Ethernet. A scan is therefore a sweep: connect to
  192.168.1.1, then .2, then .3, and see who accepts.</p>
  <p>This is worth knowing for a second reason: a sweep looks like a port scan on a
  monitored network, because it is one. There is no gentler option, but on a
  production control network it is worth telling whoever runs it first.</p>

  <h2>The six things to check</h2>

  <h3>1. Is this device on the same network?</h3>
  <p>Controls equipment is very often on its own VLAN or physical network, with no
  route from the office network or guest Wi-Fi. If you can't ping it, no Modbus
  tool will find it. This is the most common cause by a wide margin.</p>

  <h3>2. Is the port right?</h3>
  <p>Modbus TCP is registered on <strong>port 502</strong>, and that is what to try
  first. But 503 is used when two Modbus services share a host, and 5020 turns up
  on gateways and on equipment where 502 was already taken. Check the device's own
  network settings screen.</p>

  <h3>3. Is Modbus actually switched on?</h3>
  <p>A great deal of equipment ships with Modbus TCP disabled, or with only the
  serial port enabled. There is usually a menu item. Some devices need a reboot
  after it is turned on, and a few require a licence or an optional
  communications card that may not be fitted.</p>

  <h3>4. Is it really Modbus TCP, or RTU in disguise?</h3>
  <p>If the equipment is RS-485 behind a serial-to-Ethernet gateway, the gateway
  may not translate &mdash; many simply pipe the bytes through, so what arrives is
  Modbus RTU inside a TCP connection. A tool speaking proper Modbus TCP to it gets
  total silence, which looks exactly like a dead device.</p>
  <p>The fix is to switch the tool to <em>Modbus RTU over TCP</em>. If you are not
  sure which you have, try both &mdash; it costs nothing and it is the single most
  common dead end in Modbus work. See
  <a href="modbus-tcp-vs-rtu-vs-rs485.html">which kind do I have?</a></p>

  <h3>5. Is the unit ID right?</h3>
  <p>A device behind a gateway has a unit ID (also called a slave ID or station
  address), and the gateway only answers for the IDs that actually exist on its
  serial chain. The wrong one produces either silence or a &ldquo;gateway target
  device failed to respond&rdquo; error. Try 1 first, then sweep. See
  <a href="modbus-unit-id-slave-id.html">what is a Modbus unit ID?</a></p>

  <h3>6. Is something else already connected?</h3>
  <p>Many Modbus TCP devices accept exactly one connection, and some accept three
  or four and then silently stop answering. If the building management system is
  already talking to it, your tool may be refused or may get the connection and
  knock the BMS off. Close other software first, and be aware of what you might be
  interrupting.</p>

  <h2>Checking the basics yourself</h2>
  <p>Compare your own IP address and subnet with the device's: on a laptop,
  <code>ipconfig</code> (Windows) or <code>ip addr</code> (Linux and macOS); on a phone,
  the Wi-Fi details screen. If the first three numbers of a typical /24 address differ,
  you are on a different network. Then test the port on its own &mdash; for example
  <code>Test-NetConnection 192.168.1.50 -Port 502</code> in Windows PowerShell &mdash;
  which tells you whether the port is open, refused or not answering before any Modbus
  software is involved.</p>

  <h2>What an error message is telling you</h2>
  <table>
    <tr><th>What you see</th><th>What it means</th></tr>
    <tr><td>Connection refused</td><td>Something is at that IP address but nothing is listening on that port. Wrong port, or Modbus is switched off.</td></tr>
    <tr><td>Connection timed out</td><td>Nothing at that address, or a firewall is dropping it. Check routing first.</td></tr>
    <tr><td>Connected, then no reply</td><td>The port is open but Modbus is not answering. Usually the wrong framing or the wrong unit ID.</td></tr>
    <tr><td>Connection reset</td><td>Often the device's connection limit. Close other software.</td></tr>
    <tr><td>Illegal data address</td><td><strong>Good news.</strong> The device is there and talking &mdash; that register just does not exist. Try a different address.</td></tr>
    <tr><td>Gateway target device failed to respond</td><td>The gateway is there; nothing answered at that unit ID on its serial side. Wrong unit ID, or a wiring fault.</td></tr>
  </table>

  <div class="callout">
  <p>That fifth row is worth dwelling on. An <em>error</em> reply is proof of life:
  it means a Modbus device received your request, understood it, and declined it.
  Only silence means absent.</p>
  </div>
""",
    related=[
        ("guides/modbus-tcp-vs-rtu-vs-rs485", "Modbus TCP, RTU or RS-485 &mdash; which do I have?"),
        ("guides/modbus-unit-id-slave-id", "What is a Modbus unit ID or slave ID?"),
        ("guides/how-to-find-modbus-register-map", "How do I find my Modbus register map?"),
    ],
))

GUIDES.append(dict(
    slug="guides/modbus-tcp-vs-rtu-vs-rs485",
    title="Modbus TCP vs RTU vs RS-485 | Easy Modbus",
    question="Modbus TCP, Modbus RTU or RS-485 — which do I have?",
    description="How to tell Modbus TCP from Modbus RTU and RTU-over-TCP by looking at the equipment, and why mistaking one for the other looks exactly like a dead device.",
    answer_html="""<p>Look at the socket. An Ethernet socket &mdash; the square one
    a network cable clips into &mdash; usually means Modbus TCP. Two or three screw
    terminals labelled A, B and sometimes GND or SHLD mean Modbus RTU over RS-485.
    If the equipment has screw terminals but you are reaching it over the network,
    there is a gateway in between, and that gateway either translates properly
    (Modbus TCP) or just pipes bytes through (Modbus RTU over TCP). Telling those
    last two apart matters, because choosing the wrong one produces total silence,
    which looks exactly like equipment that is switched off.</p>""",
    body_html="""
  <h2>The three you will meet</h2>
  <table>
    <tr><th></th><th>Modbus TCP</th><th>Modbus RTU</th><th>RTU over TCP</th></tr>
    <tr><td>Physical</td><td>Ethernet</td><td>RS-485 twisted pair</td><td>Ethernet to a gateway, RS-485 beyond it</td></tr>
    <tr><td>How you address it</td><td>IP address and port 502</td><td>COM port, baud rate, unit ID</td><td>Gateway IP and port, plus unit ID</td></tr>
    <tr><td>Devices per connection</td><td>Normally one</td><td>Up to 32 on a chain, by unit ID</td><td>Many, by unit ID</td></tr>
    <tr><td>Speed</td><td>Fast</td><td>Slow: 9600 or 19200 baud is typical</td><td>As slow as the serial side</td></tr>
    <tr><td>Error checking</td><td>TCP handles it</td><td>A CRC on every message</td><td>A CRC on every message</td></tr>
  </table>

  <h2>How to tell by looking</h2>
  <ul>
    <li><strong>An RJ45 Ethernet socket</strong>, and a network settings menu with
    an IP address in it: Modbus TCP.</li>
    <li><strong>Screw terminals labelled A and B</strong> (or D+ and D&minus;, or
    TX+ and TX&minus;), with a baud-rate setting somewhere in the menus: Modbus RTU
    over RS-485.</li>
    <li><strong>Both</strong>: common on newer equipment. Use the Ethernet one.</li>
    <li><strong>A small separate box</strong> with an Ethernet socket on one side
    and screw terminals on the other, often on a DIN rail in the panel: a gateway.
    The equipment is RTU; what the gateway presents to the network is the
    question.</li>
  </ul>

  <h2>Telling a translating gateway from a transparent one</h2>
  <p>A gateway labelled &ldquo;Modbus TCP to Modbus RTU&rdquo; usually translates:
  you speak Modbus TCP to it and it speaks RTU to the equipment. A box labelled
  &ldquo;serial device server&rdquo;, &ldquo;serial to Ethernet&rdquo; or
  &ldquo;TCP transparent mode&rdquo; usually does not: it forwards the bytes you
  send, so you have to send RTU-framed bytes yourself.</p>
  <p>The practical answer is to try Modbus TCP, and if there is no reply at all,
  try Modbus RTU over TCP before concluding anything is broken. It costs one
  button press and resolves this more often than any other single check.</p>

  <div class="callout">
  <p>Most Modbus tools have a setting for this, usually called <em>RTU over
  TCP</em>, <em>encapsulated RTU</em> or <em>RTU framing</em>. If a device accepts the
  connection but never replies, flip that setting before anything else &mdash; this
  one problem is behind a large share of &ldquo;dead&rdquo; devices.</p>
  </div>

  <h2>Things that only matter on the serial side</h2>
  <p>If the equipment is RS-485, several settings have to match on every device on
  the chain, and they are not discoverable:</p>
  <ul>
    <li><strong>Baud rate</strong> &mdash; 9600 and 19200 are most common.</li>
    <li><strong>Parity, data bits, stop bits</strong> &mdash; usually written as
    8N1 or 8E1.</li>
    <li><strong>Unit IDs</strong> &mdash; every device on the chain needs a
    different one. Two devices sharing an ID produces garbled replies that come and
    go.</li>
    <li><strong>Termination</strong> &mdash; a resistor at each end of a long run.
    Missing termination shows up as intermittent failures that get worse the longer
    the cable.</li>
    <li><strong>A and B not swapped</strong> &mdash; and vendors disagree about
    which wire is which, so swapping them is a normal troubleshooting step rather
    than an admission of defeat.</li>
  </ul>
  <p>Serial Modbus is also much slower than it looks. At 9600 baud one request and
  reply takes tens of milliseconds, so reading forty values one at a time can take
  several seconds. Asking for a block of registers in one request rather than one
  at a time makes a large difference, and is worth doing.</p>
""",
    related=[
        ("guides/cannot-find-modbus-devices", "Why can't I find my Modbus devices?"),
        ("guides/modbus-unit-id-slave-id", "What is a Modbus unit ID or slave ID?"),
        ("guides/what-is-modbus", "What is Modbus?"),
    ],
))

GUIDES.append(dict(
    slug="guides/modbus-unit-id-slave-id",
    title="Modbus unit ID (slave ID): find the right one | Easy Modbus",
    question="What is a Modbus unit ID or slave ID?",
    description="The Modbus unit ID (slave ID) picks which device answers on a shared line or gateway. What it is, why it matters, and how to find the right one.",
    answer_html="""<p>A unit ID &mdash; also called a slave ID, station address, or
    device address &mdash; is a number from 1 to 247 that says <em>which</em> device
    you mean when several share one connection. On an RS-485 chain with a dozen
    meters on it, the unit ID is the only thing distinguishing them. Native Ethernet
    equipment often ignores it entirely and answers on any ID. If you don't know
    it, try 1 first; it is by far the most common. The wrong unit ID produces either
    silence or a &ldquo;gateway target device failed to respond&rdquo; error, both
    of which look like equipment that is switched off.</p>""",
    body_html="""
  <h2>When it matters and when it does not</h2>
  <ul>
    <li><strong>Behind a gateway: it matters completely.</strong> One IP address
    fronts a chain of devices, and the unit ID selects which one. Getting it wrong
    means talking to nothing, or worse, talking to the wrong meter.</li>
    <li><strong>Native Ethernet equipment: usually it does not.</strong> A device
    with its own IP address and no serial segment behind it often answers on any
    unit ID, because there is nothing for the field to distinguish. Many
    manufacturers still document a specific value; use it when they do.</li>
  </ul>

  <h2>Where to find it</h2>
  <ol>
    <li><strong>The device's own display or settings menu.</strong> Usually under
    Communications, Modbus, or Network. This is the authoritative answer.</li>
    <li><strong>DIP switches.</strong> Older equipment sets the address with a bank
    of small switches, read as binary &mdash; switches 1 and 3 on means address 5.
    The legend is normally printed next to them.</li>
    <li><strong>The commissioning paperwork.</strong> Whoever set the chain up had
    to assign them, and they are usually written down.</li>
    <li><strong>Sweep for it.</strong> Ask each ID in turn and see which ones
    answer. Slow, because every miss costs a timeout, but reliable.</li>
  </ol>

  <h2>Why a sweep is slow</h2>
  <p>There is no way to ask &ldquo;which unit IDs are out there?&rdquo; &mdash;
  Modbus has no discovery of any kind. So finding the occupied IDs means trying
  each one and waiting for the timeout on every empty one. Sweeping 1 to 32 at a
  one-second timeout is half a minute of mostly waiting, and a full sweep of 1 to
  247 is several minutes. Start with 1 to 32, because installers rarely go higher
  than they need to.</p>

  <p>Most Modbus masters ask one unit ID at a time, so a sweep is a loop: note every
  ID that replies &mdash; an exception reply counts, because it still proves something
  is there &mdash; and only widen the range if you need to.</p>

  <h2>Special values</h2>
  <ul>
    <li><strong>0</strong> is a broadcast address in the specification: every device
    acts on the command and none replies. Some gateways also use 0 to mean
    &ldquo;whatever is there&rdquo;. Not something to rely on.</li>
    <li><strong>255</strong> is used by some Modbus TCP devices and other tools to mean
    &ldquo;this device, no serial side involved&rdquo;. If your tool only accepts
    0&ndash;247 and 1 gets nothing, try 0.</li>
    <li><strong>248&ndash;254</strong> are reserved and should not be used.</li>
  </ul>

  <h2>Two devices with the same unit ID</h2>
  <p>On a serial chain this produces symptoms that are easy to misdiagnose: both
  devices answer at once, the replies collide, and what comes back is garbage or
  nothing. Values appear intermittently or look like they are from the wrong
  device. If a chain worked until new equipment was added, a duplicated unit ID is
  the first thing to check.</p>
""",
    related=[
        ("guides/cannot-find-modbus-devices", "Why can't I find my Modbus devices?"),
        ("guides/modbus-tcp-vs-rtu-vs-rs485", "Modbus TCP, RTU or RS-485 &mdash; which do I have?"),
        ("guides/modbus-function-codes-explained", "Modbus function codes in plain English"),
    ],
))

GUIDES.append(dict(
    slug="guides/modbus-function-codes-explained",
    title="Modbus function codes explained | Easy Modbus",
    question="What are Modbus function codes?",
    description="Function codes 1, 2, 3, 4, 5, 6, 15 and 16 explained in plain English, plus what each exception code means when a device refuses a request.",
    answer_html="""<p>A function code is the verb of a Modbus request: it says which
    of the four data lists you want and whether you are reading or writing. You only
    need eight of them in practice. Function code 3 reads holding registers and is
    the one you will use most; 4 reads input registers; 1 and 2 read on/off values;
    6 and 16 write registers; 5 and 15 write on/off values. Everything else in the
    specification is rarely seen in building equipment.</p>""",
    body_html="""
  <h2>The eight that matter</h2>
  <table>
    <tr><th>Code</th><th>Name</th><th>In plain English</th></tr>
    <tr><td>1</td><td>Read Coils</td><td>Read on/off values you are allowed to change</td></tr>
    <tr><td>2</td><td>Read Discrete Inputs</td><td>Read on/off values you cannot change &mdash; statuses, alarms</td></tr>
    <tr><td>3</td><td>Read Holding Registers</td><td>Read numbers. The workhorse; most maps live here</td></tr>
    <tr><td>4</td><td>Read Input Registers</td><td>Read numbers you cannot change &mdash; usually live measurements</td></tr>
    <tr><td>5</td><td>Write Single Coil</td><td>Switch one on/off value</td></tr>
    <tr><td>6</td><td>Write Single Register</td><td>Set one number</td></tr>
    <tr><td>15</td><td>Write Multiple Coils</td><td>Switch several on/off values at once</td></tr>
    <tr><td>16</td><td>Write Multiple Registers</td><td>Set several numbers at once &mdash; needed for anything wider than 16 bits</td></tr>
  </table>

  <p>Two notes that save time. <strong>Function code 3 versus 4</strong> is a real
  distinction and not interchangeable: a value in the holding registers cannot be
  read with code 4, and plenty of devices put their measurements in holding
  registers anyway, so the map has to tell you which. <strong>Code 16 is required
  for 32-bit values</strong>, because writing the two halves with two separate code
  6 requests leaves the device holding half of the old value and half of the new
  one for a moment, which on a setpoint can be a very large number indeed.</p>

  <h2>One more worth knowing about</h2>
  <p><strong>Function code 43, sub-function 14</strong> &mdash; Read Device
  Identification &mdash; asks the device who it is, and can return a vendor name,
  product code, model and firmware revision. It is the nearest thing Modbus has to
  self-description. It is also optional, and most equipment does not implement it,
  so a refusal here means nothing at all about whether the device is healthy.</p>

  <h2>When the device says no: exception codes</h2>
  <p>An exception reply means the device received the request, understood it, and
  declined. That is useful information: the device is alive and reachable.</p>
  <table>
    <tr><th>Code</th><th>Name</th><th>What to do</th></tr>
    <tr><td>1</td><td>Illegal function</td><td>This device does not support that function code. Try 3 instead of 4, or vice versa.</td></tr>
    <tr><td>2</td><td>Illegal data address</td><td>That register does not exist. Your address is wrong, or off by one. The device itself is fine.</td></tr>
    <tr><td>3</td><td>Illegal data value</td><td>The value or the quantity is out of range. Often means you asked for too many registers at once, or wrote a value the device will not accept.</td></tr>
    <tr><td>4</td><td>Device failure</td><td>Something went wrong inside the device while handling the request.</td></tr>
    <tr><td>5</td><td>Acknowledge</td><td>Accepted, but it needs more time. Rare.</td></tr>
    <tr><td>6</td><td>Device busy</td><td>Try again shortly.</td></tr>
    <tr><td>10</td><td>Gateway path unavailable</td><td>The gateway has no route to that unit ID.</td></tr>
    <tr><td>11</td><td>Gateway target device failed to respond</td><td>The gateway is fine; nothing answered at that unit ID on the serial side. Wrong unit ID, or a wiring problem.</td></tr>
  </table>

  <h2>How many registers in one request?</h2>
  <p>The specification allows 125 registers or 2000 bits per request. A lot of real
  equipment, especially cheap gateways, falls over well before that &mdash;
  truncating the reply, returning exception 3, or simply hanging. If reads work one
  at a time but fail in blocks, lower the block size to 32 or even 16 and try
  again.</p>
  <p>It is still worth reading in blocks rather than one register at a time. On a
  serial chain each request costs tens of milliseconds of wire time, so forty
  separate reads is a visible wait, and forty chances to collide with whatever else
  is polling that chain.</p>
""",
    related=[
        ("guides/modbus-address-off-by-one", "Why is my Modbus address off by one?"),
        ("guides/cannot-find-modbus-devices", "Why can't I find my Modbus devices?"),
        ("guides/is-it-safe-to-write-to-modbus", "Is it safe to write to a Modbus register?"),
    ],
))

GUIDES.append(dict(
    slug="guides/is-it-safe-to-write-to-modbus",
    title="Is it safe to write to a Modbus register? | Easy Modbus",
    question="Is it safe to write to a Modbus register?",
    description="Modbus writes take effect instantly and have no undo. What that means, when writing is safe, and the habits that reduce the risk.",
    answer_html="""<p>Reading is completely safe: a read request cannot change
    anything. Writing is a different matter, and Modbus gives you fewer safety nets
    than almost any comparable protocol. There is <strong>no undo, no automatic
    release, no timeout, and no priority system</strong>. A value you write to a
    register simply is the value now, until something else writes over it. Closing
    your laptop does not put it back. Before writing to live equipment, know what
    the register currently says, know what the value is supposed to be, and know
    who else is writing to it.</p>""",
    body_html="""
  <h2>What Modbus does not give you</h2>
  <p>Anyone arriving from BACnet will be looking for things that are not there:</p>
  <ul>
    <li><strong>No priority array.</strong> In BACnet a commanded value sits at a
    priority level, and releasing it hands the point back to the control system.
    Modbus has nothing of the kind. There is one value and whoever wrote it last
    owns it.</li>
    <li><strong>No relinquish or release.</strong> There is no &ldquo;put it back to
    automatic&rdquo; command, because there is nothing to put it back to.</li>
    <li><strong>No timeout.</strong> An override does not expire. A setpoint written
    in August is still written in December unless something else changes it.</li>
    <li><strong>No record of who wrote it.</strong> The device does not know and
    cannot tell you.</li>
  </ul>

  <div class="callout">
  <p>This is how equipment ends up stuck. Someone writes a fan speed to test
  something, gets called away, and the fan runs at 40% for three months while
  everybody blames the controller.</p>
  </div>

  <h2>Before you write anything</h2>
  <ol>
    <li><strong>Write down what it says now.</strong> Read the register and record
    the value before changing it. This is the only undo that exists.</li>
    <li><strong>Check the register is actually writable.</strong> Input registers
    and discrete inputs cannot be written at all &mdash; the value belongs to the
    equipment. Some holding registers are read-only too, and a device may accept
    the write and ignore it.</li>
    <li><strong>Check the range and the scaling.</strong> If the register holds
    tenths, 72 is 7.2 degrees, not 72. Writing a raw 720 where the device expected
    72 is a real and common accident.</li>
    <li><strong>Know what else is writing to it.</strong> If a building management
    system is polling and commanding the same register, your value may last
    seconds &mdash; or yours may fight its control loop. Both are bad, in different
    ways.</li>
    <li><strong>Consider what the equipment does next.</strong> Writing to a mode
    register can start a compressor. Short-cycling one is expensive.</li>
    <li><strong>Read it back.</strong> Modbus confirms a write by echoing the
    address, not the stored value. Devices clamp values to their own limits, round
    them, or ignore them silently. What it reads back afterwards is the only truth.</li>
  </ol>

  <h2>Writes that are usually fine, and writes that are not</h2>
  <table>
    <tr><th>Usually low risk</th><th>Think first</th></tr>
    <tr><td>A setpoint, moved a degree or two, during working hours, with someone on site</td><td>Anything that starts or stops a compressor, pump or fan</td></tr>
    <tr><td>Clearing a filter alarm</td><td>Mode registers &mdash; heating to cooling, auto to hand</td></tr>
    <tr><td>A test you will undo in the next minute, with the original written down</td><td>Configuration registers: baud rate, unit ID, network settings. Some take effect on reboot and can lock you out of the device entirely</td></tr>
    <tr><td></td><td>Anything at all on life-safety, fire, or medical equipment</td></tr>
  </table>

  <h2>The configuration-register trap</h2>
  <p>Some devices keep their communication settings in ordinary holding registers
  alongside the data. Writing to the wrong address can change the unit ID or the
  baud rate, at which point the device stops answering and the only way back may be
  a physical reset or a serial cable. If a register map has a configuration section,
  treat those addresses as off limits unless you mean it.</p>

  <h2>Habits that make writing safer</h2>
  <p>Whatever tool you use, these habits do most of the work:</p>
  <ul>
    <li>Keep the tool read-only, or writing switched off, until you actually mean to
    change something.</li>
    <li>Before every write, check the device, the register, the old value and the new
    value side by side.</li>
    <li><strong>Write down what each register said before you changed it.</strong>
    Modbus has no release, so putting the original value back by hand is the only undo
    there is.</li>
    <li>Know the sensible range for a setpoint before you type it, so a slipped decimal
    point is caught by you rather than by the equipment.</li>
    <li>Read the register back after writing, and treat a value that came back
    different as information, not a glitch.</li>
    <li>Keep a note of every write you made and when, so the next person knows what
    changed.</li>
  </ul>
  <p>None of that makes writing safe. It makes it deliberate, which is the most anyone
  can honestly offer on a protocol with no undo.</p>
""",
    related=[
        ("guides/modbus-function-codes-explained", "Modbus function codes in plain English"),
        ("guides/modbus-vs-bacnet", "What is the difference between Modbus and BACnet?"),
        ("guides/what-is-modbus", "What is Modbus?"),
    ],
))

GUIDES.append(dict(
    slug="guides/vendor-asking-for-modbus-information",
    title="What Modbus info to send a vendor | Easy Modbus",
    question="A vendor asked for my Modbus information — what do I send?",
    description="What to hand a vendor or integrator who asks for your Modbus details: IP, unit ID, and a full register map with types and scaling, exported as a CSV.",
    answer_html="""<p>Send five things: how to reach the equipment on the network
    (IP addresses, port, and whether it is Modbus TCP or RTU over TCP), the unit IDs
    in use, the register map for each device from the manufacturer, a note of which
    system is already polling them, and &mdash; most usefully &mdash; a live export
    showing each register with the value it is reporting right now. That last item
    resolves more questions than the other four together, because it proves what is
    actually reachable and what the numbers actually look like.</p>""",
    body_html="""
  <h2>The five things, in detail</h2>

  <h3>1. How to reach it</h3>
  <ul>
    <li>IP address of each device, or of the gateway.</li>
    <li>TCP port, if it is not 502.</li>
    <li>Whether it speaks <strong>Modbus TCP</strong> or <strong>Modbus RTU over
    TCP</strong>. Say which; do not make them guess.</li>
    <li>Which network or VLAN it is on, and how someone is supposed to get onto it
    &mdash; VPN, a jump host, a physical port in a panel.</li>
    <li>For serial equipment: baud rate and parity, usually written as 9600 8N1.</li>
  </ul>

  <h3>2. Unit IDs</h3>
  <p>Which unit ID corresponds to which piece of equipment. &ldquo;Unit 1 is the
  AHU-1 controller, unit 2 is the main electrical meter&rdquo; is exactly the right
  level of detail, and it is not guessable from the outside.</p>

  <h3>3. The register map</h3>
  <p>The manufacturer's register map for each model, with the firmware revision it
  applies to. If you do not have it, say so up front rather than letting them wait
  &mdash; and see <a href="how-to-find-modbus-register-map.html">how to find your
  Modbus register map</a>. A vendor who knows the map is missing can plan for it; a
  vendor who finds out in week three cannot.</p>

  <h3>4. What is already talking to it</h3>
  <p>Important and frequently forgotten. Many Modbus devices accept only one
  connection, or a small number, and a new system polling them can knock the
  existing one off. Tell them what is already connected and how often it polls.</p>

  <h3>5. A live export</h3>
  <p>The most useful single item you can send: a CSV listing each register with its
  address, how it is interpreted, its units, and the value it read at a known
  moment. It proves the equipment is reachable, settles every addressing and scaling
  question at a stroke, and gives them real numbers to sanity-check their own
  results against.</p>
  <p>Any spreadsheet will do, as long as it has the columns: device name, IP address,
  port, unit ID, framing (TCP or RTU over TCP), register name, table, address (and which
  convention you used), data type, word order, multiplier, units, and the live value with
  the time you read it. That is a complete and self-explanatory handover document. If the
  equipment is in the <a href="../modbus-register-maps/index.html">register-map library</a>,
  send that link too &mdash; it cites the manufacturer's own document.</p>

  <h2>What not to send</h2>
  <ul>
    <li><strong>Not a photo of a screen.</strong> Addresses get transcribed wrong.</li>
    <li><strong>Not addresses without a convention.</strong> &ldquo;Register
    7&rdquo; is ambiguous; &ldquo;40007, which is wire address 6&rdquo; is not. See
    <a href="modbus-address-off-by-one.html">the addressing guide</a>.</li>
    <li><strong>Not remote access credentials by email.</strong> Use whatever your
    organisation uses for secrets.</li>
  </ul>

  <h2>Questions worth asking them back</h2>
  <ul>
    <li>Will you be writing to anything, or only reading? If writing, to which
    registers? (See <a href="is-it-safe-to-write-to-modbus.html">is it safe to write
    to a Modbus register?</a>)</li>
    <li>How often will you poll? Every few seconds on a slow serial chain can
    saturate it.</li>
    <li>Will you open your own connection, or share an existing one?</li>
    <li>What happens at your end if the equipment stops answering?</li>
  </ul>
""",
    related=[
        ("guides/what-is-a-modbus-register-map", "What is a Modbus register map?"),
        ("guides/how-to-find-modbus-register-map", "How do I find my Modbus register map?"),
        ("guides/is-it-safe-to-write-to-modbus", "Is it safe to write to a Modbus register?"),
    ],
))

GUIDES.append(dict(
    slug="guides/modbus-vs-bacnet",
    title="Modbus vs BACnet: the difference | Easy Modbus",
    question="What is the difference between Modbus and BACnet?",
    description="Modbus sends bare 16-bit values and explains nothing; BACnet describes itself with names, units and discovery. What that means for integration.",
    answer_html="""<p>The one difference that matters in practice:
    <strong>BACnet describes itself and Modbus does not</strong>. A BACnet
    controller will tell you what it has &mdash; you ask for its object list and it
    answers with names, units and types. A Modbus device tells you nothing; it
    returns the sixteen bits in the slot you named and has no opinion about what
    they mean. Everything else &mdash; discovery, priorities, alarms, scheduling
    &mdash; follows from that. Modbus is simpler, older, and in far more
    equipment; BACnet is purpose-built for buildings and far easier to integrate.</p>""",
    body_html="""
  <h2>Side by side</h2>
  <table>
    <tr><th></th><th>Modbus</th><th>BACnet</th></tr>
    <tr><td>Published</td><td>1979</td><td>1995</td></tr>
    <tr><td>Self-describing</td><td>No. Meaning lives in a PDF</td><td>Yes. Names, units and types come from the device</td></tr>
    <tr><td>Discovery</td><td>None. You must sweep the network</td><td><em>Who-Is</em> broadcast; devices answer</td></tr>
    <tr><td>Data types</td><td>16-bit slots. You supply the interpretation</td><td>Typed values: real, boolean, enumerated, string</td></tr>
    <tr><td>Units</td><td>Not carried at all</td><td>A standard property of each point</td></tr>
    <tr><td>Writing</td><td>Last writer wins. No undo</td><td>16 priority levels, and a release that hands control back</td></tr>
    <tr><td>Alarms and trends</td><td>Not in the protocol</td><td>Built in</td></tr>
    <tr><td>Typical port</td><td>TCP 502</td><td>UDP 47808</td></tr>
    <tr><td>Found in</td><td>Meters, drives, generators, UPSs, sensors, packaged plant</td><td>Building controllers, chillers, AHUs, BMS head ends</td></tr>
  </table>

  <h2>What this means when you are integrating something</h2>
  <p>With BACnet, the work is mostly selection: discover the devices, read their
  point lists, and pick the points you want. The device has already told you what
  everything is called.</p>
  <p>With Modbus, the work is mostly archaeology. You need the register map, you
  need to resolve which addressing convention it uses, you need the data type and
  the word order and the multiplier for every value, and none of it can be checked
  against the device because the device has no opinion. That knowledge exists only
  in documents and in people's heads, and it is worth writing down properly the
  first time, because the second time costs just as much as the first.</p>

  <h2>Why anyone still chooses Modbus</h2>
  <p>It is trivial to implement, which means it can go into a $40 sensor. It is not
  owned by anybody. It has essentially no version problems. And it is already in
  an enormous installed base, so supporting it is not optional regardless of what
  anyone would prefer. A modern building very often has both: BACnet between the
  controllers, and Modbus out to the meters, drives and packaged plant.</p>

  <h2>Gateways between them</h2>
  <p>Most building systems can present Modbus equipment as BACnet objects. That
  gives the head end names and units &mdash; but the names and units were typed in
  by whoever configured the gateway, from the register map. The archaeology still
  happened; it just happened once, at commissioning, and the result is now hidden
  inside a gateway configuration that may or may not be documented anywhere.</p>

  <div class="callout">
  <p>If you are working on BACnet equipment rather than Modbus, the same author
  publishes <a href="https://easybacnet.com"><strong>Easy BACnet</strong></a>, which
  discovers BACnet/IP devices, reads their point lists, and exports them the same way
  &mdash; and its own
  <a href="https://easybacnet.com/guides/bacnet-vs-modbus.html">BACnet vs Modbus</a>
  write-up covers this from the BACnet side.</p>
  </div>
""",
    related=[
        ("guides/what-is-modbus", "What is Modbus?"),
        ("guides/is-it-safe-to-write-to-modbus", "Is it safe to write to a Modbus register?"),
        ("guides/cannot-find-modbus-devices", "Why can't I find my Modbus devices?"),
    ],
))

GUIDES.append(dict(
    slug="guides/modbus-reading-slow-or-unreliable",
    title="Modbus slow or unreliable? 5 causes and fixes | Easy Modbus",
    question="Why is my Modbus reading slow or unreliable?",
    description="Slow or intermittent Modbus reads: block sizes, serial turnaround, connection limits, polling collisions and stale replies, and how to fix each.",
    answer_html="""<p>Five usual causes. A slow serial chain behind a gateway, where
    every request costs tens of milliseconds of wire time. Asking for too many
    registers in one request, which some devices truncate or refuse. Reading one
    register at a time instead of in blocks, which multiplies the cost by the number
    of readings. Another system polling the same equipment and colliding with you.
    And stale replies, where a late answer to a timed-out request makes every
    subsequent value one register out of step &mdash; the nastiest of the five,
    because every number shown is a real number from the wrong place.</p>""",
    body_html="""
  <h2>Serial is genuinely slow</h2>
  <p>At 9600 baud a request and its reply take something like 20&ndash;50
  milliseconds of wire time, plus whatever the device takes to think. Reading forty
  values one at a time is therefore a visible wait of a couple of seconds, and that
  is with everything working. If the equipment is behind a gateway, every request
  crosses that serial wire regardless of how fast the network side is.</p>
  <p>The fix is to read in blocks. One request for registers 0 to 31 costs roughly
  what one request for register 0 costs, because the overhead dominates. Grouping a
  screenful of readings into one or two requests is frequently a tenfold
  improvement.</p>

  <h2>Blocks that are too big</h2>
  <p>The specification permits 125 registers per request. A lot of equipment,
  especially inexpensive gateways, does not manage that: it truncates the reply,
  returns exception 3 (illegal data value), or stops answering altogether.</p>
  <p>If reads work one register at a time but fail in blocks, lower the block size.
  32 is a safe starting point and 16 works almost everywhere. It is worth finding
  the largest size that works reliably rather than settling for one at a time.</p>

  <h2>Connection limits</h2>
  <p>Many Modbus TCP devices accept one connection. Some accept three or four and
  then silently stop answering new ones &mdash; the symptom being that it worked
  this morning and does not now. Close other software, and if a building management
  system is polling the same device, expect to be sharing badly.</p>

  <h2>Collisions with another poller</h2>
  <p>On an RS-485 chain there is one wire and one conversation at a time. If the BMS
  polls every five seconds and you poll at the same moment, requests collide and
  both sides see intermittent failures. This shows up as values that appear and
  disappear for no visible reason, and it gets worse the more you poll.</p>
  <p>A quiet gap between requests helps more than it sounds like it should &mdash;
  35 milliseconds is a reasonable default for anything behind a serial gateway.</p>

  <h2>Stale replies: the one to be suspicious of</h2>
  <p>Suppose a request times out, and the device's answer arrives a moment later
  anyway. If the tool does not discard it, the next request reads that leftover
  answer instead of its own, and from then on every value is one reply behind.</p>
  <p>The symptom is values that are individually plausible but clearly belong to the
  wrong registers &mdash; the supply temperature showing what the return should say.
  If readings look shuffled rather than wrong, this is the first thing to suspect.
  Closing and reopening the connection clears it.</p>

  <h2>A checklist when it is unreliable</h2>
  <ol>
    <li>Lower the block size to 16 and see if it becomes reliable.</li>
    <li>Raise the timeout. 1.5 seconds is fine for native Ethernet; a serial
    gateway often needs 3 seconds or more.</li>
    <li>Add a gap between requests, 35&nbsp;ms or so.</li>
    <li>Make sure nothing else is talking to the device.</li>
    <li>On a serial chain, check for duplicate unit IDs, missing termination, and
    total cable length.</li>
    <li>If values look shuffled rather than wrong, reconnect.</li>
  </ol>
  <p>Most Modbus masters let you set the timeout, the number of registers per request
  and the delay between requests for each device. Grouping nearby registers into a single
  block request is usually the biggest single speed-up on a slow device.</p>
""",
    related=[
        ("guides/modbus-tcp-vs-rtu-vs-rs485", "Modbus TCP, RTU or RS-485 &mdash; which do I have?"),
        ("guides/modbus-function-codes-explained", "Modbus function codes in plain English"),
        ("guides/cannot-find-modbus-devices", "Why can't I find my Modbus devices?"),
    ],
))


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------


GUIDES.append(dict(
    slug="guides/how-to-write-to-a-modbus-register",
    title="How to write to a Modbus register safely | Easy Modbus",
    question="How do I write to a Modbus register safely, and put it back afterwards?",
    description="How to write a value to a Modbus holding register or coil: which function code to use, how scaling and word order change the raw value, reading it back, and putting it back.",
    answer_html="""<p>Use <strong>function code 06</strong> to write one holding
    register, <strong>16</strong> to write several (a 32-bit value needs two, so it is
    always 16), and <strong>05</strong> to switch a single coil. Before writing,
    <strong>read the register and write down what it says</strong>. Convert the value you
    want into raw register contents using the register's scale and word order &mdash; a
    setpoint of 72.5 kept in tenths is written as 725. Afterwards, read it back. Modbus has
    no priority levels, no release and no timeout: whatever you write simply <em>is</em>
    the value until something overwrites it, so writing the original value back by hand is
    the only undo you get.</p>""",
    body_html="""
  <h2>Why writing to Modbus deserves more care than BACnet</h2>
  <p>BACnet keeps a priority array: your override sits in a slot, and releasing
  the slot hands control back. Modbus has nothing of the kind. A holding
  register is a box with a number in it. Write 55 and it contains 55, full
  stop, until the equipment's own logic or another system writes something
  else &mdash; and many devices' logic never will. Read
  <a href="is-it-safe-to-write-to-modbus.html">is it safe to write to a Modbus
  register?</a> before touching anything on live plant.</p>

  <h2>Step 1 &mdash; Read it and write down what it says</h2>
  <p>Read the register first, from the right table at the right address, and note the
  value and the time. That note is your way back. If the map has a configuration
  section &mdash; unit ID, baud rate, parity &mdash; leave those addresses alone unless
  that is the job: a wrong write there can make the device stop answering.</p>

  <h2>Step 2 &mdash; Work out the raw value</h2>
  <p>A register holds a raw 16-bit number, not the engineering value you see on a
  display. Before writing, turn the value you want into what the register actually
  stores:</p>
  <ul>
    <li><strong>Scale.</strong> If the map says &times;0.1, a setpoint of 72.5 is written
    as 725. Divide by the scale; do not write the engineering value as-is.</li>
    <li><strong>Sign.</strong> A negative value in a signed 16-bit register is written in
    two's complement: &minus;5 is 65531 (<code>0xFFFB</code>).</li>
    <li><strong>32-bit values</strong> (floats, long counters) span two registers and must
    go in the same word order the device reads them in &mdash; ABCD or CDAB, usually. The
    <a href="../modbus-float-decoder.html">float decoder</a> shows how a value splits
    across the pair.</li>
    <li><strong>Coils</strong> are on or off. Function code 05 sends <code>0xFF00</code>
    for on and <code>0x0000</code> for off; most tools hide this behind a switch.</li>
  </ul>

  <h2>Step 3 &mdash; Write with the right function code</h2>
  <table>
    <tr><th>What you are writing</th><th>Function code</th></tr>
    <tr><td>One coil (on/off)</td><td>05 &mdash; write single coil</td></tr>
    <tr><td>Several coils</td><td>15 &mdash; write multiple coils</td></tr>
    <tr><td>One 16-bit holding register</td><td>06 &mdash; write single register</td></tr>
    <tr><td>Several registers, or any 32-bit value</td><td>16 &mdash; write multiple registers</td></tr>
  </table>
  <p>Some devices accept only 16, even for a single register; if 06 comes back with an
  <em>illegal function</em> exception, try 16 with a count of one. See
  <a href="modbus-function-codes-explained.html">Modbus function codes explained</a>.</p>

  <h2>Step 4 &mdash; Read it back</h2>
  <p>A successful reply only means the device accepted the request. Read the register
  again: what it holds now is the truth, not what you asked for. A device can clamp a
  value to its own limits, round it, or have its control logic overwrite it a second
  later &mdash; all things you only see by reading back.</p>

  <h2>Step 5 &mdash; Put it back</h2>
  <p>When the test is over, write the value you noted in step 1. It is not a true undo
  &mdash; if the equipment's own logic changed the register in between, "back" means
  back to what <em>you</em> found, not to what would be there had you never visited
  &mdash; but it is the closest Modbus allows.</p>
  <div class="callout">
  <p>If you overrode something to prove a point, put it back before you leave
  site. Nobody else can see that you did it, and nothing will time it out.</p>
  </div>

  <h2>Registers you cannot write</h2>
  <ul>
    <li><strong>Input registers and discrete inputs</strong> are read-only by
    definition &mdash; they report what the equipment measures.</li>
    <li><strong>Text</strong> packed as ASCII in holding registers is nearly always a name
    or a serial number, and changing it does nothing useful.</li>
    <li>Some <strong>holding registers</strong> are read-only in practice; the
    device will answer your write with an <em>illegal data address</em> or
    <em>illegal function</em> exception. See
    <a href="modbus-exception-codes.html">Modbus exception codes</a>.</li>
  </ul>
""",
    related=[
        ("guides/is-it-safe-to-write-to-modbus", "Is it safe to write to a Modbus register?"),
        ("guides/modbus-function-codes-explained", "Modbus function codes explained"),
        ("guides/modbus-value-wrong-scaling-byte-order", "Why does my Modbus value look wrong?"),
        ("modbus-register-maps/index", "Modbus register maps with scaling and access, by manufacturer"),
    ],
))

GUIDES.append(dict(
    slug="guides/modbus-poll-alternative",
    title="Free Modbus Poll alternatives | Easy Modbus",
    question="What is a good free alternative to Modbus Poll?",
    description="Modbus Poll is a paid Windows master with a time-limited trial. The free tools people use instead, what they are good at, and the step none of them does for you.",
    answer_html="""<p>Modbus Poll is a good, mature Modbus master, and if you live
    at a Windows desk it is worth what it costs. But it is paid, Windows-only, and a
    master only &mdash; simulating a slave is a second product (Modbus Slave) bought
    separately &mdash; and its free evaluation stops communicating after about ten
    minutes per session. The free tools people most often use instead are
    <strong>QModMaster</strong>, <strong>modpoll</strong> (command line) and
    <strong>CAS Modbus Scanner</strong>. They read and write registers fine. What none of
    them can do is tell you what a register <em>means</em> &mdash; for that you need the
    device's register map.</p>""",
    body_html="""
  <h2>What people are really asking</h2>
  <p>&ldquo;Modbus Poll alternative&rdquo; is almost always one of three wishes:
  <em>I don't want to pay for it</em>, <em>the trial keeps disconnecting</em>, or
  <em>I want it to also decode the value, not just show me a raw register</em>. It is
  worth being clear which one you have, because the honest answer is different for
  each.</p>

  <h2>The ten-minute trial</h2>
  <p>Modbus Poll's free download is a fully featured evaluation that disconnects after
  roughly ten minutes, so you reconnect to keep going. That is how the trial is meant to
  work, not a bug, and there is no legitimate way round it other than buying the licence
  &mdash; which is the right call if it is your daily desk tool.</p>

  <h2>The free tools people compare</h2>
  <p>If you specifically want a free desktop master, the names that come up most are
  <strong>QModMaster</strong>, <strong>modpoll</strong> (a command-line tool) and
  <strong>CAS Modbus Scanner</strong>. They read and write fine. What they mostly do not
  do is the part that eats your afternoon: telling you that a raw <code>0x2A3D</code>
  across two registers is 12.75 as a word-swapped float rather than nonsense. See
  <a href="modbus-value-wrong-scaling-byte-order.html">why your Modbus value looks
  wrong</a> for why that step matters.</p>

  <h2>The part no tool does for you</h2>
  <p>Every Modbus master, paid or free, shows you the contents of a numbered slot. None
  of them knows what the slot is. That knowledge lives in the manufacturer's register
  map, so the fastest way to a working setup is usually to find the map first:</p>
  <ul>
    <li>The free <a href="../modbus-register-maps/index.html">register-map library</a>
    lists verified addresses, data types, word order and scaling for common meters,
    drives, generator controllers, inverters and HVAC equipment.</li>
    <li>The <a href="../modbus-float-decoder.html">float and byte-order decoder</a> shows
    two raw registers in all four word orders at once.</li>
    <li>The <a href="../modbus-address-converter.html">address converter</a> turns a
    40001-style address into the 0-based number your tool sends.</li>
  </ul>

  <div class="callout">
  <p>This is not a &ldquo;Modbus Poll is bad&rdquo; page. It is mature, fast, scriptable,
  and excellent for desk and bench work, and if that is your world the licence pays for
  itself.</p>
  </div>
""",
    related=[
        ("guides/modbus-value-wrong-scaling-byte-order", "Why does my Modbus value look wrong?"),
        ("guides/how-to-write-to-a-modbus-register", "How do I write to a Modbus register safely?"),
        ("guides/modbus-function-codes-explained", "Modbus function codes explained"),
        ("modbus-register-maps/index", "Modbus register maps by manufacturer"),
    ],
))

GUIDES.append(dict(
    slug="guides/modbus-timeout-no-response",
    title="Modbus timeout, no response? 7 causes in order | Easy Modbus",
    question="Why is my Modbus request timing out with no response?",
    description="A Modbus timeout means your request left but nothing came back. The seven causes in order of likelihood, and how to tell a network fault from a framing one.",
    answer_html="""<p>A timeout means the request went out and <strong>nothing came
    back at all</strong> &mdash; which is different from an error reply, and points
    at a different set of causes. In order of how often they turn out to be the
    problem: the wrong framing (Modbus RTU behind a transparent gateway, spoken to
    as if it were Modbus TCP), the wrong unit ID, no network route to the device, a
    connection limit already reached, Modbus switched off on the equipment, the
    wrong port, or a serial-side wiring fault. The good news is that a timeout is
    silence, and silence narrows things down fast.</p>""",
    body_html="""
  <h2>Silence versus a &ldquo;no&rdquo;</h2>
  <p>First, be sure it is actually a timeout. If the device replies with an
  <em>exception</em> &mdash; illegal data address, gateway failed to respond &mdash;
  that is not silence, it is proof of life, and it means something quite different.
  See <a href="modbus-exception-codes.html">Modbus exception codes explained</a>. A
  true timeout is when your tool waits the full timeout period and gives up with
  nothing received.</p>

  <h2>The seven causes, most likely first</h2>

  <h3>1. Wrong framing: RTU-over-TCP mistaken for Modbus TCP</h3>
  <p>This is the single most common cause of a silent Modbus connection. The
  equipment is really serial RTU behind a gateway that just pipes the bytes through
  without translating. You open a TCP connection fine &mdash; so the device
  &ldquo;is there&rdquo; &mdash; but every request times out, because it is written
  in the wrong dialect. Switch to <em>Modbus RTU over TCP</em> and try again. See
  <a href="modbus-tcp-vs-rtu-vs-rs485.html">TCP, RTU or RS-485 &mdash; which do I
  have?</a></p>

  <h3>2. Wrong unit ID</h3>
  <p>Behind a gateway, the unit ID selects which device on the serial chain
  answers. The wrong one gives either total silence or a gateway exception. Try 1
  first, then 0, then sweep. (Some tools and gateways use 255.) See <a href="modbus-unit-id-slave-id.html">what is a
  Modbus unit ID?</a></p>

  <h3>3. No route to the device</h3>
  <p>If the connection itself times out &mdash; you never even get
  <em>connected</em> &mdash; the device is on a different subnet or VLAN with no
  route, or a firewall is dropping it. Ping the IP first: if ping fails, no Modbus
  tool will do better. See <a href="cannot-find-modbus-devices.html">why can't I
  find my Modbus devices?</a></p>

  <h3>4. The device's connection limit is already reached</h3>
  <p>Many Modbus TCP devices accept only one connection, and some accept a few then
  stop answering. If a building management system is already polling it, your
  request may connect but never get a reply. Close other software, or try when the
  BMS is not polling.</p>

  <h3>5. Modbus is switched off, or on a different port</h3>
  <p>Plenty of equipment ships with Modbus TCP disabled, or listening on 503 or 5020
  rather than 502. Check the device's own network settings screen. A closed port
  usually gives <em>connection refused</em> rather than a timeout, but a firewall in
  front of it turns that refusal into silence.</p>

  <h3>6. Reading too many registers at once</h3>
  <p>If single reads work but a block read times out, the device or its gateway is
  choking on the request size. Drop the block to 32 or 16 registers. Cheap gateways
  fall over well below the 125-register limit the specification allows.</p>

  <h3>7. Serial-side trouble (RTU only)</h3>
  <p>On an RS-485 chain, silence can be a baud-rate or parity mismatch, A and B
  swapped, missing termination on a long run, or two devices sharing a unit ID and
  colliding. None of these is discoverable &mdash; every device on the chain has to
  agree, and the settings have to be entered by hand.</p>

  <h2>A two-minute triage</h2>
  <ol>
    <li><strong>Ping the IP.</strong> Fails &rarr; it is the network (cause 3). Works
    &rarr; carry on.</li>
    <li><strong>Does it connect but not reply?</strong> &rarr; framing or unit ID
    (causes 1, 2), or a connection limit (cause 4).</li>
    <li><strong>Switch to RTU-over-TCP and retry.</strong> This one move fixes more
    timeouts than any other.</li>
    <li><strong>Try unit ID 1, then 0, then sweep a small range.</strong> Some tools and
    gateways use 255.</li>
    <li><strong>Ask for one register instead of a block.</strong></li>
  </ol>
  <div class="callout">
  <p>Trying the other framing and sweeping a small range of unit IDs settle causes 1
  and 2 between them &mdash; and those two are most of all Modbus timeouts.</p>
  </div>
""",
    related=[
        ("guides/modbus-exception-codes", "What do Modbus exception codes mean?"),
        ("guides/cannot-find-modbus-devices", "Why can't I find my Modbus devices?"),
        ("guides/modbus-tcp-vs-rtu-vs-rs485", "Modbus TCP, RTU or RS-485 &mdash; which do I have?"),
        ("guides/modbus-unit-id-slave-id", "What is a Modbus unit ID or slave ID?"),
    ],
))

GUIDES.append(dict(
    slug="guides/modbus-exception-codes",
    title="Modbus exception codes explained | Easy Modbus",
    question="What do Modbus exception codes mean?",
    description="Modbus exception codes 01, 02, 03, 04, 06, 0A and 0B in plain English: what each means, what caused it, and the fix. Exception 02 is almost always addressing.",
    answer_html="""<p>An exception reply is the device saying <em>no</em> &mdash; and
    that is good news, because it proves the device received your request, understood
    it, and is alive. The code tells you why it declined. The two you will meet most
    are <strong>02, illegal data address</strong> (that register does not exist &mdash;
    almost always an off-by-one address, not a broken device) and <strong>0B, gateway
    target device failed to respond</strong> (the gateway is fine, but nothing
    answered at that unit ID). The rest are rarer and each points at one specific
    thing.</p>""",
    body_html="""
  <h2>An exception is proof of life</h2>
  <p>This is worth saying first because it changes how you read the situation. A
  <a href="modbus-timeout-no-response.html">timeout</a> is silence &mdash; maybe
  nothing is there. An <em>exception</em> is a reply: a real Modbus device got your
  message, parsed it, and returned a coded refusal. The device is reachable. You are
  now debugging the <em>request</em>, not the connection.</p>

  <h2>The codes, in plain English</h2>
  <table>
    <tr><th>Code</th><th>Name</th><th>What actually happened, and the fix</th></tr>
    <tr><td>01 (0x01)</td><td>Illegal function</td><td>This device does not support that function code. You used code 4 on a value that lives in the holding registers, or vice versa. Try 3 instead of 4. See <a href="modbus-function-codes-explained.html">function codes explained</a>.</td></tr>
    <tr><td>02 (0x02)</td><td>Illegal data address</td><td>That register number does not exist on this device. Nine times out of ten the address is off by one, or you are using the Modicon 40001 form where the tool wants the zero-based 0. The device is fine.</td></tr>
    <tr><td>03 (0x03)</td><td>Illegal data value</td><td>The value or the quantity is out of range. Usually you asked for too many registers in one request, or wrote a value the device rejects. Ask for fewer; check the allowed range.</td></tr>
    <tr><td>04 (0x04)</td><td>Server / device failure</td><td>Something failed inside the device while handling the request. Often a sensor that register depends on is faulted. Retry; if it persists, it is the equipment, not you.</td></tr>
    <tr><td>05 (0x05)</td><td>Acknowledge</td><td>Accepted, but it needs more time (used with long operations). Wait and poll. Rare in building equipment.</td></tr>
    <tr><td>06 (0x06)</td><td>Device busy</td><td>The device is mid-task and cannot answer now. Wait and retry.</td></tr>
    <tr><td>0A (0x0A)</td><td>Gateway path unavailable</td><td>A gateway has no configured route to that unit ID. The gateway's routing table needs the unit, or you have the wrong gateway.</td></tr>
    <tr><td>0B (0x0B)</td><td>Gateway target device failed to respond</td><td>The gateway is healthy; nothing answered at that unit ID on its serial side. Wrong unit ID, a device powered off, or an RS-485 wiring fault.</td></tr>
  </table>

  <h2>Exception 02 in detail, because it is the common one</h2>
  <p>&ldquo;Illegal data address&rdquo; almost never means the device is broken. It
  means you asked for a slot that is not there, and there are three usual reasons:</p>
  <ul>
    <li><strong>Off-by-one.</strong> The map lists <code>40001</code> and you sent
    <code>1</code> instead of <code>0</code> &mdash; or the reverse. This is the
    single most common addressing mistake in Modbus. See
    <a href="modbus-address-off-by-one.html">why is my Modbus address off by one?</a></li>
    <li><strong>Wrong table.</strong> The value is a holding register but you read it
    as an input register, so the address does not exist in the table you asked. Check
    the register type in the map.</li>
    <li><strong>Reading past the end.</strong> A block read that starts valid but runs
    off the end of the device's map returns 02 for the whole block. Shorten it.</li>
  </ul>
  <p>Because an 02 confirms the device is answering, it is actually the easiest error
  to chase: change one thing about the address and read again.</p>

  <h2>Exception 0B versus a timeout</h2>
  <p>These two get confused constantly. A plain <a href="modbus-timeout-no-response.html">timeout</a>
  means no gateway even answered. An <strong>0B</strong> means the gateway answered
  <em>for</em> a device that then stayed silent &mdash; so the gateway, the network
  and the port are all fine, and the problem is downstream on the serial chain: the
  unit ID, or the wiring to that one device. That is a much smaller haystack.</p>

  <div class="callout">
  <p>For an 02 (illegal data address), check the addressing first: it is almost
  always an off-by-one or the wrong table. See
  <a href="modbus-address-off-by-one.html">why Modbus addresses are off by one</a>.</p>
  </div>
""",
    related=[
        ("guides/modbus-address-off-by-one", "Why is my Modbus address off by one?"),
        ("guides/modbus-function-codes-explained", "What are Modbus function codes?"),
        ("guides/modbus-timeout-no-response", "Why is my Modbus request timing out?"),
        ("guides/cannot-find-modbus-devices", "Why can't I find my Modbus devices?"),
    ],
))

GUIDES.append(dict(
    slug="guides/modbus-crc-error",
    title="Modbus CRC error: causes and fixes | Easy Modbus",
    question="What causes a Modbus CRC error, and how do I fix it?",
    description="A Modbus CRC error means the message arrived corrupted. The real causes: noise, termination, baud mismatch, and RTU/TCP framing confusion, and how to fix each.",
    answer_html="""<p>A CRC error means a Modbus RTU message arrived but its checksum
    did not match, so the receiver knows the bytes were corrupted in transit and
    throws them away. It is almost always a <strong>physical or serial-settings
    problem</strong>, not a software one: electrical noise on the RS-485 line,
    missing or wrong termination, a baud-rate or parity mismatch, or two devices
    talking over each other. One software cause exists and is worth ruling out first
    &mdash; feeding RTU frames to a tool expecting Modbus TCP, or the reverse, which
    makes every message look corrupt.</p>""",
    body_html="""
  <h2>What the CRC actually is</h2>
  <p>Every Modbus RTU message ends with a two-byte CRC &mdash; a number calculated
  from all the preceding bytes. The receiver recalculates it and compares. If a
  single bit changed on the wire, the two will not match, and the receiver discards
  the frame rather than acting on corrupted data. So a CRC error is not the protocol
  failing; it is the protocol doing its job and catching damage. Modbus TCP has no
  CRC &mdash; the TCP layer handles integrity &mdash; so CRC errors belong to RTU and
  RTU-over-TCP.</p>

  <h2>The causes, most common first</h2>

  <h3>1. Wrong framing (the software one, rule it out first)</h3>
  <p>If a tool set to Modbus TCP is pointed at an RTU-over-TCP gateway, or a tool
  expecting RTU receives clean TCP frames, every message looks malformed and can be
  reported as a CRC or framing error. Before chasing cables, confirm you are speaking
  the right dialect. See <a href="modbus-tcp-vs-rtu-vs-rs485.html">TCP, RTU or RS-485
  &mdash; which do I have?</a></p>

  <h3>2. Baud rate, parity or stop bits mismatched</h3>
  <p>Every device on an RS-485 chain must use identical serial settings. If one is at
  9600 8N1 and the master is at 19200 8E1, the bytes are misread and the CRC never
  matches. This produces consistent, every-message CRC errors &mdash; which is
  actually a helpful signature, because intermittent errors point elsewhere.</p>

  <h3>3. Missing or wrong termination</h3>
  <p>A long RS-485 run needs a termination resistor (typically 120 ohm) at each end,
  and only at the ends. Missing termination causes reflections that corrupt bytes,
  and the symptom is classic: it works on the bench with a short cable and fails once
  it is installed on a long one. Too <em>much</em> termination &mdash; a resistor at
  every device &mdash; loads the line down and does the same.</p>

  <h3>4. Electrical noise</h3>
  <p>RS-485 near variable-speed drives, contactors or motor cabling picks up
  interference. Intermittent CRC errors that get worse when a big load switches on are
  the tell. Fixes are shielded twisted-pair cable, a proper ground on the shield at
  one end only, and routing the data cable away from power.</p>

  <h3>5. Two devices on the same unit ID</h3>
  <p>Duplicated unit IDs make two devices answer at once; their replies overlap on the
  wire and arrive as garbage that fails the CRC. If a chain worked until equipment was
  added, suspect this first. See <a href="modbus-unit-id-slave-id.html">what is a
  Modbus unit ID?</a></p>

  <h3>6. A and B swapped, or a marginal connection</h3>
  <p>Reversed data lines, a loose terminal, or a nicked conductor all corrupt bytes
  intermittently. Vendors disagree on which wire is A and which is B, so swapping them
  is a normal diagnostic step, not a mistake.</p>

  <h2>How to narrow it down</h2>
  <table>
    <tr><th>Pattern</th><th>Points at</th></tr>
    <tr><td>Every single message fails</td><td>Baud/parity mismatch, or wrong framing</td></tr>
    <tr><td>Intermittent, worse on long cable</td><td>Termination or noise</td></tr>
    <tr><td>Intermittent, worse when a load switches</td><td>Electrical noise</td></tr>
    <tr><td>Started when a device was added</td><td>Duplicate unit ID, or termination now in the wrong place</td></tr>
    <tr><td>Only over the network, never local</td><td>Framing &mdash; you are on RTU-over-TCP</td></tr>
  </table>
  <div class="callout">
  <p>Because Modbus TCP carries no CRC, moving a stubborn serial device onto a proper
  translating gateway can make the problem disappear entirely &mdash; the integrity
  check becomes TCP's job over clean Ethernet. It treats the symptom rather than the
  cause, but on a noisy site it is often the pragmatic fix.</p>
  </div>
""",
    related=[
        ("guides/modbus-tcp-vs-rtu-vs-rs485", "Modbus TCP, RTU or RS-485 &mdash; which do I have?"),
        ("guides/modbus-unit-id-slave-id", "What is a Modbus unit ID or slave ID?"),
        ("guides/modbus-timeout-no-response", "Why is my Modbus request timing out?"),
        ("guides/modbus-reading-slow-or-unreliable", "Why is my Modbus reading slow or unreliable?"),
    ],
))

GUIDES.append(dict(
    slug="guides/modbus-register-reads-zero",
    title="Modbus register reads 0? The 3 usual causes | Easy Modbus",
    question="Why does my Modbus register read 0?",
    description="A Modbus register reading 0 is usually the wrong function code, an off-by-one address, or a value split across two registers, not a dead device.",
    answer_html="""<p>A register stuck at zero is rarely a broken sensor. Five things
    cause it, and only the last is the equipment's fault: you are reading the wrong
    <strong>table</strong> (an input register with the holding-register request, or
    the reverse), the address is <strong>off by one</strong>, the value is really a
    <strong>32-bit number split across two registers</strong> and you are looking at
    the empty half, the register is <strong>genuinely unused</strong> on this model,
    or the reading really is zero right now. The quickest way to tell them apart is to
    read a block around it and look at the neighbours.</p>""",
    body_html="""
  <h2>1. Wrong table (the most common)</h2>
  <p>Modbus keeps measurements in two different lists &mdash; <em>input
  registers</em> (read with function code 4) and <em>holding registers</em> (read
  with function code 3). Ask the wrong one and many devices return zero rather than
  an error. If a value reads 0 on FC3, try FC4, and vice versa. See
  <a href="modbus-function-codes-explained.html">function codes explained</a>.</p>

  <h2>2. Off-by-one address</h2>
  <p>If the map lists <code>40001</code> and you read protocol address 1 instead of
  0, you land one slot early &mdash; often on an unused register that reads zero. This
  is the single most common Modbus addressing mistake. See
  <a href="modbus-address-off-by-one.html">why is my Modbus address off by one?</a></p>

  <h2>3. It is half of a 32-bit value</h2>
  <p>A 32-bit float or integer occupies two registers. If the real number is small,
  one of those two registers is often all zeros &mdash; so reading just that half
  gives you 0, and reading just the other half gives you nonsense. The fix is to read
  the pair as one 32-bit value, in the right word order. See
  <a href="modbus-value-wrong-scaling-byte-order.html">why does my Modbus value look
  wrong?</a></p>

  <h2>4. The register is genuinely unused</h2>
  <p>Maps reserve blocks for features a given model does not have fitted, or for
  future use. Those read a steady zero forever. If a whole run of registers reads
  zero and never moves, you are probably in reserved space &mdash; check the map for
  where the real data starts.</p>

  <h2>5. It really is zero</h2>
  <p>A flow of zero, a fault count of zero, a stopped motor's speed &mdash; sometimes
  the honest answer is zero. Make something change physically and watch: if the
  register moves, it was live all along.</p>

  <h2>The fast way to tell which</h2>
  <ol>
    <li><strong>Read a block, not one register.</strong> Ask for 0 to 20 and look at
    the pattern. Isolated zeros among live values point at addressing or a 32-bit
    split; a solid wall of zeros points at the wrong table or reserved space.</li>
    <li><strong>Compare with the device's own display.</strong> If it shows 72.5 and
    the register reads 0, the value is elsewhere &mdash; keep moving the address.</li>
    <li><strong>Decode the neighbours.</strong> A zero is often the empty half of a
    32-bit value next door &mdash; the case people miss most. Paste it and its
    neighbour into the <a href="../modbus-float-decoder.html">float decoder</a> and see
    whether the pair makes sense.</li>
  </ol>
  <div class="callout">
  <p>If instead of a zero you got an <em>error</em> reply &mdash; illegal data
  address &mdash; that is different and more helpful: the device is answering, the
  address just does not exist. See <a href="modbus-exception-codes.html">Modbus
  exception codes</a>.</p>
  </div>
""",
    related=[
        ("guides/modbus-value-wrong-scaling-byte-order", "Why does my Modbus value look wrong?"),
        ("guides/modbus-address-off-by-one", "Why is my Modbus address off by one?"),
        ("guides/modbus-function-codes-explained", "What are Modbus function codes?"),
        ("guides/modbus-exception-codes", "What do Modbus exception codes mean?"),
    ],
))

GUIDES.append(dict(
    slug="guides/modbus-connection-refused",
    title="Modbus connection refused (Errno 111) | Easy Modbus",
    question="What does Modbus connection refused (Errno 111) mean?",
    description="Connection refused means something is at that IP but nothing listens on the Modbus port. The causes (wrong port, Modbus off, wrong host, limit) and fixes.",
    answer_html="""<p>&ldquo;Connection refused&rdquo; &mdash; often shown as
    <code>[Errno 111] Connection refused</code> &mdash; means your request reached a
    real host, but nothing was listening on the Modbus port you tried, so the host
    actively said no. That is different from a timeout, which is silence. It narrows
    to four things: the wrong port (Modbus TCP is 502, but some devices use 503 or
    5020), Modbus TCP switched off on the equipment, the right port on the wrong host,
    or the device's single connection already being in use.</p>""",
    body_html="""
  <h2>Refused is not the same as timed out</h2>
  <p>The distinction tells you where to look. A <a href="modbus-timeout-no-response.html">timeout</a>
  means nothing answered at all &mdash; usually no route, or a firewall silently
  dropping packets. <strong>Refused</strong> means a host <em>was</em> reached and it
  actively rejected the connection, because nothing is listening on that port. The
  network is fine; the port is the problem.</p>

  <h2>The four causes</h2>

  <h3>1. Wrong port</h3>
  <p>Modbus TCP is registered on <strong>502</strong>, and that is the default to
  try. But 503 turns up where two Modbus services share a host, and 5020 is common on
  gateways and where 502 was already taken. Check the device's own network settings
  screen for the actual port.</p>

  <h3>2. Modbus TCP is switched off</h3>
  <p>A lot of equipment ships with Modbus disabled, or with only the serial port
  enabled. There is usually a menu item to turn Modbus TCP on, and some devices need a
  reboot afterwards. Until it is on, port 502 is closed and every attempt is refused.</p>

  <h3>3. Right port, wrong host</h3>
  <p>If you are pointing at a PC, a PLC's programming port, or a switch rather than
  the Modbus device itself, the host is up but has nothing on 502. Double-check the IP
  against the equipment label or its display.</p>

  <h3>4. The one connection is already taken</h3>
  <p>Many Modbus TCP devices accept exactly one connection. If a building management
  system or a logger already holds it, some devices refuse the second attempt outright
  rather than timing out. Close other software and try again.</p>

  <h2>How to confirm it in a minute</h2>
  <ol>
    <li><strong>Ping the IP.</strong> If ping works but Modbus is refused, it is the
    port or the service (causes 1&ndash;2), not the network.</li>
    <li><strong>Try 502, then 503, then 5020.</strong></li>
    <li><strong>Check the device screen</strong> for whether Modbus TCP is enabled and
    on which port.</li>
    <li><strong>Close anything else talking to it</strong> and retry.</li>
  </ol>
  <div class="callout">
  <p>Refused and timed out are different answers: refused means something is at that
  address and said no, so chase the port; timed out means nothing answered, so chase the
  network. Port 502 is standard, but 503 and 5020 both turn up. If the device is really serial
  behind a gateway, also see <a href="modbus-tcp-vs-rtu-vs-rs485.html">TCP, RTU or
  RS-485 &mdash; which do I have?</a></p>
  </div>
""",
    related=[
        ("guides/modbus-timeout-no-response", "Why is my Modbus request timing out?"),
        ("guides/cannot-find-modbus-devices", "Why can't I find my Modbus devices?"),
        ("guides/modbus-tcp-vs-rtu-vs-rs485", "Modbus TCP, RTU or RS-485 &mdash; which do I have?"),
        ("guides/modbus-exception-codes", "What do Modbus exception codes mean?"),
    ],
))

GUIDES.append(dict(
    slug="guides/find-modbus-baud-rate-parity",
    title="Find an unknown Modbus baud rate & parity | Easy Modbus",
    question="How do I find an unknown Modbus device's baud rate and parity?",
    description="No display, no paperwork, and a serial Modbus device that won't answer? How to find the baud rate, parity and unit ID by trying the few combinations that occur.",
    answer_html="""<p>You cannot ask a serial Modbus device what its settings are
    &mdash; there is no discovery, so you try the combinations that actually occur in
    the wild until one answers. That is fewer than it sounds: baud is almost always
    <strong>9600</strong> or <strong>19200</strong>, framing is almost always
    <strong>8N1</strong> or <strong>8E1</strong>, and the unit ID is usually
    <strong>1</strong>. Hold the framing steady, sweep the two common baud rates
    first, and the moment a read succeeds you have found all three at once.</p>""",
    body_html="""
  <h2>Why you have to guess at all</h2>
  <p>An RS-485 chain has no way to announce its serial settings, and every device on
  it must already agree on them. If the settings in your tool do not match, the bytes
  are misread and you get silence or a <a href="modbus-crc-error.html">CRC error</a>,
  never a helpful &ldquo;wrong baud rate&rdquo; message. So the job is to narrow the
  guess to the combinations that are actually used.</p>

  <h2>The short list that covers almost everything</h2>
  <table>
    <tr><th>Setting</th><th>Try in this order</th></tr>
    <tr><td>Baud rate</td><td><strong>9600</strong>, <strong>19200</strong>, then 38400, 4800, 115200, 2400</td></tr>
    <tr><td>Framing (data/parity/stop)</td><td><strong>8N1</strong>, then <strong>8E1</strong>, then 8O1, 8N2</td></tr>
    <tr><td>Unit ID</td><td><strong>1</strong>, then a sweep of 1&ndash;16, then up to 32</td></tr>
  </table>
  <p>That is 6 baud &times; 4 framings &times; a small ID sweep &mdash; a few dozen
  combinations at most, and the first two of each cover the large majority of
  equipment. You will usually land in the first handful.</p>

  <h2>A method that does not drive you mad</h2>
  <ol>
    <li><strong>Change one thing at a time.</strong> Fix framing at 8N1 and unit ID at
    1, then step through baud rates. If nothing, switch framing to 8E1 and step the
    baud rates again.</li>
    <li><strong>Watch for the shape of the reply.</strong> Total silence usually means
    the baud or framing is wrong. Garbled bytes or intermittent CRC errors mean you
    are <em>close</em> &mdash; often the right baud with the wrong parity.</li>
    <li><strong>Once anything answers, stop.</strong> A single successful read fixes
    baud, framing <em>and</em> a working unit ID in one go. Then sweep unit IDs at
    those settings to find the others on the chain.</li>
    <li><strong>Isolate if you can.</strong> If several devices share the line and
    replies collide, unplug all but one while you hunt.</li>
  </ol>

  <h2>Where to shortcut the guessing</h2>
  <p>Before sweeping, spend two minutes looking for the answer: the device's own
  display or settings menu, the DIP switches (often the unit ID in binary), the
  commissioning paperwork, or the vendor's manual &mdash; the defaults are usually
  printed there. See <a href="modbus-unit-id-slave-id.html">what is a Modbus unit
  ID?</a> for reading DIP switches.</p>

  <div class="callout">
  <p>If the device sits behind a network gateway, the baud rate and framing are set
  on the <em>gateway</em>, not in your Modbus software; only the unit ID travels with
  each request. If you are wiring straight into RS-485 with a USB adapter, your Modbus
  master's serial settings are where the baud/framing hunt happens &mdash; see <a href="modbus-tcp-vs-rtu-vs-rs485.html">TCP, RTU or
  RS-485 &mdash; which do I have?</a></p>
  </div>
""",
    related=[
        ("guides/modbus-unit-id-slave-id", "What is a Modbus unit ID or slave ID?"),
        ("guides/modbus-tcp-vs-rtu-vs-rs485", "Modbus TCP, RTU or RS-485 &mdash; which do I have?"),
        ("guides/modbus-crc-error", "What causes a Modbus CRC error?"),
        ("guides/cannot-find-modbus-devices", "Why can't I find my Modbus devices?"),
    ],
))

GUIDES.append(dict(
    slug="guides/read-eastron-sdm-modbus",
    title="Read Eastron SDM120/SDM630 over Modbus | Easy Modbus",
    question="How do I read an Eastron SDM power meter over Modbus?",
    description="Eastron SDM120/SDM220/SDM630 meters report each value as a 32-bit float over Modbus. The settings, function code, word order, and how to read them over a network.",
    answer_html="""<p>Eastron's SDM range &mdash; the SDM120, SDM220, SDM630 and their
    relatives &mdash; is one of the most common Modbus devices in the field, and it is
    refreshingly consistent: <strong>every measurement is a 32-bit IEEE-754 float</strong>,
    read with <strong>function code 4</strong> (input registers), in
    <strong>big-endian (ABCD) word order</strong>. Default serial settings are usually
    <strong>9600 baud, 8N1, unit ID 1</strong> (some ship at 2400). Get those right and
    the whole meter falls open.</p>""",
    body_html="""
  <h2>The settings that matter</h2>
  <table>
    <tr><th>Setting</th><th>Eastron SDM default</th></tr>
    <tr><td>Function code</td><td>04 &mdash; read input registers</td></tr>
    <tr><td>Data type</td><td>32-bit IEEE-754 float (every value; two registers each)</td></tr>
    <tr><td>Word order</td><td>ABCD (big-endian, high word first)</td></tr>
    <tr><td>Baud rate</td><td>9600 (SDM630); some models/older units default to 2400</td></tr>
    <tr><td>Framing</td><td>8N1 (parity is configurable on the meter)</td></tr>
    <tr><td>Unit ID</td><td>1</td></tr>
  </table>
  <p>The single most useful fact: because <em>everything</em> is a float, you never
  wonder about the data type. If a value reads as wild nonsense, it is the word order,
  not the type &mdash; and ABCD is the answer for Eastron. See
  <a href="modbus-value-wrong-scaling-byte-order.html">why your value looks wrong</a>.</p>

  <h2>Commonly documented SDM630 registers</h2>
  <p>These are the landmark measurements most people want. Addresses are for the
  SDM630; the SDM120 and SDM220 use the same float/FC04/ABCD encoding but expose a
  subset. <strong>Confirm the exact list against your model's datasheet</strong>
  &mdash; Eastron publishes a register map per model.</p>
  <table>
    <tr><th>Measurement</th><th>Register (3x)</th><th>Type</th></tr>
    <tr><td>Phase 1 voltage</td><td>30001</td><td>Float, V</td></tr>
    <tr><td>Phase 1 current</td><td>30007</td><td>Float, A</td></tr>
    <tr><td>Phase 1 active power</td><td>30013</td><td>Float, W</td></tr>
    <tr><td>Total system power</td><td>30053</td><td>Float, W</td></tr>
    <tr><td>Frequency</td><td>30071</td><td>Float, Hz</td></tr>
    <tr><td>Import active energy</td><td>30073</td><td>Float, kWh</td></tr>
    <tr><td>Export active energy</td><td>30075</td><td>Float, kWh</td></tr>
  </table>
  <p>Remember the addressing convention: <code>30001</code> is the first input
  register, which is protocol address 0 on the wire. If every value is one slot out,
  that is why &mdash; see <a href="modbus-address-off-by-one.html">Modbus address off
  by one</a>.</p>

  <h2>Reading one over the network</h2>
  <p>If the meter is on a network (native Ethernet, or RS-485 behind a gateway), any
  Modbus TCP master reads it directly. Read a block of input registers with function
  code 4 and decode each pair as a float in ABCD order; the
  <a href="../modbus-float-decoder.html">float decoder</a> confirms a pair by hand.
  Compare the result with the meter's own display before you trust the addresses. For
  the full, verified register list of each model, see the
  <a href="../modbus-register-maps/eastron/index.html">Eastron register maps</a>.</p>

  <div class="callout">
  <p>If the meter is straight RS-485 with no gateway, you will read it with a Windows
  master and a USB adapter instead &mdash; the encoding above is identical, only the
  transport differs. And a stuck 2400-vs-9600 mismatch is the usual reason a known-good
  SDM stays silent; see <a href="find-modbus-baud-rate-parity.html">finding an unknown
  baud rate</a>.</p>
  </div>
""",
    related=[
        ("modbus-register-maps/eastron/index", "Eastron SDM Modbus register maps (SDM120CT, SDM230, SDM630)"),
        ("guides/modbus-value-wrong-scaling-byte-order", "Why does my Modbus value look wrong?"),
        ("guides/find-modbus-baud-rate-parity", "How do I find an unknown Modbus baud rate?"),
        ("guides/modbus-function-codes-explained", "What are Modbus function codes?"),
    ],
))

# ---------------------------------------------------------------------------
# Free interactive tools (link magnets; generated, schema-marked)
# ---------------------------------------------------------------------------

TOOLS = []

TOOL_CSS_EXTRA = """
  .tool { background:var(--box); border:1px solid var(--line); border-radius:14px;
          padding:1.3rem 1.4rem; margin:1.75rem 0; }
  .tool label { display:block; font-family:"IBM Plex Mono",ui-monospace,monospace;
                font-size:.72rem; text-transform:uppercase; letter-spacing:.12em;
                color:var(--accent); margin:.9rem 0 .3rem; }
  .tool input, .tool select { width:100%; padding:.6rem .7rem; font-size:1rem;
                font-family:"IBM Plex Mono",ui-monospace,monospace; color:var(--fg);
                background:var(--code); border:1px solid var(--line); border-radius:8px; }
  .tool .row { display:flex; gap:1rem; flex-wrap:wrap; }
  .tool .row > div { flex:1 1 160px; }
  .tool button { margin-top:1.1rem; padding:.6rem 1.2rem; font-family:"Archivo",sans-serif;
                font-weight:700; text-transform:uppercase; letter-spacing:.03em; font-size:.85rem;
                color:var(--ink); background:var(--accent); border:none; border-radius:8px;
                cursor:pointer; }
  .tool table { margin:1.3rem 0 0; }
  .tool .best { color:var(--accent); font-weight:700; }
  .tool .out-note { color:var(--muted); font-size:.85rem; margin-top:.8rem; }
"""


def tool_page(slug, title, question, description, intro_html, tool_html, related):
    """A standalone interactive tool page. Rendered with .replace() (not %-format)
    so JavaScript in tool_html is safe. Carries BreadcrumbList + SoftwareApplication
    JSON-LD, which the competing tool sites do not."""
    rel = ""
    if related:
        items = "\n".join(
            '      <li><a href="%s.html">%s</a></li>' % (r[0], r[1]) for r in related
        )
        rel = ('\n  <nav class="more">\n    <h2>Related</h2>\n    <ul>\n' + items +
               '\n    </ul>\n  </nav>')
    jsonld = ('{"@context":"https://schema.org","@graph":['
              '{"@type":"SoftwareApplication","name":' + jstr(question) +
              ',"applicationCategory":"UtilitiesApplication","operatingSystem":"Any (web browser)"'
              ',"offers":{"@type":"Offer","price":"0","priceCurrency":"USD"}'
              ',"description":' + jstr(description) + '},'
              '{"@type":"BreadcrumbList","itemListElement":['
              '{"@type":"ListItem","position":1,"name":"Home","item":"' + BASE_URL + '/index.html"},'
              '{"@type":"ListItem","position":2,"name":' + jstr(question) +
              ',"item":"' + BASE_URL + '/' + slug + '.html"}]}]}')
    return (TOOL_TEMPLATE
            .replace("{{TITLE}}", title)
            .replace("{{DESC}}", description)
            .replace("{{BASE}}", BASE_URL)
            .replace("{{SLUG}}", slug)
            .replace("{{CSS}}", CSS + TOOL_CSS_EXTRA)
            .replace("{{JSONLD}}", jsonld)
            .replace("{{H1}}", question)
            .replace("{{UPDATED}}", UPDATED_HUMAN)
            .replace("{{INTRO}}", intro_html)
            .replace("{{TOOL}}", tool_html)
            .replace("{{REL}}", rel))


TOOL_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/svg+xml" href="icon.svg">
<title>{{TITLE}}</title>
<meta name="description" content="{{DESC}}">
<link rel="canonical" href="{{BASE}}/{{SLUG}}.html">
<meta name="robots" content="index, follow">
<meta name="theme-color" content="#14171a">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Easy Modbus">
<meta property="og:title" content="{{TITLE}}">
<meta property="og:description" content="{{DESC}}">
<meta property="og:url" content="{{BASE}}/{{SLUG}}.html">
<meta property="og:image" content="{{BASE}}/img/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;800;900&family=Manrope:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet">
<style>{{CSS}}</style>
<script type="application/ld+json">
{{JSONLD}}
</script>
</head>
<body>

<header class="site">
  <a href="index.html" style="display:inline-flex;align-items:center;gap:.5rem;text-decoration:none"><img src="icon.svg" alt="" width="26" height="26" style="border-radius:6px"><span>Easy Modbus</span></a>
  <span class="muted">&middot; free Modbus tools</span>
</header>

<article>
  <h1>{{H1}}</h1>
  <p class="updated">Free browser tool &middot; nothing is uploaded &middot; updated {{UPDATED}}</p>
  {{INTRO}}
  {{TOOL}}
</article>{{REL}}

<footer>
  <p>This tool runs entirely in your browser. Need a device&rsquo;s registers? Browse the free
  <a href="modbus-register-maps/index.html">Modbus register-map library</a> &mdash; verified addresses,
  data types, word order and scaling by manufacturer and model.</p>
  <p><a href="terms.html">Terms of use</a> &middot; <a href="privacy.html">Privacy policy</a></p>
</footer>

</body>
</html>
"""

TOOLS.append(dict(
    slug="modbus-float-decoder",
    title="Modbus float & byte-order decoder (ABCD/CDAB) | Easy Modbus",
    question="Modbus float and byte-order decoder",
    description="Paste two Modbus registers and see the 32-bit float and integer in all four word orders (ABCD, CDAB, BADC, DCBA). Free, runs in your browser, nothing uploaded.",
    intro_html="""<p>A 32-bit value lives in two Modbus registers, and vendors put the
    two halves in one of four orders. Guess wrong and a perfectly good 12.75 reads as
    wild nonsense. Paste the two registers below and this decoder shows the float and
    the integers in <strong>all four orders at once</strong>, and highlights the ones
    that land on a sensible engineering magnitude &mdash; the check you would otherwise
    do by hand, four times over. Read the
    background in <a href="guides/modbus-value-wrong-scaling-byte-order.html">why does
    my Modbus value look wrong?</a></p>""",
    tool_html="""
  <div class="tool">
    <div class="row">
      <div><label for="r1">Register 1 (first)</label><input id="r1" value="0x4248" inputmode="text"></div>
      <div><label for="r2">Register 2 (second)</label><input id="r2" value="0x0000" inputmode="text"></div>
    </div>
    <p class="out-note">Enter each 16-bit register as hex (<code>0x4248</code> or
    <code>4248</code>) or as a decimal number (<code>16968</code>).</p>
    <button onclick="decodeFloat()">Decode</button>
    <table id="fout" style="display:none">
      <tr><th>Word order</th><th>Float32</th><th>Int32 (signed)</th><th>UInt32</th></tr>
      <tbody id="fbody"></tbody>
    </table>
    <p class="out-note" id="fnote"></p>
  </div>
<script>
function pReg(s){
  s=(s||'').trim().toLowerCase();
  if(s===''){return NaN;}
  if(s.indexOf('0x')===0){return parseInt(s.slice(2),16);}
  if(/^[0-9a-f]+$/.test(s)&&/[a-f]/.test(s)){return parseInt(s,16);}
  var d=parseInt(s,10);
  return d;
}
function bytesFor(order,A,B,C,D){
  if(order==='ABCD'){return [A,B,C,D];}
  if(order==='CDAB'){return [C,D,A,B];}
  if(order==='BADC'){return [B,A,D,C];}
  return [D,C,B,A];
}
function plausible(f){
  if(!isFinite(f)){return false;}
  var a=Math.abs(f);
  if(a===0){return true;}
  return a>=0.001 && a<1e9;
}
function decodeFloat(){
  var r1=pReg(document.getElementById('r1').value);
  var r2=pReg(document.getElementById('r2').value);
  var note=document.getElementById('fnote');
  if(isNaN(r1)||isNaN(r2)||r1<0||r2<0||r1>65535||r2>65535){
    note.textContent='Enter two register values between 0 and 65535 (0x0000 to 0xFFFF).';
    document.getElementById('fout').style.display='none';
    return;
  }
  var A=(r1>>8)&255, B=r1&255, C=(r2>>8)&255, D=r2&255;
  var orders=['ABCD','CDAB','BADC','DCBA'];
  var body=document.getElementById('fbody');
  body.innerHTML='';
  var anyPlausible=false;
  for(var i=0;i<orders.length;i++){
    var bytes=bytesFor(orders[i],A,B,C,D);
    var buf=new ArrayBuffer(4), dv=new DataView(buf);
    for(var j=0;j<4;j++){dv.setUint8(j,bytes[j]);}
    var f=dv.getFloat32(0,false);
    var si=dv.getInt32(0,false);
    var ui=dv.getUint32(0,false);
    var good=plausible(f);
    if(good){anyPlausible=true;}
    var fstr=isFinite(f)?(Math.abs(f)<1e-4&&f!==0||Math.abs(f)>=1e7?f.toExponential(4):f.toPrecision(7)):String(f);
    var tr=document.createElement('tr');
    tr.innerHTML='<td>'+orders[i]+'</td><td class="'+(good?'best':'')+'">'+fstr+
      '</td><td>'+si+'</td><td>'+ui+'</td>';
    body.appendChild(tr);
  }
  document.getElementById('fout').style.display='';
  note.innerHTML=anyPlausible
    ? 'Rows in amber decode to a sensible engineering magnitude &mdash; usually the right order. Confirm against what the equipment displays.'
    : 'None of the four orders looks like a normal engineering value &mdash; this pair may not be a 32-bit float, or one register is wrong.';
}
window.addEventListener('DOMContentLoaded',decodeFloat);
</script>
""",
    related=[
        ("guides/modbus-value-wrong-scaling-byte-order", "Why does my Modbus value look wrong?"),
        ("guides/modbus-register-reads-zero", "Why does my Modbus register read 0?"),
        ("modbus-address-converter", "Modbus address converter (40001 &harr; 0)"),
    ],
))

TOOLS.append(dict(
    slug="modbus-address-converter",
    title="Modbus address converter: 40001 to 0 | Easy Modbus",
    question="Modbus address converter",
    description="Convert any Modbus address between Modicon (40001), prefixed (4x00001), 1-based and 0-based forms. Shows the register table and function code. Free tool.",
    intro_html="""<p>The same Modbus register is written four different ways, and the
    number that actually travels on the wire is the zero-based one &mdash; which is why
    values so often come out one slot off. Type an address in whatever form your manual
    uses and this converter shows the table, the protocol (wire) address, the function
    codes, and every notation. Background: <a href="guides/modbus-address-off-by-one.html">why
    is my Modbus address off by one?</a></p>""",
    tool_html="""
  <div class="tool">
    <label for="addr">Modbus address</label>
    <input id="addr" value="40007" inputmode="text">
    <p class="out-note">Try <code>40007</code>, <code>4x00007</code>, <code>30001</code>,
    <code>00001</code>, or a plain number like <code>6</code>.</p>
    <button onclick="convAddr()">Convert</button>
    <table id="aout" style="display:none"><tbody id="abody"></tbody></table>
    <p class="out-note" id="anote"></p>
  </div>
<script>
var TABLES={'0':['Coil','FC01 read / FC05,FC15 write','read/write'],
            '1':['Discrete input','FC02 read','read only'],
            '3':['Input register','FC04 read','read only'],
            '4':['Holding register','FC03 read / FC06,FC16 write','read/write']};
function row(k,v){return '<tr><th>'+k+'</th><td>'+v+'</td></tr>';}
function convAddr(){
  var s=(document.getElementById('addr').value||'').trim().toLowerCase();
  var note=document.getElementById('anote');
  var body=document.getElementById('abody');
  var out=document.getElementById('aout');
  var prefix=null, wire=null, human=null;
  var m;
  if((m=s.match(/^([0134])x0*(\\d+)$/))){ prefix=m[1]; human=parseInt(m[2],10); wire=human-1; }
  else if((m=s.match(/^([0134])(\\d{4,5})$/))){ prefix=m[1]; human=parseInt(m[2],10); wire=human-1; }
  else if((m=s.match(/^(\\d+)$/))){
    var n=parseInt(m[1],10);
    body.innerHTML=row('You entered','a plain number, '+n)
      +row('If it is 1-based','wire (protocol) address '+(n-1))
      +row('If it is 0-based','wire (protocol) address '+n+' (use as-is)')
      +row('Tip','Most vendor tables count from 1; most tools want the 0-based value. Confirm against the device display.');
    out.style.display=''; note.textContent=''; return;
  }
  if(prefix===null||isNaN(human)){
    note.textContent='Could not read that. Try a form like 40007, 4x00007, 30001 or a plain number.';
    out.style.display='none'; return;
  }
  if(human<1){ note.textContent='Register number must be 1 or more in the 4xxxx / 4x form.'; out.style.display='none'; return; }
  var t=TABLES[prefix];
  var modicon=prefix+String(human).padStart(4,'0');
  var pfx=prefix+'x'+String(human).padStart(5,'0');
  body.innerHTML=row('Register table',t[0])
    +row('Function code',t[1])
    +row('Access',t[2])
    +row('Protocol (wire) address',wire+'  &larr; the number to send')
    +row('1-based register number',human)
    +row('Modicon form',modicon)
    +row('Prefixed form',pfx);
  out.style.display=''; note.innerHTML='Remember: in Modbus documentation <code>0x</code> means the coil table, not hexadecimal.';
}
window.addEventListener('DOMContentLoaded',convAddr);
</script>
""",
    related=[
        ("guides/modbus-address-off-by-one", "Why is my Modbus address off by one?"),
        ("guides/modbus-function-codes-explained", "What are Modbus function codes?"),
        ("modbus-float-decoder", "Modbus float & byte-order decoder"),
        ("guides/modbus-exception-codes", "What do Modbus exception codes mean?"),
    ],
))

INDEX = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/svg+xml" href="icon.svg">
<title>Modbus Register Maps &amp; Lists, Free | Easy Modbus</title>
<meta name="description" content="Free Modbus register maps for {{NMODELS}} meters, drives, generator controllers, inverters and HVAC units: 0-based addresses, data types, word order, scaling. CSV/JSON.">
<link rel="canonical" href="{{BASE}}/index.html">
<meta name="robots" content="index, follow">
<meta name="google-site-verification" content="HxMj_NPDl3R9Axg40Y-NMb3WkXU5nK-otX92OkhI3Z4">
<meta name="google-site-verification" content="DD9YuFSwl6uUHegREypWoA1NwQhJyVpjQt7QftOVb4Q">
<meta name="theme-color" content="#14171a">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Easy Modbus">
<meta property="og:title" content="Free Modbus register maps &mdash; Easy Modbus">
<meta property="og:description" content="Verified Modbus register maps for {{NMODELS}} models from {{NMFRS}} manufacturers, with plain-English Modbus guides and free browser tools.">
<meta property="og:url" content="{{BASE}}/index.html">
<meta property="og:image" content="{{BASE}}/img/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Free Modbus register maps &mdash; Easy Modbus">
<meta name="twitter:description" content="Verified Modbus register maps for {{NMODELS}} models from {{NMFRS}} manufacturers, with plain-English Modbus guides and free browser tools.">
<meta name="twitter:image" content="{{BASE}}/img/og-image.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;800;900&family=Manrope:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#14171a; --panel:#1d2227; --line:#2f363d;
  --fg:#f3f5f6; --mut:#9aa4ad; --accent:#2dd4bf; --ink:#0d0f11;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{overflow-wrap:break-word;
  margin:0; background:var(--bg); color:var(--fg);
  font-family:"Manrope",system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
  font-size:17px; line-height:1.65; -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1080px; margin:0 auto; padding:0 16px}
a{color:var(--accent); text-decoration:none}
a:hover{text-decoration:underline}
.eyebrow{
  font-family:"IBM Plex Mono",ui-monospace,monospace; font-weight:600;
  font-size:.74rem; letter-spacing:.22em; text-transform:uppercase;
  color:var(--accent); margin:0 0 1rem;
}
h1,h2,h3{font-family:"Archivo",sans-serif; letter-spacing:-.01em; line-height:1.05}
h1{font-weight:900; text-transform:uppercase; font-size:clamp(2.1rem,6vw,4rem); margin:0 0 1.25rem}
h1 span{color:var(--accent)}
h2{font-weight:800; text-transform:uppercase; font-size:clamp(1.4rem,3.2vw,2rem); margin:0 0 1.25rem}
h3{font-weight:800; font-size:1.05rem; margin:0 0 .4rem}
p{margin:0 0 1rem}
strong{color:#fff}

.top{border-bottom:1px solid var(--line); background:rgba(20,23,26,.85); backdrop-filter:blur(8px); position:sticky; top:0; z-index:10}
.top .wrap{display:flex; align-items:center; gap:.65rem; height:60px}
.brand{display:inline-flex; align-items:center; gap:.6rem; color:var(--fg)!important}
.brand img{width:30px; height:30px; border-radius:8px; display:block}
.brand b{font-family:"Archivo",sans-serif; font-weight:900; text-transform:uppercase; letter-spacing:.02em; font-size:1.05rem}
.top nav{margin-left:auto; display:flex; gap:1.1rem; font-family:"IBM Plex Mono",monospace; font-size:.72rem; letter-spacing:.12em; text-transform:uppercase}
.top nav a{color:var(--mut)}

.hero{padding:clamp(2.5rem,6vw,5rem) 0 clamp(2rem,4vw,3.5rem)}
.hero .wrap{display:grid; grid-template-columns:1.15fr .85fr; gap:clamp(2rem,5vw,4rem); align-items:center}
.hero .lede{font-size:1.12rem; color:#e7ebee; max-width:46ch}
.hero .sub{color:var(--mut); font-size:1rem}
.hero .sub b{color:var(--accent)}
.finder{border:2px solid var(--accent); border-radius:18px; padding:1.4rem 1.3rem; background:var(--panel); box-shadow:0 30px 70px rgba(0,0,0,.5)}
.finder .stats{display:grid; grid-template-columns:repeat(3,1fr); gap:.5rem; margin:0 0 1.2rem}
.finder .stat b{display:block; font-family:"Archivo",sans-serif; font-weight:900; font-size:1.7rem; color:#fff; line-height:1.1}
.finder .stat span{font-family:"IBM Plex Mono",monospace; font-size:.66rem; letter-spacing:.14em; text-transform:uppercase; color:var(--mut)}
.finder label{display:block; font-family:"IBM Plex Mono",monospace; font-size:.7rem; letter-spacing:.14em; text-transform:uppercase; color:var(--mut); margin:0 0 .4rem}
.finder select{width:100%; font:inherit; font-size:1rem; padding:.7rem .8rem; border-radius:10px; border:1px solid var(--line); background:var(--ink); color:var(--fg)}
.finder .go{display:block; margin-top:1rem; text-align:center; font-weight:700; padding:.75rem 1rem; border-radius:10px; background:var(--accent); color:var(--ink)!important}

.features{padding:clamp(2rem,4vw,3.5rem) 0; border-top:1px solid var(--line)}
.grid{display:grid; grid-template-columns:repeat(3,1fr); gap:1px; background:var(--line); border:1px solid var(--line)}
.cell{background:var(--panel); padding:1.6rem 1.4rem; border-top:3px solid var(--accent)}
a.cell{display:block; color:var(--fg)}
a.cell:hover{text-decoration:none; background:#232a30}
.cell .n{font-family:"IBM Plex Mono",monospace; font-weight:600; color:var(--accent); font-size:.78rem; letter-spacing:.12em; margin-bottom:.8rem}
.cell p{color:var(--mut); font-size:.95rem; margin:0}

.band{padding:clamp(2rem,4vw,3.5rem) 0; border-top:1px solid var(--line)}
.band p{color:#e7ebee}
.linklist{list-style:none; margin:0; padding:0}
.linklist li{border-bottom:1px solid var(--line); padding:.9rem 0}
.linklist li:last-child{border-bottom:none}
.linklist a{font-family:"Archivo",sans-serif; font-weight:600; font-size:1.05rem}
.linklist .muted{display:block; color:var(--mut); font-size:.9rem; margin-top:.15rem}
.notes{list-style:none; margin:0; padding:0; display:grid; gap:1rem}
.notes li{background:var(--panel); border:1px solid var(--line); border-left:3px solid var(--accent); border-radius:10px; padding:1.1rem 1.2rem; color:var(--mut); font-size:.98rem}
.notes strong{color:#fff}

footer{border-top:1px solid var(--line); padding:2rem 0 3rem; color:var(--mut); font-size:.9rem}
footer a{color:var(--mut); text-decoration:underline}

@media (max-width:760px){
  body{font-size:16px}
  .hero .wrap{grid-template-columns:1fr}
  .grid{grid-template-columns:1fr}
  .top nav{display:none}
}
</style>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "{{BASE}}/#org",
      "name": "Easy Modbus",
      "url": "{{BASE}}/",
      "logo": "{{BASE}}/icon.svg",
      "email": "webmaster@easymodbus.com"
    },
    {
      "@type": "WebSite",
      "@id": "{{BASE}}/#site",
      "name": "Easy Modbus",
      "url": "{{BASE}}/",
      "description": "Free Modbus register-map library with plain-English Modbus guides and browser tools.",
      "publisher": { "@id": "{{BASE}}/#org" }
    }
  ]
}
</script>
</head>
<body>

<div class="top">
  <div class="wrap">
    <a class="brand" href="index.html"><img src="icon.svg" alt=""><b>Easy Modbus</b></a>
    <nav aria-label="Site"><a href="modbus-register-maps/index.html">Register maps</a><a href="#tools">Tools</a><a href="#guides">Guides</a></nav>
  </div>
</div>

<section class="hero">
  <div class="wrap">
    <div class="copy">
      <p class="eyebrow">Free library &middot; {{NMODELS}} models &middot; {{NMFRS}} manufacturers</p>
      <h1>Modbus register maps, <span>checked</span> against the manual</h1>
      <p class="lede">A Modbus device will tell you what is in register 7 and never what
      register 7 <em>is</em>. This free library has the answer for {{NMODELS}} meters,
      drives, generator controllers, inverters, boilers, pumps and HVAC units: every
      register with its 0-based address, data type, word order, scaling, units and
      access, re-typed from the manufacturer&rsquo;s own document and linked to it.</p>
      <p class="sub">No sign-up. <b>Free.</b> Every map downloads as CSV or JSON.</p>
    </div>
    <div class="art">
      <form class="finder" action="modbus-register-maps/index.html" onsubmit="return false" aria-label="Find a register map">
        <div class="stats">
          <div class="stat"><b>{{NMODELS}}</b><span>models</span></div>
          <div class="stat"><b>{{NMFRS}}</b><span>makers</span></div>
          <div class="stat"><b>{{NREGS}}</b><span>registers</span></div>
        </div>
        <label for="mfr-pick">Find a register map</label>
        <select id="mfr-pick"><option value="">Choose a manufacturer&hellip;</option>{{MFR_OPTIONS}}</select>
        <a class="go" href="modbus-register-maps/index.html">Browse the whole library &rarr;</a>
      </form>
    </div>
  </div>
</section>

<section class="features">
  <div class="wrap">
    <h2>Browse by equipment</h2>
    <div class="grid">
{{CATEGORIES}}
    </div>
  </div>
</section>

<section class="band">
  <div class="wrap">
    <h2>What every map gives you</h2>
    <ul class="notes">
      <li><strong>The address on the wire.</strong> Every register is listed by its 0-based
      protocol address, with the manual&rsquo;s own 40001-style number beside it when the two
      differ &mdash; the off-by-one is settled for you.</li>
      <li><strong>Data type and word order.</strong> 16-bit, 32-bit, float or text, and for
      32-bit values whether the high word comes first (ABCD) or second (CDAB).</li>
      <li><strong>Scale, units and access.</strong> The multiplier that turns the raw number
      into an engineering value, the units, and which registers are writable.</li>
      <li><strong>The source.</strong> A link to the manufacturer&rsquo;s free public document,
      so you can check any row yourself, plus CSV and JSON downloads.</li>
    </ul>
  </div>
</section>

<section class="band" id="tools">
  <div class="wrap">
    <h2>Free tools</h2>
    <p>Quick browser calculators for the two arithmetic problems that come up most.
    Nothing is uploaded.</p>
    <ul class="linklist">
{{TOOLS}}
    </ul>
  </div>
</section>

<section class="band" id="guides">
  <div class="wrap">
    <h2>Guides</h2>
    <p>If Modbus is new to you, read <a href="guides/what-is-modbus.html">what is Modbus?</a>
    first. It explains the one thing that causes most of the difficulty: a Modbus device
    will happily tell you the contents of slot number 7, and will never tell you what
    slot 7 is.</p>
    <ul class="linklist">
{{GUIDES}}
    </ul>
  </div>
</section>

<section class="band">
  <div class="wrap">
    <h2>Before you connect</h2>
    <ul class="notes">
      <li>Get onto the <strong>same network</strong> as the equipment. Controls gear is
      usually on its own VLAN, and guest Wi-Fi will not reach it.</li>
      <li>Modbus TCP is <strong>port 502</strong>. 503 and 5020 are both seen.</li>
      <li>Finding equipment means <strong>sweeping the subnet</strong>, because Modbus
      devices never announce themselves. On a monitored network that looks like a port
      scan, so tell whoever runs it.</li>
      <li>Reading is harmless. <strong>Writing has no undo</strong> &mdash; no priorities,
      no timeout, no release. Read
      <a href="guides/is-it-safe-to-write-to-modbus.html">the writing guide</a> before
      changing anything on live equipment.</li>
    </ul>
  </div>
</section>

<footer>
  <div class="wrap">
    <p>Register maps are re-typed from each manufacturer&rsquo;s free public documentation and
    checked against it. Brand names identify the equipment only; easymodbus.com is not
    affiliated with any manufacturer listed. Spotted an error, or want a map removed? Email
    <a href="mailto:webmaster@easymodbus.com">webmaster@easymodbus.com</a>.</p>
    <p><a href="terms.html">Terms of use</a> &middot; <a href="privacy.html">Privacy policy</a></p>
  </div>
</footer>

<script>
(function(){var p=document.getElementById('mfr-pick');if(p){p.addEventListener('change',function(){if(p.value)location.href=p.value;});}})();
</script>
</body>
</html>
"""



PRIVACY = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/svg+xml" href="icon.svg">
<title>Privacy policy &mdash; Easy Modbus</title>
<meta name="description" content="easymodbus.com privacy policy: no accounts or forms, Google Analytics only after you accept the cookie banner, browser tools that run locally.">
<link rel="canonical" href="%(base)s/privacy.html">
<meta name="robots" content="index, follow">
<meta name="theme-color" content="#14171a">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Easy Modbus">
<meta property="og:title" content="Privacy policy &mdash; Easy Modbus">
<meta property="og:description" content="easymodbus.com privacy policy: no accounts or forms, Google Analytics only after you accept the cookie banner, browser tools that run locally.">
<meta property="og:url" content="%(base)s/privacy.html">
<meta property="og:image" content="%(base)s/img/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Privacy policy &mdash; Easy Modbus">
<meta name="twitter:description" content="easymodbus.com privacy policy: no accounts or forms, Google Analytics only after you accept the cookie banner, browser tools that run locally.">
<meta name="twitter:image" content="%(base)s/img/og-image.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;800;900&family=Manrope:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet">
<style>%(css)s</style>
</head>
<body>

<header class="site">
  <a href="index.html" style="display:inline-flex;align-items:center;gap:.5rem;text-decoration:none"><img src="icon.svg" alt="" width="26" height="26" style="border-radius:6px"><span>Easy Modbus</span></a>
  <a class="muted" href="/modbus-register-maps/index.html">Register maps &rarr;</a>
</header>

<h1>Privacy policy</h1>
<p class="muted">Last updated: %(updated)s</p>

<div class="answer">
  <strong>Summary</strong>
  <p>easymodbus.com is a static website: register maps, guides and browser tools. There
  are no accounts, no sign-up and no forms, and nothing you type into the tools leaves
  your browser. The site uses <strong>Google Analytics</strong>, but only after you accept
  the cookie banner &mdash; see <a href="#website-analytics">Website analytics</a>.</p>
</div>

<h2 id="website-analytics">Website analytics</h2>
<p>easymodbus.com uses Google Analytics (GA4) to understand which pages are useful and
how visitors arrive. It is loaded with Google Consent Mode: no analytics cookie is set
and no data is sent until you choose <em>Accept</em> on the cookie banner. If you
decline, or ignore the banner, Analytics stays off. Your choice is remembered in your
browser and you can clear it any time by clearing this site's data. IP addresses are
anonymised, and no advertising or cross-site tracking signals are collected. Google's
handling of Analytics data is described in
<a href="https://policies.google.com/privacy">Google's Privacy Policy</a>.</p>

<h2>Hosting and fonts</h2>
<p>The site is served by Cloudflare. Like any web host, Cloudflare processes the
technical details of each request &mdash; your IP address, the page requested, your
browser's user-agent &mdash; to deliver the page and protect the site from abuse; see
<a href="https://www.cloudflare.com/privacypolicy/">Cloudflare's privacy policy</a>. Page
fonts are loaded from Google Fonts, which receives your IP address when it serves them.</p>

<h2>The browser tools</h2>
<p>The float decoder, the address converter and the register filters on each map run
entirely in your browser. The values you type are not sent anywhere.</p>

<h2>Downloads</h2>
<p>The CSV and JSON register-map downloads are plain static files. Downloading one does
not require or record anything beyond the ordinary request described under Hosting.</p>

<h2>Email</h2>
<p>If you email us, we receive your email address and whatever you write, and use them
only to reply. We do not add you to any list.</p>

<h2>What the site does not do</h2>
<ul>
  <li>No accounts, sign-in or registration.</li>
  <li>No advertising or cross-site tracking.</li>
  <li>No selling or sharing of your data.</li>
</ul>

<h2>Children</h2>
<p>This site is a reference for building and industrial equipment and is not directed
at children. It does not knowingly collect personal information from anyone.</p>

<h2>Changes to this policy</h2>
<p>If this policy changes, the &ldquo;last updated&rdquo; date above changes with it.</p>

<h2>Contact</h2>
<p>Questions about this policy: %(contact)s</p>

<footer>
  <p><a href="index.html">Home</a> &middot; <a href="modbus-register-maps/index.html">Register maps</a> &middot; <a href="terms.html">Terms of use</a></p>
</footer>

</body>
</html>
"""



TERMS = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/svg+xml" href="icon.svg">
<title>Terms of use &mdash; Easy Modbus</title>
<meta name="description" content="Terms of use for easymodbus.com: register-map accuracy, industrial-control safety, no warranty, and limitation of liability.">
<link rel="canonical" href="%(base)s/terms.html">
<meta name="robots" content="index, follow">
<meta name="theme-color" content="#14171a">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Easy Modbus">
<meta property="og:title" content="Terms of use &mdash; Easy Modbus">
<meta property="og:description" content="Terms of use for easymodbus.com: register-map accuracy, industrial-control safety, no warranty, and limitation of liability.">
<meta property="og:url" content="%(base)s/terms.html">
<meta property="og:image" content="%(base)s/img/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Terms of use &mdash; Easy Modbus">
<meta name="twitter:description" content="Terms of use for easymodbus.com: register-map accuracy, industrial-control safety, no warranty, and limitation of liability.">
<meta name="twitter:image" content="%(base)s/img/og-image.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;800;900&family=Manrope:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet">
<style>%(css)s</style>
</head>
<body>

<header class="site">
  <a href="index.html" style="display:inline-flex;align-items:center;gap:.5rem;text-decoration:none"><img src="icon.svg" alt="" width="26" height="26" style="border-radius:6px"><span>Easy Modbus</span></a>
  <a class="muted" href="/modbus-register-maps/index.html">Register maps &rarr;</a>
</header>

<h1>Terms of use</h1>
<p class="muted">Last updated: %(updated)s</p>

<div class="answer">
  <strong>Please read this first</strong>
  <p>These terms apply to the easymodbus.com website: its register maps, guides,
  downloads and browser tools (together, the &ldquo;site&rdquo;). By using the site you
  agree to them. The register maps describe real industrial and building equipment; the
  safety section below is the part that matters most.</p>
</div>

<h2>1. Industrial-control safety &mdash; your responsibility</h2>
<p>The register maps and guides describe how to read from and write to Modbus
equipment that controls real machinery, building services and industrial processes.
Working with control systems is inherently hazardous when it is done without a full
understanding of the equipment.</p>
<ul>
  <li><strong>Do not change a value, register, point or control logic unless you
  understand exactly what it does and what will happen when it changes.</strong>
  A Modbus write takes effect immediately, has no undo, and stays in effect until
  something else overwrites it.</li>
  <li><strong>Always consult the equipment manufacturer's documentation &mdash;
  the register/points list, control drawings and user manual &mdash; before
  reading, writing, or changing any point or logic.</strong></li>
  <li>You are responsible for correctly identifying addresses, data types,
  scaling and units, and for verifying the effect of any change on non-critical
  equipment first where possible.</li>
  <li>You are responsible for having the authority and permission to access and
  modify the equipment you connect to, and for complying with all applicable
  site rules, codes, standards and laws.</li>
  <li>Do not rely on the site for life-safety, emergency, medical, or other systems
  where a fault, an incorrect value, or a communication interruption could cause
  injury, loss of life, or significant damage.</li>
</ul>
<p>If you are not certain what you are doing, stop, and consult a qualified
controls engineer and the manufacturer before proceeding.</p>

<h2>2. Register maps: accuracy</h2>
<p>Each register map is re-typed from the manufacturer's free public documentation,
checked against it, and linked to it. Registers still vary by model, firmware,
options and configuration, and a transcription can be wrong. Treat every map as a
starting point and <strong>confirm it against the manufacturer's current document and
the live device</strong> before you rely on it, and especially before you write to
anything. If you find an error, please tell us so it can be fixed.</p>

<h2>3. Information, not advice</h2>
<p>The site's maps, guides and tools are general information. They are not
engineering, safety, or professional advice, and they are not a substitute for the
manufacturer's documentation or a qualified professional. The browser tools show
<em>possible</em> interpretations of raw values and can be wrong.</p>

<h2>4. Trademarks and sources</h2>
<p>Manufacturer and product names are used only to identify the equipment a map
describes. easymodbus.com is not affiliated with, endorsed by, or sponsored by any
manufacturer listed. The original documents remain the property of their publishers;
we link to them rather than host them. A manufacturer who would like a map removed can
ask at the address below.</p>

<h2>5. Using the content</h2>
<p>You may use the register maps, downloads and guides in your own work, including
commercial work. Please link back to the page when you quote or republish part of
it.</p>

<h2>6. No warranty</h2>
<p>The site is provided &ldquo;as is&rdquo; and &ldquo;as available&rdquo;, without
warranty of any kind, whether express, implied or statutory, to the maximum extent
permitted by law. This includes, without limitation, any implied warranties of
merchantability, fitness for a particular purpose, accuracy, and non-infringement.
We do not warrant that any register map, guide, or tool output will be correct,
complete, or safe for your equipment.</p>

<h2>7. Limitation of liability</h2>
<p>To the maximum extent permitted by applicable law, in no event will First
Impact Development, or anyone involved in creating or supplying the site, be liable
for any damages of any kind arising out of or in connection with your use of, or
inability to use, the site. This includes, without limitation, direct, indirect,
incidental, special, consequential, exemplary or punitive damages; loss of profits,
revenue, data or goodwill; and damage to, malfunction of, or downtime of any
equipment, process or property, and any resulting injury &mdash; whether based on
warranty, contract, tort (including negligence), or any other legal theory, and
whether or not we have been advised of the possibility of such damage.</p>

<h2>8. Links to other sites</h2>
<p>The site links to manufacturers' documents and other third-party sites. We do not
control them, and your use of them is subject to their own terms.</p>

<h2>9. Changes</h2>
<p>The site and these terms may change over time. The &ldquo;last updated&rdquo; date
above shows the current version.</p>

<h2>10. Contact</h2>
<p>Questions about these terms: %(contact)s</p>

<p class="muted">These terms are provided in good faith and in plain language;
they are not legal advice.</p>

<footer>
  <p><a href="index.html">Home</a> &middot; <a href="modbus-register-maps/index.html">Register maps</a> &middot; <a href="privacy.html">Privacy policy</a></p>
</footer>

</body>
</html>
"""



LLMS = """# Easy Modbus (easymodbus.com)

> A free Modbus register-map library: verified register maps for power meters,
> drives, generator controllers, solar inverters, boilers, pumps and HVAC equipment,
> each listing every register's 0-based wire address, documented address, data type,
> word order, scale, units and access, re-typed from the manufacturer's public
> document and linked to it. Published with plain-English Modbus guides for facility
> managers and building engineers, and two free browser calculators.

The register maps and guides are free to quote with attribution. Every map is also
available as CSV and JSON.
%(library)s

## Free tools

%(tools)s

## Guides

%(guides)s

## Key facts about Modbus that these guides cover

- Modbus has no discovery: devices never announce themselves, so finding them
  requires sweeping addresses.
- Modbus carries no data types, names, or units. A register is sixteen bits and
  the meaning exists only in vendor documentation.
- The same register is written as 40001, 4x00001, "register 1" and "address 0" by
  different documents. Off-by-one addressing is the most common single mistake.
- In Modbus documentation "0x" denotes the coil table, not hexadecimal.
- Values spanning two registers come in four word orders; CDAB is very common on
  power meters and drives.
- Reporting tenths in a 16-bit integer is the most widespread scaling convention.
- Writes have no undo, no timeout, and no priority system. A written value stays
  written until something overwrites it.
- An exception reply proves a device is present and reachable; only silence means
  absent.
"""



NOT_FOUND = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/svg+xml" href="icon.svg">
<title>Page not found &mdash; Easy Modbus</title>
<meta name="robots" content="noindex">
<meta name="theme-color" content="#14171a">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@800;900&family=Manrope:wght@400;600&display=swap" rel="stylesheet">
<style>
  html { color-scheme: dark; }
  body{overflow-wrap:break-word; max-width: 40rem; margin: 0 auto; padding: 6rem 1.25rem; text-align: center;
         font-family:"Manrope",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
         font-size:17px; line-height:1.7; color:#f3f5f6; background:#14171a; }
  h1 { font-family:"Archivo",sans-serif; font-weight:900; text-transform:uppercase;
       font-size:2rem; margin:0 0 .75rem; }
  a { color:#2dd4bf; font-weight:600; text-decoration:none; }
  p { color:#9aa4ad; }
</style>
</head>
<body>
  <h1>Page not found</h1>
  <p>Sorry, that page does not exist or has moved.</p>
  <p><a href="/modbus-register-maps/">Browse the Modbus register maps</a> &middot; <a href="/">Home</a></p>
</body>
</html>
"""



# Pages removed 2026-11-10 when easymodbus.com became a register-map library only.
# Cloudflare Pages applies these before serving static files. Both the clean URL
# and the old .html form are listed.
REMOVED_PAGES = [
    ("guides/how-to-use-easy-modbus", "/modbus-register-maps/"),
    ("guides/how-to-build-a-modbus-remote", "/guides/is-it-safe-to-write-to-modbus"),
    ("guides/how-to-build-a-modbus-control-panel", "/guides/is-it-safe-to-write-to-modbus"),
    ("guides/how-to-export-modbus-data", "/guides/vendor-asking-for-modbus-information"),
    ("guides/log-modbus-to-csv-on-phone", "/guides/vendor-asking-for-modbus-information"),
    ("guides/modbus-scanner-app-android", "/guides/cannot-find-modbus-devices"),
    ("guides/modbus-poll-vs-easy-modbus", "/guides/modbus-poll-alternative"),
    ("guides/modbus-poll-10-minute-limit", "/guides/modbus-poll-alternative"),
    ("pc-privacy", "/privacy"),
]
REDIRECTS = "".join("/%s %s 301\n/%s.html %s 301\n" % (old, new, old, new)
                    for old, new in REMOVED_PAGES)


def ping_indexnow(urls):
    """Tell IndexNow-consuming engines (Bing/Yandex/Seznam/Naver) to recrawl.
    Safe to call repeatedly; run it after a deploy is live."""
    payload = json.dumps({
        "host": "easymodbus.com",
        "key": INDEXNOW_KEY,
        "keyLocation": "%s/%s.txt" % (BASE_URL, INDEXNOW_KEY),
        "urlList": urls,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.indexnow.org/indexnow", data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            print("IndexNow: submitted %d URLs -> HTTP %d (200/202 = accepted)" % (len(urls), resp.status))
    except urllib.error.HTTPError as e:
        print("IndexNow: HTTP %d %s (422 = key/URL mismatch; ensure %s.txt is deployed)" % (e.code, e.reason, INDEXNOW_KEY))
    except Exception as e:  # never fail the build over a ping
        print("IndexNow: ping skipped/failed - %s" % e)


def main(ping=False):
    # Modbus register-map library (register_library.py, data in register_data/).
    lib_paths, lib_llms = register_library.build(write)

    for g in GUIDES:
        write(
            g["slug"] + ".html",
            page(
                g["slug"], g["title"], g["question"], g["answer_html"],
                g["body_html"], g["related"], g["description"],
            ),
        )

    for t in TOOLS:
        write(
            t["slug"] + ".html",
            tool_page(
                t["slug"], t["title"], t["question"], t["description"],
                t["intro_html"], t["tool_html"], t["related"],
            ),
        )

    links = "\n".join(
        '  <li><a href="%s.html">%s</a><br><span class="muted">%s</span></li>'
        % (g["slug"], g["question"], summarise(g["description"]))
        for g in GUIDES
    )
    tool_links = "\n".join(
        '  <li><a href="%s.html">%s</a><br><span class="muted">%s</span></li>'
        % (t["slug"], t["question"], summarise(t["description"]))
        for t in TOOLS
    )
    st = register_library.STATS
    cat_cells = "\n".join(
        '      <a class="cell" href="/%s"><div class="n">%02d / %d MODEL%s</div><h3>%s</h3><p>%s</p></a>'
        % (path, i, n, "" if n == 1 else "S", html_module.escape(label), html_module.escape(mfrs))
        for i, (path, label, n, mfrs) in enumerate(st["cats"], 1))
    mfr_opts = "".join('<option value="/%s">%s (%d)</option>' % (
        _to_clean_url(path), html_module.escape(name), n) for path, name, n in st["mfrs"])
    write("index.html", INDEX.replace("{{BASE}}", BASE_URL)
          .replace("{{NMODELS}}", str(st["models"])).replace("{{NMFRS}}", str(st["mfr_count"]))
          .replace("{{NREGS}}", "{:,}".format(st["registers"]))
          .replace("{{CATEGORIES}}", cat_cells).replace("{{MFR_OPTIONS}}", mfr_opts)
          .replace("{{TOOLS}}", tool_links).replace("{{GUIDES}}", links))

    write(
        "privacy.html",
        PRIVACY % {
            "base": BASE_URL,
            "css": CSS,
            "updated": "10 November 2026",
            "contact": '<a href="mailto:webmaster@easymodbus.com">webmaster@easymodbus.com</a>',
        },
    )

    write(
        "terms.html",
        TERMS % {
            "base": BASE_URL,
            "css": CSS,
            "updated": "10 November 2026",
            "contact": '<a href="mailto:webmaster@easymodbus.com">webmaster@easymodbus.com</a>',
        },
    )

    # sitemap + robots so crawlers and agents can enumerate the whole set
    urls = (["index.html", "privacy.html", "terms.html"]
            + [t["slug"] + ".html" for t in TOOLS]
            + [g["slug"] + ".html" for g in GUIDES]
            + lib_paths)
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sm.append("  <url><loc>%s/%s</loc><lastmod>%s</lastmod></url>" % (
            BASE_URL, u, register_library.LASTMOD.get(u, UPDATED)))
    sm.append("</urlset>")
    write("sitemap.xml", "\n".join(sm) + "\n")

    write("robots.txt", "User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n" % BASE_URL)

    # AdMob app-ads.txt (app publisher pub-6721099502169382). Must sit at the
    # root of the developer-website domain entered on the Play store listing.
    write("app-ads.txt", "google.com, pub-6721099502169382, DIRECT, f08c47fec0942fa0\n")

    # llms.txt: the same enumeration, for assistants that look for it.
    llm_links = "\n".join(
        "- [%s](%s/%s): %s" % (g["question"], BASE_URL, g["slug"], g["description"])
        for g in GUIDES
    )
    tool_llm_links = "\n".join(
        "- [%s](%s/%s): %s" % (t["question"], BASE_URL, t["slug"], t["description"])
        for t in TOOLS
    )
    write("llms.txt", LLMS % {"guides": llm_links, "tools": tool_llm_links,
                              "library": "\n".join(lib_llms)})

    # IndexNow key file (its contents ARE the ownership proof) + optional ping.
    write(INDEXNOW_KEY + ".txt", INDEXNOW_KEY + "\n")
    if ping:
        ping_indexnow([BASE_URL + "/" if _to_clean_url(u) == "/" else BASE_URL + "/" + _to_clean_url(u)
                       for u in urls])

    # Custom-domain and hosting files for GitHub Pages.
    write("CNAME", "easymodbus.com\n")
    write(".nojekyll", "")
    write("404.html", NOT_FOUND)
    write("_redirects", REDIRECTS)

    print()
    print("%d guides, %d pages total." % (len(GUIDES), len(urls)))
    if "REPLACE-ME" in BASE_URL:
        print("NOTE: BASE_URL is still a placeholder. Set it to the real GitHub")
        print("      Pages URL and re-run before publishing, or canonical tags,")
        print("      the sitemap and llms.txt will point at nothing.")


if __name__ == "__main__":
    main(ping="--ping" in sys.argv)
