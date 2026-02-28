import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime
from unittest.mock import patch, MagicMock

from core.scanner import _parse_exif_date, date_to_year_week, read_exif, SUPPORTED_EXTENSIONS
from core.gps import parse_gps_dms


def test_parse_exif_date_colon_format():
    dt = _parse_exif_date('2023:06:15 14:30:00')
    assert dt == datetime(2023, 6, 15, 14, 30, 0)


def test_parse_exif_date_dash_format():
    dt = _parse_exif_date('2023-06-15 14:30:00')
    assert dt == datetime(2023, 6, 15, 14, 30, 0)


def test_parse_exif_date_invalid():
    dt = _parse_exif_date('not a date')
    assert dt is None


def test_parse_exif_date_none():
    dt = _parse_exif_date(None)
    assert dt is None


def test_date_to_year_week():
    # 2023-01-02 is ISO week 1 of 2023
    dt = datetime(2023, 1, 2)
    year, week = date_to_year_week(dt)
    assert year == 2023
    assert week == 1


def test_date_to_year_week_cross_year():
    # 2023-01-01 is ISO week 52 of 2022
    dt = datetime(2023, 1, 1)
    year, week = date_to_year_week(dt)
    assert year == 2022
    assert week == 52


def test_supported_extensions():
    assert '.jpg' in SUPPORTED_EXTENSIONS
    assert '.jpeg' in SUPPORTED_EXTENSIONS
    assert '.png' in SUPPORTED_EXTENSIONS
    assert '.tiff' in SUPPORTED_EXTENSIONS
    assert '.txt' not in SUPPORTED_EXTENSIONS


def test_parse_gps_dms_north_east():
    # Simulate rational numbers as fractions
    from fractions import Fraction
    gps_info = {
        1: 'N',
        2: (Fraction(48), Fraction(51), Fraction(29, 10)),
        3: 'E',
        4: (Fraction(2), Fraction(21), Fraction(3, 10)),
    }
    lat, lon = parse_gps_dms(gps_info)
    assert lat is not None and abs(lat - 48.858) < 0.01
    assert lon is not None and abs(lon - 2.351) < 0.01


def test_parse_gps_dms_south_west():
    from fractions import Fraction
    gps_info = {
        1: 'S',
        2: (Fraction(33), Fraction(52), Fraction(0)),
        3: 'W',
        4: (Fraction(70), Fraction(40), Fraction(0)),
    }
    lat, lon = parse_gps_dms(gps_info)
    assert lat is not None and lat < 0
    assert lon is not None and lon < 0


def test_parse_gps_dms_missing():
    lat, lon = parse_gps_dms({})
    assert lat is None
    assert lon is None


def test_read_exif_fallback_to_mtime(tmp_path):
    # Create a minimal PNG (no EXIF)
    from PIL import Image
    img = Image.new('RGB', (10, 10), color='red')
    img_path = tmp_path / 'test.png'
    img.save(str(img_path))

    result = read_exif(str(img_path))
    assert result['date_taken'] is not None
    assert result['lat'] is None
    assert result['lon'] is None
