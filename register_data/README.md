# Modbus register-map data (source for /modbus-register-maps/)

One JSON file per model: `register_data/<manufacturer_slug>/<model_slug>.json`.
`register_library.py` turns them into pages; `tools_audit_registers.py` checks them.

Rules that override everything else:

1. **Facts only, re-keyed.** Register numbers, data types, word order, scale, units,
   access and enum/bit meanings are facts and are copied exactly. Every `description`,
   `summary` and integration note is written in our own words — never paste the
   manufacturer's prose. Never re-host the PDF; link it.
2. **Exactness beats volume.** Data type, word order and scale must match the source
   exactly. If the manual is ambiguous about a register's type, word order or scaling,
   **leave the register out** (and say why in `notes`). Never guess.
3. Free, public manufacturer documents only. Never bypass a bot check or a login.

## Model fields

```jsonc
{
  "manufacturer": "Schneider Electric",       // display name
  "manufacturer_slug": "schneider-electric",   // == folder name, [a-z0-9-]
  "model": "PowerLogic PM5300",                // display name
  "model_slug": "pm5300",                      // == file name, [a-z0-9-]
  "short_model": "PM5300",                     // optional, used in <title> (keep short)
  "aliases": ["PM5310", "PM5320", "METSEPM5310"], // other names / part numbers this map applies to
  "equipment_type": "Power meter",             // see categories below
  "applies_to": "One line: which variants/firmware the map covers.",
  "summary": "2-4 sentences in our own words: what the device is, how Modbus is exposed, what the map covers.",
  "transport": ["RTU", "TCP"],                 // subset of RTU, TCP, ASCII
  "defaults": {                                // null for anything the source does not state
    "unit_id": 1, "baud": 19200, "parity": "Even", "data_bits": 8, "stop_bits": 1, "tcp_port": 502
  },
  "addressing": {
    "convention": "1-based",                   // how the SOURCE prints addresses: "0-based", "1-based",
                                               // "Modicon" (30001/40001 style), "hex 0-based", "parameter-derived"
    "note": "Own-words explanation, e.g. 'The manual lists register 3000; request address 2999 on the wire.'"
  },
  "default_word_order": "ABCD",                // most common order for 32/64-bit values in this map, or null
  "firmware": "As stated in the source, or null",
  "source": {
    "title": "Exact document title",
    "doc_number": "Document / part number incl. revision letter, or null",
    "revision_date": "YYYY-MM-DD or YYYY-MM or as printed, or null",
    "url": "https://... direct manufacturer URL of the PDF (or its official download page)",
    "pages": "e.g. 'pp. 112-140' - where the table lives, for the verifier"
  },
  "notes": ["Own-words caveats: omitted registers and why, quirks, option-dependent blocks."],
  "registers": [ /* see below */ ],
  "integration": { /* see below */ }
}
```

### Register fields

```jsonc
{
  "table": "holding_register",   // coil | discrete_input | input_register | holding_register
  "address": 2999,               // 0-based PROTOCOL (wire) address - what goes in the request PDU
  "documented": "3000",          // the address EXACTLY as printed in the source (string; "40001", "0x0BB8", "P 4-12")
  "name": "Current A",           // short name; the manual's register name is fine (facts), trimmed
  "description": "Own-words, <= 16 words. Empty string if the name says it all.",
  "data_type": "FLOAT32",        // BIT (coils/discrete inputs) | INT16 | UINT16 | INT32 | UINT32 | FLOAT32 |
                                 // INT64 | UINT64 | FLOAT64 | STRING | BITMAP16 (packed flags in one UINT16)
  "length": 2,                   // number of 16-bit registers (BIT = 1). Required for STRING; check others.
  "word_order": "ABCD",          // required when length >= 2 and not STRING: ABCD (high word first),
                                 // CDAB (low word first), BADC, DCBA. null otherwise.
                                 // 64-bit: ABCD = most significant word first, CDAB = least
                                 // significant word first (all four words reversed) - the
                                 // same rule the Easy Modbus codec applies.
  "scale": 1,                    // multiplier: engineering value = raw * scale + offset. "Divide by 10" -> 0.1
  "offset": 0,                   // optional, rarely non-zero
  "scale_factor_ref": null,      // SunSpec-style: {"table":"holding_register","address":40083} when
                                 // value = raw * 10^(signed int16 at that register). scale must then be 1.
  "units": "A",                  // as published ("V", "kWh", "Hz", "%", "°C", "rpm", "s"), "" if none
  "access": "R",                 // R | RW | W
  "values": {"0": "Stopped", "1": "Running"},   // enum meanings, or null
  "bits": {"0": "Alarm active", "3": "Remote mode"} // bit meanings for BITMAP16 / status words, or null
}
```

Address convention, worked: a manual that prints holding register `40101` (Modicon) or
`101` (1-based) means wire address `100`. A manual that prints `100` and says addresses
are 0-based / "PDU address" / hex means wire address `100`. Danfoss-style parameter maps
(register = parameter × 10 − 1) are "parameter-derived": state the rule in `addressing.note`.
If the document does not make the convention clear, write that in `addressing.note`,
say which way you resolved it and why (e.g. an example request frame in the manual).

## Integration block

```jsonc
"integration": {
  "summary": "2-3 sentences: the fastest correct path to reading and controlling this device.",
  "minimum_registers": [
    {"table": "holding_register", "address": 2999, "why": "Phase A current"}
  ],                                       // 4-10 entries, each MUST exist in registers[]
  "enable": "How to turn on Modbus / remote control / writes (parameters, DIP switches, menu path).",
  "watchdog": "Communication-loss timeout or watchdog behaviour and its parameters, or null if none documented.",
  "quirks": ["Byte-order and addressing quirks an integrator will trip over."],
  "setup": ["Network setup steps: where to set unit ID, baud, parity, IP; termination; restart needed?"],
  "gotchas": ["Anything else that wastes a site visit."]
}
```

Only state what the source (or another free official document, cited in `notes`) supports.

## Equipment types (equipment_type should contain one of these words)

Power meter / Energy meter, Generator controller, Variable frequency drive, Solar inverter,
Battery inverter, EV charger, Boiler, Pump, Chiller, Heat pump, Air handler, Rooftop unit, VRF / split AC
gateway, Thermostat, Actuator / valve, Sensor, Transfer switch, UPS.
