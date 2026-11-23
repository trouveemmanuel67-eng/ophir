"""Archive des fichiers bruts non Yahoo (FRED, BCE, screeners, métadonnées) pour GitHub Actions."""
from __future__ import annotations
import argparse, tarfile, sys
from pathlib import Path

from . import paths

ARCHIVE_NAME = 'raw_inputs.tar.gz'

EXCLUDE_DIR_PREFIXES = (
    'secteurs/fond/',      # fondamentaux déjà publiés dans fondamentaux.json
    'secteurs/holdings/',  # déjà versionnés
    'yahoo_cache/',
    'fibo_max/',
    'historique_notes/',
)
EXCLUDE_NAMES = {'fetch_report.json', 'cl_home.html', 'hub.html', ARCHIVE_NAME}


def is_yahoo(rel: str, name: str) -> bool:
    parts = rel.split('/')
    if name.startswith('yahoo_1wk_'):
        return True
    if parts[:1] == ['fibo_max'] and name.endswith('.json'):
        return True
    if parts[:2] == ['pays', 'wk']:
        return True
    if parts[:1] == ['metaux'] and name.startswith('y_'):
        return True
    if parts[:1] == ['obligations'] and name.startswith('w_'):
        return True
    if parts[:1] == ['elliott'] and name.startswith('y_'):
        return True
    if parts and parts[0] in {'energie', 'secteurs', 'crypto', 'liquidites', 'actions', 'fx'} and name.startswith('yahoo_1wk_'):
        return True
    return False


def should_pack(rel: str) -> bool:
    name = Path(rel).name
    if name in EXCLUDE_NAMES or name.endswith('.bak'):
        return False
    for p in EXCLUDE_DIR_PREFIXES:
        if rel == p.rstrip('/') or rel.startswith(p):
            return False
    if is_yahoo(rel, name):
        return False
    return True


INCLUDE_DIRS = (
    'actions', 'crypto', 'energie', 'liquidites', 'metaux', 'obligations',
    'obpays', 'pays', 'secteurs', 'indicateur', 'elliott',
)
TOP_FILES = (
    'crypto_liquidite.json',
    'ecb_M.FR.B.A2C.P.R.A.2250.EUR.N.csv',
    'ecb_M.FR.B.A2C.A.R.A.2250.EUR.N.csv',
    'ecb_M.FR.B.A2C.AM.R.A.2250.EUR.N.csv',
    'ecb_M.FR.B.A2C.O.R.A.2250.EUR.N.csv',
    'insee_010567059_ipla_fm_cvs.xml',
    'trends_achat_FR_12m.csv',
    'trends_vente_pivot_FR_12m.csv',
    't_001788025.xml',
    't_010567008.xml',
    't_010567059.xml',
)


def iter_files():
    data = paths.data_dir()
    for folder in INCLUDE_DIRS:
        d = data / folder
        if not d.exists():
            continue
        for p in d.rglob('*'):
            if p.is_file():
                rel = p.relative_to(data).as_posix()
                if should_pack(rel):
                    yield p, rel
    for name in TOP_FILES:
        p = data / name
        if p.exists():
            yield p, name


def archive_path() -> Path:
    return paths.data_dir() / ARCHIVE_NAME


def pack(dest: Path | None = None) -> Path:
    dest = dest or archive_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    n, total = 0, 0
    with tarfile.open(dest, 'w:gz') as tar:
        for p, rel in iter_files():
            tar.add(p, arcname=rel)
            n += 1
            total += p.stat().st_size
    print(f'raw_inputs: packed {n} files, {total/1e6:.1f} MB raw -> {dest} ({dest.stat().st_size/1e6:.1f} MB gz)')
    return dest


def extract(src: Path | None = None, overwrite: bool = False) -> int:
    src = src or archive_path()
    if not src.exists():
        print('raw_inputs: archive absente', src)
        return 0
    data = paths.data_dir()
    n = 0
    with tarfile.open(src, 'r:gz') as tar:
        for m in tar.getmembers():
            if not m.isfile():
                continue
            # path traversal guard
            rel = Path(m.name)
            if rel.is_absolute() or '..' in rel.parts:
                continue
            dest = data / rel
            if dest.exists() and not overwrite:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            f = tar.extractfile(m)
            if f is None:
                continue
            dest.write_bytes(f.read())
            n += 1
    print(f'raw_inputs: extracted {n} missing files from {src} -> {data}')
    return n


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('pack', 'extract', 'list'))
    ap.add_argument('--overwrite', action='store_true')
    args = ap.parse_args(argv)
    if args.cmd == 'pack':
        pack()
    elif args.cmd == 'extract':
        extract(overwrite=args.overwrite)
    else:
        for _, rel in sorted(iter_files(), key=lambda x: x[1]):
            print(rel)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
