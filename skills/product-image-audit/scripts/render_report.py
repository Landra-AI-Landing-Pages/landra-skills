#!/usr/bin/env python3
"""Turn an audit (report.json) into ONE self-contained, visual HTML report.

    python3 render_report.py report.json --gallery ./gallery --out image-audit-<product>.html
    python3 render_report.py report.json --md  > image-audit-<product>.md   # the text version

Python 3 standard library only. Thumbnails come from the extractor (gallery/thumbs/NN.jpg) and are
embedded as base64 data URIs, so the file has no external images, fonts or scripts. A slide with no
thumbnail gets a numbered coloured tile, never a broken image.
The report.json shape is documented in references/report-artifact.md.
"""
import argparse, base64, html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "report-template.html")

RUNGS = [("feature", "Feature"), ("benefit", "Benefit"), ("end", "End result"), ("none", "Slogan, claim or none")]
STATUS = {"strong": ("good", "✓", "Strong"), "ok": ("warn", "!", "Improve"), "fix": ("bad", "✕", "Fix")}
CHECK = {"yes": ("good", "✓"), "partial": ("warn", "–"), "no": ("bad", "✕")}


def e(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def rung_key(r):
    r = (r or "").lower()
    if "end" in r:
        return "end"
    if "benefit" in r:
        return "benefit"
    if "feature" in r:
        return "feature"
    return "none"


def load_thumbs(gallery):
    out = {}
    if not gallery:
        return out
    man = os.path.join(gallery, "manifest.json")
    items = []
    if os.path.exists(man):
        try:
            items = json.load(open(man)).get("items", [])
        except Exception:
            items = []
    for it in items:
        p = it.get("thumb")
        if p and not os.path.isabs(p) and not os.path.exists(p):
            p = os.path.join(gallery, p)
        if not p or not os.path.exists(p):
            p = os.path.join(gallery, "thumbs", f"{it.get('position', 0):02d}.jpg")
        if os.path.exists(p):
            out[it["position"]] = p
    tdir = os.path.join(gallery, "thumbs")
    if os.path.isdir(tdir):
        for f in os.listdir(tdir):
            m = re.match(r"(\d+)\.jpe?g$", f, re.I)
            if m and int(m.group(1)) not in out:
                out[int(m.group(1))] = os.path.join(tdir, f)
    uris = {}
    for n, p in out.items():
        data = open(p, "rb").read()
        if len(data) > 200000:  # keep the file light; a tile beats a 1 MB report
            continue
        uris[n] = "data:image/jpeg;base64," + base64.b64encode(data).decode()
    return uris


def tile(n, thumbs, label=None, cls=""):
    if n in thumbs:  # each image is embedded ONCE, as a CSS class (see thumb_css), and reused everywhere
        return f'<div class="tile im t{n} {cls}" role="img" aria-label="Slide {n}"></div>'
    return f'<div class="tile ph c{(n - 1) % 6} {cls}"><span>{e(label or n)}</span></div>'


def thumb_css(thumbs):
    return "\n".join(f'.t{n}{{background-image:url("{u}")}}' for n, u in sorted(thumbs.items()))


def ring(have, total, partial=0):
    total = max(total, 1)
    r, c = 52, 2 * 3.14159 * 52
    a = c * have / total
    b = c * partial / total
    return f'''<svg class="ring" viewBox="0 0 128 128" role="img" aria-label="{have} of {total} must-have shots{f', {partial} partial' if partial else ''}">
  <title>{have} of {total} must-have shots{f' ({partial} partial)' if partial else ''}</title>
  <circle cx="64" cy="64" r="{r}" class="ring-bg"/>
  <circle cx="64" cy="64" r="{r}" class="ring-have" stroke-dasharray="{a:.1f} {c:.1f}" transform="rotate(-90 64 64)"/>
  {f'<circle cx="64" cy="64" r="{r}" class="ring-part" stroke-dasharray="{b:.1f} {c:.1f}" stroke-dashoffset="{-a:.1f}" transform="rotate(-90 64 64)"/>' if partial else ''}
  <text x="64" y="62" class="ring-num">{have}<tspan class="ring-of">/{total}</tspan></text>
  <text x="64" y="84" class="ring-lbl">must-haves</text>
</svg>'''


def rung_chart(slides):
    counts = {k: 0 for k, _ in RUNGS}
    for s in slides:
        counts[rung_key(s.get("rung"))] += 1
    mx = max(counts.values()) or 1
    rows = []
    for k, label in RUNGS:
        n = counts[k]
        w = 100 * n / mx
        rows.append(f'''<div class="bar-row" title="{e(label)}: {n} slide{'s' if n != 1 else ''}">
  <span class="bar-lbl">{e(label)}</span>
  <span class="bar-track"><span class="bar r-{k}" style="width:{max(w, 0.0):.0f}%"></span></span>
  <span class="bar-val">{n}</span></div>''')
    total = sum(counts.values())
    top = counts["end"]
    head = (f"{top} of {total} slides reach the buyer's end goal" if top else "No slide reaches the buyer's end goal yet")
    return f'<div class="chart"><p class="chart-title">{e(head)}</p>{"".join(rows)}</div>'


def pill(rung):
    k = rung_key(rung)
    return f'<span class="pill r-{k}">{e(rung or "none")}</span>'


def status(s):
    cls, icon, label = STATUS.get((s or "ok").lower(), STATUS["ok"])
    return f'<span class="st {cls}"><b>{icon}</b>{e(label)}</span>'


def lines(xs):
    return "".join(f"<li>{x}</li>" for x in xs)


def md_inline(s):
    """Allow **bold** in the JSON strings; escape everything else."""
    s = e(s)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)


def render_html(r, thumbs):
    slides = r.get("slides", [])
    by_n = {s["n"]: s for s in slides}
    mh = r.get("must_have", {})
    parts = []

    # Header card
    note = f'<p class="note">{md_inline(r["note"])}</p>' if r.get("note") else ""
    missing_mh = ", ".join(mh.get("missing", [])) or "none"
    parts.append(f'''<header class="card hero">
  <div class="hero-top">
    <div><p class="eyebrow">Product image audit</p><h1>{e(r.get("product"))}</h1>
    <p class="meta">{e(r.get("slides_summary", ""))} · {e(r.get("category", ""))}</p></div>
    {ring(mh.get("have", 0), mh.get("total", 0), mh.get("partial", 0))}
  </div>
  {note}
  <dl class="facts">
    <div><dt>Missing must-haves</dt><dd>{md_inline(missing_mh)}</dd></div>
    <div><dt>Buyer's end goal</dt><dd>{md_inline(r.get("end_goal", ""))}</dd></div>
    <div><dt>Slide 1</dt><dd>{md_inline(r.get("slide1", ""))}</dd></div>
  </dl>
  <div class="gap"><span class="gap-k">Biggest gap</span><p>{md_inline(r.get("biggest_gap", ""))}</p></div>
</header>''')

    # Gallery strip
    cards = []
    for s in slides:
        cards.append(f'''<figure class="g">
  <div class="g-img">{tile(s["n"], thumbs)}<span class="num">{s["n"]}</span></div>
  <figcaption>{status(s.get("status"))}<p class="job">{e(s.get("what", ""))}</p>{pill(s.get("rung"))}</figcaption>
</figure>''')
    parts.append(f'''<section class="card"><h2>Your gallery, in order</h2>
  <p class="sub">What shoppers swipe through. Pill = how far the copy climbs: feature, benefit, or the buyer's end result.</p>
  <div class="strip">{"".join(cards)}</div>
  {rung_chart(slides)}
</section>''')

    # Slide by slide
    rows = []
    for s in slides:
        copy = s.get("copy") or "none"
        copy_html = f'<q>{e(copy)}</q>' if copy != "none" else '<span class="muted">No copy on it</span>'
        rows.append(f'''<div class="row">
  <div class="row-img">{tile(s["n"], thumbs)}<span class="num">{s["n"]}</span></div>
  <div class="row-body"><div class="row-head"><b>{e(s.get("what", ""))}</b>{status(s.get("status"))}</div>
  <p class="copy">{copy_html} {pill(s.get("rung"))}</p><p>{md_inline(s.get("note", ""))}</p></div>
</div>''')
    working = r.get("working", [])
    working_html = ('<div class="callout good"><h3>What&#39;s working</h3><ul>' + lines(md_inline(w) for w in working) + "</ul></div>") if working else ""
    parts.append(f'''<section class="card"><h2>What you have</h2>{"".join(rows)}
  {working_html}
</section>''')

    # Copy rewrites
    rw = []
    for c in r.get("rewrites", []):
        n = c.get("slide")
        rw.append(f'''<div class="rw">
  <div class="rw-img">{tile(n, thumbs)}<span class="num">{e(n)}</span></div>
  <div class="rw-body">
    <p class="before"><span class="tag">Now</span> <q>{e(c.get("now", ""))}</q> {pill(c.get("rung"))}</p>
    <p class="after"><span class="tag">Try</span> <q>{md_inline(c.get("try", ""))}</q></p>
    <p class="why">{md_inline(c.get("why", ""))}</p>
  </div></div>''')
    best = f'<div class="callout best"><h3>Best line in the gallery</h3><p>{md_inline(r["best_line"])}</p></div>' if r.get("best_line") else ""
    if rw or best:
        parts.append(f'<section class="card"><h2>Copy on your images</h2>{"".join(rw)}{best}</section>')

    # Checklist
    groups = {}
    for c in r.get("checklist", []):
        groups.setdefault(c.get("group", "Must-have"), []).append(c)
    if groups:
        cols = []
        for g, xs in groups.items():
            have = sum(1 for x in xs if x.get("state") == "yes")
            lis = []
            for x in xs:
                cls, icon = CHECK.get(x.get("state"), CHECK["no"])
                where = f" <em>{e(x['where'])}</em>" if x.get("where") else ""
                lis.append(f'<li class="ck {cls}"><b>{icon}</b><span>{md_inline(x.get("item", ""))}{where}</span></li>')
            items = "".join(lis)
            cols.append(f'<div class="ck-col"><h3>{e(g)} <span class="muted">{have}/{len(xs)}</span></h3><ul>{items}</ul></div>')
        parts.append(f'<section class="card"><h2>Shot checklist</h2><div class="ck-grid">{"".join(cols)}</div></section>')

    # Missing shots
    ms = []
    for i, m in enumerate(r.get("missing", []), 1):
        pr = (m.get("priority") or "").lower()
        existing = f'<p class="have-it">★ {md_inline(m["existing"])}</p>' if m.get("existing") else ""
        ms.append(f'''<article class="brief">
  <div class="brief-tile"><span class="new">NEW</span><span class="pos">#{e(m.get("position", "?"))}</span><span class="brief-shot">{e(m.get("message", ""))}</span></div>
  <div class="brief-body"><h3>{i}. {e(m.get("type", ""))} <span class="prio {'must' if pr.startswith('must') else 'should'}">{e(m.get("priority", ""))}</span></h3>
  <p>{md_inline(m.get("why", ""))}</p>
  <dl><dt>Shot</dt><dd>{md_inline(m.get("shot", ""))}</dd>
  <dt>Message</dt><dd>{md_inline(m.get("message", ""))}</dd>
  <dt>On-image text</dt><dd>{md_inline(m.get("text", "none"))}</dd>
  <dt>Put it at</dt><dd>position {e(m.get("position", ""))}</dd></dl>{existing}</div>
</article>''')
    if ms:
        parts.append(f'<section class="card"><h2>What&#39;s missing <span class="muted">most important first</span></h2><div class="briefs">{"".join(ms)}</div></section>')

    # Suggested order
    od = []
    for i, o in enumerate(r.get("order", []), 1):
        if o.get("new"):
            od.append(f'<div class="o o-new"><div class="tile ph nw"><span>NEW</span></div><span class="num">{i}</span><p>{md_inline(o.get("label", ""))}</p></div>')
        else:
            n = o.get("slide")
            cut = o.get("cut")
            od.append(f'<div class="o{" cut" if cut else ""}">{tile(n, thumbs)}<span class="num">{"cut" if cut else i}</span>'
                      f'<p>{"<b>Cut:</b> " if cut else ""}{md_inline(o.get("label", ""))}</p></div>')
    if od:
        extra = f'<p class="sub">{md_inline(r["order_note"])}</p>' if r.get("order_note") else ""
        parts.append(f'<section class="card"><h2>Suggested order</h2><div class="order">{"".join(od)}</div>{extra}</section>')

    # Callouts
    cl = []
    if r.get("fixes"):
        cl.append(f'<div class="callout fix"><h3>Fix in what you have</h3><ul>{lines(md_inline(x) for x in r["fixes"])}</ul></div>')
    if r.get("check"):
        cl.append(f'<div class="callout chk"><h3>Check these</h3><ul>{lines(md_inline(x) for x in r["check"])}</ul></div>')
    if cl:
        parts.append(f'<section class="duo">{"".join(cl)}</section>')

    tpl = open(TEMPLATE).read()
    tpl = tpl.replace("/*THUMBS*/", thumb_css(thumbs))
    return tpl.replace("{{TITLE}}", e(f"Image audit: {r.get('product', '')}")).replace("<!--BODY-->", "\n".join(parts))


def render_md(r):
    """The text version. Same words, laid out per references/report-template.md."""
    mh, out = r.get("must_have", {}), []
    out.append(f"## Product image audit: {r.get('product', '')}\n")
    if r.get("note"):
        out.append(r["note"] + "\n")
    out.append(f"**{r.get('slides_summary', '')}. {r.get('category', '')}.**")
    pt = f", {mh['partial']} partial" if mh.get("partial") else ""
    out.append(f"**Has {mh.get('have', 0)} of the {mh.get('total', 0)} shots every {r.get('category', '').lower()} page needs{pt}:** missing {', '.join(mh.get('missing', [])) or 'none'}.")
    out.append(f"**Buyer's end goal:** {r.get('end_goal', '')}")
    out.append(f"**Slide 1:** {r.get('slide1', '')}")
    out.append(f"**Biggest gap:** {r.get('biggest_gap', '')}\n")
    out.append("### What you have\n| # | What it is | Copy on it | Rung | Note |\n|---|---|---|---|---|")
    for s in r.get("slides", []):
        c = s.get("copy") or "none"
        c = f'"{c}"' if c != "none" else "none"
        out.append(f"| {s['n']} | {s.get('what', '')} | {c} | {s.get('rung', '')} | {s.get('note', '')} |")
    if r.get("working"):
        out.append("\n**What's working:**\n" + "\n".join(f"- {w}" for w in r["working"]))
    if r.get("rewrites") or r.get("best_line"):
        out.append("\n### Copy on your images")
        for c in r.get("rewrites", []):
            out.append(f"- **Slide {c.get('slide')}:** now \"{c.get('now', '')}\" ({c.get('rung', '')}). Try: \"{c.get('try', '')}\". {c.get('why', '')}")
        if r.get("best_line"):
            out.append(f"- **Best line:** {r['best_line']}")
    if r.get("missing"):
        out.append("\n### What's missing (most important first)")
        for i, m in enumerate(r["missing"], 1):
            out.append(f"{i}. **{m.get('type', '')}** ({m.get('priority', '')}). {m.get('why', '')}")
            out.append(f"   - **Shot:** {m.get('shot', '')}\n   - **Message:** {m.get('message', '')}\n   - **On-image text:** {m.get('text', 'none')}\n   - **Put it at:** position {m.get('position', '')}")
            if m.get("existing"):
                out.append(f"   - {m['existing']}")
    if r.get("order"):
        out.append("\n### Suggested order")
        for i, o in enumerate(r["order"], 1):
            pre = "NEW: " if o.get("new") else ("cut: " if o.get("cut") else f"Slide {o.get('slide')}, ")
            out.append(f"{i}. {pre}{o.get('label', '')}")
        if r.get("order_note"):
            out.append("\n" + r["order_note"])
    if r.get("fixes"):
        out.append("\n### Fix in what you have\n" + "\n".join(f"- {x}" for x in r["fixes"]))
    if r.get("check"):
        out.append("\n### Check these\n" + "\n".join(f"- {x}" for x in r["check"]))
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report")
    ap.add_argument("--gallery", default="./gallery", help="extractor output folder (for thumbnails)")
    ap.add_argument("--out", help="HTML file to write (default image-audit-<product>.html)")
    ap.add_argument("--md", action="store_true", help="print the markdown text version instead")
    a = ap.parse_args()
    r = json.load(open(a.report))
    if a.md:
        sys.stdout.write(render_md(r))
        return
    thumbs = load_thumbs(a.gallery)
    slug = re.sub(r"[^a-z0-9]+", "-", (r.get("product") or "product").lower()).strip("-")[:50] or "product"
    out = a.out or f"image-audit-{slug}.html"
    doc = render_html(r, thumbs)
    open(out, "w").write(doc)
    n = len(r.get("slides", []))
    print(json.dumps({"html": os.path.abspath(out), "kb": round(len(doc) / 1024), "slides": n,
                      "thumbs_embedded": sum(1 for s in r.get("slides", []) if s["n"] in thumbs),
                      "tiles_used": sum(1 for s in r.get("slides", []) if s["n"] not in thumbs)}))


if __name__ == "__main__":
    main()
