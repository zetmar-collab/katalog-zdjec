import sqlite3
from pathlib import Path


def init_db(db_path):
    conn = sqlite3.connect(db_path)
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


def upsert_photo(conn, photo_dict):
    conn.execute("""
        INSERT INTO photos (path, filename, date_taken, week, year, lat, lon, thumbnail_blob)
        VALUES (:path, :filename, :date_taken, :week, :year, :lat, :lon, :thumbnail_blob)
        ON CONFLICT(path) DO UPDATE SET
            filename=excluded.filename,
            date_taken=excluded.date_taken,
            week=excluded.week,
            year=excluded.year,
            lat=excluded.lat,
            lon=excluded.lon,
            thumbnail_blob=excluded.thumbnail_blob
    """, photo_dict)
    conn.commit()


def get_photos_by_week(conn, year, week):
    cursor = conn.execute(
        "SELECT * FROM photos WHERE year=? AND week=? ORDER BY date_taken, filename",
        (year, week)
    )
    return [dict(row) for row in cursor.fetchall()]


def get_all_weeks(conn):
    cursor = conn.execute(
        "SELECT DISTINCT year, week FROM photos WHERE year IS NOT NULL AND week IS NOT NULL ORDER BY year, week"
    )
    return [(row["year"], row["week"]) for row in cursor.fetchall()]


def get_photo_by_path(conn, path):
    cursor = conn.execute("SELECT * FROM photos WHERE path=?", (str(path),))
    row = cursor.fetchone()
    return dict(row) if row else None


def delete_photo(conn, path):
    conn.execute("DELETE FROM photos WHERE path=?", (str(path),))
    conn.commit()


def delete_photos_by_week(conn, year, week):
    conn.execute("DELETE FROM photos WHERE year=? AND week=?", (year, week))
    conn.commit()


def delete_photos_by_year(conn, year):
    conn.execute("DELETE FROM photos WHERE year=?", (year,))
    conn.commit()


def get_photos_by_year(conn, year):
    cursor = conn.execute("SELECT * FROM photos WHERE year=? ORDER BY date_taken, filename", (year,))
    return [dict(row) for row in cursor.fetchall()]


def find_duplicate_filenames(conn, filenames):
    """Zwraca listę (filename, existing_path) dla plików już w katalogu."""
    duplicates = []
    for name in filenames:
        row = conn.execute(
            "SELECT path FROM photos WHERE filename=?", (name,)
        ).fetchone()
        if row:
            duplicates.append((name, row['path']))
    return duplicates
