"""Data-quality audit for register_data/*/*.json.

Run:  python tools_audit_registers.py            (every file)
      python tools_audit_registers.py abb        (one manufacturer folder)
Exit code 1 when any ERROR is found; WARN lines are worth reading but don't fail.
"""
import collections
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TABLES = ("coil", "discrete_input", "input_register", "holding_register")
LENGTHS = {"BIT": 1, "INT16": 1, "UINT16": 1, "BITMAP16": 1, "INT32": 2, "UINT32": 2, "FLOAT32": 2,
           "INT64": 4, "UINT64": 4, "FLOAT64": 4}
ORDERS = ("ABCD", "CDAB", "BADC", "DCBA")
HEADER_WORDS = {"name", "register", "address", "description", "data type", "type", "units", "access", "parameter"}
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def audit(path):
    err, warn = [], []
    try:
        d = json.load(io.open(path, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return ["invalid JSON: %s" % e], []
    folder = os.path.basename(os.path.dirname(path))
    stem = os.path.splitext(os.path.basename(path))[0]
    for k in ("manufacturer", "manufacturer_slug", "model", "model_slug", "equipment_type", "summary",
              "transport", "addressing", "source", "registers", "integration", "applies_to"):
        if not d.get(k):
            err.append("missing " + k)
    if err:
        return err, warn
    if d["manufacturer_slug"] != folder or not SLUG.fullmatch(folder):
        err.append("manufacturer_slug %r != folder %r" % (d["manufacturer_slug"], folder))
    if d["model_slug"] != stem or not SLUG.fullmatch(stem):
        err.append("model_slug %r != file %r" % (d["model_slug"], stem))
    src = d["source"]
    if not str(src.get("url", "")).startswith("http"):
        err.append("source.url missing")
    if not src.get("title"):
        err.append("source.title missing")
    if not set(d["transport"]) <= {"RTU", "TCP", "ASCII"}:
        err.append("transport must be RTU/TCP/ASCII: %r" % d["transport"])
    conv = (d["addressing"] or {}).get("convention")
    if conv not in ("0-based", "1-based", "Modicon", "hex 0-based", "parameter-derived"):
        err.append("addressing.convention %r" % conv)
    if len(d.get("summary") or "") > 700:
        warn.append("summary long (%d chars)" % len(d["summary"]))

    regs = d["registers"]
    seen = collections.Counter()
    spans = collections.defaultdict(list)
    for i, r in enumerate(regs):
        tag = "reg[%d] %s %s" % (i, r.get("table"), r.get("address"))
        if r.get("table") not in TABLES:
            err.append(tag + ": bad table")
            continue
        a = r.get("address")
        if not isinstance(a, int) or not (0 <= a <= 65535):
            err.append(tag + ": address must be int 0..65535")
            continue
        seen[(r["table"], a)] += 1
        n = (r.get("name") or "").strip()
        if not n:
            err.append(tag + ": no name")
        if n.lower() in HEADER_WORDS:
            err.append(tag + ": header leaked as name %r" % n)
        if len(n) > 80:
            warn.append(tag + ": long name")
        if not str(r.get("documented") or "").strip():
            err.append(tag + ": documented address missing")
        dt = r.get("data_type")
        bit_table = r["table"] in ("coil", "discrete_input")
        if bit_table and dt != "BIT":
            err.append(tag + ": coil/discrete input must be BIT")
        if not bit_table and dt == "BIT":
            err.append(tag + ": BIT only valid for coils/discrete inputs (use BITMAP16 + bits)")
        if dt not in LENGTHS and dt != "STRING":
            err.append(tag + ": bad data_type %r" % dt)
            continue
        ln = r.get("length")
        if dt == "STRING":
            if not isinstance(ln, int) or ln < 1:
                err.append(tag + ": STRING needs length")
                ln = 1
        else:
            if ln is not None and ln != LENGTHS[dt]:
                err.append(tag + ": length %r doesn't match %s" % (ln, dt))
            ln = LENGTHS[dt]
        wo = r.get("word_order")
        if ln >= 2 and dt != "STRING" and wo not in ORDERS:
            err.append(tag + ": %s needs word_order" % dt)
        if ln == 1 and wo not in (None, ""):
            warn.append(tag + ": word_order on a 1-register value")
        sc = r.get("scale", 1)
        if not isinstance(sc, (int, float)) or sc == 0:
            err.append(tag + ": scale must be a non-zero number")
        if r.get("scale_factor_ref"):
            ref = r["scale_factor_ref"]
            if sc != 1:
                err.append(tag + ": scale must be 1 when scale_factor_ref is set")
            if not isinstance(ref, dict) or ref.get("table") not in TABLES or not isinstance(ref.get("address"), int):
                err.append(tag + ": bad scale_factor_ref")
        if r.get("access") not in ("R", "RW", "W"):
            err.append(tag + ": access must be R/RW/W")
        if r["table"] in ("discrete_input", "input_register") and r.get("access") != "R":
            err.append(tag + ": input tables are read-only")
        if len((r.get("description") or "").split()) > 16:
            warn.append(tag + ": description > 16 words")
        if dt == "BITMAP16" and not r.get("bits"):
            warn.append(tag + ": BITMAP16 without bits")
        for k in ("values", "bits"):
            v = r.get(k)
            if v is not None and not isinstance(v, dict):
                err.append(tag + ": %s must be an object" % k)
        spans[r["table"]].append((a, a + ln - 1, n))
    for k, c in seen.items():
        if c > 1:
            err.append("duplicate register %s %s" % k)
    for t, lst in spans.items():
        lst.sort()
        for (a0, a1, n0), (b0, b1, n1) in zip(lst, lst[1:]):
            if b0 <= a1:
                warn.append("overlap %s %d-%d %r and %d %r" % (t, a0, a1, n0, b0, n1))
    # documented vs 0-based consistency for plain numeric conventions
    for r in regs:
        doc = str(r.get("documented") or "").strip()
        a = r.get("address")
        if not isinstance(a, int) or not re.fullmatch(r"\d+", doc):
            continue
        v = int(doc)
        if conv == "0-based" and v != a:
            warn.append("%s %s: documented %s but convention 0-based" % (r["table"], a, doc))
        elif conv == "1-based" and v != a + 1:
            warn.append("%s %s: documented %s but convention 1-based" % (r["table"], a, doc))
        elif conv == "Modicon":
            base = {"coil": 0, "discrete_input": 10000, "input_register": 30000, "holding_register": 40000}[r["table"]]
            big = {"coil": 0, "discrete_input": 100000, "input_register": 300000, "holding_register": 400000}[r["table"]]
            if v - base - 1 != a and v - big - 1 != a:
                warn.append("%s %s: documented %s doesn't fit Modicon" % (r["table"], a, doc))

    it = d["integration"]
    if not isinstance(it, dict):
        err.append("integration must be an object")
    else:
        keys = {(r.get("table"), r.get("address")) for r in regs}
        mins = it.get("minimum_registers") or []
        if not mins:
            err.append("integration.minimum_registers empty")
        for mr in mins:
            if (mr.get("table"), mr.get("address")) not in keys:
                err.append("minimum register %s %s not in registers" % (mr.get("table"), mr.get("address")))
        if not it.get("summary"):
            warn.append("integration.summary empty")
        if not it.get("enable"):
            warn.append("integration.enable empty")
    if len(regs) < 5:
        warn.append("only %d registers" % len(regs))
    return err, warn


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else "*"
    files = sorted(glob.glob(os.path.join(HERE, "register_data", only, "*.json")))
    n_err = 0
    total = 0
    for p in files:
        err, warn = audit(p)
        try:
            total += len(json.load(io.open(p, encoding="utf-8")).get("registers") or [])
        except Exception:  # noqa: BLE001
            pass
        if err or warn:
            print("\n" + os.path.relpath(p, HERE))
            for e in list(dict.fromkeys(err))[:25]:
                print("  ERROR " + e)
            for w in list(dict.fromkeys(warn))[:12]:
                print("  WARN  " + w)
        n_err += len(err)
    print("\n%d files, %d registers, %d errors" % (len(files), total, n_err))
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
