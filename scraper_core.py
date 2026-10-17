#!/usr/bin/env python3
"""
Core scraper skripsi UNAIR Digital Collection (dipakai CLI + GUI).

Viewer FlipBuilder simpan tiap halaman sebagai JPG:
  <BASE>/<HASH>/files/mobile/<N>.jpg
Judul skripsi ada di <title> / meta og:title index.html.
"""

import html
import io
import re

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from PIL import Image
except ImportError:
    Image = None

BASE = "https://ir.unair.ac.id/uploaded_files/temporary/DigitalCollection"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    ),
    "Referer": BASE + "/",
}

GENERIC_TITLES = {"", "perpustakaan unair", "flipbuilder", "not found (#404)"}
_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def extract_hash(arg: str) -> str:
    """Ambil HASH dari URL index.html atau terima langsung HASH-nya."""
    m = re.search(r"DigitalCollection/([^/]+)", arg)
    if m:
        return m.group(1)
    return arg.strip().strip("/")


def img_url(h: str, page: int) -> str:
    return f"{BASE}/{h}/files/mobile/{page}.jpg"


def sanitize_filename(name: str, maxlen: int = 150) -> str:
    """Ubah judul jadi nama file aman Windows."""
    name = _ILLEGAL.sub("", name).strip().strip(".")
    name = re.sub(r"\s+", " ", name)
    if len(name) > maxlen:
        name = name[:maxlen].rsplit(" ", 1)[0]
    return name or "skripsi_unair"


def fetch_title(target: str, sess: requests.Session | None = None) -> str | None:
    """
    Ambil judul skripsi dari index.html.
    Coba og:title, <title>, meta Description; lewati judul generic.
    Return judul (str) atau None kalau tidak ketemu.
    """
    return fetch_title_detail(target, sess)["title"]


def _meta_content(page: str, key: str, value: str) -> str | None:
    """Ambil content dari <meta> berdasarkan atribut key=value, urutan atribut bebas."""
    for tag in re.findall(r"<meta\b[^>]*>", page, re.I):
        attrs = dict(
            (k.lower(), v)
            for k, v in re.findall(r'([\w:-]+)\s*=\s*"([^"]*)"', tag)
        )
        if attrs.get(key.lower(), "").lower() == value.lower():
            content = attrs.get("content")
            if content:
                return content
    return None


def fetch_title_detail(target: str, sess: requests.Session | None = None) -> dict:
    """
    Sama seperti fetch_title tapi ikut melaporkan apa yang terjadi.
    Return: {"title": str|None, "reason": str, "status": int|None, "url": str}
    """
    sess = sess or requests.Session()
    h = extract_hash(target)
    url = f"{BASE}/{h}/index.html"
    out = {"title": None, "reason": "", "status": None, "url": url}

    try:
        r = sess.get(url, headers=HEADERS, timeout=25, verify=False)
    except requests.RequestException as e:
        out["reason"] = f"gagal konek: {e.__class__.__name__}"
        return out

    out["status"] = r.status_code
    if r.status_code != 200:
        out["reason"] = f"index.html HTTP {r.status_code} (link mungkin kedaluwarsa)"
        return out

    t = r.text
    candidates = []
    for c in (_meta_content(t, "property", "og:title"),
              _meta_content(t, "name", "Description")):
        if c:
            candidates.append(c)
    m = re.search(r"<title>(.*?)</title>", t, re.S | re.I)
    if m:
        candidates.insert(1, m.group(1))

    seen = []
    for c in candidates:
        c = html.unescape(c).strip()
        c = re.sub(r"\s+", " ", c)
        if not c:
            continue
        seen.append(c)
        if c.lower() not in GENERIC_TITLES:
            out["title"] = c
            out["reason"] = "ok"
            return out

    if seen:
        out["reason"] = f"judul generik ({seen[0]!r}), bukan judul skripsi"
    else:
        out["reason"] = "tidak ada tag judul di index.html"
    return out


def fetch_total_pages(target: str, sess: requests.Session | None = None) -> int | None:
    """Ambil bookConfig.totalPageCount dari mobile/javascript/config.js. None kalau tidak ada."""
    sess = sess or requests.Session()
    h = extract_hash(target)
    url = f"{BASE}/{h}/mobile/javascript/config.js"
    try:
        r = sess.get(url, headers=HEADERS, timeout=25, verify=False)
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    m = re.search(r"totalPageCount\s*=\s*(\d+)", r.text)
    if m:
        n = int(m.group(1))
        return n if n > 0 else None
    return None


def download_page(sess: requests.Session, h: str, page: int):
    """Return bytes JPG atau None kalau halaman tidak ada."""
    r = sess.get(img_url(h, page), headers=HEADERS, timeout=30, verify=False)
    if r.status_code == 200 and r.headers.get("Content-Type", "").startswith("image"):
        return r.content
    return None


def scrape(target, on_page=None, on_status=None, should_stop=None,
           max_pages=2000, miss_tolerance=2, delay=0.15):
    """
    Download semua halaman. Return list of bytes (JPG).

    Callback opsional:
      on_page(page_no, kb)     -> tiap halaman berhasil
      on_status(text)          -> pesan status
      should_stop()            -> return True untuk membatalkan
    """
    import time

    def status(msg):
        if on_status:
            on_status(msg)

    h = extract_hash(target)
    status(f"HASH: {h}")
    sess = requests.Session()
    images = []
    misses = 0
    page = 1

    while page <= max_pages:
        if should_stop and should_stop():
            status("Dibatalkan.")
            break
        try:
            data = download_page(sess, h, page)
        except requests.RequestException as e:
            status(f"Halaman {page}: error jaringan ({e}); coba lagi...")
            time.sleep(1.0)
            continue

        if data is None:
            misses += 1
            if misses >= miss_tolerance:
                break
            page += 1
            continue

        misses = 0
        images.append(data)
        if on_page:
            on_page(page, len(data) // 1024)
        page += 1
        time.sleep(delay)

    return images


def images_to_pdf(images, out_pdf):
    """Gabung list bytes JPG jadi satu PDF. Return path atau raise."""
    if Image is None:
        raise RuntimeError("Pillow belum terpasang. Install: pip install pillow")
    if not images:
        raise ValueError("Tidak ada gambar.")
    pil = [Image.open(io.BytesIO(b)).convert("RGB") for b in images]
    pil[0].save(out_pdf, save_all=True, append_images=pil[1:])
    return out_pdf
