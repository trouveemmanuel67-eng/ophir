"""Découpage des bougies hebdomadaires Yahoo en semaines closant le vendredi.

Bug corrigé le 23/11/2026 (vu sur POSCO, ENPH, APP) :
- une barre horodatée au début de semaine (lundi ou dimanche 00:00, fuseau de la place)
  représente la semaine qui se termine le vendredi suivant ;
- un tick intra-semaine non minuit (clôture du lundi, dernier échange de la séance, etc.)
  appartient à LA MÊME semaine (vendredi à venir), et non au vendredi précédent ;
- si plusieurs horodatages tombent sur le même vendredi : on conserve la première
  ouverture, le plus haut, le plus bas, la dernière clôture (l'ouverture n'est plus écrasée) ;
- une semaine n'est « clôturée » que si la date du jour est postérieure à ce vendredi
  ET, pour la dernière barre, si le fichier a été téléchargé après le vendredi
  (samedi 00:00 heure de Paris). Sinon la barre intra-semaine n'est pas utilisée
  comme clôture officielle du vendredi.
"""
import os
import json
import datetime as D
from zoneinfo import ZoneInfo

PARIS = ZoneInfo('Europe/Paris')


def week_friday(loc):
    """Horodatage local de la place → vendredi de la semaine Yahoo correspondante."""
    ld = loc.date()
    wd = ld.weekday()  # lundi=0 … dimanche=6
    if wd <= 4:
        return ld + D.timedelta(days=4 - wd)
    midnight = loc.hour == 0 and loc.minute == 0 and loc.second == 0
    if midnight:
        # barre de début de semaine (souvent dimanche 00:00) → vendredi à venir
        return ld + D.timedelta(days=(4 - wd) % 7)
    # samedi / dimanche après la clôture → vendredi qui vient de se terminer
    return ld - D.timedelta(days=wd - 4)


def friday_closed(fri, now=None, path=None, is_last=False):
    """Semaine close si le vendredi est passé. La dernière barre d'un fichier
    périmé (téléchargé avant le lendemain de ce vendredi) reste « live »."""
    now = now or D.datetime.now(PARIS)
    if isinstance(fri, str):
        fri = D.date.fromisoformat(fri[:10])
    if now.date() <= fri:
        return False
    if is_last and path and os.path.exists(path):
        mt = D.datetime.fromtimestamp(os.path.getmtime(path), PARIS)
        deadline = D.datetime.combine(fri + D.timedelta(days=1), D.time(0, 0), tzinfo=PARIS)
        if mt < deadline:
            return False
    return True


def parse_yahoo_weekly(path, now=None):
    """Lit un JSON Yahoo chart 1wk.

    Retourne (bars, meta) où bars est une liste triée de dicts :
      date (vendredi ISO), open, high, low, close, volume, closed (bool).
    """
    now = now or D.datetime.now(PARIS)
    raw = json.load(open(path))
    result = (raw.get('chart') or {}).get('result') or []
    if not result:
        return [], {}
    d = result[0]
    ts = d.get('timestamp') or []
    q = (d.get('indicators') or {}).get('quote') or [{}]
    q = q[0]
    meta = d.get('meta') or {}
    tz = ZoneInfo(meta.get('exchangeTimezoneName') or 'UTC')
    opens = q.get('open') or [None] * len(ts)
    highs = q.get('high') or [None] * len(ts)
    lows = q.get('low') or [None] * len(ts)
    closes = q.get('close') or [None] * len(ts)
    vols = q.get('volume') or [None] * len(ts)
    wk = {}
    for t, o, h, l, c, v in zip(ts, opens, highs, lows, closes, vols):
        if c is None:
            continue
        loc = D.datetime.fromtimestamp(t, tz)
        fri = week_friday(loc)
        rec = wk.get(fri)
        if rec is None:
            wk[fri] = {
                'open': o if (o is not None and o > 0) else None,
                'high': h, 'low': l, 'close': c, 'volume': v,
                't0': t, 't1': t,
            }
            continue
        if t < rec['t0']:
            if o is not None and o > 0:
                rec['open'] = o
            rec['t0'] = t
        if t >= rec['t1']:
            rec['close'] = c
            rec['t1'] = t
            if v is not None and (rec['volume'] is None or v >= rec['volume']):
                rec['volume'] = v
        if h is not None:
            rec['high'] = h if rec['high'] is None else max(rec['high'], h)
        if l is not None:
            rec['low'] = l if rec['low'] is None else min(rec['low'], l)
        if rec['open'] is None and o is not None and o > 0 and t <= rec['t0']:
            rec['open'] = o
    fris = sorted(wk)
    last = fris[-1] if fris else None
    bars = []
    for fri in fris:
        r = wk[fri]
        bars.append({
            'date': fri.isoformat(),
            'open': r['open'],
            'high': r['high'],
            'low': r['low'],
            'close': r['close'],
            'volume': r['volume'],
            'closed': friday_closed(fri, now=now, path=path, is_last=(fri == last)),
        })
    return bars, meta


def as_yweekly(path, now=None):
    """Compatibilité ind_core.yweekly : ([(date, close, closed), ...], meta)."""
    bars, meta = parse_yahoo_weekly(path, now=now)
    return [(b['date'], b['close'], b['closed']) for b in bars], meta


def as_yopens(path, now=None):
    """{vendredi ISO: ouverture}."""
    bars, _ = parse_yahoo_weekly(path, now=now)
    return {b['date']: b['open'] for b in bars}


def as_yhl(path, now=None):
    """{vendredi ISO: (high, low)} — ignore les barres sans haut/bas."""
    bars, _ = parse_yahoo_weekly(path, now=now)
    return {b['date']: (b['high'], b['low']) for b in bars if b['high'] is not None and b['low'] is not None}
