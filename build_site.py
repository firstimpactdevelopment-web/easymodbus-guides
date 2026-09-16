#!/usr/bin/env python3
"""
Generates the Easy Modbus public site (GitHub Pages).

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
import os

BASE_URL = "https://easymodbus.com"

HERE = os.path.dirname(os.path.abspath(__file__))

CSS = """
  :root { color-scheme: light dark; --fg:#1a1a1a; --bg:#fff; --muted:#5a5a5a;
          --accent:#00695C; --box:#e8f4f1; --line:#bfe0d9; --code:#f0f0f0; }
  @media (prefers-color-scheme: dark) {
    :root { --fg:#e6e6e6; --bg:#121212; --muted:#a5a5a5; --accent:#5ec8b4;
            --box:#10231f; --line:#23443d; --code:#262626; }
  }
  * { box-sizing: border-box; }
  body { max-width: 48rem; margin: 0 auto; padding: 2rem 1.25rem 5rem;
         font: 16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
         Helvetica, Arial, sans-serif; color: var(--fg); background: var(--bg); }
  header.site { display:flex; align-items:center; gap:.6rem; padding-bottom:1.5rem;
                border-bottom:1px solid var(--line); margin-bottom:2rem;
                flex-wrap:wrap; }
  header.site a { color: var(--accent); text-decoration: none; font-weight: 600; }
  h1 { font-size: 1.85rem; line-height: 1.25; margin: 0 0 .75rem; }
  h2 { font-size: 1.25rem; margin-top: 2.4rem; }
  h3 { font-size: 1.05rem; margin-top: 1.8rem; }
  a { color: var(--accent); }
  .answer { background: var(--box); border: 1px solid var(--line);
            border-radius: 10px; padding: 1rem 1.15rem; margin: 1.25rem 0 2rem; }
  .answer strong { display:block; margin-bottom:.35rem; text-transform:uppercase;
                   font-size:.75rem; letter-spacing:.08em; color: var(--muted); }
  .answer p:last-child { margin-bottom: 0; }
  code { background: var(--code); padding: .1rem .35rem; border-radius: 4px; font-size: .9em; }
  pre { background: var(--code); padding: 1rem; border-radius: 8px; overflow-x: auto; }
  pre code { background: none; padding: 0; }
  table { border-collapse: collapse; width: 100%; margin: 1.25rem 0;
          display:block; overflow-x:auto; }
  th, td { text-align: left; padding: .5rem .7rem; border-bottom: 1px solid var(--line);
           vertical-align: top; }
  th { font-size: .85rem; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }
  ul, ol { padding-left: 1.3rem; }
  li { margin: .4rem 0; }
  .muted { color: var(--muted); font-size: .92rem; }
  .callout { border-left: 3px solid var(--accent); padding: .25rem 0 .25rem 1rem;
             margin: 1.5rem 0; }
  nav.more { margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--line); }
  nav.more ul { list-style: none; padding: 0; }
  nav.more li { margin: .5rem 0; }
  footer { margin-top: 3.5rem; padding-top: 1.5rem; border-top: 1px solid var(--line);
           color: var(--muted); font-size: .9rem; }
  figure.shot { margin: 1.6rem 0; text-align: center; }
  figure.shot img { max-width: 300px; width: 100%; height: auto; border: 1px solid var(--line);
                    border-radius: 14px; box-shadow: 0 2px 12px rgba(0,0,0,.14); }
  figure.shot figcaption { color: var(--muted); font-size: .88rem; margin-top: .55rem; }
  .shots { display: flex; flex-wrap: wrap; gap: 1.5rem; justify-content: center;
           align-items: flex-start; margin: 1.6rem 0; }
  .shots figure.shot { margin: 0; flex: 0 1 300px; }
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
  "@type": "FAQPage",
  "mainEntity": [{
    "@type": "Question",
    "name": %s,
    "acceptedAnswer": { "@type": "Answer", "text": %s }
  }]
}""" % (
        jstr(question),
        jstr(strip_tags(answer_html)),
    )

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
<meta name="theme-color" content="#00695C">
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
<style>%(css)s</style>
<script type="application/ld+json">
%(jsonld)s
</script>
</head>
<body>

<header class="site">
  <a href="%(prefix)sindex.html" style="display:inline-flex;align-items:center;gap:.5rem;text-decoration:none"><img src="icon.svg" alt="" width="26" height="26" style="border-radius:6px"><span>Easy Modbus</span></a>
  <span class="muted">&middot; plain-English Modbus reference</span>
</header>

<article>
  <h1>%(question)s</h1>

  <div class="answer">
    <strong>Short answer</strong>
    %(answer)s
  </div>

%(body)s
</article>%(rel)s

<footer>
  <p>Published alongside <a href="%(prefix)sindex.html">Easy Modbus</a>, a free
  Android app that finds Modbus TCP equipment on a network, helps you work out
  what its registers mean, and exports the result as a CSV.</p>
  <p><a href="%(prefix)sprivacy.html">Privacy policy</a></p>
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


def write(relpath, content):
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
    description="Modbus is a simple, very old industrial protocol for reading numbers out of equipment and writing numbers into it. Here is what it is, what it is not, and why it is confusing.",
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
    description="A Modbus register map is the document that says what each numbered register in a device means: its address, data type, scaling and units. Here is what one contains and how to read it.",
    answer_html="""<p>A Modbus register map &mdash; also called a register list,
    address list, point list, or Modbus table &mdash; is the document that says
    what each numbered slot inside a piece of equipment actually means. A row of it
    says something like &ldquo;holding register 40007, 16-bit signed, multiply by
    0.1, degrees Fahrenheit, leaving water temperature&rdquo;. Without it, a Modbus
    device is a list of meaningless numbers; the protocol itself carries no names,
    no units and no data types. It is the single most important document in any
    Modbus integration, and it comes from the equipment manufacturer.</p>""",
    body_html="""
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
    description="Four ways to get a Modbus register map: ask the manufacturer, find the installation manual, ask your controls contractor, or read the device and work backwards. Plus what to do when none of them work.",
    answer_html="""<p>Four routes, easiest first: search the manufacturer's site for
    the model number plus &ldquo;Modbus&rdquo;, look in the installation or
    integration manual rather than the user manual, ask your controls contractor
    for the submittal documents, or connect to the device and work backwards from
    the values it reports. The last one sounds hardest but is often fastest,
    because it is the only method that does not depend on someone else answering an
    email.</p>""",
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

  <h2>Doing this from a phone</h2>
  <p><a href="../index.html">Easy Modbus</a> is built for exactly this job. It
  sweeps the network for equipment, reads blocks of registers and shows them in hex
  and decimal, and for each one offers the plausible interpretations with the
  reasoning &mdash; &ldquo;12.75 as a 32-bit float with the words swapped, which is
  a sensible engineering magnitude&rdquo;. When a number looks right, you name it
  and the app remembers the whole interpretation, so nobody has to work it out
  again. The result exports as a CSV, which is how an undocumented device ends up
  documented.</p>

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
    title="Why is my Modbus address off by one? 40001 vs 1 vs 0 | Easy Modbus",
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

  <p><a href="../index.html">Easy Modbus</a> sidesteps the problem: type the
  address however your manual writes it &mdash; <code>40007</code>,
  <code>4x00007</code> or <code>6</code> &mdash; and it tells you how it read it
  and which register that actually is, before you save anything.</p>
""",
    related=[
        ("guides/modbus-value-wrong-scaling-byte-order", "Why does my Modbus value look wrong?"),
        ("guides/what-is-a-modbus-register-map", "What is a Modbus register map?"),
        ("guides/modbus-function-codes-explained", "Modbus function codes in plain English"),
    ],
))

GUIDES.append(dict(
    slug="guides/modbus-value-wrong-scaling-byte-order",
    title="Why does my Modbus value look wrong? | Easy Modbus",
    question="Why does my Modbus value look wrong?",
    description="A Modbus value that is ten times too big, negative when it should not be, or wild nonsense is almost always scaling, signedness, or word order. Here is how to tell which.",
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
  <p><a href="../index.html">Easy Modbus</a> does the arithmetic for you: it shows
  the raw registers in hex and binary, lists every plausible interpretation with
  the reasoning, and warns when a value is outside the range the quantity can
  physically have &mdash; a humidity of 452% being the obvious case.</p>
""",
    related=[
        ("guides/modbus-address-off-by-one", "Why is my Modbus address off by one?"),
        ("guides/what-is-a-modbus-register-map", "What is a Modbus register map?"),
        ("guides/how-to-find-modbus-register-map", "How do I find my Modbus register map?"),
    ],
))

GUIDES.append(dict(
    slug="guides/cannot-find-modbus-devices",
    title="Why can't I find my Modbus devices on the network? | Easy Modbus",
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
    title="Modbus TCP, Modbus RTU or RS-485 — which do I have? | Easy Modbus",
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
  <p><a href="../index.html">Easy Modbus</a> has a <em>Test connection</em> action
  that tries both framings and tells you which one answered, then offers to switch
  the device over. This one problem is the reason that feature exists.</p>
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
    title="What is a Modbus unit ID or slave ID? | Easy Modbus",
    question="What is a Modbus unit ID or slave ID?",
    description="A Modbus unit ID says which device on a shared connection you are talking to. Here is what it does, what to do when you don't know it, and why the wrong one looks like a dead device.",
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

  <p><a href="../index.html">Easy Modbus</a> has a <em>Find unit IDs</em> action
  that does this with a progress display and a cancel button, then offers to add
  each one it found as its own device.</p>

  <h2>Special values</h2>
  <ul>
    <li><strong>0</strong> is a broadcast address in the specification: every device
    acts on the command and none replies. Some gateways also use 0 to mean
    &ldquo;whatever is there&rdquo;. Not something to rely on.</li>
    <li><strong>255</strong> is used by some Modbus TCP devices to mean &ldquo;this
    device, no serial side involved&rdquo;. Worth trying if 1 gets nothing.</li>
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
    title="Modbus function codes explained in plain English | Easy Modbus",
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
    description="Reading Modbus is harmless. Writing has no undo, no timeout and no priority system — a written value stays written. Here is what to check before changing anything on live equipment.",
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

  <h2>How Easy Modbus handles this</h2>
  <p><a href="../index.html">Easy Modbus</a> is read-only until you deliberately
  turn write mode on, and it turns itself off again every time the app starts. When
  it is on:</p>
  <ul>
    <li>Every write is confirmed against a summary showing the old value, the new
    value, and which register on which device.</li>
    <li>The app remembers what each register said the first time it saw it, and
    offers a <em>Put It Back</em> action &mdash; the closest honest equivalent to a
    release that Modbus permits.</li>
    <li>Each reading can carry a minimum and maximum, so a fat-fingered setpoint is
    refused before it is sent.</li>
    <li>Every write is read back, and a value that came back different is reported
    rather than assumed.</li>
    <li>Every write and failure is logged for the session.</li>
  </ul>
  <p>None of that makes writing safe. It makes it deliberate, which is the most any
  tool can honestly offer on a protocol with no undo.</p>
""",
    related=[
        ("guides/modbus-function-codes-explained", "Modbus function codes in plain English"),
        ("guides/modbus-vs-bacnet", "What is the difference between Modbus and BACnet?"),
        ("guides/what-is-modbus", "What is Modbus?"),
    ],
))

GUIDES.append(dict(
    slug="guides/vendor-asking-for-modbus-information",
    title="A vendor asked for my Modbus information — what do I send? | Easy Modbus",
    question="A vendor asked for my Modbus information — what do I send?",
    description="Exactly what to send when an integrator, analytics provider or contractor asks for your Modbus details: network access, addressing, register maps and a live export.",
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
  <p><a href="../index.html">Easy Modbus</a> produces this directly: it exports
  device name, IP, port, unit ID, framing, reading name, table, the address in all
  three conventions, data type, word order, multiplier, units, and the live value.
  That is a complete and self-explanatory handover document.</p>

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
    title="What is the difference between Modbus and BACnet? | Easy Modbus",
    question="What is the difference between Modbus and BACnet?",
    description="Modbus sends numbered sixteen-bit values and explains nothing. BACnet describes itself: names, units and object lists. Here is what that means for anyone integrating either.",
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
  publishes <strong>Easy BACnet</strong>, which discovers BACnet/IP devices, reads
  their point lists, and exports them the same way.</p>
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
    title="Why is my Modbus reading slow or unreliable? | Easy Modbus",
    question="Why is my Modbus reading slow or unreliable?",
    description="Modbus reads that are slow, intermittent, or occasionally return the wrong value: block sizes, serial turnaround, connection limits, polling collisions and stale replies.",
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
  <p>All four of the first three settings are adjustable per device in
  <a href="../index.html">Easy Modbus</a>, which also groups nearby readings into
  single block requests automatically.</p>
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


# ---------------------------------------------------------------------------
# How-to guides for the app itself (added 2026-09-15)
# ---------------------------------------------------------------------------

GUIDES.append(dict(
    slug="guides/how-to-use-easy-modbus",
    title="How to use Easy Modbus to read a device | Easy Modbus",
    question="How do I use Easy Modbus to read values from a Modbus device?",
    description="Step by step: find or add the device, test the connection, add your first reading with the Easy wizard, and export the register map with live values.",
    answer_html="""<p>Connect your phone to the same network as the equipment,
    open Easy Modbus and either tap <strong>Find devices</strong> to sweep the
    network or add the device by typing its IP address. Test the connection,
    then add a reading: in Easy mode the app asks what kind of value it is
    &mdash; a temperature, a kilowatt figure, an on/off &mdash; and picks the
    data type, scaling and units for you, reads it straight away, and warns you
    if the answer is not plausible. Name it and it is saved. Once you have the
    readings you want, <strong>Export</strong> hands you a CSV with live
    values.</p>""",
    body_html="""
  <h2>The thing to understand first</h2>
  <p>A Modbus device will tell you the contents of register 7 and will never
  tell you what register 7 <em>is</em>. Unlike BACnet, there is no list to ask
  for. So most of what Easy Modbus does is help you build that list yourself
  &mdash; and then remember it, so nobody has to work it out twice. See
  <a href="what-is-a-modbus-register-map.html">what a Modbus register map is</a>.</p>

  <h2>Step 1 &mdash; Get on the network</h2>
  <p>Join the building's Wi-Fi or plug the phone into the controls network with
  a USB-Ethernet adapter. Modbus TCP normally uses port 502; if the equipment
  has an Ethernet socket that is almost certainly what it speaks. Serial
  equipment behind a gateway box is covered below.</p>

  <h2>Step 2 &mdash; Find or add the device</h2>
  <ul>
    <li><strong>Find devices</strong> sweeps your local subnet for anything
    answering on port 502. The app tells you first that this is a port scan of
    someone's network, because it is; on a customer site, ask before you tap.
    A typical /24 takes a few seconds.</li>
    <li><strong>Add by address</strong> when you already know the IP, or when the
    equipment is on another subnet the sweep cannot reach. This is the normal
    route in practice.</li>
  </ul>
  <figure class="shot">
    <img src="../img/app-devices.png" alt="Easy Modbus device list showing saved Modbus devices with their addresses and unit IDs" loading="lazy">
    <figcaption>Your saved devices. Tap <strong>Find devices</strong> to sweep the network, or the + button to add one by address.</figcaption>
  </figure>
  <p>Then <strong>Test connection</strong>. The app tries plain Modbus TCP and
  Modbus RTU-over-TCP and tells you which one answered. This matters because a
  serial gateway that needs RTU framing looks <em>exactly</em> like a device
  that is switched off. An error reply counts as success here &mdash; an
  exception from the device proves something is listening. Only silence means
  absent. See <a href="cannot-find-modbus-devices.html">cannot find Modbus
  devices</a>.</p>
  <p>If the device is a gateway with several units behind it, <strong>Find unit
  IDs</strong> sweeps a range of unit IDs and offers to add each one that
  answers. See <a href="modbus-unit-id-slave-id.html">Modbus unit IDs</a>.</p>

  <h2>Step 3 &mdash; Add a reading (Easy mode)</h2>
  <p>Open the device and add a reading. Easy mode asks <strong>what kind of
  reading is it?</strong> &mdash; temperature, humidity, pressure, power,
  energy, a count, an on/off status &mdash; and picks the data type, word
  order, multiplier and units that are usual for that quantity. You give it the
  register address, typed however your manual writes it (40007, 4x0007,
  "register 7", "address 6" all mean the same thing; the app shows you how it
  read it &mdash; see <a href="modbus-address-off-by-one.html">why the address
  is off by one</a>).</p>
  <p>The app reads the register immediately and shows the value. If the answer
  is not plausible for that kind of quantity &mdash; a humidity of 452%, a
  room at 1,847 degrees &mdash; it says so, because that means the scaling or
  word order is wrong, not the sensor. Adjust and read again. When it looks
  right, name the reading and it is saved.</p>
  <figure class="shot">
    <img src="../img/app-reading-detail.png" alt="A saved reading in Easy Modbus showing its decoded value, address, data type, scaling and units" loading="lazy">
    <figcaption>A saved reading, decoded with its data type, word order, scaling and units &mdash; and read back live.</figcaption>
  </figure>
  <div class="callout">
  <p>That saved reading &mdash; address, type, word order, scaling, units, name
  &mdash; is the product. It is the register map the vendor never gave you,
  built one row at a time, and it is there next visit.</p>
  </div>

  <h2>When you do not know what a register is</h2>
  <p>Switch to <strong>Pro mode</strong> (in Settings) and open the
  <strong>register browser</strong>. Read a block and the app shows each
  register in hex and decimal alongside its best guesses: "12.75 as a 32-bit
  float, words swapped", "a counter", "packed text", each with the reasoning.
  A wrong guess is visibly wrong. See
  <a href="modbus-value-wrong-scaling-byte-order.html">why the value looks
  wrong</a>.</p>
  <div class="shots">
    <figure class="shot">
      <img src="../img/app-register-browser.png" alt="Easy Modbus Pro-mode register browser listing raw registers in hex and decimal" loading="lazy">
      <figcaption>The Pro-mode register browser: every register in hex and decimal.</figcaption>
    </figure>
    <figure class="shot">
      <img src="../img/app-analyzer.png" alt="Easy Modbus showing ranked interpretations of a register such as a word-swapped 32-bit float, with reasoning" loading="lazy">
      <figcaption>&ldquo;What could this be?&rdquo; ranks each interpretation and explains why.</figcaption>
    </figure>
  </div>

  <h2>Step 4 &mdash; Read them all, and export</h2>
  <p>The device's reading list refreshes every saved reading in one tap,
  grouping neighbouring registers into as few requests as the equipment
  allows. <strong>Export</strong> produces a CSV of the whole map with the live
  values and hands it to your email app; you choose who gets it. If a vendor
  gives you a CSV register map, <strong>Import</strong> reads it in rather than
  making you type forty rows. See
  <a href="vendor-asking-for-modbus-information.html">a vendor asked for my
  Modbus information</a>.</p>
  <figure class="shot">
    <img src="../img/app-readings.png" alt="Easy Modbus reading list showing several named readings with their live values and units" loading="lazy">
    <figcaption>The device's reading list &mdash; your register map &mdash; refreshed in one tap, ready to export.</figcaption>
  </figure>

  <h2>Things worth knowing</h2>
  <ul>
    <li><strong>Reading cannot change anything.</strong> Writing is a separate
    mode that is off by default &mdash; see
    <a href="how-to-write-to-a-modbus-register.html">how to write to a
    register</a>.</li>
    <li><strong>Nothing leaves the phone</strong> except a CSV you export
    yourself. No account, no server.</li>
    <li><strong>Pro mode changes what you see, not what is sent.</strong> The
    same requests go on the wire either way; Pro just stops hiding the hex,
    function codes, per-device timeouts and the frame log.</li>
  </ul>
""",
    related=[
        ("guides/how-to-write-to-a-modbus-register", "How do I write to a Modbus register with Easy Modbus, and put it back?"),
        ("guides/how-to-build-a-modbus-remote", "How do I build a custom remote in Easy Modbus?"),
        ("guides/what-is-a-modbus-register-map", "What is a Modbus register map?"),
        ("guides/cannot-find-modbus-devices", "Why can't I find my Modbus devices?"),
    ],
))

GUIDES.append(dict(
    slug="guides/how-to-write-to-a-modbus-register",
    title="How to write to a Modbus register with Easy Modbus, and put it back | Easy Modbus",
    question="How do I write to a Modbus register with Easy Modbus, and put it back afterwards?",
    description="Turning on write mode, setting limits, confirming the write, and using Put It Back to restore what the register said before you touched it. Modbus has no undo; this is the closest thing.",
    answer_html="""<p>Turn on <strong>Write mode</strong> from the menu and accept
    the warning. Open the reading, choose to change its value, enter the new
    one, and confirm against the summary. The app writes it, reads it back and
    logs it. When you are done, use <strong>Put It Back</strong>: the app
    remembered what the register said the first time it saw it this session,
    and offers to write that value again. Modbus has no priority levels, no
    release and no timeout &mdash; whatever you write simply <em>is</em> the
    value until something overwrites it &mdash; so Put It Back is the only undo
    you get.</p>""",
    body_html="""
  <h2>Why writing to Modbus deserves more care than BACnet</h2>
  <p>BACnet keeps a priority array: your override sits in a slot, and releasing
  the slot hands control back. Modbus has nothing of the kind. A holding
  register is a box with a number in it. Write 55 and it contains 55, full
  stop, until the equipment's own logic or another system writes something
  else &mdash; and many devices' logic never will. Read
  <a href="is-it-safe-to-write-to-modbus.html">is it safe to write to a Modbus
  register?</a> before touching anything on live plant.</p>

  <h2>Step 1 &mdash; Turn on write mode</h2>
  <p>Write mode is off every time the app starts and is not remembered. Open the
  menu, tap <strong>Write mode</strong>, read the warning and accept it. Until
  then no screen in the app offers a write.</p>
  <figure class="shot">
    <img src="../img/app-write-warning.png" alt="Easy Modbus write-mode warning dialog explaining that writes have no undo, before enabling writing" loading="lazy">
    <figcaption>Write mode is off at every launch. You accept this warning before any write is possible.</figcaption>
  </figure>

  <h2>Step 2 &mdash; Set limits, if you can</h2>
  <p>A reading can carry a minimum and maximum. Set them on anything you are
  going to write to &mdash; a setpoint that should live between 60 and 80, a
  speed reference that must stay under 100%. The app refuses a write outside
  those bounds before it gets anywhere near the wire. A typo becomes a message
  instead of a chiller trip.</p>

  <h2>Step 3 &mdash; Write</h2>
  <p>Open the reading and choose to change its value. Enter the new value in the
  same units the reading displays &mdash; the app applies the reading's
  multiplier and word order to produce the raw register contents, so you type
  <em>72.5</em>, not <em>725</em>. For an on/off coil you pick the state.</p>
  <p>Confirm against the summary: the device, the register, the current value,
  the new value, and the safety wording. The app then writes, waits for the
  device to acknowledge, and <strong>reads the register back</strong> so what
  is on screen is what the equipment actually holds, not what you asked for.
  A refusal comes back with the device's exception in plain words.</p>
  <figure class="shot">
    <img src="../img/app-write-confirm.png" alt="Easy Modbus write confirmation summary showing device, register, current value and new value before writing" loading="lazy">
    <figcaption>Every write is confirmed against a summary &mdash; device, register, current and new value &mdash; then read back.</figcaption>
  </figure>

  <h2>Step 4 &mdash; Put It Back</h2>
  <p>The first time the app reads a register in a session it remembers the
  value. <strong>Put It Back</strong> offers to write that value again. Use it
  before you leave on anything you changed for a test. It is not a true undo
  &mdash; if the equipment's own logic changed the register in between, "back"
  means back to what <em>you</em> found, not to what would be there had you
  never visited &mdash; but it is the closest Modbus allows.</p>
  <div class="callout">
  <p>If you overrode something to prove a point, put it back before you leave
  site. Nobody else can see that you did it, and nothing will time it out.</p>
  </div>

  <h2>Readings you cannot write</h2>
  <ul>
    <li><strong>Input registers and discrete inputs</strong> are read-only by
    definition &mdash; they report what the equipment measures.</li>
    <li><strong>Text readings</strong> are not offered a write; a packed-ASCII
    string in holding registers is nearly always a name or a serial number, and
    changing it does nothing useful.</li>
    <li>Some <strong>holding registers</strong> are read-only in practice; the
    device will answer your write with an <em>illegal data address</em> or
    <em>illegal function</em> exception, which the app shows you.</li>
  </ul>
""",
    related=[
        ("guides/is-it-safe-to-write-to-modbus", "Is it safe to write to a Modbus register?"),
        ("guides/how-to-use-easy-modbus", "How do I use Easy Modbus to read a device?"),
        ("guides/how-to-build-a-modbus-remote", "How do I build a custom remote in Easy Modbus?"),
        ("guides/modbus-function-codes-explained", "Modbus function codes explained"),
    ],
))

GUIDES.append(dict(
    slug="guides/how-to-build-a-modbus-remote",
    title="How to build a custom remote in Easy Modbus | Easy Modbus",
    question="How do I build a custom remote for a Modbus device in Easy Modbus?",
    description="Build a drag-and-drop control screen for one drive, meter or controller from readings you have already saved: setpoint arrows, on/off switches, readouts and a restore button, sized for gloves.",
    answer_html="""<p>Open a device, tap the menu and choose <strong>Custom
    Remote</strong>, then <strong>Edit</strong> and <strong>Add Control</strong>.
    Pick one of the device's saved readings, choose what kind of control it
    should be &mdash; a readout, a setpoint with minus and plus, an on/off
    toggle, a button, a multi-state picker, or a <em>Restore</em> button that
    puts the register back to what it was &mdash; and it appears on a grid.
    Drag to arrange, tap to rename or recolour, tap <strong>Done</strong>. The
    remote is free and it stays.</p>""",
    body_html="""
  <h2>Build the readings first</h2>
  <p>A remote's controls are made from the device's <strong>saved
  readings</strong> &mdash; the ones you named in Easy mode or the browser. If
  the reading does not exist yet, add it first (see
  <a href="how-to-use-easy-modbus.html">how to use Easy Modbus</a>). A control
  keeps a copy of its reading's settings, so editing the reading later updates
  the control, and deleting the reading does not break it.</p>

  <h2>Adding and arranging</h2>
  <p>Open the device, menu &rarr; <strong>Custom Remote</strong>, then
  <strong>Edit</strong>, then <strong>Add Control</strong>. Choose the reading,
  then the kind of control:</p>
  <table>
    <tr><th>Control</th><th>What it does</th><th>Use it for</th></tr>
    <tr><td>Readout</td><td>Shows the live value. Never writes.</td><td>Leaving water temp, kW, status.</td></tr>
    <tr><td>Setpoint</td><td>Minus, value, plus. Tap the value to type one.</td><td>A setpoint or speed reference.</td></tr>
    <tr><td>Toggle</td><td>Tap to flip on/off.</td><td>A coil: run enable, remote start.</td></tr>
    <tr><td>Button</td><td>Writes one fixed value when tapped.</td><td>A reset, a fixed mode.</td></tr>
    <tr><td>Multi-state</td><td>Tap to pick from named states.</td><td>Off/Hand/Auto, a mode register.</td></tr>
    <tr><td>Restore</td><td>Writes back what the register held when you arrived.</td><td>Put one beside every control that writes.</td></tr>
  </table>
  <p>Controls snap to a four-column grid. <strong>Drag</strong> to move one (it
  will not land on another); <strong>tap</strong> to rename it, widen it, change
  its step size, states, colour or card style, or delete it. Nothing talks to
  the device in Edit mode. Tap <strong>Done</strong> to go live.</p>
  <figure class="shot">
    <img src="../img/app-remote.png" alt="A custom remote in Easy Modbus: readout tiles, a setpoint with minus and plus, and an on/off toggle on a grid" loading="lazy">
    <figcaption>A finished remote &mdash; readouts, a setpoint and a toggle on a grid, sized for gloves.</figcaption>
  </figure>
  <div class="callout">
  <p>Give the control that stops the pump a red card and leave the temperature
  readouts plain. With gloves on, at arm's length, colour is what you see
  first.</p>
  </div>

  <h2>Using it</h2>
  <p>Live, the top line reports the connection honestly: <strong>Online</strong>
  with the time of the last reply, or <strong>No response from device</strong>
  &mdash; and when the device stops answering, the values grey out instead of
  sitting there looking current. <strong>Refresh</strong> re-reads everything.
  Controls that write need <strong>Write mode</strong> on, exactly like the rest
  of the app; until then the remote is read-only and says so. See
  <a href="how-to-write-to-a-modbus-register.html">how to write to a Modbus
  register</a>, including why <em>Restore</em> matters.</p>

  <h2>Free, and kept</h2>
  <p>Custom remotes in Easy Modbus are free and are not deleted. They are stored
  on the phone only, under the device they belong to, and are not backed up to
  the cloud &mdash; a saved remote names a customer's equipment and registers,
  and that should not leave the phone by accident.</p>
""",
    related=[
        ("guides/how-to-use-easy-modbus", "How do I use Easy Modbus to read a device?"),
        ("guides/how-to-write-to-a-modbus-register", "How do I write to a Modbus register with Easy Modbus, and put it back?"),
        ("guides/is-it-safe-to-write-to-modbus", "Is it safe to write to a Modbus register?"),
    ],
))

INDEX = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/svg+xml" href="icon.svg">
<title>Easy Modbus &mdash; Modbus explained in plain English</title>
<meta name="description" content="Free Android app that finds Modbus TCP equipment on a network, works out what its registers mean, and exports a CSV. Plus plain-English guides to register maps, addressing, scaling, word order and unit IDs.">
<link rel="canonical" href="%(base)s/index.html">
<meta name="robots" content="index, follow">
<meta name="theme-color" content="#00695C">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Easy Modbus">
<meta property="og:title" content="Easy Modbus &mdash; Modbus explained in plain English">
<meta property="og:description" content="Free Android app that finds Modbus TCP equipment on a network, works out what its registers mean, and exports a CSV. Plus plain-English guides to register maps, addressing, scaling, word order and unit IDs.">
<meta property="og:url" content="%(base)s/index.html">
<meta property="og:image" content="%(base)s/img/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Easy Modbus &mdash; Modbus explained in plain English">
<meta name="twitter:description" content="Free Android app that finds Modbus TCP equipment on a network, works out what its registers mean, and exports a CSV. Plus plain-English guides to register maps, addressing, scaling, word order and unit IDs.">
<meta name="twitter:image" content="%(base)s/img/og-image.png">
<style>%(css)s</style>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "Easy Modbus",
  "applicationCategory": "UtilitiesApplication",
  "operatingSystem": "Android 8.0 or later",
  "offers": { "@type": "Offer", "price": "0", "priceCurrency": "USD" },
  "description": "Finds Modbus TCP and Modbus RTU-over-TCP equipment on a local network, helps work out what its registers mean, saves the register map, and exports the result as a CSV."
}
</script>
</head>
<body>

<header class="site">
  <a href="index.html" style="display:inline-flex;align-items:center;gap:.5rem;text-decoration:none"><img src="icon.svg" alt="" width="26" height="26" style="border-radius:6px"><span>Easy Modbus</span></a>
  <span class="muted">&middot; plain-English Modbus reference</span>
</header>

<h1>Modbus, explained for people who have to deal with it</h1>

<div class="answer">
  <strong>What this is</strong>
  <p>Easy Modbus is a free Android app for facility managers, building engineers
  and controls technicians. It finds Modbus TCP equipment on a network, helps you
  work out what its registers actually mean, remembers that so nobody has to work
  it out twice, and exports the result as a CSV you can hand to anybody. No
  account, no server &mdash; everything happens on your phone and your local
  network.</p>
  <p>The guides below answer the questions that come up first, in plain language.</p>
</div>

<h2>Start here</h2>
<p>If Modbus is new to you, read
<a href="guides/what-is-modbus.html">what is Modbus?</a> first. It explains the
one thing that causes most of the difficulty: a Modbus device will happily tell
you the contents of slot number 7, and will never tell you what slot 7 is.</p>

<h2>Using the app</h2>
<ul>
  <li><a href="guides/how-to-use-easy-modbus.html">How do I use Easy Modbus to read values from a device?</a></li>
  <li><a href="guides/how-to-write-to-a-modbus-register.html">How do I write to a register, and put it back afterwards?</a></li>
  <li><a href="guides/how-to-build-a-modbus-remote.html">How do I build a custom remote for a device?</a></li>
</ul>

<h2>Guides</h2>
<nav class="more" style="margin-top:0;border-top:none;padding-top:0">
<ul>
%(guides)s
</ul>
</nav>

<h2>What the app does</h2>
<ul>
  <li><strong>Finds equipment</strong> &mdash; sweeps the local network for
  anything answering Modbus, because Modbus has no discovery of its own. Or add a
  device by typing its address.</li>
  <li><strong>Two modes.</strong> Easy mode asks what kind of reading you are
  after &mdash; a temperature, a kilowatt figure, an on/off status &mdash; and
  picks the settings for you. Pro mode exposes raw registers in hex, word order,
  function codes and the frame log.</li>
  <li><strong>Works out what registers mean</strong> &mdash; reads a block, shows
  it in hex and decimal, and offers the plausible interpretations with the
  reasoning, so a wrong guess is visibly wrong.</li>
  <li><strong>Remembers the map</strong> &mdash; name a reading once and the
  address, data type, word order, scaling and units are saved for next time.</li>
  <li><strong>Imports and exports</strong> &mdash; paste a vendor's CSV register
  map in rather than retyping forty rows; export the whole thing with live values
  to hand on.</li>
  <li><strong>Writes carefully</strong> &mdash; off by default, off again every
  launch, confirmed against a summary, bounded by limits you set, read back
  afterwards, and with a <em>Put It Back</em> action that rewrites what the
  register said when you arrived.</li>
  <li><strong>Custom control screens</strong> &mdash; build a drag-and-drop panel
  of readouts, setpoints and switches for one device, sized for a gloved finger.</li>
</ul>

<h2>Notes for anyone connecting to building equipment</h2>
<ul>
  <li>Get onto the <strong>same network</strong> as the equipment. Controls gear is
  usually on its own VLAN, and guest Wi-Fi will not reach it.</li>
  <li>Modbus TCP is <strong>port 502</strong>. 503 and 5020 are both seen.</li>
  <li>Finding equipment means <strong>sweeping the subnet</strong>, because Modbus
  devices never announce themselves. On a monitored network that looks like a port
  scan, so tell whoever runs it.</li>
  <li>Reading is harmless. <strong>Writing has no undo</strong> &mdash; no
  priorities, no timeout, no release. Read
  <a href="guides/is-it-safe-to-write-to-modbus.html">the writing guide</a> before
  changing anything on live equipment.</li>
</ul>

<footer>
  <p><a href="privacy.html">Privacy policy</a></p>
</footer>

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
<meta name="description" content="Easy Modbus privacy policy. The app has no account and sends nothing to any server; the free version shows Google AdMob ads.">
<link rel="canonical" href="%(base)s/privacy.html">
<meta name="robots" content="index, follow">
<meta name="theme-color" content="#00695C">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Easy Modbus">
<meta property="og:title" content="Privacy policy &mdash; Easy Modbus">
<meta property="og:description" content="Easy Modbus privacy policy. The app has no account and sends nothing to any server; the free version shows Google AdMob ads.">
<meta property="og:url" content="%(base)s/privacy.html">
<meta property="og:image" content="%(base)s/img/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Privacy policy &mdash; Easy Modbus">
<meta name="twitter:description" content="Easy Modbus privacy policy. The app has no account and sends nothing to any server; the free version shows Google AdMob ads.">
<meta name="twitter:image" content="%(base)s/img/og-image.png">
<style>%(css)s</style>
</head>
<body>

<header class="site">
  <a href="index.html" style="display:inline-flex;align-items:center;gap:.5rem;text-decoration:none"><img src="icon.svg" alt="" width="26" height="26" style="border-radius:6px"><span>Easy Modbus</span></a>
  <span class="muted">&middot; privacy policy</span>
</header>

<h1>Privacy policy</h1>
<p class="muted">Last updated: %(updated)s</p>

<div class="answer">
  <strong>Summary</strong>
  <p>Easy Modbus has no account and no analytics, and the app itself sends
  nothing to any server. Everything it does happens on your phone and on the
  local network you connect it to. The one exception is advertising: the free
  version shows occasional rewarded video ads from Google AdMob, described
  below, and the one-time purchase removes them.</p>
</div>

<h2>What the app stores, and where</h2>
<p>Easy Modbus saves the following on your phone, and nowhere else:</p>
<ul>
  <li>The devices you add &mdash; address, port, unit ID and name.</li>
  <li>The register maps you build &mdash; addresses, data types, scaling, units
  and notes.</li>
  <li>Any custom control screens you create.</li>
  <li>Your choice of Easy or Pro mode.</li>
</ul>
<p>This data is deliberately excluded from Android cloud backup and from
device-to-device transfer, because a register map names a customer's equipment.
That does mean it does not follow you to a new phone; the CSV export is the way to
move a map.</p>

<h2>Advertising</h2>
<p>The free version shows occasional rewarded video ads, supplied by Google
AdMob, in exchange for exporting a report or opening a saved custom remote. To
serve them, Google's advertising SDK may collect a device advertising
identifier and standard ad-delivery information. How Google uses that data is
described in <a href="https://policies.google.com/privacy">Google's Privacy
Policy</a> and in <a href="https://policies.google.com/technologies/partner-sites">How
Google uses information from sites or apps that use its services</a>. In the EEA,
the UK and Switzerland you are asked for consent before any personalised ad, and
may choose non-personalised ads instead. The one-time in-app purchase removes all
advertising and also unlocks unlimited custom remotes. The developer receives
only aggregate, anonymous earnings figures from AdMob &mdash; never your data.</p>

<h2>What leaves the phone</h2>
<p>Two things, both only when you ask for them:</p>
<ul>
  <li><strong>Modbus requests</strong> to the equipment you point the app at, on
  your local network.</li>
  <li><strong>A CSV export</strong>, when you tap Export. The file is written to
  the app's cache and handed to whichever app you choose to send it with. Easy
  Modbus has no server and does not upload it anywhere.</li>
</ul>

<h2>What the app does not do</h2>
<ul>
  <li>No account, sign-in, or registration.</li>
  <li>No analytics, telemetry, or crash reporting. (The free version shows Google AdMob ads — see Advertising below.)</li>
  <li>No location, contacts, photos, or microphone access.</li>
  <li>No internet use beyond talking to the equipment you point it at.</li>
</ul>

<h2>Permissions</h2>
<ul>
  <li><strong>Internet</strong> and <strong>network state</strong> &mdash; to open
  TCP connections to Modbus equipment, and to find out which local network the
  phone is on so it can be swept.</li>
  <li><strong>Wi-Fi state</strong> &mdash; to read the local address and subnet.</li>
</ul>

<h2>Your choices</h2>
<ul>
  <li>You can reset or delete your advertising identifier, or turn off ad
  personalisation, in Android <em>Settings &rarr; Privacy &rarr; Ads</em>.</li>
  <li>Where a consent prompt applies, you can change your answer at any time;
  declining simply leaves you with non-personalised ads.</li>
  <li>The one-time purchase removes advertising entirely.</li>
  <li>To erase everything the app has stored, uninstall it &mdash; nothing is kept
  anywhere else.</li>
</ul>

<h2>Children</h2>
<p>Easy Modbus is a tool for building and industrial equipment and is not directed
at children. It collects no personal information from anyone.</p>

<h2>Changes to this policy</h2>
<p>If this policy changes, the &ldquo;last updated&rdquo; date above changes with
it. Material changes will be reflected here before they take effect in a new
release.</p>

<h2>Contact</h2>
<p>Questions about this policy: %(contact)s</p>

<footer>
  <p><a href="index.html">Easy Modbus</a> &middot; <a href="pc-privacy.html">Easy Modbus PC (Windows) privacy policy</a></p>
</footer>

</body>
</html>
"""

PC_PRIVACY = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/svg+xml" href="icon.svg">
<title>Privacy policy &mdash; Easy Modbus PC</title>
<meta name="description" content="Privacy policy for Easy Modbus PC, the Windows desktop app. No account, no analytics, no ads; everything stays on your PC and your local network.">
<link rel="canonical" href="%(base)s/pc-privacy.html">
<meta name="robots" content="index, follow">
<meta name="theme-color" content="#00695C">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Easy Modbus">
<meta property="og:title" content="Privacy policy &mdash; Easy Modbus PC">
<meta property="og:description" content="Privacy policy for Easy Modbus PC, the Windows desktop app. No account, no analytics, no ads; everything stays on your PC.">
<meta property="og:url" content="%(base)s/pc-privacy.html">
<meta property="og:image" content="%(base)s/img/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Privacy policy &mdash; Easy Modbus PC">
<meta name="twitter:description" content="Privacy policy for Easy Modbus PC, the Windows desktop app. No account, no analytics, no ads; everything stays on your PC.">
<meta name="twitter:image" content="%(base)s/img/og-image.png">
<style>%(css)s</style>
</head>
<body>

<header class="site">
  <a href="index.html" style="display:inline-flex;align-items:center;gap:.5rem;text-decoration:none"><img src="icon.svg" alt="" width="26" height="26" style="border-radius:6px"><span>Easy Modbus</span></a>
  <span class="muted">&middot; PC version privacy policy</span>
</header>

<h1>Privacy policy &mdash; Easy Modbus PC</h1>
<p class="muted">Windows desktop application &middot; last updated: %(updated)s</p>

<div class="answer">
  <strong>Summary</strong>
  <p>Easy Modbus PC has no account, no analytics, and no advertising. The app
  sends nothing to the developer or to any server. Everything it does happens on
  your own computer and on the local network you connect it to. A license, if you
  buy one, is checked on your own machine without contacting anyone.</p>
</div>

<h2>What the app stores, and where</h2>
<p>Easy Modbus PC saves the following on your computer, and nowhere else, under
<code>%%APPDATA%%\\EasyModbusPC</code>:</p>
<ul>
  <li>The devices you add &mdash; address, port, unit ID and name.</li>
  <li>The register maps you build &mdash; addresses, data types, scaling, units and notes.</li>
  <li>The custom remotes (control panels) you create.</li>
  <li>The emulator units you configure, and their register values.</li>
  <li>Your settings, and your license key if you enter one.</li>
</ul>
<p>This file never leaves your computer unless you copy it yourself.</p>

<h2>What leaves your computer</h2>
<p>Only the network traffic you ask for, all of it on your own network:</p>
<ul>
  <li><strong>Modbus requests</strong> to the equipment you point the Explorer at.</li>
  <li><strong>A network scan</strong>, when you use &ldquo;Find devices&rdquo; &mdash; the app
  connects to port 502 on the addresses of your local subnet to see what answers.
  It is a scan of your own network and nothing is transmitted off it.</li>
  <li><strong>Inbound connections you host</strong> &mdash; when you run the built-in
  device emulator, the app opens a listening socket on the port you choose so other
  software on your network can connect to it. It answers with the register values
  you configured and makes no outbound connection of its own.</li>
</ul>
<p>None of this reaches the developer. Easy Modbus PC has no server.</p>

<h2>Licensing</h2>
<p>Custom Remotes are free for one control panel; a one-time license unlocks
unlimited remotes. The license key is verified entirely on your own computer
&mdash; the app does not contact a license server, and no information about you or
your machine is sent when you enter a key.</p>

<h2>What the app does not do</h2>
<ul>
  <li>No account, sign-in, or registration.</li>
  <li>No analytics, telemetry, or crash reporting.</li>
  <li>No advertising and no advertising identifiers.</li>
  <li>No access to your files beyond its own settings folder, and no access to
  location, camera, or microphone.</li>
  <li>No internet use beyond the local-network Modbus traffic described above.</li>
</ul>

<h2>Your choices</h2>
<p>To erase everything the app has stored, delete the
<code>%%APPDATA%%\\EasyModbusPC</code> folder or uninstall the app. Nothing is kept
anywhere else, so there is nothing to request from us and nothing for us to delete.</p>

<h2>Children</h2>
<p>Easy Modbus PC is a tool for building and industrial equipment and is not
directed at children. It collects no personal information from anyone.</p>

<h2>Changes to this policy</h2>
<p>If this policy changes, the &ldquo;last updated&rdquo; date above changes with it.</p>

<h2>Contact</h2>
<p>Questions about this policy: %(contact)s</p>

<footer>
  <p><a href="index.html">Easy Modbus</a> &middot; <a href="privacy.html">Android app privacy policy</a></p>
</footer>

</body>
</html>
"""

LLMS = """# Easy Modbus

> Free Android app that finds Modbus TCP and Modbus RTU-over-TCP equipment on a
> local network, helps work out what its registers mean, saves that register map,
> and exports it as CSV. Published with a set of plain-English Modbus guides
> written for facility managers and building engineers rather than for protocol
> specialists.

The guides below each answer one question directly in their first paragraph and
are free to quote with attribution.

## Guides

%(guides)s

## About the app

- Platform: Android 8.0 or later. Free with rewarded ads (AdMob) removable by one-time purchase; no account, no analytics.
- Protocols: Modbus TCP and Modbus RTU over TCP, function codes 1, 2, 3, 4, 5, 6,
  15, 16, and 43/14 device identification.
- Finds equipment by sweeping the local subnet for open port 502, because Modbus
  has no discovery mechanism.
- Decodes INT16, UINT16, INT32, UINT32, FLOAT32, INT64, UINT64, FLOAT64, single
  bits within a register, and packed ASCII, in ABCD, CDAB, BADC and DCBA word
  order, with per-reading multiplier and offset.
- Accepts addresses in Modicon (40007), prefixed (4x00007), one-based and
  zero-based forms, and explains how it read them.
- Writes are off by default and off again at every launch; each write is
  confirmed, bounded by per-reading limits, read back afterwards, and logged.

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
<style>
  html { color-scheme: light dark; }
  body { max-width: 40rem; margin: 0 auto; padding: 4rem 1.25rem;
         font: 16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
         Helvetica, Arial, sans-serif; text-align: center; }
  h1 { font-size: 1.85rem; margin: 0 0 .75rem; }
  a { color: #00695C; font-weight: 600; text-decoration: none; }
  p { color: #5a5a5a; }
</style>
</head>
<body>
  <h1>Page not found</h1>
  <p>Sorry, that page does not exist or has moved.</p>
  <p><a href="/">Go to Easy Modbus</a></p>
</body>
</html>
"""


def main():
    for g in GUIDES:
        write(
            g["slug"] + ".html",
            page(
                g["slug"], g["title"], g["question"], g["answer_html"],
                g["body_html"], g["related"], g["description"],
            ),
        )

    links = "\n".join(
        '  <li><a href="%s.html">%s</a><br><span class="muted">%s</span></li>'
        % (g["slug"], g["question"], summarise(g["description"]))
        for g in GUIDES
    )
    write("index.html", INDEX % {"base": BASE_URL, "css": CSS, "guides": links})

    write(
        "privacy.html",
        PRIVACY % {
            "base": BASE_URL,
            "css": CSS,
            "updated": "15 September 2026",
            "contact": "Firstimpactdevelopment@gmail.com",
        },
    )

    write(
        "pc-privacy.html",
        PC_PRIVACY % {
            "base": BASE_URL,
            "css": CSS,
            "updated": "15 September 2026",
            "contact": "Firstimpactdevelopment@gmail.com",
        },
    )

    # sitemap + robots so crawlers and agents can enumerate the whole set
    urls = ["index.html", "privacy.html", "pc-privacy.html"] + [g["slug"] + ".html" for g in GUIDES]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sm.append("  <url><loc>%s/%s</loc></url>" % (BASE_URL, u))
    sm.append("</urlset>")
    write("sitemap.xml", "\n".join(sm) + "\n")

    write("robots.txt", "User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n" % BASE_URL)

    # llms.txt: the same enumeration, for assistants that look for it.
    llm_links = "\n".join(
        "- [%s](%s/%s.html): %s" % (g["question"], BASE_URL, g["slug"], g["description"])
        for g in GUIDES
    )
    write("llms.txt", LLMS % {"guides": llm_links})

    # Custom-domain and hosting files for GitHub Pages.
    write("CNAME", "easymodbus.com\n")
    write(".nojekyll", "")
    write("404.html", NOT_FOUND)

    print()
    print("%d guides, %d pages total." % (len(GUIDES), len(urls)))
    if "REPLACE-ME" in BASE_URL:
        print("NOTE: BASE_URL is still a placeholder. Set it to the real GitHub")
        print("      Pages URL and re-run before publishing, or canonical tags,")
        print("      the sitemap and llms.txt will point at nothing.")


if __name__ == "__main__":
    main()
