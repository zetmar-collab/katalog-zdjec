import io
import logging
import os
from datetime import datetime
from fractions import Fraction
from pathlib import Path

from PIL import Image, ExifTags

from core.gps import parse_gps_dms

try:
    import exifread
    HAS_EXIFREAD = True
except ImportError:
    HAS_EXIFREAD = False

log = logging.getLogger(__name__)

# Standardowe formaty obsługiwane przez Pillow
PILLOW_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tiff', '.heic'}

# Formaty RAW (wymagają exifread do metadanych, embedded JPEG do miniatur)
RAW_EXTENSIONS = {
    '.cr2', '.cr3',   # Canon
    '.nef', '.nrw',   # Nikon
    '.arw', '.srf', '.sr2',  # Sony
    '.orf',           # Olympus
    '.rw2',           # Panasonic
    '.dng',           # Adobe DNG (universal)
    '.raf',           # Fujifilm
    '.pef', '.ptx',   # Pentax
    '.srw',           # Samsung
    '.3fr',           # Hasselblad
    '.mrw',           # Minolta
    '.erf',           # Epson
    '.kdc', '.dcr',   # Kodak
    '.x3f',           # Sigma
    '.rwl',           # Leica
    '.mef',           # Mamiya
}

SUPPORTED_EXTENSIONS = PILLOW_EXTENSIONS | RAW_EXTENSIONS

EXIF_DATE_TAGS = [
    'DateTimeOriginal',
    'DateTimeDigitized',
    'DateTime',
]


# ---------------------------------------------------------------------------
# Pillow helpers
# ---------------------------------------------------------------------------

def _get_exif_dict(img):
    try:
        raw = img._getexif()
        if not raw:
            return {}
        return {ExifTags.TAGS.get(k, k): v for k, v in raw.items()}
    except Exception:
        return {}


def _parse_exif_date(date_str):
    for fmt in ('%Y:%m:%d %H:%M:%S', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


# ---------------------------------------------------------------------------
# exifread helpers (RAW)
# ---------------------------------------------------------------------------

def _exifread_decimal(tag_values, ref):
    """Konwertuje DMS z exifread na dziesiętne stopnie."""
    try:
        d = float(Fraction(str(tag_values[0])))
        m = float(Fraction(str(tag_values[1])))
        s = float(Fraction(str(tag_values[2])))
        decimal = d + m / 60 + s / 3600
        if str(ref).strip().upper() in ('S', 'W'):
            decimal = -decimal
        return decimal
    except Exception:
        return None


def _read_exif_raw(path):
    """Czyta metadane EXIF z pliku RAW przy użyciu exifread."""
    result = {'date_taken': None, 'lat': None, 'lon': None, 'exif': {}}
    if not HAS_EXIFREAD:
        return result
    try:
        with open(path, 'rb') as f:
            tags = exifread.process_file(f, details=True, strict=False)

        # Data
        for tag_name in ('EXIF DateTimeOriginal', 'EXIF DateTimeDigitized', 'Image DateTime'):
            if tag_name in tags:
                dt = _parse_exif_date(str(tags[tag_name]))
                if dt:
                    result['date_taken'] = dt
                    break

        # GPS
        lat_tag = tags.get('GPS GPSLatitude')
        lat_ref = tags.get('GPS GPSLatitudeRef')
        lon_tag = tags.get('GPS GPSLongitude')
        lon_ref = tags.get('GPS GPSLongitudeRef')
        if lat_tag and lat_ref and lon_tag and lon_ref:
            result['lat'] = _exifread_decimal(lat_tag.values, lat_ref)
            result['lon'] = _exifread_decimal(lon_tag.values, lon_ref)

        # Wszystkie tagi jako stringi (z pominięciem binarnych)
        result['exif'] = {
            k: str(v) for k, v in tags.items()
            if not k.startswith(('Thumbnail', 'JPEGThumbnail'))
        }
    except Exception as e:
        log.debug("exifread error %s: %s", path, e)
    return result


# ---------------------------------------------------------------------------
# Thumbnail extraction
# ---------------------------------------------------------------------------

def _extract_embedded_jpeg(path, size=(150, 150)):
    """Wyodrębnia osadzony podgląd JPEG z pliku RAW (pierwsze 20 MB)."""
    try:
        with open(path, 'rb') as f:
            data = f.read(20 * 1024 * 1024)

        # Znajdź największy blok JPEG
        best = None
        start = 0
        while True:
            pos = data.find(b'\xff\xd8\xff', start)
            if pos == -1:
                break
            end = data.find(b'\xff\xd9', pos)
            if end == -1:
                start = pos + 3
                continue
            blob = data[pos:end + 2]
            if len(blob) > len(best or b''):
                best = blob
            start = pos + 3

        if not best or len(best) < 5000:
            return None

        img = Image.open(io.BytesIO(best))
        img.thumbnail(size, Image.LANCZOS)
        buf = io.BytesIO()
        img.convert('RGB').save(buf, format='JPEG', quality=70)
        return buf.getvalue()
    except Exception:
        return None


def make_thumbnail(path, size=(150, 150)):
    path = Path(path)
    is_raw = path.suffix.lower() in RAW_EXTENSIONS

    if is_raw:
        thumb = _extract_embedded_jpeg(path, size)
        if thumb:
            return thumb
        # DNG może być otwieralny przez Pillow (TIFF-based) — próbujemy
    try:
        with Image.open(path) as img:
            img = img.copy()
            try:
                exif = img._getexif()
                if exif:
                    for k, v in exif.items():
                        if ExifTags.TAGS.get(k) == 'Orientation':
                            rotations = {3: 180, 6: 270, 8: 90}
                            if v in rotations:
                                img = img.rotate(rotations[v], expand=True)
                            break
            except Exception:
                pass
            img.thumbnail(size, Image.LANCZOS)
            buf = io.BytesIO()
            img.convert('RGB').save(buf, format='JPEG', quality=70)
            return buf.getvalue()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def read_exif(path):
    path = Path(path)
    is_raw = path.suffix.lower() in RAW_EXTENSIONS

    if is_raw:
        result = _read_exif_raw(path)
    else:
        result = {'date_taken': None, 'lat': None, 'lon': None, 'exif': {}}
        try:
            with Image.open(path) as img:
                exif = _get_exif_dict(img)
                result['exif'] = {k: str(v) for k, v in exif.items() if k != 'GPSInfo'}
                for tag in EXIF_DATE_TAGS:
                    if tag in exif:
                        dt = _parse_exif_date(exif[tag])
                        if dt:
                            result['date_taken'] = dt
                            break
                gps_info = exif.get('GPSInfo')
                if gps_info:
                    lat, lon = parse_gps_dms(gps_info)
                    result['lat'] = lat
                    result['lon'] = lon
        except Exception:
            pass

    if result['date_taken'] is None:
        mtime = os.path.getmtime(path)
        result['date_taken'] = datetime.fromtimestamp(mtime)

    return result


def date_to_year_week(dt):
    iso = dt.isocalendar()
    return iso[0], iso[1]


def scan_directory(root, callback=None):
    root = Path(root)
    files = [
        p for p in root.rglob('*')
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    total = len(files)
    for i, path in enumerate(files):
        exif_data = read_exif(path)
        dt = exif_data['date_taken']
        year, week = date_to_year_week(dt)
        thumbnail = make_thumbnail(path)
        photo = {
            'path': str(path),
            'filename': path.name,
            'date_taken': dt.strftime('%Y-%m-%d %H:%M:%S') if dt else None,
            'year': year,
            'week': week,
            'lat': exif_data['lat'],
            'lon': exif_data['lon'],
            'thumbnail_blob': thumbnail,
        }
        if callback:
            callback(i + 1, total, path.name)
        yield photo
