import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sqlite3
from pathlib import Path

from core.database import init_db, upsert_photo
from core.organizer import organize_photos


def _make_db(tmp_path):
    db_path = str(tmp_path / 'test.db')
    conn = init_db(db_path)
    return conn


def _create_photo_file(directory, name='photo.jpg'):
    path = directory / name
    path.write_bytes(b'\xff\xd8\xff' + b'\x00' * 100)  # minimal fake JPEG header
    return path


def test_organize_copy(tmp_path):
    src_dir = tmp_path / 'source'
    src_dir.mkdir()
    photo_file = _create_photo_file(src_dir, 'IMG_001.jpg')

    dest_root = tmp_path / 'catalog'
    dest_root.mkdir()

    conn = _make_db(tmp_path)
    upsert_photo(conn, {
        'path': str(photo_file),
        'filename': 'IMG_001.jpg',
        'date_taken': '2023-06-15 10:00:00',
        'year': 2023,
        'week': 24,
        'lat': None,
        'lon': None,
        'thumbnail_blob': None,
    })

    moves = organize_photos(str(dest_root), conn, mode='copy')

    assert len(moves) == 1
    src, dst = moves[0]
    assert src == str(photo_file)
    dest_path = Path(dst)
    assert dest_path.exists()
    assert dest_path.parent.name == 'W24'
    assert dest_path.parent.parent.name == '2023'
    # Original still exists (copy mode)
    assert photo_file.exists()


def test_organize_move(tmp_path):
    src_dir = tmp_path / 'source'
    src_dir.mkdir()
    photo_file = _create_photo_file(src_dir, 'IMG_002.jpg')

    dest_root = tmp_path / 'catalog'
    dest_root.mkdir()

    conn = _make_db(tmp_path)
    upsert_photo(conn, {
        'path': str(photo_file),
        'filename': 'IMG_002.jpg',
        'date_taken': '2023-01-10 08:00:00',
        'year': 2023,
        'week': 2,
        'lat': None,
        'lon': None,
        'thumbnail_blob': None,
    })

    moves = organize_photos(str(dest_root), conn, mode='move')
    assert len(moves) == 1
    _, dst = moves[0]
    assert Path(dst).exists()
    assert not photo_file.exists()


def test_organize_collision(tmp_path):
    src_dir = tmp_path / 'source'
    src_dir.mkdir()
    photo1 = _create_photo_file(src_dir, 'same.jpg')

    dest_root = tmp_path / 'catalog'
    dest_root.mkdir()
    # Pre-create a file with the same name in the destination
    dest_week_dir = dest_root / '2023' / 'W10'
    dest_week_dir.mkdir(parents=True)
    (dest_week_dir / 'same.jpg').write_bytes(b'existing')

    conn = _make_db(tmp_path)
    upsert_photo(conn, {
        'path': str(photo1),
        'filename': 'same.jpg',
        'date_taken': '2023-03-06 12:00:00',
        'year': 2023,
        'week': 10,
        'lat': None,
        'lon': None,
        'thumbnail_blob': None,
    })

    moves = organize_photos(str(dest_root), conn, mode='copy')
    assert len(moves) == 1
    _, dst = moves[0]
    # Should have a suffix to avoid collision
    assert Path(dst).name == 'same_1.jpg'


def test_organize_skips_missing_files(tmp_path):
    dest_root = tmp_path / 'catalog'
    dest_root.mkdir()

    conn = _make_db(tmp_path)
    upsert_photo(conn, {
        'path': str(tmp_path / 'nonexistent.jpg'),
        'filename': 'nonexistent.jpg',
        'date_taken': '2023-06-01 00:00:00',
        'year': 2023,
        'week': 22,
        'lat': None,
        'lon': None,
        'thumbnail_blob': None,
    })

    moves = organize_photos(str(dest_root), conn, mode='copy')
    assert moves == []
