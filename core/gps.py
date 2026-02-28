import webbrowser


def _dms_to_decimal(dms, ref):
    try:
        deg, minutes, seconds = dms
        def to_float(v):
            if hasattr(v, 'numerator'):
                return v.numerator / v.denominator
            return float(v)
        decimal = to_float(deg) + to_float(minutes) / 60 + to_float(seconds) / 3600
        if ref in ('S', 'W'):
            decimal = -decimal
        return decimal
    except Exception:
        return None


def parse_gps_dms(exif_gps_info):
    try:
        lat_dms = exif_gps_info.get(2)
        lat_ref = exif_gps_info.get(1)
        lon_dms = exif_gps_info.get(4)
        lon_ref = exif_gps_info.get(3)
        if not (lat_dms and lat_ref and lon_dms and lon_ref):
            return None, None
        lat = _dms_to_decimal(lat_dms, lat_ref)
        lon = _dms_to_decimal(lon_dms, lon_ref)
        return lat, lon
    except Exception:
        return None, None


def build_osm_url(lat, lon):
    return f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom=15"


def open_on_map(lat, lon):
    url = build_osm_url(lat, lon)
    webbrowser.open(url)
