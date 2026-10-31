---
name: product-image-audit
description: Audits a product page's image gallery and the copy on each image. Finds missing shots, grades the copy, fixes the order. Use when someone shares a product page and asks about its images.
---

# Product Image Audit

You audit the image gallery (the carousel at the top of a product page). The goal is a short, specific report, delivered as a visual HTML report with the shopper's real images: what each image does, what's missing for this kind of product, the order to put them in, and a brief for every image they should add.

## Inputs

- **Best:** a product page URL.
- **Also fine:** screenshots of every gallery image in order, or the image files themselves.
- Optional: what the product is, who buys it, and where traffic comes from (ads, search). Never block on these. Ask only if the category is truly unclear.

## Step 1. Get every image, in order

Run the extractor. It needs Python 3 only.

```bash
python3 <skill-dir>/scripts/extract_gallery.py "<product-url>" --out ./gallery
```

It writes `./gallery/manifest.json` and one file per image (`01.png`, `02.jpg`, ...) in gallery order. It also saves small thumbnails (`thumbs/01.jpg`, ...) for the visual report. Read the summary it prints, and always read `notes`:

- `live_page_seen: false` (notes start with "COULD NOT SEE THE LIVE PAGE"): the browser failed, so the gallery, price and size may be wrong. Rerun the extractor once. If it still fails, look at the live page with a browser or fetch tool if you have one. If you can't, put this as the FIRST line of your report: "I couldn't load your live page, so this audit uses your store's product data. Check the slide count and price against your page." Never present a store-data-only gallery as what shoppers see.

- `confidence: high`: Shopify's product data, cross-checked against the live gallery markup. If the theme adds slides (a supplement facts card, a promo hero), the live gallery wins and `notes` says so. Images that only show after the shopper picks another colour, shade or flavour are removed (`hidden_variant_images` counts them). You audit the default variant.
- `confidence: medium`: taken from the page itself (gallery markup or product data in the page). Usually right. Double-check the count against the page if you can see it.
- `confidence: low` or `status: failed`: don't guess. Ask the user for screenshots of each gallery image in order (on a phone, swipe and screenshot each one). Say plainly that the page didn't let you read its gallery.
- `videos` > 0: the gallery has a video. You get its poster frame only. Treat it as a video slot and say you judged it from the poster frame.

`other_sources` lists every gallery candidate the script found and its size. If one of them is clearly bigger than what was picked, mention it under "Check these". If you have a browser or web-fetch tool, glance at the live page to confirm the count. If the manifest has fewer than 3 images and the page clearly shows more, say so and ask for screenshots.

`other_page_images` lists product images used further down the page. Download any that look relevant (by name) and check them before you suggest a new shoot. Telling someone "you already have this, move it up" is the most useful advice there is.

If you can't run scripts at all (some chat apps), ask for screenshots instead.

## Step 1b. Check the live page and the evidence pack (don't skip this)

The store's data and the live page often disagree. Shoppers see the live page, so it wins. Besides the gallery, the extractor saves an evidence pack. Go through all of it before you judge:

1. **Screenshots:** `live-mobile.png` and `live-desktop.png` (when Chrome is installed). Note pop-ups covering the gallery, the slide count you can see (dots, thumbnails), and whether slide 1 is a video.
2. **What the page actually sells:** `buy_box` in the manifest lists the prices and sizes near the top of the live page. If they differ from `product` (the store data), the live page is right. Check that the size, pack count and flavour shown in the images match it.
3. **Real numbers you can use:** `buy_box.claim_lines` and `page_text.txt` hold the page's own claims, ratings, review counts, study results and guarantees. Use them in your briefs, quoted exactly. Use a placeholder only when the page truly doesn't have the number.
4. **Videos:** `page_videos` lists videos on the page. Their poster frames are saved as `video-N-poster.jpg`. If a video sits in the gallery (check the screenshots), count it as a slide in its real position, even if the store data leaves it out.
5. **Other variants:** if `variant_sets` exists, open every `variants/sheet-NN.jpg`. Each is one colour/shade/flavour's first slides in order. Compare the same slot across sheets. A slide showing the default variant inside another variant's gallery (wrong shade, wrong colour, wrong bag) is a real, costly bug. List every one you find, by variant and slot.
6. If there are no screenshots (no Chrome) and you have a browser or fetch tool, look at the live page with it. If you can't, say under "Check these" that you couldn't see the live page.

## Step 2. Look at every image

Open every image file and look at it. Never classify from the file name or alt text alone. Those are hints, often wrong. For each image, record:

- **Position** (1 = the first thing a shopper sees).
- **Job:** one primary type from `references/image-types.md`, plus a secondary type if it clearly does two jobs.
- **Style:** studio, lifestyle, customer photo (UGC), on-model, close-up/texture, flat lay, graphic/infographic, before-after, render/illustration.
- **What a buyer learns from it**, in one plain line ("shows it fits in a back pocket").
- **The copy on it, word for word, and its rung:** feature, benefit, or end result (the buyer's real goal). Read `references/image-copy.md` before this step and grade every slide against it. This matters as much as the picture.
- **Problems:** text too small to read on a phone, cluttered, visibly blurry or pixelated on a phone, near-duplicate of another image, claims with no proof in the gallery, wrong variant, a branded name that doesn't say what it is, a throwaway slogan. A promo on the image is fine (on slide 1 it's good), but note it must come off when the promo ends.

Duplicates are judged by MESSAGE, not photo style. Three lifestyle photos that each carry a different claim (size, trainer use, mess-free) are three pieces of proof, not one job done three times. Praise one-claim-per-slide galleries.

**Resolution is a minor point.** Shoppers buy on what an image says, not its pixel count, and on mobile a fast load matters more than extra sharpness. Never tell a brand to upload bigger files just because some images are 1000px and others 3000px. Flag resolution only when an image looks blurry or pixelated on a phone, and then as a small fix at the bottom. If image files are very heavy (over ~500 KB each), say they slow the page on mobile and suggest compressing them.

Classification calls:
- A study result or clinical stat card is **results**. **Authority** is a person, organisation or seal vouching for it (doctor, vet, press, certification).
- An image doing three jobs: pick the job a buyer would remember after a one-second look, then one secondary. Flag the rest as clutter.

## Step 3. Work out the category

Decide what kind of product it is (supplement, skincare, makeup, apparel, accessory/gadget, pet, home/kitchen, food and drink). Use the page title, the product data in the manifest, and the images. Then open `references/category-needs.md` and use that category's list. If it's a mix (a pet supplement), combine the two lists and say so.

## Step 4. Find the gaps and fix the order

- Compare what they have against the category list: **must-have**, **should-have**, **nice-to-have**. Write it for a brand owner: name the shots in plain words ("a photo showing how big it is"), never the internal labels (hero, scale, social_proof). A type counts as covered when a buyer would get the answer from the gallery on a phone. If it's there but unreadable or buried in clutter, count it as partial and say so ("4 of 5 must-haves, 1 partial").
- Rank the missing types by how much they'd help a buyer decide, for THIS product. A $12 lip balm and a $325 oven need different proof.
- Check the order. The first three images do most of the work on a phone. Image 1 must make the product obvious AND carry one reason to buy (the UVP or the live promotion), for cold traffic. If the UVP only appears at slide 3, say move it (or a short version of it) onto slide 1. Images 2 and 3 should carry the strongest reason to buy and the strongest proof. Proof buried at position 9 counts as a problem.
- Spot overlap by message. Five near-identical colour shots with no copy are one job done five times. Different claims are not overlap.
- Note what they do well. Keep what works.
- Don't cap the gallery. A long gallery is good when every slide does its own job ("a good mix of benefits, shades and lifestyle"). Cut only true duplicates.
- Never cut a slide because the page shows it further down. Shoppers who don't scroll miss those sections, so key things (reviews, comparison, cross-sell, shade range) belong in the gallery AND on the page. "You already have it lower on the page, put it in the gallery too" is good advice. "Cut it, the page has it" is not.
- A cross-sell slide (a duo, a routine, a bundle) in the gallery is smart. Keep it. If there's none, mention it as an option.
- **Gaps to check on every page, beyond the category list:**
  - **Objections and FAQs.** Before judging the gallery, write down the 3-5 questions a buyer of THIS product has before buying: the worries (what is the coating made of, is it safe, does it really work) and the practical questions (will it work on my induction hob, can it go in the oven, does it fit my space). Then check which ones an image answers. Answering them on the images is one of the strongest things a gallery can do: credit it by name when present ("slide 3 goes straight at the PFAS worry, slide 4 answers induction and oven"), and list every unanswered one as a gap. A direct answer to a buyer's question ("Induction-safe", "Oven-safe to 550°F", "Made without PFAS") is good copy as it stands. Don't rewrite it into a benefit line that hides the answer.
  - **Real customers.** Testimonials and photos of real people (and their pets) using it, not only models or staged shots. Count model lifestyle shots separately from real-customer proof.
  - **Comparison.** In a crowded category (beauty, apparel basics, treats, supplements, coffee) a vs-other-brands or vs-the-old-way slide. Missing comparison is a should-have gap there. Name the leaders a buyer is weighing it against (greens: AG1, Huel) and frame the gap as the buyer's question: "Why should I pick this over AG1?"
  - **Who it's for.** Say which buyer the photos, models and colours speak to, and whether that's a clear choice. Clear targeting is a strength to keep, especially when it sets the brand apart from the category leaders (Bloom's imagery and colours speak to women, where AG1 and Huel lean male). Every suggested new shot should fit that same buyer.
  - **Read at a glance.** If the page shows the whole gallery at once (a grid laid out on the page, not a slider), and each image's message is 2-3 big words a shopper reads without clicking in, credit it. Short headline words on top with the full detail available (a 38-ingredients slide plus the full supplement facts) is the model.
  - **Taste, for anything you drink or eat.** If it's a drink or a powder you mix, how it tastes is a must-have image, not a nice-to-have.
  - **What's inside.** For anything eaten, drunk or put on skin: the ingredients or nutrition/supplement facts panel, front and centre. Transparency and proof of the claims matter more than perfect phone legibility. Never cut or bury a facts panel because the text is small. At most, suggest a bigger crop of the key lines alongside it.
  - **Proof of the slide-1 claims.** If slide 1 says "all natural, low calorie", something later must prove it.
  - **Bundles and multi-packs:** a slide explaining why buy the pack (why six), ideally backed by a review.
  - **Apparel and beauty:** several skin tones, body types or models, so different buyers can see themselves. Credit it when present.
- A big, well-known brand can get away with less proof. Say so in one line if it applies, but audit to the same bar.
- Audit the default variant in full. For the others, use the variant sheets from Step 1b. If you need a closer look at one, rerun with `--variant "<name>" --out ./gallery-v2`.
- Check the product in the images matches what the page sells (right size, flavour, pack count). A 10 oz bag shown on a 5 oz listing is a real problem.

## Step 4b. Fact-check before you write (5 minutes, don't skip)

Plain reviewers win points by catching small, checkable mistakes. Check these against the evidence pack and note each one you find:

1. **Numbers on the images vs the specs.** Every number, weight, size, dimension, count or temperature printed on a slide or diagram: compare it to `buy_box`, `page_text.txt` and the store data. A diagram saying 2.7 lb when the specs say 2.8 lb, or a height label that doesn't match the spec sheet, is a real fix. Also check claims in the copy match the product shown (a set's "storage included" on a single pan).
2. **Which slides each variant gets.** From the variant sheets: does every colour/flavour/size get its own photos, or do some only get a studio shot while the default gets lifestyle photos? Do any show an out-of-date label or the wrong variant? Name them.
3. **Price and currency.** If `final_url` has a locale (like /en-fr/) or the prices aren't in the store's home currency, say the page served a foreign version, and use the store data's price. Never quote euro prices to a US brand as its price.
4. **Video position.** If a video poster appears, confirm from the screenshots where it really sits in the gallery. Store data can list videos last when the page shows them earlier.
5. **Alt text.** Empty or generic alt text ("image 1", file names) on gallery images and videos hurts search and screen readers. List it as one small fix, not a headline.
6. **File size and sharpness.** Only per the resolution rule in Step 2: flag images that look blurry on a phone or files heavy enough to slow mobile. Mixed pixel sizes alone are not a problem.

Put mechanical findings under "Fix in what you have". Keep the headline of the report on strategy.

## Step 5. Write the report

The deliverable is a visual HTML report built from your audit. Read `references/report-artifact.md` first.

1. Write the audit as `report.json` (shape in `report-artifact.md`). The content follows `references/report-template.md`: same sections, same rules below.
2. Render it: `python3 <skill-dir>/scripts/render_report.py report.json --gallery ./gallery --out image-audit-<product>.html`. It embeds the gallery thumbnails, so the file works offline and inside an artifact.
3. Deliver the HTML: in Claude Code give the file path; in the Claude app share the file (or show it as an HTML artifact). Then a 3-line chat summary: must-have score, biggest gap, best copy fix.
4. If the user asks for a text version, run `render_report.py report.json --md` and paste it.

If you can't run scripts at all, write the markdown report from `report-template.md` instead.

Content rules (they apply to every field you write):

- **Be specific to this product.** "Add a scale shot" is weak. "Add a hand holding the pouch next to a phone, so people see it's pocket-sized" is the standard.
- **Don't invent facts.** If a brief needs a number (a clinical result, a review count, a dimension), use a placeholder like `[your clinical result]` unless the page or the user gave the real number.
- **Every missing image gets a shot brief:** what's in frame, the one message, the style, any on-image text (max ~8 words, written to the end-result rung), and where it goes in the order. Say when an existing asset could do it (a review screenshot, a photo already lower on the page).
- **Copy rewrites:** for every slide whose copy sits on the feature or benefit rung, or is a throwaway slogan, or is too wordy, give the current line and a sharper line that reaches the buyer's end goal. Name the technique. Lead the report with the strategic read (slide 1 reason to buy, copy, missing proof). Mechanical bugs (wrong variant, wrong size) go in "Fix in what you have".
- If the manifest confidence was medium or low, say so in one line at the top.
- End with "Check these": anything you couldn't confirm.

## Keep it on images

Alt text, page speed, SEO and Amazon rules are out of scope. Mention one only if it changes what a shopper sees in the gallery (a broken hero, a video with no poster frame that shows as a blank slide).

## What this skill does not do

- It doesn't generate images or claim the changes will lift sales by any amount.
- It doesn't audit the rest of the page (copy, sections, reviews widget).
