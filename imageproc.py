"""Image standardisation for the wardrobe.

Takes a photo (any size, any plain-ish background) and returns a clean,
uniform, transparent-background PNG so every piece looks consistent and
outfits can be composed (top stacked over bottom).

Background removal:
  * If the optional `rembg` package is installed, it is used — this handles
    busy backgrounds and tricky (e.g. very light) garments well.
  * Otherwise a dependency-free corner flood-fill is used, which works great
    for plain/solid backgrounds (most product photos) and needs only Pillow.
"""

import base64
import io

from PIL import Image, ImageDraw

# Optional, much stronger background remover. Absent by default.
try:
    from rembg import remove as _rembg_remove  # type: ignore
    _HAS_REMBG = True
except Exception:  # pragma: no cover - optional dependency
    _HAS_REMBG = False

CANVAS = (900, 1100)      # standard frame every piece is fitted into
MARGIN = 0.08             # breathing room around the garment
MAX_INPUT = 1400          # downscale huge uploads before working on them


def _flood_remove_bg(img, thresh=34):
    """Make the outer (plain) background transparent via corner flood-fill."""
    rgb = img.convert("RGB")
    w, h = rgb.size
    sentinel = (255, 0, 255)
    seeds = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
             (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]
    for xy in seeds:
        try:
            ImageDraw.floodfill(rgb, xy, sentinel, thresh=thresh)
        except Exception:
            pass
    src = rgb.load()
    out = img.convert("RGBA")
    dst = out.load()
    for y in range(h):
        for x in range(w):
            if src[x, y] == sentinel:
                dst[x, y] = (0, 0, 0, 0)
    return out


def _remove_bg(img):
    if _HAS_REMBG:
        try:
            return _rembg_remove(img.convert("RGBA"))
        except Exception:
            pass
    return _flood_remove_bg(img)


def _trim_and_pad(img, canvas=CANVAS, margin=MARGIN):
    bbox = img.getbbox()
    if not bbox:
        return img
    g = img.crop(bbox)
    cw, ch = canvas
    maxw, maxh = int(cw * (1 - margin * 2)), int(ch * (1 - margin * 2))
    r = min(maxw / g.width, maxh / g.height)
    g = g.resize((max(1, int(g.width * r)), max(1, int(g.height * r))), Image.LANCZOS)
    out = Image.new("RGBA", canvas, (0, 0, 0, 0))
    out.paste(g, ((cw - g.width) // 2, (ch - g.height) // 2), g)
    return out


def _downscale(img, longest=MAX_INPUT):
    m = max(img.size)
    if m > longest:
        r = longest / m
        img = img.resize((int(img.width * r), int(img.height * r)), Image.LANCZOS)
    return img


def _to_png_data_url(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _data_url_to_image(data_url):
    header, _, b64 = data_url.partition(",")
    if "base64" not in header:
        raise ValueError("not a base64 data URL")
    return Image.open(io.BytesIO(base64.b64decode(b64)))


def standardize(data_url, remove_bg=True):
    """Return a standardised transparent-PNG data URL, or the input unchanged
    if it isn't a processable data URL."""
    if not isinstance(data_url, str) or not data_url.startswith("data:image"):
        return data_url
    img = _data_url_to_image(data_url)
    img = _downscale(img)
    img = _remove_bg(img) if remove_bg else img.convert("RGBA")
    img = _trim_and_pad(img)
    return _to_png_data_url(img)


def has_rembg():
    return _HAS_REMBG
