import shutil
from pathlib import Path

from core.database import get_all_weeks, get_photos_by_week


def _unique_dest(dst):
    if not dst.exists():
        return dst
    stem = dst.stem
    suffix = dst.suffix
    parent = dst.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def organize_photos(root, db_conn, mode='copy'):
    root = Path(root)
    weeks = get_all_weeks(db_conn)
    moves = []

    for year, week in weeks:
        photos = get_photos_by_week(db_conn, year, week)
        dest_dir = root / str(year) / f"W{week:02d}"
        dest_dir.mkdir(parents=True, exist_ok=True)

        for photo in photos:
            src = Path(photo['path'])
            if not src.exists():
                continue
            dst = _unique_dest(dest_dir / src.name)
            if src == dst:
                continue
            if mode == 'move':
                shutil.move(str(src), str(dst))
            else:
                shutil.copy2(str(src), str(dst))
            moves.append((str(src), str(dst)))

    return moves
