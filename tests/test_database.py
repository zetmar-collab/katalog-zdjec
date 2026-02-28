import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sqlite3

from core.database import init_db, upsert_photo, get_photos_by_week, get_all_weeks, get_photo_by_path


def _in_memory_db():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            filename TEXT NOT NULL,
            date_taken TEXT,
            week INTEGER,
            year INTEGER,
            lat REAL,
            lon REAL,
            thumbnail_blob BLOB
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_year_week ON photos(year, week)")
    conn.commit()
    return conn


SAMPLE_PHOTO = {
    'path': '/photos/2023/IMG_001.jpg',
    'filename': 'IMG_001.jpg',
    'date_taken': '2023-06-15 14:30:00',
    'week': 24,
    'year': 2023,
    'lat': 48.858,
    'lon': 2.351,
    'thumbnail_blob': None,
}


def test_upsert_and_query():
    conn = _in_memory_db()
    upsert_photo(conn, SAMPLE_PHOTO)
    photos = get_photos_by_week(conn, 2023, 24)
    assert len(photos) == 1
    assert photos[0]['filename'] == 'IMG_001.jpg'


def test_upsert_updates_existing():
    conn = _in_memory_db()
    upsert_photo(conn, SAMPLE_PHOTO)
    updated = dict(SAMPLE_PHOTO)
    updated['filename'] = 'UPDATED.jpg'
    upsert_photo(conn, updated)
    photos = get_photos_by_week(conn, 2023, 24)
    assert len(photos) == 1
    assert photos[0]['filename'] == 'UPDATED.jpg'


def test_get_photos_by_week_empty():
    conn = _in_memory_db()
    photos = get_photos_by_week(conn, 2023, 24)
    assert photos == []


def test_get_all_weeks():
    conn = _in_memory_db()
    upsert_photo(conn, SAMPLE_PHOTO)
    photo2 = dict(SAMPLE_PHOTO)
    photo2['path'] = '/photos/2023/IMG_002.jpg'
    photo2['week'] = 25
    upsert_photo(conn, photo2)
    photo3 = dict(SAMPLE_PHOTO)
    photo3['path'] = '/photos/2024/IMG_003.jpg'
    photo3['year'] = 2024
    photo3['week'] = 1
    upsert_photo(conn, photo3)

    weeks = get_all_weeks(conn)
    assert (2023, 24) in weeks
    assert (2023, 25) in weeks
    assert (2024, 1) in weeks
    assert len(weeks) == 3


def test_get_all_weeks_sorted():
    conn = _in_memory_db()
    photo_a = dict(SAMPLE_PHOTO)
    photo_a['path'] = '/a.jpg'
    photo_a['year'] = 2022
    photo_a['week'] = 50
    upsert_photo(conn, photo_a)
    upsert_photo(conn, SAMPLE_PHOTO)

    weeks = get_all_weeks(conn)
    assert weeks[0] == (2022, 50)
    assert weeks[1] == (2023, 24)


def test_get_photo_by_path():
    conn = _in_memory_db()
    upsert_photo(conn, SAMPLE_PHOTO)
    photo = get_photo_by_path(conn, '/photos/2023/IMG_001.jpg')
    assert photo is not None
    assert photo['lat'] == 48.858


def test_get_photo_by_path_missing():
    conn = _in_memory_db()
    photo = get_photo_by_path(conn, '/does/not/exist.jpg')
    assert photo is None


def test_get_photos_by_week_ordering():
    conn = _in_memory_db()
    photo_b = dict(SAMPLE_PHOTO)
    photo_b['path'] = '/b.jpg'
    photo_b['filename'] = 'b.jpg'
    photo_b['date_taken'] = '2023-06-16 10:00:00'
    upsert_photo(conn, photo_b)
    photo_a = dict(SAMPLE_PHOTO)
    photo_a['path'] = '/a.jpg'
    photo_a['filename'] = 'a.jpg'
    photo_a['date_taken'] = '2023-06-15 08:00:00'
    upsert_photo(conn, photo_a)

    photos = get_photos_by_week(conn, 2023, 24)
    assert photos[0]['filename'] == 'a.jpg'
    assert photos[1]['filename'] == 'b.jpg'
