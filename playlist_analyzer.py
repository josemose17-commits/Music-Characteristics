#!/usr/bin/env python3
"""Analyze a whole playlist from per-song Cyanite results.

Cyanite analyzes one song at a time. Export (or copy) the results for every
song in your playlist into a CSV file, then run:

    python playlist_analyzer.py my_playlist.csv

You get a playlist summary in the terminal and an HTML report
(my_playlist_report.html) with the mood/genre mix, BPM and key spread,
energy flow, songs that don't fit, and a suggested track order.

Only the Python standard library is used.
"""

import argparse
import csv
import html
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

# Canonical field -> header names it may appear under (normalized: lowercase,
# letters and digits only). Exact matches win over partial matches.
COLUMN_ALIASES = {
    "title": ["title", "tracktitle", "trackname", "track", "songtitle", "song", "name", "filename", "file"],
    "artist": ["artist", "artists", "artistname"],
    "bpm": ["bpm", "tempo", "bpmprediction", "bpmrangeadjusted"],
    "key": ["key", "keyprediction", "musicalkey"],
    "energy": ["energylevel", "energy"],
    "genre": ["genre", "genres", "genretags", "maingenre"],
    "subgenre": ["subgenre", "subgenres", "subgenretags"],
    "mood": ["mood", "moods", "moodtags"],
    "character": ["character", "charactertags"],
    "movement": ["movement", "movementtags"],
    "instruments": ["instruments", "instrument", "instrumenttags"],
    "voice": ["voice", "vocals", "voicegender", "predominantvoicegender"],
}
TAG_FIELDS = ["genre", "subgenre", "mood", "character", "movement", "instruments"]

ENERGY_WORDS = {"verylow": 1, "low": 2, "medium": 3, "mid": 3, "high": 4, "veryhigh": 5}
ENERGY_NAMES = {1: "very low", 2: "low", 3: "medium", 4: "high", 5: "very high"}

NOTE_PC = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
PC_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
KEY_RE = re.compile(r"^([a-g])(#|♯|sharp|b|♭|flat)?(major|maj|minor|min|m)?$")


def norm(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


def match_columns(headers):
    """Map canonical field names to the CSV headers that hold them."""
    normalized = {h: norm(h) for h in headers}
    found = {}
    used = set()
    for exact in (True, False):
        for field, aliases in COLUMN_ALIASES.items():
            if field in found:
                continue
            for alias in aliases:
                hit = next(
                    (h for h, n in normalized.items()
                     if h not in used and (n == alias if exact else alias in n)),
                    None,
                )
                if hit:
                    found[field] = hit
                    used.add(hit)
                    break
    return found


def split_tags(value):
    """'Happy, Uplifting (0.82); Chill' -> ['happy', 'uplifting', 'chill']."""
    tags = []
    for part in re.split(r"[,;|]", value or ""):
        part = re.sub(r"\(.*?\)|[:=]?\s*\d*\.?\d+%?$", "", part.strip()).strip().lower()
        if part and part not in ("none", "n/a", "-"):
            tags.append(part)
    return tags


def parse_bpm(value):
    m = re.search(r"\d+(\.\d+)?", value or "")
    return float(m.group()) if m else None


def parse_energy(value):
    value = (value or "").strip()
    if not value:
        return None
    word = norm(value)
    if word in ENERGY_WORDS:
        return ENERGY_WORDS[word]
    try:
        number = float(value.rstrip("%"))
    except ValueError:
        return None  # e.g. "variable"
    if value.endswith("%") or number > 5:
        number /= 100
    if number <= 1:
        return 1 + round(number * 4)
    return round(number)


def parse_key(value):
    """'A minor', 'aMinor', 'C#m', 'Bb' -> (pitch_class, is_minor) or None."""
    text = re.sub(r"[\s\-_]", "", (value or "").lower())
    m = KEY_RE.match(text)
    if not m:
        return None
    letter, accidental, mode = m.groups()
    pc = NOTE_PC[letter]
    if accidental in ("#", "♯", "sharp"):
        pc += 1
    elif accidental in ("b", "♭", "flat"):
        pc -= 1
    return pc % 12, mode in ("minor", "min", "m")


def key_name(key):
    pc, minor = key
    return f"{PC_NAMES[pc]} {'minor' if minor else 'major'}"


def camelot(key):
    """Camelot wheel code used by DJs, e.g. A minor -> (8, 'A')."""
    pc, minor = key
    major_pc = (pc + 3) % 12 if minor else pc
    number = ((major_pc * 7) % 12 + 7) % 12 + 1
    return number, "A" if minor else "B"


def key_distance(a, b):
    """0 = same key, 1 = harmonically compatible neighbour, higher = clash."""
    (na, la), (nb, lb) = camelot(a), camelot(b)
    step = min(abs(na - nb), 12 - abs(na - nb))
    return step + (la != lb)


def bpm_distance(a, b):
    """BPM gap, treating half/double time as close (90 BPM ~ 180 BPM)."""
    return min(abs(a - b), abs(a * 2 - b), abs(a - b * 2))


class Track:
    def __init__(self, index, row, cols):
        get = lambda f: (row.get(cols[f]) or "").strip() if f in cols else ""
        self.index = index
        self.title = get("title") or f"Track {index + 1}"
        self.artist = get("artist")
        self.bpm = parse_bpm(get("bpm"))
        self.key = parse_key(get("key"))
        self.raw_key = get("key")
        self.energy = parse_energy(get("energy"))
        self.voice = get("voice").lower()
        self.tags = {f: split_tags(get(f)) for f in TAG_FIELDS}

    @property
    def label(self):
        return f"{self.artist} - {self.title}" if self.artist else self.title


def load_tracks(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        cols = match_columns(reader.fieldnames or [])
        rows = [r for r in reader if any((v or "").strip() for v in r.values())]
    return [Track(i, r, cols) for i, r in enumerate(rows)], cols


def tag_profile(tracks, field):
    """Share of tracks carrying each tag, most common first."""
    counts = Counter(t for tr in tracks for t in set(tr.tags[field]))
    tagged = sum(1 for tr in tracks if tr.tags[field]) or 1
    return [(tag, n / tagged) for tag, n in counts.most_common()]


def find_outliers(tracks):
    """Score how far each song sits from the rest of the playlist."""
    bpms = [t.bpm for t in tracks if t.bpm]
    energies = [t.energy for t in tracks if t.energy]
    mid_bpm = statistics.median(bpms) if bpms else None
    mid_energy = statistics.median(energies) if energies else None
    profiles = {f: dict(tag_profile(tracks, f)) for f in ("genre", "mood")}

    results = []
    for t in tracks:
        score, reasons = 0.0, []
        if mid_bpm and t.bpm:
            gap = bpm_distance(t.bpm, mid_bpm)
            if gap > 20:
                score += gap / 20
                reasons.append(f"tempo {t.bpm:.0f} BPM vs playlist ~{mid_bpm:.0f}")
        if mid_energy and t.energy and abs(t.energy - mid_energy) >= 2:
            score += abs(t.energy - mid_energy)
            reasons.append(f"energy {ENERGY_NAMES[t.energy]} vs playlist "
                           f"{ENERGY_NAMES[round(mid_energy)]}")
        for field, profile in profiles.items():
            if t.tags[field] and profile:
                fit = max(profile.get(tag, 0) for tag in t.tags[field])
                if fit < 0.25:
                    score += (0.25 - fit) * 8
                    reasons.append(f"{field} ({', '.join(t.tags[field][:3])}) is rare here")
        if reasons:
            results.append((score, t, reasons))
    results.sort(key=lambda r: -r[0])
    return [r for r in results if r[0] >= 1.5]


def transition_cost(a, b):
    cost = 0.0
    if a.key and b.key:
        cost += key_distance(a.key, b.key)
    if a.bpm and b.bpm:
        cost += bpm_distance(a.bpm, b.bpm) / 8
    if a.energy and b.energy:
        cost += abs(a.energy - b.energy) * 0.75
    return cost


def order_cost(tracks):
    return sum(transition_cost(a, b) for a, b in zip(tracks, tracks[1:]))


def suggest_order(tracks):
    """Greedy smooth-flow ordering: start calm, always take the closest next song."""
    if len(tracks) < 3:
        return list(tracks)
    remaining = list(tracks)
    start = min(remaining, key=lambda t: (t.energy or 3, t.bpm or 0))
    order = [start]
    remaining.remove(start)
    while remaining:
        nxt = min(remaining, key=lambda t: transition_cost(order[-1], t))
        order.append(nxt)
        remaining.remove(nxt)
    return order


def analyze(tracks):
    bpms = [t.bpm for t in tracks if t.bpm]
    keys = [t.key for t in tracks if t.key]
    energies = [t.energy for t in tracks if t.energy]
    order = suggest_order(tracks)
    return {
        "count": len(tracks),
        "bpm": {
            "min": min(bpms), "max": max(bpms),
            "median": statistics.median(bpms), "mean": statistics.mean(bpms),
        } if bpms else None,
        "keys": Counter(key_name(k) for k in keys).most_common(),
        "minor_share": sum(1 for k in keys if k[1]) / len(keys) if keys else None,
        "energy": {
            "flow": [(t, t.energy) for t in tracks],
            "average": statistics.mean(energies) if energies else None,
            "counts": Counter(ENERGY_NAMES[e] for e in energies),
        },
        "voice": Counter(t.voice for t in tracks if t.voice).most_common(),
        "tags": {f: tag_profile(tracks, f) for f in TAG_FIELDS},
        "outliers": find_outliers(tracks),
        "order": order,
        "cost_now": order_cost(tracks),
        "cost_suggested": order_cost(order),
    }


def pct(x):
    return f"{x * 100:.0f}%"


def describe_vibe(result):
    parts = []
    moods = result["tags"]["mood"][:2]
    if moods:
        parts.append(" & ".join(m for m, _ in moods))
    genres = result["tags"]["genre"][:2]
    if genres:
        parts.append(" / ".join(g for g, _ in genres))
    if result["bpm"]:
        parts.append(f"around {result['bpm']['median']:.0f} BPM")
    if result["energy"]["average"]:
        parts.append(f"{ENERGY_NAMES[round(result['energy']['average'])]} energy")
    return ", ".join(parts) or "not enough data"


def text_report(result, cols, source):
    lines = [f"Playlist analysis: {source}", "=" * 60,
             f"Songs: {result['count']}",
             f"Overall vibe: {describe_vibe(result)}", ""]
    if result["bpm"]:
        b = result["bpm"]
        lines.append(f"BPM: {b['min']:.0f}-{b['max']:.0f} (median {b['median']:.0f})")
    if result["keys"]:
        top = ", ".join(f"{k} x{n}" for k, n in result["keys"][:5])
        lines.append(f"Keys: {top}  |  minor: {pct(result['minor_share'])}")
    if result["energy"]["counts"]:
        lines.append("Energy: " + ", ".join(
            f"{name} x{n}" for name, n in result["energy"]["counts"].most_common()))
    for field in TAG_FIELDS:
        profile = result["tags"][field]
        if profile:
            lines.append(f"{field.capitalize()}: " + ", ".join(
                f"{tag} {pct(share)}" for tag, share in profile[:6]))
    if result["voice"]:
        lines.append("Voice: " + ", ".join(f"{v} x{n}" for v, n in result["voice"]))

    lines += ["", "Songs that don't fit:"]
    if result["outliers"]:
        for _, t, reasons in result["outliers"]:
            lines.append(f"  - {t.label}: {'; '.join(reasons)}")
    else:
        lines.append("  none - the playlist is consistent")

    lines += ["", "Suggested order (smoother key / BPM / energy transitions):"]
    for i, t in enumerate(result["order"], 1):
        info = [f"{t.bpm:.0f} BPM" if t.bpm else "",
                key_name(t.key) if t.key else "",
                ENERGY_NAMES.get(t.energy, "")]
        lines.append(f"  {i:2}. {t.label}  ({', '.join(x for x in info if x)})")
    if result["cost_now"]:
        gain = 1 - result["cost_suggested"] / result["cost_now"]
        if gain > 0:
            lines.append(f"  -> about {pct(gain)} smoother than the current order")

    missing = [f for f in ("bpm", "key", "energy", "genre", "mood") if f not in cols]
    if missing:
        lines += ["", f"Note: no column found for {', '.join(missing)}. "
                      f"Columns recognised: {', '.join(cols.values()) or 'none'}"]
    return "\n".join(lines)


def html_bars(profile, limit=10):
    rows = []
    for tag, share in profile[:limit]:
        rows.append(
            f'<div class="bar"><span class="name">{html.escape(tag)}</span>'
            f'<span class="track"><span class="fill" style="width:{share * 100:.0f}%"></span></span>'
            f'<span class="val">{pct(share)}</span></div>')
    return "\n".join(rows)


def html_report(result, source):
    e = html.escape
    cards = [("Songs", str(result["count"]))]
    if result["bpm"]:
        b = result["bpm"]
        cards.append(("BPM", f"{b['min']:.0f}–{b['max']:.0f}"))
    if result["keys"]:
        cards.append(("Top key", result["keys"][0][0]))
    if result["energy"]["average"]:
        cards.append(("Energy", ENERGY_NAMES[round(result["energy"]["average"])]))

    sections = []
    for field in TAG_FIELDS:
        if result["tags"][field]:
            sections.append(f"<section><h2>{field.capitalize()}</h2>"
                            f"{html_bars(result['tags'][field])}</section>")
    if result["keys"]:
        total = sum(n for _, n in result["keys"])
        sections.append("<section><h2>Keys</h2>"
                        + html_bars([(k, n / total) for k, n in result["keys"]]) + "</section>")

    flow = [(t, en) for t, en in result["energy"]["flow"]]
    if any(en for _, en in flow):
        cols = "".join(
            f'<div class="col" title="{e(t.label)}: {ENERGY_NAMES.get(en, "unknown")}">'
            f'<span style="height:{(en or 0) * 20}%"></span></div>' for t, en in flow)
        sections.append("<section class='wide'><h2>Energy flow (current order)</h2>"
                        f"<div class='flow'>{cols}</div></section>")

    if result["outliers"]:
        items = "".join(f"<li><b>{e(t.label)}</b> — {e('; '.join(r))}</li>"
                        for _, t, r in result["outliers"])
    else:
        items = "<li>None — the playlist is consistent.</li>"
    sections.append(f"<section class='wide'><h2>Songs that don't fit</h2><ul>{items}</ul></section>")

    rows = "".join(
        f"<tr><td>{i}</td><td>{e(t.label)}</td><td>{f'{t.bpm:.0f}' if t.bpm else ''}</td>"
        f"<td>{key_name(t.key) if t.key else e(t.raw_key)}</td>"
        f"<td>{'%d%s' % camelot(t.key) if t.key else ''}</td>"
        f"<td>{ENERGY_NAMES.get(t.energy, '')}</td></tr>"
        for i, t in enumerate(result["order"], 1))
    sections.append(
        "<section class='wide'><h2>Suggested order</h2>"
        "<table><tr><th>#</th><th>Song</th><th>BPM</th><th>Key</th><th>Camelot</th>"
        f"<th>Energy</th></tr>{rows}</table></section>")

    card_html = "".join(f"<div class='card'><small>{e(k)}</small><b>{e(v)}</b></div>"
                        for k, v in cards)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Playlist Analysis</title>
<style>
:root {{ --bg:#f7f7f9; --fg:#1d1d24; --muted:#6b6b78; --panel:#fff; --accent:#5b5bd6; --line:#e4e4ea; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#141419; --fg:#ececf1; --muted:#9a9aa8; --panel:#1e1e26; --accent:#8b8bf0; --line:#2d2d38; }}
}}
body {{ margin:0; background:var(--bg); color:var(--fg); font:15px/1.5 system-ui, sans-serif; }}
main {{ max-width:960px; margin:0 auto; padding:24px 16px; }}
h1 {{ margin:0 0 4px; }} .vibe {{ color:var(--muted); margin:0 0 20px; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:12px; margin-bottom:16px; }}
.card, section {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px; }}
.card small {{ display:block; color:var(--muted); }} .card b {{ font-size:22px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:12px; }}
section.wide {{ grid-column:1/-1; }} h2 {{ font-size:16px; margin:0 0 10px; }}
.bar {{ display:grid; grid-template-columns:110px 1fr 44px; gap:8px; align-items:center; margin:4px 0; }}
.bar .name {{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.bar .track {{ background:var(--line); border-radius:4px; height:10px; }}
.bar .fill {{ display:block; height:100%; background:var(--accent); border-radius:4px; }}
.bar .val {{ text-align:right; color:var(--muted); }}
.flow {{ display:flex; align-items:flex-end; gap:3px; height:120px; }}
.flow .col {{ flex:1; height:100%; display:flex; align-items:flex-end; }}
.flow .col span {{ display:block; width:100%; background:var(--accent); border-radius:3px 3px 0 0; }}
table {{ width:100%; border-collapse:collapse; }} td, th {{ text-align:left; padding:6px; border-bottom:1px solid var(--line); }}
section {{ overflow-x:auto; }}
</style></head><body><main>
<h1>Playlist analysis</h1>
<p class="vibe">{e(source)} — {e(describe_vibe(result))}</p>
<div class="cards">{card_html}</div>
<div class="grid">{''.join(sections)}</div>
</main></body></html>
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description="Analyze a playlist from Cyanite song results (CSV).")
    parser.add_argument("csv", help="CSV with one row per song (Cyanite export or template)")
    parser.add_argument("-o", "--output", help="HTML report path (default: <csv name>_report.html)")
    args = parser.parse_args(argv)

    path = Path(args.csv)
    tracks, cols = load_tracks(path)
    if not tracks:
        sys.exit(f"No songs found in {path}")
    result = analyze(tracks)
    print(text_report(result, cols, path.name))

    out = Path(args.output) if args.output else path.with_name(f"{path.stem}_report.html")
    out.write_text(html_report(result, path.name), encoding="utf-8")
    print(f"\nHTML report written to {out}")


if __name__ == "__main__":
    main()
