#!/usr/bin/env python3
"""Pull every image in a product page's gallery, in order.

Usage:
    python3 extract_gallery.py <product-page-url> [--out DIR] [--width 1200] [--render]

Writes DIR/manifest.json plus one image file per gallery item (01.jpg, 02.jpg ...).
Standard library only, so it runs anywhere Python 3.8+ runs.

How it finds the gallery, most reliable first:
  1. Shopify product data (<store>/products/<handle>.js). Exact order, media type, alt text,
     and which images belong to which variant (colour, size, flavour).
  2. Product data embedded in the page HTML (Shopify product JSON in a script tag, or
     schema.org Product JSON-LD).
  3. --render: the page as a browser draws it (headless Chrome, if installed), then the
     same parsing as step 2 plus the largest image group inside the product section.
If all of that fails, the manifest says so and the skill asks the user for screenshots.
"""
import argparse, json, os, re, shutil, signal, subprocess, sys, tempfile, time, urllib.parse, urllib.request, html as htmlmod
try:
    import fcntl
except ImportError:  # Windows: no cross-process lock, Chrome runs unqueued
    fcntl = None

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.geturl(), r.read()


def abs_url(u, base):
    if not u:
        return None
    u = htmlmod.unescape(u.strip())
    if u.startswith("//"):
        u = "https:" + u
    return urllib.parse.urljoin(base, u)


def sized(u, width):
    """Ask Shopify's image CDN for a smaller copy. Other hosts are left alone."""
    if not u:
        return u
    if "cdn.shopify.com" in u or "/cdn/shop/" in u:
        p = urllib.parse.urlparse(u)
        q = [(k, v) for k, v in urllib.parse.parse_qsl(p.query) if k != "width"]
        q.append(("width", str(width)))
        return urllib.parse.urlunparse(p._replace(query=urllib.parse.urlencode(q)))
    return u


def norm_key(u):
    """Same image at different sizes -> same key."""
    p = urllib.parse.urlparse(u or "")
    path = re.sub(r"_(\d+x\d*|\d*x\d+|small|medium|large|grande|master)(?=\.)", "", p.path)
    return path.rsplit("/", 1)[-1].lower()


# ---------- 1. Shopify product data ----------
VARIANT = None  # set from --variant


def shopify_media(page_url):
    p = urllib.parse.urlparse(page_url)
    m = re.search(r"/products/([^/?#]+)", p.path)
    if not m:
        return None, "no /products/<handle> in the URL"
    prefix = p.path[: m.start()]  # keeps locale prefixes like /en-us
    handle = m.group(1)
    for path in (f"{prefix}/products/{handle}.js", f"/products/{handle}.js"):
        try:
            _, body = fetch(f"{p.scheme}://{p.netloc}{path}")
            data = json.loads(body)
            break
        except Exception:
            data = None
    if not data or not isinstance(data, dict):
        return None, "Shopify product data not available"
    variant_media = {}
    variants = data.get("variants") or []
    # Shopify themes open on the first variant that is in stock
    default_v = next((v for v in variants if v.get("available")), variants[0] if variants else {})
    if VARIANT:
        pick = next((v for v in variants if VARIANT.lower() in (v.get("title") or "").lower()), None)
        if pick:
            default_v = pick
    first_opts = [o for o in (default_v.get("options") or []) if o] if variants else []
    all_opts = sorted({o for v in variants for o in (v.get("options") or []) if o})
    for v in variants:
        fm = v.get("featured_media") or {}
        if fm.get("id"):
            variant_media.setdefault(fm["id"], []).append(v.get("title"))
    items = []
    media = data.get("media") or []
    if media:
        for mm in media:
            prev = (mm.get("preview_image") or {}).get("src") or mm.get("src")
            items.append({
                "media_type": mm.get("media_type", "image"),
                "src": abs_url(prev, page_url),
                "alt": mm.get("alt") or "",
                "variants": variant_media.get(mm.get("id"), []),
                "video_sources": [s.get("url") for s in (mm.get("sources") or []) if s.get("url")][:1],
            })
    else:
        for src in data.get("images") or []:
            items.append({"media_type": "image", "src": abs_url(src, page_url), "alt": "", "variants": []})
    meta = {"title": data.get("title"), "vendor": data.get("vendor"), "type": data.get("type"),
            "price": (data.get("price") or 0) / 100 if isinstance(data.get("price"), int) else data.get("price"),
            "variant_count": len(data.get("variants") or []),
            "option_names": [o.get("name") if isinstance(o, dict) else o for o in data.get("options") or []],
            "default_variant": default_v.get("title") if variants else None}
    mark_default_view(items, first_opts, all_opts, default_v.get("title") if variants else None)
    return {"method": "shopify_product_data", "product": meta, "items": items}, None


def mark_default_view(items, first_opts, all_opts, first_title):
    """Work out which images a shopper sees before picking a colour/flavour/size.

    Stores keep every variant's photos in one list. Themes then show only the selected
    variant's set, using one of two common conventions:
      a) alt text = the variant's option value (e.g. "Onyx Black / M"), or
      b) each variant has one 'featured' image, and the rest are shared.
    """
    if not items:
        return
    def has(text, opt):
        return re.search(r"(?<![a-z0-9])" + re.escape(opt) + r"(?![a-z0-9])", (text or "").lower()) is not None
    opt_l = [o.lower() for o in all_opts if len(o) >= 3]
    first_l = [o.lower() for o in first_opts if len(o) >= 3]
    tagged = [it for it in items if any(has(it["alt"], o) for o in opt_l)]
    if opt_l and first_l and len(tagged) >= 0.6 * len(items):
        # convention a: alt-text grouping. Option values every image shares (a size) don't split groups.
        distinct = [o for o in first_l if sum(1 for it in items if has(it["alt"], o)) < len(items)] or first_l
        for it in items:
            hits = [o for o in opt_l if has(it["alt"], o)]
            it["shown_by_default"] = (not hits) or any(has(it["alt"], o) for o in distinct)
        return
    featured_by_other = [it for it in items if it.get("variants") and first_title not in it["variants"]]
    if featured_by_other:
        for it in items:
            it["shown_by_default"] = not (it.get("variants") and first_title not in it["variants"])
        return
    for it in items:
        it["shown_by_default"] = True


# ---------- 2/3. HTML parsing ----------
def from_html(page_html, page_url, method):
    items, meta = [], {}
    # Shopify themes often embed the product JSON in a script tag
    for blob in re.findall(r"<script[^>]*type=[\"']application/json[\"'][^>]*>(.*?)</script>", page_html, re.S):
        if '"media"' not in blob or '"variants"' not in blob:
            continue
        try:
            d = json.loads(blob)
        except Exception:
            continue
        d = d.get("product", d) if isinstance(d, dict) else d
        if isinstance(d, dict) and d.get("media"):
            for mm in d["media"]:
                prev = (mm.get("preview_image") or {}).get("src") or mm.get("src")
                items.append({"media_type": mm.get("media_type", "image"), "src": abs_url(prev, page_url),
                              "alt": mm.get("alt") or "", "variants": []})
            meta = {"title": d.get("title")}
            return {"method": method + ":embedded_product_json", "product": meta, "items": items}
    # schema.org Product JSON-LD
    for blob in re.findall(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", page_html, re.S):
        try:
            d = json.loads(blob.strip())
        except Exception:
            continue
        stack = d if isinstance(d, list) else [d]
        while stack:
            node = stack.pop(0)
            if isinstance(node, dict):
                if "@graph" in node:
                    stack.extend(node["@graph"])
                t = node.get("@type")
                if t == "Product" or (isinstance(t, list) and "Product" in t):
                    imgs = node.get("image")
                    imgs = imgs if isinstance(imgs, list) else [imgs]
                    for im in imgs:
                        src = im.get("url") if isinstance(im, dict) else im
                        if src:
                            items.append({"media_type": "image", "src": abs_url(src, page_url), "alt": "", "variants": []})
                    meta = {"title": node.get("name")}
                    if len(items) > 1:
                        return {"method": method + ":json_ld", "product": meta, "items": items}
    # Last resort: biggest run of product-looking images in the page
    cands = []
    for tag in re.findall(r"<img\b[^>]*>", page_html, re.I):
        src = None
        for attr in ("data-zoom", "data-src", "data-srcset", "srcset", "src"):
            m = re.search(attr + r"\s*=\s*[\"']([^\"']+)", tag, re.I)
            if m:
                src = m.group(1).split(",")[-1].strip().split(" ")[0]
                break
        if not src or src.startswith("data:") or re.search(r"(logo|icon|sprite|badge|flag|payment|avatar)", src, re.I):
            continue
        alt = re.search(r"alt\s*=\s*[\"']([^\"']*)", tag, re.I)
        cands.append({"media_type": "image", "src": abs_url(src, page_url), "alt": alt.group(1) if alt else "", "variants": []})
    if len(items) <= 1 and cands:
        seen, out = set(), []
        for c in cands:
            k = norm_key(c["src"])
            if k not in seen:
                seen.add(k)
                out.append(c)
        return {"method": method + ":img_tags_low_confidence", "product": meta, "items": out[:30]}
    if items:
        return {"method": method + ":json_ld_single", "product": meta, "items": items}
    return None


from html.parser import HTMLParser

GALLERY_RE = re.compile(r"(gallery|media|slider|slideshow|carousel|swiper|splide|flickity|slick|product[-_]?image|product__image|thumbnail|thumbs|zoom)", re.I)
NOT_GALLERY_RE = re.compile(r"(header|nav|menu|footer|drawer|cart|recommend|related|upsell|cross[-_]?sell|you[-_]?may|review|testimonial|collection|card|instagram|ugc[-_]?feed|logo|badge|icon|announcement|mega)", re.I)


class _Tree(HTMLParser):
    VOID = {"img", "br", "hr", "input", "meta", "link", "source", "area", "base", "col", "embed", "param", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.groups, self.n, self.order = [], {}, 0, 0
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style", "noscript", "template"):
            self.skip += 1
            if tag != "noscript":
                return
        label = " ".join(filter(None, [a.get("class"), a.get("id"), a.get("data-section-type"), a.get("aria-label")]))
        if tag == "img" or tag == "source":
            if self.skip:
                return
            src = None
            for attr in ("data-zoom", "data-zoom-src", "data-src", "data-srcset", "srcset", "src"):
                if a.get(attr):
                    src = a[attr].split(",")[-1].strip().split(" ")[0]
                    break
            if not src or src.startswith("data:"):
                return
            gal = None
            for node in reversed(self.stack):
                if NOT_GALLERY_RE.search(node[1]):
                    return
                if gal is None and GALLERY_RE.search(node[1]):
                    gal = node[0]
            if gal is not None:
                self.order += 1
                self.groups.setdefault(gal, []).append((self.order, src, a.get("alt") or ""))
            return
        if tag in self.VOID:
            return
        self.n += 1
        self.stack.append((self.n, label, tag))

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "template"):
            self.skip = max(0, self.skip - 1)
            if tag != "noscript":
                return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][2] == tag:
                del self.stack[i:]
                break


def gallery_groups(page_html, page_url):
    """Every group of 2+ distinct images inside a gallery-like container, in page order."""
    t = _Tree()
    try:
        t.feed(page_html)
    except Exception:
        return []
    groups = []
    for gid, imgs in sorted(t.groups.items(), key=lambda kv: kv[1][0][0]):
        seen, out = set(), []
        for _, src, alt in imgs:
            u = abs_url(src, page_url)
            if re.search(r"(logo|icon|sprite|payment|flag|avatar|placeholder)", u, re.I):
                continue
            k = norm_key(u)
            if k not in seen:
                seen.add(k)
                out.append({"media_type": "image", "src": u, "alt": alt, "variants": []})
        if len(out) >= 2:
            groups.append(out)
    return groups


def gallery_from_dom(page_html, page_url):
    """Largest early group of product images that sits inside a gallery-like container."""
    t = _Tree()
    try:
        t.feed(page_html)
    except Exception:
        return []
    best = []
    for gid, imgs in sorted(t.groups.items(), key=lambda kv: kv[1][0][0]):
        seen, out = set(), []
        for _, src, alt in imgs:
            u = abs_url(src, page_url)
            if re.search(r"(logo|icon|sprite|payment|flag|avatar|placeholder)", u, re.I):
                continue
            k = norm_key(u)
            if k not in seen:
                seen.add(k)
                out.append({"media_type": "image", "src": u, "alt": alt, "variants": []})
        if len(out) >= 3:
            return out  # first sizeable gallery in page order
        if len(out) > len(best):
            best = out
    return best


def embedded_image_arrays(page_html, page_url, title=None):
    """Product JSON blobs that theme scripts load (e.g. a flavour's own product)."""
    out = []
    for m in re.finditer(r'"images"\s*:\s*\[((?:\s*"[^"]+"\s*,?)+)\]', page_html):
        arr = [abs_url(x.replace("\\/", "/"), page_url) for x in re.findall(r'"([^"]+)"', m.group(1))]
        arr = [u for u in arr if re.search(r"\.(jpe?g|png|webp|avif)", u, re.I)]
        if len(arr) >= 2:
            out.append([{"media_type": "image", "src": u, "alt": "", "variants": []} for u in arr])
    return out


def variant_sets(library, all_variant_titles, out_dir, width=300, per=8):
    """Small copies of the first slides of every variant's gallery, so a wrong-variant slide is easy to spot."""
    if not library or not any(x.get("variants") for x in library):
        return []
    groups, current = [], None
    for x in library:
        if x.get("variants"):
            current = {"variant": ", ".join(map(str, x["variants"][:2])), "items": []}
            groups.append(current)
        if current is not None:
            current["items"].append(x)
    if len(groups) < 2:
        return []
    made = []
    for gi, g in enumerate(groups[:8], 1):
        d = os.path.join(out_dir, "variants", f"{gi:02d}")
        os.makedirs(d, exist_ok=True)
        files = []
        for i, x in enumerate(g["items"][:per], 1):
            try:
                _, data = fetch(sized(x["src"], width), timeout=30)
                f = os.path.join(d, f"{i:02d}.jpg")
                open(f, "wb").write(data)
                files.append(f)
            except Exception:
                pass
        sheet = None
        if files and shutil.which("montage"):
            sheet = os.path.join(out_dir, "variants", f"sheet-{gi:02d}.jpg")
            subprocess.run(["montage", *files, "-resize", "300x300", "-tile", f"{len(files)}x1", "-geometry", "+2+2", sheet],
                           capture_output=True, timeout=60)
            sheet = sheet if os.path.exists(sheet) else None
        made.append({"variant": g["variant"], "files": files, "sheet": sheet})
    return made


def find_chrome():
    return next((c for c in ("google-chrome", "chromium", "chromium-browser", "chrome") if shutil.which(c)), None)


RENDER_LOG = []


def run_chrome(args, timeouts=(90, 150), text=False, ok=lambda r: True):
    """Run headless Chrome safely when several audits run at once.

    Each call gets its own throwaway profile, waits its turn on a machine-wide lock
    (several Chromes at once overload small machines and every one of them hangs),
    kills the whole Chrome process tree on timeout, and retries once with more time.
    """
    chrome = find_chrome()
    if not chrome:
        RENDER_LOG.append("no Chrome/Chromium installed")
        return None
    lock = None
    if fcntl:
        lock = open(os.path.join(tempfile.gettempdir(), "product-image-audit-chrome.lock"), "w")
        fcntl.flock(lock, fcntl.LOCK_EX)  # queue behind other audits' Chrome runs
    try:
        for attempt, t in enumerate(timeouts, 1):
            prof = tempfile.mkdtemp(prefix="pia-chrome-")
            cmd = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage",
                   "--no-first-run", f"--user-data-dir={prof}", f"--user-agent={UA}"] + args
            started = time.time()
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=text,
                                    start_new_session=True)
            try:
                out, _ = proc.communicate(timeout=t)
                if ok(out):
                    return out if out is not None else ""
                RENDER_LOG.append(f"attempt {attempt}: Chrome finished in {time.time()-started:.0f}s but returned nothing usable")
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except Exception:
                    proc.kill()
                proc.communicate()
                RENDER_LOG.append(f"attempt {attempt}: Chrome timed out after {t}s")
            finally:
                shutil.rmtree(prof, ignore_errors=True)
        return None
    finally:
        if lock:
            fcntl.flock(lock, fcntl.LOCK_UN)
            lock.close()


def screenshot(url, path, width, height):
    got = run_chrome(["--hide-scrollbars", "--virtual-time-budget=12000", f"--window-size={width},{height}",
                      f"--screenshot={path}", url],
                     ok=lambda _: os.path.exists(path) and os.path.getsize(path) > 5000)
    return got is not None


def page_facts(page_html):
    def meta(prop):
        m = re.search(r'<meta[^>]+(?:property|name)=["\']' + re.escape(prop) + r'["\'][^>]+content=["\']([^"\']*)', page_html, re.I)
        return htmlmod.unescape(m.group(1)).strip() if m else None
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page_html, re.S | re.I)
    return {"title": meta("og:title"), "price": meta("og:price:amount") or meta("product:price:amount"),
            "currency": meta("og:price:currency") or meta("product:price:currency"),
            "h1": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h1.group(1))).strip()[:150] if h1 else None}


def visible_text(page_html):
    t = re.sub(r"<(script|style|noscript|template|svg)[^>]*>.*?</\1>", " ", page_html, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>|</(p|div|li|h[1-6]|tr|section|button|span)>", "\n", t, flags=re.I)
    t = htmlmod.unescape(re.sub(r"<[^>]+>", " ", t))
    lines = [re.sub(r"[ \t]+", " ", x).strip() for x in t.split("\n")]
    out, prev = [], None
    for x in lines:
        if x and x != prev and len(x) < 400:
            out.append(x)
            prev = x
    return "\n".join(out)


def buy_box_hints(text):
    """Prices and sizes as the shopper reads them, near the top of the page."""
    head = text[:6000]
    prices = re.findall(r"(?:[$€£]\s?\d[\d,.]*|\d[\d,.]*\s?(?:USD|EUR|GBP|€))", head)
    sizes = re.findall(r"\b\d+(?:[.,]\d+)?\s?(?:oz|fl ?oz|ml|mL|g|kg|lb|lbs|ct|count|pack|pcs|capsules|gummies|servings)\b", head, re.I)
    claims = [l for l in text.split("\n") if re.search(r"(\d+%|clinically|study|reviews?|rated|stars?|customers|guarantee|tested)", l, re.I)][:40]
    def uniq(xs):
        seen, o = set(), []
        for x in xs:
            if x not in seen:
                seen.add(x); o.append(x)
        return o
    return {"prices_near_top": uniq(prices)[:8], "sizes_near_top": uniq(sizes)[:8], "claim_lines": uniq(claims)}


def page_videos(page_html, page_url):
    out = []
    for m in re.finditer(r"<video\b[^>]*>(.*?)</video>", page_html, re.S | re.I):
        tag = page_html[m.start(): page_html.find(">", m.start()) + 1]
        poster = re.search(r'poster=["\']([^"\']+)', tag)
        src = re.search(r'src=["\']([^"\']+\.(?:mp4|webm|m3u8)[^"\']*)', m.group(0))
        if poster or src:
            out.append({"poster": abs_url(poster.group(1), page_url) if poster else None,
                        "src": abs_url(src.group(1), page_url) if src else None,
                        "autoplay": "autoplay" in tag.lower()})
    return out[:6]


def render_html(url):
    return run_chrome(["--virtual-time-budget=12000", "--window-size=430,2400", "--dump-dom", url],
                      text=True, ok=lambda out: bool(out) and len(out) > 2000)


def noscript_gallery(page_html, page_url):
    """Some themes print a plain list of the gallery for no-JS visitors right after the title."""
    for m in re.finditer(r"<noscript>(.*?)</noscript>", page_html, re.S | re.I):
        b = m.group(1)
        if "<h1" in b.lower():
            srcs = re.findall(r"<img[^>]*src=[\"']([^\"']+)", b, re.I)
            if len(srcs) >= 2:
                return [{"media_type": "image", "src": abs_url(u, page_url), "alt": "", "variants": []} for u in srcs]
    return []


def dedupe(items):
    seen, out = set(), []
    for it in items:
        k = norm_key(it["src"])
        if k not in seen:
            seen.add(k)
            out.append(it)
    return out


def page_candidates(page_html, url, label, hero_keys=()):
    c = []
    groups = gallery_groups(page_html, url)
    if hero_keys:
        # the real gallery shows the product's own main image; kit/accessory carousels don't
        with_hero = [g for g in groups if any(norm_key(x["src"]) in hero_keys for x in g[:3])]
        if with_hero:
            c.append((label + ":gallery_container", dedupe(max(with_hero, key=len))))
    else:
        g = next((g for g in groups if len(g) >= 3), max(groups, key=len) if groups else None)
        if g:
            c.append((label + ":gallery_container", dedupe(g)))
    for arr in embedded_image_arrays(page_html, url):
        c.append((label + ":embedded_image_list", dedupe(arr)))
    n = noscript_gallery(page_html, url)
    if n:
        c.append((label + ":noscript_gallery", dedupe(n)))
    h = from_html(page_html, url, label)
    if h and h.get("items"):
        c.append((h["method"], dedupe(h["items"])))
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out", default="gallery")
    ap.add_argument("--width", type=int, default=1200)
    ap.add_argument("--no-render", action="store_true", help="never use the headless-browser fallback")
    ap.add_argument("--no-download", action="store_true")
    ap.add_argument("--variant", help="audit the gallery a shopper sees after picking this variant (part of its name)")
    a = ap.parse_args()
    global VARIANT
    VARIANT = a.variant
    os.makedirs(a.out, exist_ok=True)
    notes = []

    url = a.url
    try:
        final, body = fetch(url)
        url = final
        page_html = body.decode("utf-8", "replace")
    except Exception as e:
        page_html = ""
        notes.append(f"could not load the page directly: {e}")

    dom = None
    shop, why = shopify_media(url)
    if not shop:
        notes.append(why)
    library = dedupe(shop["items"]) if shop else []
    shop_default = [it for it in library if it.get("shown_by_default", True)]

    hero_keys = {norm_key(x["src"]) for x in library[:1]} | {norm_key(x["src"]) for x in shop_default[:1]}
    hero_keys |= {norm_key(x["src"]) for x in library if x.get("variants")}
    cands = page_candidates(page_html, url, "html", hero_keys) if page_html else []
    rendered = False
    best_page = max((c for c in cands if not c[0].endswith("low_confidence")), key=lambda c: len(c[1]), default=None)
    if not a.no_render and len(shop_default) < 3 and (not best_page or len(best_page[1]) < 3):
        dom = render_html(url)
        if dom:
            rendered = True
            cands += page_candidates(dom, url, "rendered", hero_keys)
        else:
            notes.append("browser render failed: " + "; ".join(RENDER_LOG[-2:]))

    live_dom = None
    if not a.no_render and find_chrome():
        live_dom = dom if rendered else render_html(url)
        for name, w, h in (("live-mobile.png", 390, 1600), ("live-desktop.png", 1440, 1400)):
            if not screenshot(url, os.path.join(a.out, name), w, h):
                notes.append(f"{name} screenshot failed: " + "; ".join(RENDER_LOG[-2:]))
    usable = [c for c in cands if not c[0].endswith("low_confidence") and len(c[1]) >= 2]
    best_page = max(usable, key=lambda c: len(c[1]), default=None)

    chosen, method, confidence = None, None, None
    if len(shop_default) >= 3:
        chosen, method, confidence = shop_default, "shopify_product_data", "high"
        gal = max((c for c in usable if ":gallery_container" in c[0]), key=lambda c: len(c[1]), default=None)
        if gal and len(gal[1]) != len(shop_default):
            lib_keys = {norm_key(x["src"]) for x in library}
            def_keys = {norm_key(x["src"]) for x in shop_default}
            gal_keys = [norm_key(x["src"]) for x in gal[1]]
            covers_default = sum(1 for k in def_keys if k in gal_keys) / max(1, len(def_keys))
            from_library = sum(1 for k in gal_keys if k in lib_keys) / len(gal_keys)
            if len(gal[1]) > len(shop_default) and covers_default >= 0.5:
                chosen, method, confidence = gal[1], gal[0], "high"
                notes.append(f"the live gallery has {len(gal[1])} slides, the store's product data {len(shop_default)}: "
                             "the theme adds or swaps slides, so the live gallery is used")
            elif len(gal[1]) > len(shop_default) + 1 and from_library < 0.5:
                chosen, method, confidence = gal[1], gal[0], "medium"
                notes.append("the page shows a custom gallery that differs from the store's product image list")
            elif len(gal[1]) > len(shop_default):
                confidence = "medium"
                notes.append(f"store data says {len(shop_default)} images, page markup shows {len(gal[1])}: check the live page")
    elif best_page:
        nos = next((c for c in usable if c[0].endswith(":noscript_gallery")), None)
        if nos and len(nos[1]) >= 3:
            best_page = nos
        chosen, method = best_page[1], best_page[0]
        confidence = "medium" if (":embedded" in method or ":gallery" in method or ":noscript" in method or "json" in method) else "low"
        if shop_default:
            notes.append(f"store image list has only {len(shop_default)} image(s), the page gallery has {len(chosen)}")
    elif shop_default:
        chosen, method, confidence = shop_default, "shopify_product_data", "medium"
    else:
        low = [c for c in cands if c[1]]
        if low:
            chosen, method, confidence = low[0][1][:30], low[0][0], "low"

    if not chosen:
        manifest = {"url": a.url, "status": "failed", "notes": notes,
                    "next_step": "Ask the user for screenshots of every gallery image, in order."}
        json.dump(manifest, open(os.path.join(a.out, "manifest.json"), "w"), indent=2)
        print(json.dumps(manifest, indent=2))
        sys.exit(2)

    shots = [n for n in ("live-mobile.png", "live-desktop.png") if os.path.exists(os.path.join(a.out, n))]
    live_seen = bool(live_dom) or bool(shots)
    if not a.no_render and not live_seen:
        notes.insert(0, "COULD NOT SEE THE LIVE PAGE: the browser render and screenshots all failed. "
                        "Gallery, prices and sizes come from store data only and may not match what shoppers see.")
        if rendered is False and method == "shopify_product_data" and len(shop_default) < 3:
            confidence = "low"
    items = dedupe(chosen)
    for i, it in enumerate(items, 1):
        it["position"] = i
        if a.no_download:
            continue
        try:
            _, data = fetch(sized(it["src"], a.width), timeout=40)
            ext = (".png" if data[:8] == b"\x89PNG\r\n\x1a\n" else ".webp" if data[8:12] == b"WEBP" else
                   ".gif" if data[:3] == b"GIF" else ".avif" if b"ftypavif" in data[:32] else ".jpg")
            path = os.path.join(a.out, f"{i:02d}{ext}")
            open(path, "wb").write(data)
            it["file"] = path
        except Exception as e:
            it["file"] = None
            it["download_error"] = str(e)

    gal_keys = {norm_key(x["src"]) for x in items}
    others, seenk = [], set()
    for u in re.findall(r"(?:https?:)?//[^\s\"'()<>]+?/(?:cdn/shop/files|s/files)/[^\s\"'()<>]+?\.(?:jpe?g|png|webp)", page_html, re.I):
        k = norm_key(u)
        if k in gal_keys or k in seenk or re.search(r"(logo|icon|badge|flag|payment|nav|menu|thumb)", u, re.I):
            continue
        seenk.add(k)
        others.append(abs_url(u, url))
    manifest = {
        "url": a.url, "final_url": url, "status": "ok", "method": method, "confidence": confidence,
        "rendered": rendered, "live_page_seen": live_seen if not a.no_render else None, "product": (shop or {}).get("product", {}), "count": len(items),
        "variant_names": sorted({t for x in library for t in (x.get("variants") or [])})[:30] if shop else [],
        "videos": sum(1 for x in items if x["media_type"] != "image"),
        "store_library_count": len(library),
        "hidden_variant_images": len(library) - len(shop_default) if shop else 0,
        "other_sources": [[c[0], len(c[1])] for c in cands],
        "notes": notes, "items": items,
        "other_page_images": others[:40],
        "page_facts": page_facts(live_dom or page_html),
        "page_videos": page_videos(live_dom or page_html, url),
        "buy_box": buy_box_hints(visible_text(live_dom or page_html)),
        "live_screenshots": shots,
    }
    open(os.path.join(a.out, "page_text.txt"), "w").write(visible_text(live_dom or page_html)[:40000])
    if not a.no_download:
        manifest["variant_sets"] = variant_sets(library, None, a.out)
        for vi, v in enumerate(manifest["page_videos"][:3], 1):
            if v.get("poster"):
                try:
                    _, data = fetch(v["poster"], timeout=30)
                    f = os.path.join(a.out, f"video-{vi}-poster.jpg")
                    open(f, "wb").write(data)
                    v["poster_file"] = f
                except Exception:
                    pass
    json.dump(manifest, open(os.path.join(a.out, "manifest.json"), "w"), indent=2)
    print(json.dumps({k: v for k, v in manifest.items() if k not in ("items", "other_page_images", "variant_sets")}, indent=2))
    for it in items:
        print(f"{it['position']:02d} {it['media_type']} alt={it['alt'][:70]!r} {it['src'].rsplit('/',1)[-1][:60]}")


if __name__ == "__main__":
    main()
