# The visual report (main deliverable)

The report is ONE self-contained HTML file with the shopper's real gallery as thumbnails, coloured
rung pills, a must-have ring, a copy chart, before/after cards, new-shot briefs and the suggested
order as a strip. `report-template.md` is still the content spec: the same sections, the same
rules, the same words. Only the presentation changes.

You don't write HTML. You write the audit as `report.json` (shape below), then run:

```bash
python3 <skill-dir>/scripts/render_report.py report.json --gallery ./gallery --out image-audit-<product>.html
```

It embeds the thumbnails the extractor saved (`gallery/thumbs/NN.jpg`, ~320px JPEG) as base64
data URIs, once each, so the file needs no internet, no external images and no scripts. It prints
`thumbs_embedded` and `tiles_used`. A slide without a thumbnail becomes a numbered coloured tile,
never a broken image. If you only have screenshots from the user, put them (or small copies) in
`<folder>/thumbs/01.jpg, 02.jpg, ...` in gallery order and pass that folder as `--gallery`.

**Where it goes:**
- **Claude Code / a terminal:** write `image-audit-<product>.html` in the working folder and give the path.
- **Claude app:** save the file to the outputs folder (for example `/mnt/user-data/outputs/`) so the user can open it. If you can't share files there, show it as an HTML artifact with the file's full contents, unchanged.
- Then write a 3-line chat summary: the must-have score, the biggest gap, and the single best copy fix.
- **Text version:** if the user asks for it (or can't open HTML), run `render_report.py report.json --md` and paste the output. Same words.

## report.json

Plain strings. `**bold**` is allowed in notes, fixes and checks. Don't add HTML.

```json
{
  "product": "Soft & Chewy Beef Training Treats (10 oz)",
  "category": "Pet treats",
  "note": "One line from the extractor notes or a confidence warning, or null",
  "slides_summary": "7 slides (7 photos, 0 videos)",
  "must_have": {"have": 3, "total": 5, "partial": 0, "missing": ["the ingredients panel", "how many to give"]},
  "end_goal": "what they really bought this to get",
  "slide1": "does it make the product obvious AND give one reason to buy?",
  "biggest_gap": "the single most valuable fix, one sentence",
  "slides": [
    {"n": 1, "what": "plain words", "copy": "exact words or none", "rung": "feature / benefit / end result / none (or slogan, claim no proof)",
     "status": "strong | ok | fix", "note": "what a buyer learns, then the problem or 'strong'"}
  ],
  "working": ["1-3 specific bullets (plus 'who it's for' when clear)"],
  "rewrites": [{"slide": 2, "now": "exact line", "rung": "feature", "try": "line that reaches the end goal", "why": "technique"}],
  "best_line": "the best line in the gallery and why it works",
  "checklist": [{"group": "Must-have | Should-have | Nice-to-have | Buyer questions", "item": "plain words", "state": "yes | partial | no", "where": "slide 3"}],
  "missing": [{"type": "plain words", "priority": "must | should", "why": "", "shot": "", "message": "", "text": "max ~8 words or none",
               "position": 3, "existing": "You already have X lower on the page. Use that. (or omit)"}],
  "order": [{"slide": 1, "label": "Hero (keep)"}, {"new": true, "label": "Review card"}, {"slide": 6, "cut": true, "label": "why it goes"}],
  "order_note": "optional extra line under the order",
  "fixes": ["Fix in what you have"],
  "check": ["Check these"]
}
```

How the pieces map:
- **Header:** product, category, `must_have` as a ring ("3/5 must-haves", partial shown in amber), the missing must-haves, end goal, slide 1, biggest gap.
- **Gallery strip:** every slide in order with its thumbnail, `status` as a green/amber/red chip (Strong / Improve / Fix, always with an icon and word), the job, and the rung pill.
- **Copy chart:** counts slides per rung (feature, benefit, end result, slogan/claim/none) from each slide's `rung`. Any rung text containing "end" counts as end result, then "benefit", then "feature"; anything else counts as none. So write the rung honestly ("mostly feature", "claim, no proof").
- **Rewrites:** before → after cards next to the slide's thumbnail. Skip slides already on the end-result rung.
- **Checklist:** ticks/crosses grouped by `group`. Use the category's must-have and should-have lists, plus a "Buyer questions" group for the 3-5 objections/FAQs from Step 4.
- **Missing:** one brief card per item with a "NEW #position" placeholder tile.
- **Order:** existing thumbnails, dashed NEW tiles, greyed "cut" tiles (put cuts at the end).
- **Fixes / Check these:** two compact callouts at the bottom.

Status guide: `strong` = keep as is; `ok` = works, one sharper line or small fix would help; `fix` = a real problem (wrong variant or size, claim with no proof, unreadable, throwaway copy on a key slide).
