"""Pipeline quotidien : (optionnel) fetch, recalcul, changements, GOOD INVEST, build du site."""
from __future__ import annotations
import argparse, json, os, subprocess, sys
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

from . import paths
from . import changements, good_invest, raw_inputs, note_diff

TZ = ZoneInfo('Europe/Paris')


def stamp_maj():
    now = datetime.now(TZ)
    rec = {
        'at': now.isoformat(),
        'label': now.strftime('%d/%m/%Y %H:%M') + ' Europe/Paris',
        'date': now.strftime('%Y-%m-%d'),
        'timezone': 'Europe/Paris',
    }
    dest = paths.data_dir() / 'maj.json'
    dest.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return rec


def _run(script: str):
    src = paths.src_dir()
    env = os.environ.copy()
    env['APEX_ROOT'] = str(paths.root())
    env['PYTHONPATH'] = str(paths.root()) + os.pathsep + str(src) + os.pathsep + env.get('PYTHONPATH', '')
    print(f'---- {script} {datetime.now(TZ).isoformat()} ----', flush=True)
    subprocess.check_call([sys.executable, '-u', str(src / script)], cwd=str(src), env=env)


REBUILD = [
    'build_secteurs.py', 'build_pays.py', 'build_energie.py', 'build_metaux.py',
    'build_obligations.py', 'build_crypto_fiches.py',
    'build_apex_bars.py', 'build_indicateur.py', 'build_sentiment_secteurs.py', 'build_achatvente.py',
    'build_data_tabs.py', 'build_fx_apex.py', 'build_obpays.py', 'build_apex10.py', 'apply_sentiment.py', 'build.py',
]


def rebuild():
    for s in REBUILD:
        p = paths.src_dir() / s
        if p.exists():
            _run(s)


def copy_site():
    """Copie index.html vers le dossier site (ophir)."""
    src = paths.root() / 'index.html'
    site = paths.site_dir()
    if src.exists() and site.resolve() != paths.root().resolve():
        dest = site / 'index.html'
        dest.write_bytes(src.read_bytes())
        print('copied index.html ->', dest, 'bytes', dest.stat().st_size)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--fetch', action='store_true', help='Télécharger les cours hebdo avant de recalculer')
    ap.add_argument('--no-rebuild', action='store_true', help='Ne pas relancer les scripts de build')
    ap.add_argument('--fetch-limit', type=int, default=None)
    ap.add_argument('--force-publish', action='store_true', help='Publier même si le diff de notes est important')
    args = ap.parse_args(argv)

    print('APEX_ROOT', paths.root(), flush=True)
    raw_inputs.extract()
    before = note_diff.collect()
    bak = paths.data_dir() / '_note_backup'
    note_diff.backup_files(bak)
    if args.fetch:
        from . import fetch_yahoo
        fetch_yahoo.run(limit=args.fetch_limit)
    if not args.no_rebuild:
        # rebuild exige les caches hebdo ; si absents, on se contente de tamponner les JSON déjà là
        try:
            rebuild()
        except subprocess.CalledProcessError as e:
            print('rebuild failed', e, file=sys.stderr)
            note_diff.restore_files(bak)
            raise
    after = note_diff.collect()
    report = note_diff.compare(before, after)
    note_diff.write(report)
    if report['blocking'] and not args.no_rebuild and not args.force_publish:
        print('GROS ÉCARTS de notes APEX /100 — publication annulée, JSON restaurés.', flush=True)
        note_diff.restore_files(bak)
        note_diff.write(report)
        return 2
    maj = stamp_maj()
    gi = good_invest.build()
    ch = changements.build()
    # build.py est rapide et injecte data/maj.json dans index.html
    try:
        _run('build.py')
    except Exception as e:
        print('build.py', e)
        raise
    copy_site()
    print('maj', maj['label'], 'good_invest', gi['n'], 'changements', ch['n_changements_couleur'], 'anomalies', ch['n_anomalies'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
