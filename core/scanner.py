import io
import os
from datetime import datetime
from pathlib import Path

from PIL import Image, ExifTags

from core.gps import parse_gps_dms

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tiff', '.heic'}

EXIF_DATE_TAGS = [
    'DateTimeOriginal',
    'DateTimeDigitized',
    'DateTime',
]


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


def read_exif(path):
    result = {'date_taken': None, 'lat': None, 'lon': None, 'exif': {}}
    path = Path(path)

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


def make_thumbnail(path, size=(150, 150)):
    try:
        with Image.open(path) as img:
            img = img.copy()
            try:
                exif = img._getexif()
                if exif:
                    orientation = None
                    for k, v in exif.items():
                        if ExifTags.TAGS.get(k) == 'Orientation':
                            orientation = v
                            break
                    rotations = {3: 180, 6: 270, 8: 90}
                    if orientation in rotations:
                        img = img.rotate(rotations[orientation], expand=True)
            except Exception:
                pass
            img.thumbnail(size, Image.LANCZOS)
            buf = io.BytesIO()
            img.convert('RGB').save(buf, format='JPEG', quality=70)
            return buf.getvalue()
    except Exception:
        return None


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
