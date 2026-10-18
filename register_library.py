"""
Modbus register-map library for easymodbus.com.

Source data lives in register_data/<manufacturer_slug>/<model_slug>.json, one file
per model, re-keyed from each manufacturer's free public Modbus documentation and
checked by an independent verifier (schema: register_data/README.md, audit:
tools_audit_registers.py). We publish the FACTS (table, address, data type, word
order, scale, units, access, enum/bit meanings) in our own tables, describe them
in our own words and link the manufacturer's document; we never re-host the PDF.

Pages generated (clean URLs; build_site.write() strips .html/index.html):
  /modbus-register-maps/                           hub: pick a manufacturer, search all models
  /modbus-register-maps/<mfr>/                     every model we have for that manufacturer
  /modbus-register-maps/equipment/<type>/          every model of one equipment type
  /modbus-register-maps/<mfr>/<model>              the register table + downloads + integration
  /modbus-register-maps/<mfr>/<model>.csv          spreadsheet CSV (every column)
  /modbus-register-maps/<mfr>/<model>-easymodbus.csv  Easy Modbus import format (app + PC)
  /modbus-register-maps/<mfr>/<model>.json         machine-readable, for tools and AI agents
  /modbus-register-maps/index.json                 catalogue of everything above

build_site.main() calls build(write) and folds the returned paths into the
sitemap, llms.txt and IndexNow ping.
"""

import csv
import glob
import html
import io
import json
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "register_data")
BASE_URL = "https://easymodbus.com"
ROOT = "modbus-register-maps"

# Bump when the library's data or pages change meaningfully.
UPDATED = "2026-10-16"
UPDATED_HUMAN = "16 October 2026"

# table -> (heading, short code, function codes, Modicon prefix, Easy Modbus app name)
TABLES = {
    "coil": ("Coil", "CO", "FC01 read / FC05, FC15 write", 0, "Coil"),
    "discrete_input": ("Discrete input", "DI", "FC02 read", 1, "Discrete Input"),
    "input_register": ("Input register", "IR", "FC04 read", 3, "Input Register"),
    "holding_register": ("Holding register", "HR", "FC03 read / FC06, FC16 write", 4, "Holding Register"),
}
TABLE_ORDER = list(TABLES)
LENGTHS = {"BIT": 1, "INT16": 1, "UINT16": 1, "BITMAP16": 1, "INT32": 2, "UINT32": 2, "FLOAT32": 2,
           "INT64": 4, "UINT64": 4, "FLOAT64": 4}
ORDER_HINT = {"ABCD": "high word first (big-endian)", "CDAB": "low word first (word-swapped)",
              "BADC": "bytes swapped in each word", "DCBA": "fully reversed (little-endian)"}
CONVENTION_TEXT = {
    "0-based": "0-based (the number printed is the address on the wire)",
    "1-based": "1-based (subtract 1 for the wire address)",
    "Modicon": "Modicon 3xxxx/4xxxx (drop the prefix, subtract 1)",
    "hex 0-based": "hexadecimal, 0-based",
    "parameter-derived": "derived from parameter numbers",
}


def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def slug_ok(s):
    return bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", s or ""))


def num(x):
    """Plain number text: 0.1 not 0.10000000000000001, 1000 not 1000.0."""
    if isinstance(x, bool) or x is None:
        return ""
    if isinstance(x, int) or (isinstance(x, float) and x.is_integer() and abs(x) < 1e12):
        return str(int(x))
    return ("%.10f" % x).rstrip("0").rstrip(".")


# ---------------------------------------------------------------------------
# Data loading + validation (the full checks live in tools_audit_registers.py)
# ---------------------------------------------------------------------------

def load_all():
    models = []
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "*", "*.json"))):
        with io.open(path, encoding="utf-8") as f:
            d = json.load(f)
        problems = validate(d, path)
        if problems:
            print("SKIP %s:\n  - %s" % (os.path.relpath(path, HERE), "\n  - ".join(problems)))
            continue
        if not d.get("verified") and not os.environ.get("MODBUS_LIB_DRAFT"):
            print("SKIP %s: not verified yet" % os.path.relpath(path, HERE))
            continue
        d["_path"] = path
        models.append(d)
    return models


def validate(d, path):
    p = []
    for k in ("manufacturer", "manufacturer_slug", "model", "model_slug", "source", "registers"):
        if not d.get(k):
            p.append("missing " + k)
    if p:
        return p
    folder = os.path.basename(os.path.dirname(path))
    stem = os.path.splitext(os.path.basename(path))[0]
    if d["manufacturer_slug"] != folder or not slug_ok(folder):
        p.append("manufacturer_slug %r doesn't match folder %r" % (d["manufacturer_slug"], folder))
    if d["model_slug"] != stem or not slug_ok(stem):
        p.append("model_slug %r doesn't match file %r" % (d["model_slug"], stem))
    if not str(d["source"].get("url", "")).startswith("http"):
        p.append("source.url missing")
    for i, r in enumerate(d["registers"]):
        if r.get("table") not in TABLES or not isinstance(r.get("address"), int) or not r.get("name"):
            p.append("register %d malformed" % i)
            break
        dt = r.get("data_type")
        if dt not in LENGTHS and dt != "STRING":
            p.append("register %d bad data_type %r" % (i, dt))
            break
        r["length"] = r.get("length") if dt == "STRING" else LENGTHS[dt]
        if r["length"] >= 2 and dt != "STRING" and r.get("word_order") not in ORDER_HINT:
            p.append("register %d (%s) has no word order" % (i, r["name"]))
            break
        if r.get("access") not in ("R", "RW", "W"):
            r["access"] = "R"
        for k in ("description", "units", "documented"):
            r[k] = ("" if r.get(k) is None else str(r.get(k))).strip()
        if not isinstance(r.get("scale"), (int, float)) or r.get("scale") == 0:
            r["scale"] = 1
        if not isinstance(r.get("offset"), (int, float)):
            r["offset"] = 0
    d["registers"].sort(key=lambda r: (TABLE_ORDER.index(r["table"]), r["address"]))
    return p


def by_manufacturer(models):
    groups = {}
    for m in models:
        groups.setdefault(m["manufacturer_slug"], []).append(m)
    for v in groups.values():
        v.sort(key=lambda m: m["model"].lower())
    return dict(sorted(groups.items(), key=lambda kv: kv[1][0]["manufacturer"].lower()))


def table_counts(regs):
    c = {}
    for r in regs:
        c[r["table"]] = c.get(r["table"], 0) + 1
    return [(t, c[t]) for t in TABLE_ORDER if t in c]


def writable_count(regs):
    return sum(1 for r in regs if r["access"] in ("RW", "W"))


# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------

def hub_path():
    return ROOT + "/index.html"


def mfr_path(mslug):
    return "%s/%s/index.html" % (ROOT, mslug)


def model_path(m, ext=".html"):
    return "%s/%s/%s%s" % (ROOT, m["manufacturer_slug"], m["model_slug"], ext)


def cat_path(cslug):
    return "%s/equipment/%s/index.html" % (ROOT, cslug)


def clean(relpath):
    """Absolute clean URL for a site-relative .html path."""
    u = re.sub(r"index\.html$", "", relpath)
    u = re.sub(r"\.html$", "", u)
    return BASE_URL + "/" + u


# ---------------------------------------------------------------------------
# Page shell ("Field" design: same tokens as the homepage, teal accent)
# ---------------------------------------------------------------------------

CSS = """
:root{color-scheme:dark;--bg:#14171a;--panel:#1d2227;--panel2:#191e22;--line:#2f363d;
  --fg:#f3f5f6;--mut:#9aa4ad;--accent:#2dd4bf;--ink:#0d0f11;--code:#101418;--ok:#5fd38d;--warn:#ffb454}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font-family:"Manrope",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  font-size:16.5px;line-height:1.65;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:0 16px}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
h1,h2,h3{font-family:"Archivo",sans-serif;letter-spacing:-.01em;line-height:1.1}
h1{font-weight:900;text-transform:uppercase;font-size:clamp(1.7rem,4.6vw,2.9rem);margin:.4rem 0 .8rem}
h1 .mfr{color:var(--accent)}
h2{font-weight:800;font-size:clamp(1.2rem,2.6vw,1.55rem);margin:2.6rem 0 .9rem}
h3{font-weight:800;font-size:1.05rem;margin:0 0 .35rem}
p{margin:0 0 1rem}
strong{color:#fff}
.mono{font-family:"IBM Plex Mono",ui-monospace,monospace}
.top{border-bottom:1px solid var(--line);background:rgba(20,23,26,.9);backdrop-filter:blur(8px);position:sticky;top:0;z-index:20}
.top .wrap{display:flex;align-items:center;gap:.65rem;height:58px}
.brand{display:inline-flex;align-items:center;gap:.55rem;color:var(--fg)!important;text-decoration:none!important}
.brand img{width:28px;height:28px;border-radius:7px;display:block}
.brand b{font-family:"Archivo",sans-serif;font-weight:900;text-transform:uppercase;letter-spacing:.02em}
.top nav{margin-left:auto;display:flex;gap:1.1rem;font-family:"IBM Plex Mono",monospace;font-size:.72rem;letter-spacing:.12em;text-transform:uppercase}
.top nav a{color:var(--mut)}
.top nav a.on{color:var(--accent)}
.crumbs{font-family:"IBM Plex Mono",monospace;font-size:.74rem;letter-spacing:.06em;color:var(--mut);margin:1.6rem 0 0;padding:0;list-style:none;display:flex;flex-wrap:wrap;gap:.35rem}
.crumbs li:not(:last-child)::after{content:"/";margin-left:.35rem;color:var(--line)}
.crumbs a{color:var(--mut)}
.eyebrow{font-family:"IBM Plex Mono",monospace;font-weight:600;font-size:.72rem;letter-spacing:.2em;text-transform:uppercase;color:var(--accent);margin:1.4rem 0 0}
.lede{font-size:1.08rem;color:#e7ebee;max-width:70ch}
.updated{color:var(--mut);font-family:"IBM Plex Mono",monospace;font-size:.74rem;letter-spacing:.06em}
.answer{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:12px;padding:1.1rem 1.3rem;margin:1.4rem 0;max-width:78ch}
.answer > b{display:block;font-family:"IBM Plex Mono",monospace;font-size:.7rem;letter-spacing:.18em;text-transform:uppercase;color:var(--accent);margin-bottom:.4rem}
.answer p:last-child{margin:0}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:12px;overflow:hidden;margin:1.4rem 0}
.facts div{background:var(--panel);padding:.85rem 1rem}
.facts dt{font-family:"IBM Plex Mono",monospace;font-size:.68rem;letter-spacing:.14em;text-transform:uppercase;color:var(--mut)}
.facts dd{margin:.2rem 0 0;font-weight:700;word-break:break-word}
.chips{display:flex;flex-wrap:wrap;gap:.45rem;margin:.6rem 0 0;padding:0;list-style:none}
.chip{font-family:"IBM Plex Mono",monospace;font-size:.76rem;border:1px solid var(--line);background:var(--panel2);border-radius:999px;padding:.25rem .7rem;color:var(--fg);cursor:pointer}
.chip b{color:var(--accent);margin-left:.3rem}
.chip[aria-pressed="true"]{border-color:var(--accent);background:rgba(45,212,191,.12)}
.dl{display:flex;flex-wrap:wrap;gap:.6rem;margin:1.2rem 0}
.btn{display:inline-flex;align-items:center;gap:.45rem;font:inherit;font-weight:700;font-size:.92rem;padding:.6rem 1rem;border-radius:9px;border:1px solid var(--line);background:var(--panel);color:var(--fg)!important;text-decoration:none!important;cursor:pointer}
.btn.primary{background:var(--accent);border-color:var(--accent);color:var(--ink)!important}
.btn small{font-family:"IBM Plex Mono",monospace;font-weight:500;font-size:.68rem;opacity:.75}
.tools{display:flex;flex-wrap:wrap;gap:.7rem;align-items:center;margin:1rem 0 .4rem}
.search{flex:1 1 260px;font:inherit;color:var(--fg);background:var(--code);border:1px solid var(--line);border-radius:9px;padding:.65rem .85rem}
.search:focus,select:focus{outline:2px solid var(--accent);outline-offset:1px}
select.pick{font:inherit;font-weight:700;color:var(--fg);background:var(--code);border:1px solid var(--line);border-radius:9px;padding:.7rem .85rem;min-width:min(100%,320px)}
.count{color:var(--mut);font-family:"IBM Plex Mono",monospace;font-size:.76rem}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px;margin:.6rem 0 1rem;background:var(--panel2)}
table.pts{border-collapse:collapse;width:100%;font-size:.88rem;min-width:980px}
table.pts th,table.pts td{text-align:left;padding:.5rem .65rem;border-bottom:1px solid var(--line);vertical-align:top}
table.pts thead th{position:sticky;top:0;background:#20262c;font-family:"IBM Plex Mono",monospace;font-size:.66rem;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);font-weight:600;white-space:nowrap}
table.pts td.t,table.pts td.i,table.pts td.f{font-family:"IBM Plex Mono",monospace;white-space:nowrap}
table.pts td.t{color:#cfe1f2}
table.pts td.i{text-align:right}
table.pts td.i small{display:block;color:var(--mut);font-size:.7rem}
table.pts td.n{font-weight:600}
table.pts td.d,table.pts td.s{color:var(--mut)}
table.pts td.s{font-size:.82rem;min-width:200px}
table.pts tr:hover td{background:rgba(255,255,255,.025)}
.acc{font-family:"IBM Plex Mono",monospace;font-size:.72rem;border-radius:5px;padding:.08rem .4rem;border:1px solid var(--line);white-space:nowrap}
.acc.RW,.acc.W{color:var(--ok);border-color:rgba(95,211,141,.45)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:1rem;margin:1rem 0;padding:0;list-style:none}
.card{display:block;background:var(--panel);border:1px solid var(--line);border-top:3px solid var(--accent);border-radius:12px;padding:1.05rem 1.1rem;color:var(--fg)!important;text-decoration:none!important;height:100%}
.card:hover{border-color:var(--accent)}
.card .k{font-family:"IBM Plex Mono",monospace;font-size:.7rem;letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}
.card h3{margin:.35rem 0 .3rem;font-size:1.08rem}
.card p{color:var(--mut);font-size:.9rem;margin:0}
.card .meta{margin-top:.6rem;font-family:"IBM Plex Mono",monospace;font-size:.72rem;color:var(--mut)}
.notes{margin:0;padding-left:1.2rem}
.notes li{margin:.35rem 0}
.callout{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:12px;padding:1rem 1.2rem;margin:1.5rem 0;max-width:78ch}
.callout p:last-child{margin:0}
.faq details{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:.8rem 1rem;margin:.6rem 0;max-width:78ch}
.faq summary{cursor:pointer;font-weight:700}
.faq details p{margin:.6rem 0 0;color:#dfe4e8}
.ibgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1rem;margin:1.2rem 0}
.ib{background:var(--panel);border:1px solid var(--line);border-top:3px solid var(--accent);border-radius:12px;padding:1rem 1.1rem}
.ib p{margin:0;color:#dfe4e8;font-size:.95rem}
.integ h3{margin-top:1.4rem}
table.pts.min{min-width:560px}
.hidden{display:none!important}
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
.toast{color:var(--ok);font-family:"IBM Plex Mono",monospace;font-size:.76rem;align-self:center}
footer{border-top:1px solid var(--line);margin-top:3.5rem;padding:2rem 0 3rem;color:var(--mut);font-size:.9rem}
footer a{color:var(--mut);text-decoration:underline}
@media (max-width:640px){.top nav{display:none}body{font-size:16px}}
"""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;800;900&family=Manrope:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet">')


def shell(relpath, title, description, h1_html, body, jsonld, crumbs, og_type="website"):
    url = clean(relpath)
    crumb_html = "".join(
        '<li><a href="%s">%s</a></li>' % (esc(href), esc(name)) if href else
        '<li aria-current="page">%s</li>' % esc(name)
        for name, href in crumbs)
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<meta name="description" content="%(desc)s">
<link rel="canonical" href="%(url)s">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
<meta name="theme-color" content="#14171a">
<link rel="icon" type="image/svg+xml" href="/icon.svg">
<meta property="og:type" content="%(ogtype)s">
<meta property="og:site_name" content="Easy Modbus">
<meta property="og:title" content="%(title)s">
<meta property="og:description" content="%(desc)s">
<meta property="og:url" content="%(url)s">
<meta property="og:image" content="%(base)s/img/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="%(title)s">
<meta name="twitter:description" content="%(desc)s">
<meta name="twitter:image" content="%(base)s/img/og-image.png">
%(fonts)s
<style>%(css)s</style>
<script type="application/ld+json">
%(jsonld)s
</script>
</head>
<body>
<div class="top"><div class="wrap">
  <a class="brand" href="/index.html"><img src="/icon.svg" alt="" width="28" height="28"><b>Easy Modbus</b></a>
  <nav aria-label="Site"><a href="/modbus-register-maps/index.html" class="on">Register maps</a><a href="/index.html#guides">Guides</a><a href="/index.html">The app</a></nav>
</div></div>
<main class="wrap">
<ol class="crumbs" aria-label="Breadcrumb">%(crumbs)s</ol>
%(h1)s
%(body)s
</main>
<footer><div class="wrap">
  <p>Register maps are re-typed from each manufacturer&rsquo;s free public documentation, checked against it a
  second time, and linked to the original. Registers vary by firmware, options and configuration &mdash; always
  confirm against the live device before you write to it. Brand names identify the equipment only; Easy Modbus is
  not affiliated with any manufacturer listed. Spotted an error, or want a map removed? Email
  <a href="mailto:Firstimpactdevelopment@gmail.com">Firstimpactdevelopment@gmail.com</a>.</p>
  <p><a href="/index.html">Easy Modbus</a> &middot; <a href="/modbus-register-maps/index.html">Register maps</a> &middot;
  <a href="/index.html#guides">Guides</a> &middot; <a href="/terms.html">Terms of use</a> &middot; <a href="/privacy.html">Privacy policy</a></p>
</div></footer>
%(script)s
</body>
</html>
""" % {
        "title": esc(title), "desc": esc(description), "url": url, "base": BASE_URL,
        "ogtype": og_type, "fonts": FONTS, "css": CSS, "jsonld": jsonld,
        "crumbs": crumb_html, "h1": h1_html, "body": body, "script": PAGE_JS,
    }


# One small script for every page: free-text filter + table chips, the
# manufacturer picker, and "Copy for Easy Modbus". Pages are fully rendered
# without it (crawlers and no-JS readers see every row).
PAGE_JS = """<script>
(function(){
  var pick=document.getElementById('mfr-pick');
  if(pick){pick.addEventListener('change',function(){if(pick.value)location.href=pick.value;});}
  document.querySelectorAll('[data-filter]').forEach(function(box){
    var scope=document.getElementById(box.getAttribute('data-filter'));if(!scope)return;
    var rows=[].slice.call(scope.querySelectorAll('[data-row]'));
    var chips=[].slice.call(document.querySelectorAll('[data-chip-for="'+scope.id+'"]'));
    var out=document.querySelector('[data-count-for="'+scope.id+'"]');
    var type='';
    function run(){
      var q=box.value.trim().toLowerCase(),n=0;
      rows.forEach(function(r){
        var ok=(!q||r.textContent.toLowerCase().indexOf(q)>=0)&&(!type||r.getAttribute('data-type')===type);
        r.classList.toggle('hidden',!ok);if(ok)n++;
      });
      if(out)out.textContent=n+' of '+rows.length+' shown';
    }
    chips.forEach(function(c){c.addEventListener('click',function(){
      var t=c.getAttribute('data-type');type=(type===t)?'':t;
      chips.forEach(function(x){x.setAttribute('aria-pressed',x.getAttribute('data-type')===type?'true':'false');});run();});});
    box.addEventListener('input',run);
  });
  var cp=document.getElementById('copy-em');
  if(cp){cp.addEventListener('click',function(){
    var msg=document.getElementById('copy-msg');
    fetch(cp.getAttribute('data-src')).then(function(r){return r.text();}).then(function(t){
      return navigator.clipboard.writeText(t);
    }).then(function(){if(msg)msg.textContent='Copied. In Easy Modbus open the device, tap ⋮, choose Import map from CSV, and paste.';},
      function(){if(msg)msg.textContent='Copy blocked by the browser. Use the download instead.';});
  });}
})();
</script>"""


def graph(*nodes):
    return json.dumps({"@context": "https://schema.org", "@graph": list(nodes)},
                      ensure_ascii=False, indent=1).replace("</", "<\\/")


def breadcrumb_ld(crumbs, last_url):
    items = []
    for i, (name, href) in enumerate(crumbs, 1):
        u = clean(href.lstrip("/")) if href else last_url
        items.append({"@type": "ListItem", "position": i, "name": name, "item": u})
    return {"@type": "BreadcrumbList", "itemListElement": items}


ORG = {"@type": "Organization", "@id": BASE_URL + "/#org", "name": "Easy Modbus",
       "url": BASE_URL + "/", "logo": BASE_URL + "/icon.svg"}


# ---------------------------------------------------------------------------
# Equipment categories (cross-manufacturer landing pages)
# ---------------------------------------------------------------------------

# (slug, plural heading, singular noun, keywords matched against equipment_type) - first match wins.
CATEGORIES = [
    ("generator-controllers", "Generator controllers", "generator controller", ["generator", "genset", "transfer switch"]),
    ("solar-inverters", "Solar & battery inverters", "inverter", ["inverter", "pv ", "solar", "battery", "energy storage"]),
    ("vfds", "Variable frequency drives", "drive", ["frequency drive", "vfd", "drive"]),
    ("power-meters", "Power & energy meters", "meter", ["meter", "power analy", "energy analy", "network analy"]),
    ("hvac-gateways", "AC & VRF gateways", "AC gateway", ["gateway", "vrf", "split"]),
    ("boilers", "Boilers & water heaters", "boiler", ["boiler", "water heater"]),
    ("pumps", "Pumps", "pump", ["pump"]),
    ("chillers-heat-pumps", "Chillers & heat pumps", "chiller / heat pump", ["chiller", "heat pump"]),
    ("hvac", "HVAC equipment", "HVAC", ["air handl", "rooftop", "thermostat", "fan coil", "hvac", "ahu", "doas"]),
    ("valves-actuators-sensors", "Valves, actuators & sensors", "valve / actuator / sensor", ["valve", "actuator", "sensor"]),
]
OTHER_CAT = ("other-equipment", "Other equipment", "device", [])


def category_of(m):
    et = (m.get("equipment_type") or "").lower() + " "
    for c in CATEGORIES:
        if any(k in et for k in c[3]):
            return c
    return OTHER_CAT


def group_by_category(models):
    order = list(CATEGORIES) + [OTHER_CAT]
    buckets = {c[0]: [] for c in order}
    for m in models:
        buckets[category_of(m)[0]].append(m)
    return [(c, sorted(buckets[c[0]], key=lambda m: (m["manufacturer"].lower(), m["model"].lower())))
            for c in order if buckets[c[0]]]


# ---------------------------------------------------------------------------
# Titles + descriptions
# ---------------------------------------------------------------------------

def mfr_short(m):
    """Manufacturer without a parenthetical owner, e.g. 'Intesis (HMS Networks)' -> 'Intesis'."""
    return re.sub(r"\s*\([^)]*\)", "", m["manufacturer"]).strip()


def short_model(m):
    """Model name trimmed for <title>: explicit short_model (or the full model when two
    titles would collide), minus parentheticals, ' - ' tails, a repeated manufacturer
    name and a trailing 'Modbus', so titles stay under 62 characters."""
    full = bool(m.get("_full_title"))
    s = m["model"] if full or not m.get("short_model") else m["short_model"]
    if not full:
        s = re.sub(r"\s*\([^)]*\)", "", s)
        s = re.split(r"\s+[-–]\s+", s)[0]
    for name in {m["manufacturer"], mfr_short(m)}:
        s = re.sub(r"^%s\s+" % re.escape(name), "", s, flags=re.I)
    s = re.sub(r"(?i)\s+modbus(\s+(rtu|tcp|map|module|gateway|interface))?$", "", s).strip()
    return s or m["model"]


def page_title(m):
    brand = mfr_short(m)
    for mm in ("%s %s" % (brand, short_model(m)), "%s %s" % (brand.split()[0], short_model(m))):
        for t in ("%s Modbus Register Map | Easy Modbus" % mm,
                  "%s Modbus Register Map" % mm,
                  "%s Modbus Registers" % mm):
            if len(t) <= 62:
                return t
    out = brand.split()[0]
    for w in short_model(m).split():
        if len(out) + len(w) + 1 > 62 - len(" Modbus Registers"):
            break
        out = (out + " " + w).strip()
    return "%s Modbus Registers" % out


def model_title(m):
    return "%s %s Modbus register map" % (m["manufacturer"], m["model"])


def fit(*candidates, limit=160):
    for s in candidates:
        if s and len(s) <= limit:
            return s
    s = [c for c in candidates if c][-1]
    return s[:limit - 3].rsplit(" ", 1)[0] + "..."


def model_desc(m):
    n = len(m["registers"])
    mm = "%s %s" % (mfr_short(m), short_model(m))
    orders = sorted({r["word_order"] for r in m["registers"] if r.get("word_order")})
    t = "/".join(TABLES[t][1] for t, _ in table_counts(m["registers"]))
    return fit(
        "%s Modbus register map: %d registers with addresses, data types, %sscaling and units, "
        "plus integration notes and a free CSV." % (mm, n, "word order, " if orders else ""),
        "%s Modbus register map: %d %s registers with data types, scaling, units and integration notes."
        % (mm, n, t),
        "%s Modbus register map: %d registers, data types, scaling and units." % (mm, n))


def source_line(m):
    s = m["source"]
    bits = [esc(s.get("title") or "Manufacturer documentation")]
    if s.get("doc_number"):
        bits.append(esc(s["doc_number"]))
    if s.get("revision_date"):
        bits.append("rev. " + esc(s["revision_date"]))
    return " &middot; ".join(bits)


# ---------------------------------------------------------------------------
# Register formatting
# ---------------------------------------------------------------------------

def modicon(r):
    one = r["address"] + 1
    prefix = TABLES[r["table"]][3]
    return ("%d%04d" if one <= 9999 else "%d%05d") % (prefix, one)


def row_id(r):
    return "r-%s-%d" % (TABLES[r["table"]][1].lower(), r["address"])


def ref_text(r):
    return "%s %d" % (TABLES[r["table"]][1], r["address"])


def type_text(r):
    dt = r["data_type"]
    if dt == "STRING":
        return "STRING[%d]" % (r["length"] * 2)
    return dt


def scale_text(r):
    if r.get("scale_factor_ref"):
        ref = r["scale_factor_ref"]
        return "&times; 10^SF (%s %s)" % (TABLES[ref["table"]][1], ref["address"])
    s = r.get("scale", 1)
    out = "" if s == 1 else "&times; " + num(s)
    if r.get("offset"):
        out += (" + " if r["offset"] > 0 else " &minus; ") + num(abs(r["offset"]))
    return out


def scale_plain(r):
    if r.get("scale_factor_ref"):
        ref = r["scale_factor_ref"]
        return "x 10^SF, SF at %s %d" % (TABLES[ref["table"]][0].lower(), ref["address"])
    return num(r.get("scale", 1))


def meanings(r):
    parts = []
    for k, label in (("values", ""), ("bits", "bit ")):
        v = r.get(k)
        if isinstance(v, dict) and v:
            keys = sorted(v, key=lambda x: (len(x), x))
            parts.append("; ".join("%s%s = %s" % (label, kk, v[kk]) for kk in keys))
    return " | ".join(parts)


def access_label(a):
    return {"R": "Read", "RW": "Read/write", "W": "Write"}[a]


def registers_table(m, tid="regs"):
    rows = []
    for r in m["registers"]:
        doc = r["documented"]
        rows.append(
            '<tr data-row data-type="%s" id="%s"><td class="t"><abbr title="%s, %s">%s</abbr></td>'
            '<td class="i">%d%s</td><td class="n">%s</td><td class="d">%s</td>'
            '<td class="f">%s</td><td class="f">%s</td><td class="f">%s</td><td>%s</td>'
            '<td><span class="acc %s">%s</span></td><td class="s">%s</td></tr>'
            % (r["table"], row_id(r), esc(TABLES[r["table"]][0]), esc(TABLES[r["table"]][2]),
               TABLES[r["table"]][1], r["address"],
               ('<small>doc %s</small>' % esc(doc)) if doc and doc != str(r["address"]) else "",
               esc(r["name"]), esc(r["description"]), esc(type_text(r)),
               esc(r.get("word_order") or "") if r["length"] >= 2 and r["data_type"] != "STRING" else "",
               scale_text(r), esc(r["units"]), r["access"], access_label(r["access"]), esc(meanings(r))))
    return ('<div class="tablewrap"><table class="pts" id="%s">'
            '<caption class="sr-only">%s</caption>'
            '<thead><tr><th scope="col">Table</th><th scope="col">Address</th><th scope="col">Name</th>'
            '<th scope="col">Description</th><th scope="col">Type</th><th scope="col">Order</th>'
            '<th scope="col">Scale</th><th scope="col">Units</th><th scope="col">Access</th>'
            '<th scope="col">Values / bits</th></tr></thead><tbody>\n%s\n</tbody></table></div>'
            % (tid, esc(model_title(m)), "\n".join(rows)))


# ---------------------------------------------------------------------------
# Integration block
# ---------------------------------------------------------------------------

def integration_of(m):
    it = m.get("integration")
    if not isinstance(it, dict):
        return None
    index = {(r["table"], r["address"]): r for r in m["registers"]}
    mins = []
    for mr in it.get("minimum_registers") or []:
        r = index.get((mr.get("table"), mr.get("address")))
        if r is None:
            print("  WARN %s %s: minimum register %r not in map" % (m["manufacturer"], m["model"], mr))
            continue
        mins.append((r, (mr.get("why") or "").strip()))

    def txt(k):
        return (it.get(k) or "").strip() or None

    def lst(k):
        v = it.get(k) or []
        if isinstance(v, str):
            v = [v]
        return [x.strip() for x in v if x and x.strip()]
    out = {"summary": txt("summary"), "minimum": mins, "enable": txt("enable"), "watchdog": txt("watchdog"),
           "quirks": lst("quirks"), "setup": lst("setup"), "gotchas": lst("gotchas")}
    if not (out["summary"] or mins or out["enable"] or out["watchdog"]):
        return None
    return out


def integration_html(m):
    it = integration_of(m)
    if not it:
        return ""
    out = ['<section class="integ" id="integration"><h2>Integration notes: %s %s</h2>'
           % (esc(m["manufacturer"]), esc(m["model"]))]
    if it["summary"]:
        out.append('<div class="answer"><b>Integration in brief</b><p>%s</p></div>' % esc(it["summary"]))
    if it["minimum"]:
        rows = "".join(
            '<tr><td class="t"><a href="#%s">%s %d</a></td><td class="n">%s</td><td class="f">%s%s</td><td>%s</td>'
            '<td><span class="acc %s">%s</span></td></tr>' % (
                row_id(r), TABLES[r["table"]][1], r["address"], esc(r["name"]), esc(type_text(r)),
                (" " + esc(r["word_order"])) if r.get("word_order") and r["length"] >= 2 else "",
                esc(why), r["access"], access_label(r["access"]))
            for r, why in it["minimum"])
        out.append('<h3>Minimum registers to map</h3><p class="count">Addresses are 0-based wire addresses. '
                   'Enough to monitor and run the unit; map more as the job needs.</p>'
                   '<div class="tablewrap"><table class="pts min"><thead><tr><th scope="col">Register</th>'
                   '<th scope="col">Name</th><th scope="col">Type</th><th scope="col">Why</th>'
                   '<th scope="col">Access</th></tr></thead><tbody>%s</tbody></table></div>' % rows)
    blocks = [("Enable Modbus control &amp; writes", it["enable"]),
              ("Communication loss &amp; watchdog", it["watchdog"])]
    cards = "".join('<div class="ib"><h3>%s</h3><p>%s</p></div>' % (h, esc(t)) for h, t in blocks if t)
    if cards:
        out.append('<div class="ibgrid">%s</div>' % cards)
    for head, key in (("Byte order &amp; addressing", "quirks"), ("Network setup", "setup"),
                      ("Watch out for", "gotchas")):
        if it[key]:
            out.append('<h3>%s</h3><ul class="notes">%s</ul>' % (head, "".join("<li>%s</li>" % esc(x) for x in it[key])))
    out.append("</section>")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Model page
# ---------------------------------------------------------------------------

def defaults_text(m):
    d = m.get("defaults") or {}
    out = []
    if d.get("baud"):
        out.append("%s baud" % d["baud"])
    if d.get("parity"):
        out.append("%s%s%s" % (d.get("data_bits") or 8, str(d["parity"])[:1].upper(), d.get("stop_bits") or 1))
    return out


def model_faq(m):
    mm = "%s %s" % (m["manufacturer"], m["model"])
    regs = m["registers"]
    n, w = len(regs), writable_count(regs)
    s = m["source"]
    a = m.get("addressing") or {}
    tc = ", ".join("%d %s%s" % (c, TABLES[t][0].lower(), "s" if c != 1 else "") for t, c in table_counts(regs))
    orders = sorted({r["word_order"] for r in regs if r.get("word_order") and r["length"] >= 2})
    qa = [
        ("What Modbus registers does the %s have?" % mm,
         "This map lists %d registers: %s. %d of them can be written. Registers vary with firmware, options "
         "and configuration, so confirm against the device." % (n, tc, w)),
        ("Are the %s Modbus addresses 0-based or 1-based?" % mm,
         "The manufacturer's document numbers registers %s. Every address on this page is the 0-based wire "
         "address you put in the request; the documented number is shown under it where it differs. %s"
         % (CONVENTION_TEXT.get(a.get("convention"), "in its own style"), a.get("note") or "")),
    ]
    if orders:
        qa.append(("What byte order does the %s use for 32-bit values?" % mm,
                   "Multi-register values in this map use %s. %s" % (
                       " and ".join("%s (%s)" % (o, ORDER_HINT[o]) for o in orders),
                       "Each register's order is in the Order column." if len(orders) > 1 else
                       "Set your client to this order for every 32/64-bit value in the table.")))
    it = integration_of(m)
    if it:
        if it["minimum"]:
            qa.append(("What are the minimum Modbus registers to integrate the %s?" % mm,
                       "Start with " + "; ".join(
                           "%s %d %s%s" % (TABLES[r["table"]][1], r["address"], r["name"],
                                           (" (%s)" % why.rstrip(".")) if why else "")
                           for r, why in it["minimum"]) + "."))
        if it["enable"]:
            qa.append(("How do I enable Modbus control of the %s?" % mm, it["enable"]))
        if it["watchdog"]:
            qa.append(("What happens when the %s loses Modbus communication?" % mm, it["watchdog"]))
    qa.append(("Where is the official %s Modbus documentation?" % mm,
               "The source is %s%s%s, published free by %s at %s." % (
                   s.get("title") or "the manufacturer's Modbus documentation",
                   (" (" + s["doc_number"] + ")") if s.get("doc_number") else "",
                   (", revision " + s["revision_date"]) if s.get("revision_date") else "",
                   m["manufacturer"], s["url"])))
    return qa


def model_page(m, siblings):
    relpath = model_path(m)
    url = clean(relpath)
    regs = m["registers"]
    n, w = len(regs), writable_count(regs)
    mfr_href = "/" + mfr_path(m["manufacturer_slug"])
    crumbs = [("Home", "/index.html"), ("Modbus register maps", "/" + hub_path()),
              (m["manufacturer"], mfr_href), (m["model"], None)]
    title = page_title(m)
    desc = model_desc(m)
    s = m["source"]
    faq = model_faq(m)
    d = m.get("defaults") or {}
    a = m.get("addressing") or {}

    chips = "".join(
        '<li><button type="button" class="chip" data-chip-for="regs" data-type="%s" aria-pressed="false" '
        'title="%s">%s<b>%d</b></button></li>' % (t, esc(TABLES[t][0]), esc(TABLES[t][0] + "s"), c)
        for t, c in table_counts(regs))

    aliases = [x for x in (m.get("aliases") or []) if x and x != m["model"]]
    cat = category_of(m)
    facts = [
        ("Manufacturer", '<a href="%s">%s</a>' % (mfr_href, esc(m["manufacturer"]))),
        ("Model", esc(m["model"])),
        ("Equipment type", '<a href="/%s">%s</a>' % (cat_path(cat[0]), esc(m.get("equipment_type") or cat[1]))),
        ("Registers", "%d (%d writable)" % (n, w)),
        ("Transport", esc(", ".join("Modbus " + t for t in m.get("transport") or [])) or "&mdash;"),
        ("Default unit ID", esc(d.get("unit_id")) if d.get("unit_id") not in (None, "") else "Not stated"),
    ]
    ser = defaults_text(m)
    if ser:
        facts.append(("Default serial", esc(", ".join(ser))))
    if d.get("tcp_port"):
        facts.append(("TCP port", esc(d["tcp_port"])))
    facts.append(("Documented addressing", esc(CONVENTION_TEXT.get(a.get("convention"), a.get("convention") or ""))))
    if m.get("default_word_order"):
        facts.append(("32-bit word order", "%s <small class=\"count\">%s</small>" % (
            esc(m["default_word_order"]), esc(ORDER_HINT.get(m["default_word_order"], "")))))
    if m.get("firmware"):
        facts.append(("Firmware", esc(m["firmware"])))
    if aliases:
        facts.append(("Also known as", esc(", ".join(aliases))))
    facts.append(("Source document", '<a href="%s" rel="nofollow noopener" target="_blank">%s</a>'
                  % (esc(s["url"]), source_line(m))))
    facts_html = '<dl class="facts">%s</dl>' % "".join(
        "<div><dt>%s</dt><dd>%s</dd></div>" % (k, v) for k, v in facts)

    notes = m.get("notes") or []
    notes_html = ""
    if notes:
        notes_html = '<h2>Notes on this map</h2><ul class="notes">%s</ul>' % "".join(
            "<li>%s</li>" % esc(x) for x in notes)

    sib = [x for x in siblings if x is not m]
    sib_html = ""
    if sib:
        sib_html = ('<h2>More %s Modbus register maps</h2><ul class="grid">%s</ul>'
                    % (esc(m["manufacturer"]), "".join(card(x) for x in sib)))

    faq_html = '<h2>Questions about the %s %s</h2><div class="faq">%s</div>' % (
        esc(m["manufacturer"]), esc(m["model"]),
        "".join("<details%s><summary>%s</summary><p>%s</p></details>"
                % (" open" if i == 0 else "", esc(q), esc(ans)) for i, (q, ans) in enumerate(faq)))

    h1 = ('<p class="eyebrow">%s &middot; Modbus register map</p>'
          '<h1><span class="mfr">%s</span> %s Modbus register map</h1>'
          '<p class="updated">Updated %s</p>' % (
              esc(m.get("equipment_type") or "Equipment"), esc(m["manufacturer"]), esc(m["model"]),
              UPDATED_HUMAN))

    base = "/" + model_path(m, "")
    n_app = len(easymodbus_rows(m))
    body = """
<div class="answer"><b>Short answer</b><p>%(summary)s</p>
<p>This page lists <strong>%(n)d Modbus registers</strong> for the %(mfr)s %(model)s &mdash; %(w)d writable &mdash;
with the table, 0-based wire address, data type, word order, scale, units and access of each, re-typed from
%(mfr)s&rsquo;s own free documentation (linked below) and checked against it.</p></div>
%(facts)s
<div class="dl">
  <button type="button" class="btn primary" id="copy-em" data-src="%(base)s-easymodbus.csv">Copy for the phone app <small>%(napp)d rows</small></button>
  <a class="btn" href="%(base)s-easymodbus.csv" download>Download Easy Modbus CSV</a>
  <a class="btn" href="%(base)s.csv" download>Download CSV <small>all columns</small></a>
  <a class="btn" href="%(base)s.json">JSON</a>
  <a class="btn" href="%(src)s" rel="nofollow noopener" target="_blank">Manufacturer PDF &#8599;</a>
  <span class="toast" id="copy-msg" role="status"></span>
</div>
<p class="count">Phone app: tap <em>Copy for the phone app</em>, open the device in Easy Modbus, then
&#8942; &rarr; <strong>Import map from CSV</strong> and paste (the phone app does not open files or links).
Easy Modbus PC: Explorer &rarr; Import, pick the downloaded Easy Modbus CSV. Addresses import as wire addresses whatever your address style is.</p>
%(integ)s
<h2 id="registers">%(mfr)s %(model)s Modbus registers</h2>
<p class="count">Address = 0-based wire address (the documented number is shown under it when it differs) &middot;
Order: ABCD = high word first, CDAB = low word first &middot; Scale: engineering value = raw &times; scale.</p>
<ul class="chips" aria-label="Filter by register table">%(chips)s</ul>
<div class="tools"><input class="search" type="search" placeholder="Filter registers &mdash; name, units, type&hellip;"
 aria-label="Filter registers" data-filter="regs"><span class="count" data-count-for="regs">%(n)d of %(n)d shown</span></div>
%(table)s
%(notes)s
<div class="callout"><p><strong>Check it against the live device.</strong> A register map tells you what the
controller <em>can</em> expose; the unit in front of you may differ by firmware or options. <a href="/index.html">Easy
Modbus</a> reads these registers from an Android phone or a Windows PC, and its datatype Analyzer shows a value
decoded every way at once, so a wrong word order or scale is obvious. New to this? Read
<a href="/guides/what-is-a-modbus-register-map.html">what a register map is</a> and
<a href="/guides/modbus-address-off-by-one.html">why addresses are off by one</a>.</p></div>
%(faq)s
%(sib)s
<p class="updated">Source: <a href="%(src)s" rel="nofollow noopener" target="_blank">%(srcline)s</a>.
Register numbers, types, scaling and units are reproduced as published; descriptions are our own.</p>
""" % {
        "summary": esc(m.get("summary") or ""), "n": n, "w": w, "napp": n_app,
        "mfr": esc(m["manufacturer"]), "model": esc(m["model"]), "facts": facts_html,
        "base": base, "src": esc(s["url"]), "chips": chips, "table": registers_table(m),
        "notes": notes_html, "faq": faq_html, "integ": integration_html(m),
        "sib": sib_html, "srcline": source_line(m),
    }

    keywords = [model_title(m), "%s %s Modbus registers" % (m["manufacturer"], m["model"]),
                "%s Modbus map" % m["manufacturer"]] + ["%s Modbus register map" % x for x in aliases]
    dataset = {
        "@type": "Dataset", "@id": url + "#dataset", "name": model_title(m),
        "description": ((m.get("summary") or "") + " " + desc).strip(),
        "url": url, "keywords": keywords, "isAccessibleForFree": True,
        "license": BASE_URL + "/terms",
        "creator": {"@id": ORG["@id"]}, "publisher": {"@id": ORG["@id"]},
        "dateModified": UPDATED,
        "isBasedOn": {"@type": "CreativeWork", "name": s.get("title") or "", "url": s["url"],
                      "author": {"@type": "Organization", "name": m["manufacturer"]}},
        "about": {"@type": "Product", "name": "%s %s" % (m["manufacturer"], m["model"]),
                  "brand": {"@type": "Brand", "name": m["manufacturer"]},
                  "category": m.get("equipment_type") or ""},
        "variableMeasured": ["Register table", "Wire address (0-based)", "Documented address", "Register name",
                             "Data type", "Word order", "Scale", "Engineering units", "Access",
                             "Enumeration / bit meanings"],
        "distribution": [
            {"@type": "DataDownload", "encodingFormat": "text/csv", "name": "Easy Modbus import CSV",
             "contentUrl": BASE_URL + base + "-easymodbus.csv"},
            {"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": BASE_URL + base + ".csv"},
            {"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": BASE_URL + base + ".json"},
        ],
        "includedInDataCatalog": {"@id": clean(hub_path()) + "#catalog"},
    }
    faq_ld = {"@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": ans}} for q, ans in faq]}
    page_ld = {"@type": "WebPage", "@id": url, "url": url, "name": title, "description": desc,
               "dateModified": UPDATED, "isPartOf": {"@id": BASE_URL + "/#site"},
               "mainEntity": {"@id": url + "#dataset"}, "publisher": {"@id": ORG["@id"]}}
    jsonld = graph(ORG, page_ld, dataset, faq_ld, breadcrumb_ld(crumbs, url))
    return shell(relpath, title, desc, h1, body, jsonld, crumbs, og_type="article")


def card(m):
    regs = m["registers"]
    return ('<li><a class="card" href="/%s" data-row><span class="k">%s</span>'
            '<h3>%s %s</h3><p>%s</p><div class="meta">%d registers &middot; %d writable &middot; %s</div>%s</a></li>'
            % (model_path(m), esc(m.get("equipment_type") or ""), esc(m["manufacturer"]), esc(m["model"]),
               esc(m.get("applies_to") or ""), len(regs), writable_count(regs),
               esc("/".join(m.get("transport") or [])),
               ('<span class="sr-only"> Also known as: %s</span>' % esc(", ".join(m["aliases"])))
               if m.get("aliases") else ""))


# ---------------------------------------------------------------------------
# Manufacturer, equipment-type and hub pages (lean by design)
# ---------------------------------------------------------------------------

def collection_ld(url, title, desc, models, about=None):
    item_list = {"@type": "ItemList", "itemListElement": [
        {"@type": "ListItem", "position": i, "url": clean(model_path(m)), "name": model_title(m)}
        for i, m in enumerate(models, 1)]}
    page_ld = {"@type": "CollectionPage", "@id": url, "url": url, "name": title, "description": desc,
               "dateModified": UPDATED, "isPartOf": {"@id": BASE_URL + "/#site"}, "mainEntity": item_list,
               "publisher": {"@id": ORG["@id"]}}
    if about:
        page_ld["about"] = about
    return page_ld


def mfr_page(mslug, models):
    name = models[0]["manufacturer"]
    relpath = mfr_path(mslug)
    url = clean(relpath)
    crumbs = [("Home", "/index.html"), ("Modbus register maps", "/" + hub_path()), (name, None)]
    total = sum(len(m["registers"]) for m in models)
    brand = mfr_short(models[0])
    title = fit("%s Modbus Register Maps | Easy Modbus" % brand, "%s Modbus Register Maps" % brand, limit=62)
    desc = fit("Free %s Modbus register maps for %d model%s including %s: addresses, data types, word order, "
               "scaling and units, with CSV downloads." % (name, len(models), "" if len(models) == 1 else "s",
                                                           ", ".join(short_model(m) for m in models[:3])),
               "Free %s Modbus register maps for %d models: addresses, data types, word order, scaling and "
               "units, with CSV downloads." % (name, len(models)))
    h1 = ('<p class="eyebrow">Manufacturer</p><h1><span class="mfr">%s</span> Modbus register maps</h1>'
          '<p class="updated">Updated %s</p>' % (esc(name), UPDATED_HUMAN))
    body = """
<p class="lede">%(nm)d %(name)s model%(s)s, %(total)s registers in all, each re-typed from %(name)s&rsquo;s
own free documentation and checked against it.</p>
<div class="tools"><input class="search" type="search" placeholder="Filter %(name)s models&hellip;"
 aria-label="Filter models" data-filter="models"><span class="count" data-count-for="models">%(nm)d of %(nm)d shown</span></div>
<ul class="grid" id="models">%(cards)s</ul>
""" % {"name": esc(name), "nm": len(models), "s": "" if len(models) == 1 else "s",
       "total": "{:,}".format(total), "cards": "".join(card(m) for m in models)}
    ld = collection_ld(url, title, desc, models, {"@type": "Brand", "name": name})
    return shell(relpath, title, desc, h1, body, graph(ORG, ld, breadcrumb_ld(crumbs, url)), crumbs)


def mfr_card(models):
    m0 = models[0]
    total = sum(len(m["registers"]) for m in models)
    names = esc(", ".join(short_model(m) for m in models[:4])) + ("&hellip;" if len(models) > 4 else "")
    return ('<li><a class="card" href="/%s" data-row><span class="k">%d model%s &middot; %s registers</span>'
            '<h3>%s</h3><p>%s</p></a></li>'
            % (mfr_path(m0["manufacturer_slug"]), len(models), "" if len(models) == 1 else "s",
               "{:,}".format(total), esc(m0["manufacturer"]), names))


def cat_page(cat, models):
    cslug, heading, noun, _ = cat
    relpath = cat_path(cslug)
    url = clean(relpath)
    crumbs = [("Home", "/index.html"), ("Modbus register maps", "/" + hub_path()), (heading, None)]
    mfrs = sorted({m["manufacturer"] for m in models})
    title = fit("%s Modbus Register Maps | Easy Modbus" % heading.replace(" & ", " and "),
                "%s Modbus Register Maps" % heading, limit=62)
    desc = fit("Free Modbus register maps for %d %s models from %s: addresses, data types, word order, scaling "
               "and CSV downloads." % (len(models), noun, ", ".join(mfrs[:4]) + (" and more" if len(mfrs) > 4 else "")),
               "Free Modbus register maps for %d %s models: addresses, data types, word order, scaling and CSV "
               "downloads." % (len(models), noun))
    h1 = ('<p class="eyebrow">Equipment type</p><h1><span class="mfr">%s</span> Modbus register maps</h1>'
          '<p class="updated">Updated %s</p>' % (esc(heading), UPDATED_HUMAN))
    body = """
<p class="lede">%(n)d %(heading_l)s register map%(s)s from %(nm)d manufacturer%(s2)s: %(mfrs)s.</p>
<div class="tools"><input class="search" type="search" placeholder="Filter %(heading_l)s&hellip;"
 aria-label="Filter models" data-filter="models"><span class="count" data-count-for="models">%(n)d of %(n)d shown</span></div>
<ul class="grid" id="models">%(cards)s</ul>
""" % {"n": len(models), "heading_l": esc(heading.lower()), "nm": len(mfrs), "mfrs": esc(", ".join(mfrs)),
       "s": "" if len(models) == 1 else "s", "s2": "" if len(mfrs) == 1 else "s",
       "cards": "".join(card(m) for m in models)}
    ld = collection_ld(url, title, desc, models)
    return shell(relpath, title, desc, h1, body, graph(ORG, ld, breadcrumb_ld(crumbs, url)), crumbs)


def cat_card(cat, models):
    mf = sorted({m["manufacturer"] for m in models})
    return ('<li><a class="card" href="/%s" data-row><span class="k">%d model%s</span><h3>%s</h3><p>%s</p></a></li>'
            % (cat_path(cat[0]), len(models), "" if len(models) == 1 else "s", esc(cat[1]),
               esc(", ".join(mf[:5])) + ("&hellip;" if len(mf) > 5 else "")))


def hub_page(groups):
    relpath = hub_path()
    url = clean(relpath)
    crumbs = [("Home", "/index.html"), ("Modbus register maps", None)]
    models = [m for g in groups.values() for m in g]
    total = sum(len(m["registers"]) for m in models)
    title = "Modbus Register Maps by Manufacturer | Easy Modbus"
    desc = fit("Free Modbus register maps for %d models from %d manufacturers, including %s. Addresses, data "
               "types, word order and scaling, with CSV downloads." % (
                   len(models), len(groups), ", ".join(g[0]["manufacturer"] for g in list(groups.values())[:3])),
               "Free Modbus register maps for %d models from %d manufacturers: addresses, data types, word order "
               "and scaling, with CSV downloads." % (len(models), len(groups)))
    options = "".join('<option value="/%s">%s (%d)</option>' % (mfr_path(s), esc(g[0]["manufacturer"]), len(g))
                      for s, g in groups.items())
    h1 = ('<p class="eyebrow">Free library</p><h1>Modbus register maps <span class="mfr">by manufacturer</span></h1>'
          '<p class="updated">Updated %s</p>' % UPDATED_HUMAN)
    body = """
<p class="lede"><strong>%(nm)d models from %(ng)d manufacturers</strong> &mdash; %(total)s registers &mdash; each with
the 0-based address, data type, word order, scale, units and access, checked against the manufacturer&rsquo;s own
document and ready to paste into Easy Modbus or download as CSV.</p>
<form class="tools" action="#" onsubmit="return false" aria-label="Choose a manufacturer">
  <label class="mono count" for="mfr-pick">Select manufacturer</label>
  <select class="pick" id="mfr-pick"><option value="">Choose a manufacturer&hellip;</option>%(options)s</select>
</form>
<h2>Manufacturers</h2>
<ul class="grid">%(mcards)s</ul>
<h2>Browse by equipment type</h2>
<ul class="grid">%(ccards)s</ul>
<h2>Search every model</h2>
<div class="tools"><input class="search" type="search" placeholder="Model, part number or equipment &mdash; e.g. PM5300, SDM630, drive, inverter&hellip;"
 aria-label="Search all models" data-filter="all"><span class="count" data-count-for="all">%(nm)d of %(nm)d shown</span></div>
<ul class="grid" id="all">%(cards)s</ul>
""" % {"nm": len(models), "ng": len(groups), "total": "{:,}".format(total), "options": options,
       "mcards": "".join(mfr_card(g) for g in groups.values()),
       "ccards": "".join(cat_card(c, ms) for c, ms in group_by_category(models)),
       "cards": "".join(card(m) for m in models)}
    catalog = {"@type": "DataCatalog", "@id": url + "#catalog", "name": "Easy Modbus register-map library",
               "url": url, "description": desc, "publisher": {"@id": ORG["@id"]},
               "dataset": [{"@id": clean(model_path(m)) + "#dataset"} for m in models]}
    item_list = {"@type": "ItemList", "itemListElement": [
        {"@type": "ListItem", "position": i, "url": clean(mfr_path(s)),
         "name": "%s Modbus register maps" % g[0]["manufacturer"]}
        for i, (s, g) in enumerate(groups.items(), 1)]}
    page_ld = {"@type": "CollectionPage", "@id": url, "url": url, "name": title, "description": desc,
               "dateModified": UPDATED, "isPartOf": {"@id": BASE_URL + "/#site"}, "mainEntity": item_list,
               "publisher": {"@id": ORG["@id"]}}
    return shell(relpath, title, desc, h1, body, graph(ORG, page_ld, catalog, breadcrumb_ld(crumbs, url)), crumbs)


# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------

def csv_text(m):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(["# %s %s Modbus register map - easymodbus.com - source: %s" %
                (m["manufacturer"], m["model"], m["source"]["url"])])
    w.writerow(["Table", "Function codes", "Wire address (0-based)", "Documented address", "Modicon", "Name",
                "Description", "Data type", "Registers", "Word order", "Scale", "Offset", "Units", "Access",
                "Values / bits"])
    for r in m["registers"]:
        w.writerow([TABLES[r["table"]][0], TABLES[r["table"]][2], r["address"], r["documented"], modicon(r),
                    r["name"], r["description"], type_text(r), r["length"],
                    r.get("word_order") or "" if r["length"] >= 2 and r["data_type"] != "STRING" else "",
                    scale_plain(r), num(r.get("offset") or 0), r["units"], access_label(r["access"]), meanings(r)])
    return "\ufeff" + buf.getvalue()   # BOM so Excel reads UTF-8 (°C etc.)


# Easy Modbus app/PC importer (CsvExporter.importCsv): header must be line 1, one record
# per line, columns matched by name. "Wire Address" is always parsed as 0-based. These
# are exactly the columns the app's own map export writes, so a round trip is lossless.
EM_HEADERS = ["Device Name", "Host", "Port", "Unit ID", "Transport",
              "Reading Name", "Table", "Wire Address", "Register Number", "Modicon",
              "Data Type", "Word Order", "Bit", "Multiplier", "Offset Value", "Units",
              "Value", "Status", "Notes"]


def em_cell(s):
    s = re.sub(r"[\r\n]+", " ", "" if s is None else str(s))
    if s[:1] in ("=", "@", "+", "-") and not re.fullmatch(r"[+-]?\d+(\.\d+)?", s):
        s = "'" + s
    if any(c in s for c in ',"'):
        s = '"' + s.replace('"', '""') + '"'
    return s


def easymodbus_rows(m):
    rows = []
    for r in m["registers"]:
        if r["data_type"] == "STRING":
            continue   # importer can't carry a string length; the app defaults to 8 registers
        dt = {"BITMAP16": "UINT16"}.get(r["data_type"], r["data_type"])
        notes = [r["description"]] if r["description"] else []
        if r.get("scale_factor_ref"):
            ref = r["scale_factor_ref"]
            notes.append("Multiply by 10^SF; SF is the INT16 at %s %d" % (TABLES[ref["table"]][4], ref["address"]))
        mm = meanings(r)
        if mm:
            notes.append(mm)
        rows.append([
            r["name"], TABLES[r["table"]][4], str(r["address"]), str(r["address"] + 1), modicon(r), dt,
            r.get("word_order") or "" if r["length"] >= 2 else "", "",
            "1" if r.get("scale_factor_ref") else num(r.get("scale", 1)), num(r.get("offset") or 0),
            r["units"], " | ".join(notes)])
    return rows


def easymodbus_csv(m):
    d = m.get("defaults") or {}
    dev = "%s %s" % (m["manufacturer"], short_model(m))
    port = str(d.get("tcp_port") or 502)
    unit = str(d.get("unit_id") if d.get("unit_id") not in (None, "") else 1)
    transport = "TCP" if "TCP" in (m.get("transport") or []) else "RTU_OVER_TCP"
    lines = [",".join(EM_HEADERS)]
    for name, table, wire, num1, mod, dt, order, bit, mult, off, units, notes in easymodbus_rows(m):
        lines.append(",".join(em_cell(x) for x in [dev, "", port, unit, transport, name, table, wire, num1, mod,
                                                    dt, order, bit, mult, off, units, "", "", notes]))
    return "\r\n".join(lines) + "\r\n"


def json_text(m):
    out = {k: v for k, v in m.items() if not k.startswith("_") and k != "verified"}
    out["page"] = clean(model_path(m))
    out["address_note"] = "address = 0-based Modbus wire (PDU) address; documented = as printed in the source."
    out["note"] = ("Re-typed from the manufacturer's public documentation (see source) and verified against it. "
                   "Registers vary by firmware and options; verify against the live device before writing.")
    return json.dumps(out, ensure_ascii=False, indent=1) + "\n"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build(write):
    """Generate every library page and download via build_site.write().
    Returns (sitemap_paths, llms_lines)."""
    models = load_all()
    out_dir = os.path.join(HERE, ROOT)
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)   # everything under ROOT is generated
    if not models:
        print("register library: no data yet, skipped")
        return [], []
    groups = by_manufacturer(models)
    seen = {}
    for m in models:
        seen.setdefault(page_title(m), []).append(m)
    for ms in seen.values():
        if len(ms) > 1:
            for m in ms:
                m["_full_title"] = True
    paths = [hub_path()]
    write(hub_path(), hub_page(groups))
    for mslug, ms in groups.items():
        write(mfr_path(mslug), mfr_page(mslug, ms))
        paths.append(mfr_path(mslug))
        for m in ms:
            write(model_path(m), model_page(m, ms))
            write(model_path(m, ".csv"), csv_text(m))
            write(model_path(m, "-easymodbus.csv"), easymodbus_csv(m))
            write(model_path(m, ".json"), json_text(m))
            paths.append(model_path(m))
    cats = group_by_category(models)
    for c, ms in cats:
        write(cat_path(c[0]), cat_page(c, ms))
        paths.append(cat_path(c[0]))
    catalogue = {
        "name": "Easy Modbus register-map library", "url": clean(hub_path()), "updated": UPDATED,
        "address_note": "All addresses are 0-based Modbus wire addresses.",
        "models": [{
            "manufacturer": m["manufacturer"], "model": m["model"], "aliases": m.get("aliases") or [],
            "equipment_type": m.get("equipment_type"), "transport": m.get("transport") or [],
            "registers": len(m["registers"]), "writable": writable_count(m["registers"]),
            "page": clean(model_path(m)), "csv": BASE_URL + "/" + model_path(m, ".csv"),
            "easymodbus_csv": BASE_URL + "/" + model_path(m, "-easymodbus.csv"),
            "json": BASE_URL + "/" + model_path(m, ".json"), "source": m["source"]["url"]}
            for g in groups.values() for m in g]}
    write(ROOT + "/index.json", json.dumps(catalogue, ensure_ascii=False, indent=1) + "\n")

    llms = ["", "## Modbus register maps (free library, by manufacturer)",
            "Every map gives the 0-based wire address, documented address, data type, word order, scale, units "
            "and access for each register, verified against the manufacturer's public document.",
            "- [Library home](%s)" % clean(hub_path()),
            "- [Machine-readable catalogue](%s/%s/index.json)" % (BASE_URL, ROOT)]
    for c, ms in cats:
        llms.append("- [%s Modbus register maps](%s): %d models" % (c[1], clean(cat_path(c[0])), len(ms)))
    for mslug, ms in groups.items():
        llms.append("- [%s Modbus register maps](%s)" % (ms[0]["manufacturer"], clean(mfr_path(mslug))))
        for m in ms:
            llms.append("  - [%s](%s): %d registers; JSON %s" % (
                model_title(m), clean(model_path(m)), len(m["registers"]), BASE_URL + "/" + model_path(m, ".json")))
    print("register library: %d manufacturers, %d models, %d registers" % (
        len(groups), len(models), sum(len(m["registers"]) for m in models)))
    return paths, llms
