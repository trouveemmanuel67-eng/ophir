#!/usr/bin/env python3
"""Garde-fou publication APEX.

Vérifie la syntaxe de tout le JavaScript du site (fichiers src/*.js et
scripts inline extraits de index.html), puis charge la page dans un
Chrome/Chromium headless. Échec (code 1) s'il y a une exception JS ou
si aucune fiche n'est rendue — dans ce cas, ne pas commiter ni publier.
"""
from __future__ import annotations

import argparse
import http.server
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIN_FICHES_ACTIONS = 20
MIN_NOTES_ACCUEIL = 5


def _ok(msg):
    print(f'  OK  {msg}', flush=True)


def _fail(msg):
    print(f'  ÉCHEC  {msg}', flush=True)


def _node_bin():
    n = shutil.which('node') or shutil.which('nodejs')
    if not n:
        raise SystemExit(
            'ÉCHEC — node introuvable (nécessaire pour node --check). Ne pas publier.'
        )
    return n


def _check_js_text(node, name, source, tmpdir):
    if not source or not source.strip():
        return
    safe = re.sub(r'[^A-Za-z0-9._-]+', '_', name)[:80] or 'script'
    path = Path(tmpdir) / f'{safe}.js'
    path.write_text(source, encoding='utf-8')
    r = subprocess.run([node, '--check', str(path)], capture_output=True, text=True)
    if r.returncode != 0:
        err = (r.stderr or r.stdout or 'erreur de syntaxe').strip()
        _fail(f'{name}\n{err}')
        raise SystemExit(1)


def _extract_scripts(html):
    """Retourne [(nom, type, body), ...] pour chaque <script> avec un corps."""
    out = []
    for i, m in enumerate(
        re.finditer(r'<script([^>]*)>(.*?)</script>', html, flags=re.S | re.I)
    ):
        attrs, body = m.group(1), m.group(2)
        if re.search(r'\bsrc\s*=', attrs, flags=re.I) and not body.strip():
            continue
        typ = ''
        tm = re.search(r'type=["\']([^"\']+)', attrs, flags=re.I)
        if tm:
            typ = tm.group(1).strip().lower()
        idm = re.search(r'id=["\']([^"\']+)', attrs, flags=re.I)
        name = idm.group(1) if idm else f'script-inline-{i+1}'
        out.append((name, typ, body))
    return out


def check_syntax(root=ROOT):
    print('[syntaxe] JavaScript du site', flush=True)
    node = _node_bin()
    js_files = sorted((root / 'src').glob('*.js'))
    if not js_files:
        _fail(f'aucun src/*.js dans {root}')
        raise SystemExit(1)
    with tempfile.TemporaryDirectory(prefix='apex-js-check-') as td:
        for p in js_files:
            _check_js_text(node, str(p.relative_to(root)), p.read_text(encoding='utf-8'), td)
        _ok(f'node --check : {len(js_files)} fichier(s) src/*.js')

        index = root / 'index.html'
        if not index.exists():
            _fail('index.html introuvable')
            raise SystemExit(1)
        html = index.read_text(encoding='utf-8')
        scripts = _extract_scripts(html)
        n_js = n_json = 0
        for name, typ, body in scripts:
            if typ in ('application/json', 'application/ld+json'):
                try:
                    json.loads(body)
                except Exception as e:
                    _fail(f'JSON embarqué #{name} : {e}')
                    raise SystemExit(1)
                n_json += 1
            else:
                _check_js_text(node, f'index.html#{name}', body, td)
                n_js += 1
        if n_js < 1:
            _fail('aucun script JavaScript inline dans index.html')
            raise SystemExit(1)
        _ok(f'node --check : {n_js} script(s) inline extraits de index.html')
        if n_json:
            _ok(f'JSON embarqué : {n_json} bloc(s) valides')
    return 0


def _ws_connect(url, timeout=15):
    from urllib.parse import urlparse
    import base64

    u = urlparse(url)
    host, port = u.hostname, u.port or (443 if u.scheme == 'wss' else 80)
    path = u.path + (('?' + u.query) if u.query else '')
    sock = socket.create_connection((host, port), timeout=timeout)
    sock.settimeout(timeout)
    key = base64.b64encode(os.urandom(16)).decode()
    req = (
        f'GET {path or "/"} HTTP/1.1\r\n'
        f'Host: {host}:{port}\r\n'
        'Upgrade: websocket\r\n'
        'Connection: Upgrade\r\n'
        f'Sec-WebSocket-Key: {key}\r\n'
        'Sec-WebSocket-Version: 13\r\n'
        '\r\n'
    )
    sock.sendall(req.encode())
    buf = b''
    while b'\r\n\r\n' not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            raise RuntimeError('WebSocket : connexion fermée pendant la poignée de main')
        buf += chunk
    header, rest = buf.split(b'\r\n\r\n', 1)
    if b'101' not in header.split(b'\r\n', 1)[0]:
        raise RuntimeError(
            'WebSocket : échec handshake\n' + header.decode('latin1', 'replace')[:400]
        )
    return sock, rest


def _ws_send(sock, payload, opcode=1):
    data = payload if isinstance(payload, bytes) else payload.encode()
    mask = os.urandom(4)
    n = len(data)
    hdr = bytes([0x80 | opcode])
    if n < 126:
        hdr += bytes([0x80 | n])
    elif n < 65536:
        hdr += bytes([0x80 | 126]) + struct.pack('!H', n)
    else:
        hdr += bytes([0x80 | 127]) + struct.pack('!Q', n)
    hdr += mask
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
    sock.sendall(hdr + masked)


def _ws_recv_frame(sock, leftover=b''):
    buf = leftover

    def need(n):
        nonlocal buf
        while len(buf) < n:
            chunk = sock.recv(max(4096, n - len(buf)))
            if not chunk:
                raise RuntimeError('WebSocket : connexion fermée')
            buf += chunk

    need(2)
    b0, b1 = buf[0], buf[1]
    buf = buf[2:]
    opcode = b0 & 0x0F
    masked = bool(b1 & 0x80)
    length = b1 & 0x7F
    if length == 126:
        need(2)
        length = struct.unpack('!H', buf[:2])[0]
        buf = buf[2:]
    elif length == 127:
        need(8)
        length = struct.unpack('!Q', buf[:8])[0]
        buf = buf[8:]
    mask = b''
    if masked:
        need(4)
        mask, buf = buf[:4], buf[4:]
    need(length)
    payload, buf = buf[:length], buf[length:]
    if masked:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    if opcode == 0x8:
        return opcode, payload, buf
    if opcode == 0x9:
        _ws_send(sock, payload, opcode=0xA)
        return _ws_recv_frame(sock, buf)
    return opcode, payload, buf


def _ws_recv_msg(sock, leftover=b''):
    data = b''
    while True:
        opcode, payload, leftover = _ws_recv_frame(sock, leftover)
        data += payload
        if opcode == 1:
            return data.decode(), leftover
        if opcode == 2:
            return data, leftover
        if data:
            try:
                return data.decode(), leftover
            except Exception:
                return data, leftover


class Cdp:
    def __init__(self, url):
        self.sock, self.leftover = _ws_connect(url)
        self._id = 0
        self.events = []

    def call(self, method, params=None, timeout=30, session_id=None):
        self._id += 1
        mid = self._id
        msg = {'id': mid, 'method': method, 'params': params or {}}
        if session_id:
            msg['sessionId'] = session_id
        _ws_send(self.sock, json.dumps(msg))
        deadline = time.time() + timeout
        while time.time() < deadline:
            remain = deadline - time.time()
            self.sock.settimeout(max(0.2, remain))
            try:
                text, self.leftover = _ws_recv_msg(self.sock, self.leftover)
            except socket.timeout:
                continue
            data = json.loads(text)
            if data.get('id') == mid:
                if 'error' in data:
                    raise RuntimeError(f'CDP {method} : {data["error"]}')
                return data.get('result') or {}
            self.events.append(data)
        raise TimeoutError(f'CDP : délai dépassé pour {method}')

    def drain(self, seconds=0.4):
        deadline = time.time() + seconds
        while time.time() < deadline:
            self.sock.settimeout(max(0.05, deadline - time.time()))
            try:
                text, self.leftover = _ws_recv_msg(self.sock, self.leftover)
                self.events.append(json.loads(text))
            except (socket.timeout, TimeoutError):
                break

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


def find_chrome():
    for env in ('CHROME_PATH', 'CHROME_BIN', 'GOOGLE_CHROME_BIN'):
        v = os.environ.get(env)
        if v and Path(v).exists():
            return v
    for name in (
        'google-chrome',
        'google-chrome-stable',
        'chromium-browser',
        'chromium',
        'chrome',
    ):
        p = shutil.which(name)
        if p:
            return p
    for p in (
        '/usr/bin/google-chrome',
        '/usr/bin/google-chrome-stable',
        '/usr/bin/chromium-browser',
        '/usr/bin/chromium',
    ):
        if Path(p).exists():
            return p
    return None


def _free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _start_http(root, port):
    os.chdir(root)

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), Quiet)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


def _exceptions_from(events):
    out = []
    for ev in events:
        method = ev.get('method') or ''
        params = ev.get('params') or {}
        if method == 'Runtime.exceptionThrown':
            d = params.get('exceptionDetails') or {}
            exc = d.get('exception') or {}
            desc = exc.get('description') or d.get('text') or 'exception'
            loc = ''
            if d.get('lineNumber') is not None:
                loc = f" (ligne {d.get('lineNumber') + 1})"
            out.append(desc.split('\n', 1)[0] + loc)
    return out


EVAL_JS = (
    "(() => {"
    "  const notes = document.querySelectorAll('.apex10, .fl-apex, .apex-dec').length;"
    "  const tabs = !!(document.getElementById('tactions') && document.getElementById('taccueil'));"
    "  const text = (document.body && document.body.innerText) || '';"
    "  const sigs = Array.from(document.querySelectorAll('.home-card .home-sig')).map(el => {"
    "    const t = ((el.innerText || '') + '').replace(/\\s+/g, ' ').trim();"
    "    const m = t.match(/(\\d+)\\s*\\/\\s*100/);"
    "    return {t, n: m ? Number(m[1]) : null};"
    "  });"
    "  const tens = sigs.filter(s => s.n === 10).length;"
    "  const nums = sigs.map(s => s.n).filter(n => n != null);"
    "  return {"
    "    notes, tabs,"
    "    n_lis: document.querySelectorAll('li').length,"
    "    buttons: document.querySelectorAll('button').length,"
    "    has_actions: /Actions/.test(text),"
    "    text_len: text.trim().length,"
    "    text_head: text.replace(/\\s+/g, ' ').trim().slice(0, 280),"
    "    home_sigs: sigs,"
    "    home_sig_tens: tens,"
    "    home_sig_max: nums.length ? Math.max.apply(null, nums) : null,"
    "    home_sig_n: sigs.length"
    "  };"
    "})()"
)

CHECK_REGLES_OPEN_JS = r"""
(() => {
  const btn = document.getElementById('rgBtn');
  if (btn) btn.click();
  document.querySelectorAll('#rg-page .rg-acc-btn[aria-expanded="false"]').forEach(b=>{ if(typeof rgAccToggle==='function') rgAccToggle(b,true); else b.click(); });
  const page = document.getElementById('rg-page');
  const r = page ? page.getBoundingClientRect() : null;
  const root = document.getElementById('rg-table-actions');
  const text = page ? (page.innerText || '') : '';
  const vis = !!(page && document.body.classList.contains('rg-on') && !page.hasAttribute('hidden'));
  const covers = !!(r && r.width >= window.innerWidth * 0.95 && r.height >= window.innerHeight * 0.95);
  const h2 = Array.from((page||document).querySelectorAll('h2')).map(el => (el.innerText||'').trim());
  const cards = root ? Array.from(root.querySelectorAll('.rg-card')) : [];
  const nameOf = c => ((c.querySelector('.rg-card-name')||{}).textContent||'').trim();
  const findCard = re => cards.find(c => re.test(nameOf(c)));
  const cardText = c => c ? ((c.innerText||'')+'').replace(/\s+/g,' ') : '';
  const rsiText = cardText(findCard(/^RSI\b/i));
  const macdText = cardText(findCard(/^MACD\b/i));
  const fiboText = cardText(findCard(/^Fibonacci\b/i));
  const ellText = cardText(findCard(/Elliott/i));
  const cciText = cardText(findCard(/^CCI\b/i));
  const totText = '';
  const names = cards.map(nameOf);
  const sameRow = (a,b) => !!(a&&b) && Math.abs(a.getBoundingClientRect().top - b.getBoundingClientRect().top) < 12;
  const techBox = root && root.querySelector('[data-group="technique"] .rg-cards');
  const techKids = techBox ? Array.from(techBox.children) : [];
  const fondCols = root ? Array.from(root.querySelectorAll('.rg-fond-col')) : [];
  return {
    vis, covers,
    w: r && Math.round(r.width), h: r && Math.round(r.height),
    vw: window.innerWidth, vh: window.innerHeight,
    hasTable: cards.length >= 13,
    rows: cards.length,
    hasBack: !!document.getElementById('rgBack'),
    hasClose: !!document.getElementById('rgClose'),
    hasBase: true,
    noIntro: !/La note part de 0/.test(text) && !/part de 50/.test(text) && !document.querySelector('.rg-lead'),
    hasScale: /−\s*50\s*à\s*250/.test(text) && !!document.querySelector('.rg-scale'),
    ptsLeft: (function(){ const c=root&&root.querySelector('.rg-card'); if(!c) return false; const pts=c.querySelector('.rg-card-pts'), name=c.querySelector('.rg-card-name'); return !!(pts&&name&&pts.getBoundingClientRect().left < name.getBoundingClientRect().left - 2); })(),
    oneLine: !root || Array.from(root.querySelectorAll('.rg-card')).every(c => { const name=c.querySelector('.rg-card-name'); return name && c.scrollHeight <= name.offsetHeight + 24 && c.scrollWidth <= c.clientWidth + 1; }),
    noOldIntro: !/part de 50/.test(text) && !/clip dans/.test(text) && !/Actions cotées/i.test(text),
    noBaseRow: !names.some(n => /^Base\b/i.test(n)),
    hasActions: (function(){
      const acc=(document.querySelector('#rg-sec-actions .rg-acc-btn, #rg-sec-actions h2')||{});
      const label=((acc.innerText||'')+'').replace(/\s+/g,' ').trim();
      return /^Actions\b/.test(label) || h2.some(s => /^Actions\b/.test((s||'').replace(/\s+/g,' ').trim()));
    })(),
    accOpen: (document.querySelector('#rg-sec-actions .rg-acc-btn')||{}).getAttribute?.('aria-expanded')==='true',
    accBtn: !!document.querySelector('#rg-sec-actions .rg-acc-btn'),
    otherH2: h2.filter(s => { const t=(s||'').replace(/\s+/g,' ').trim(); return !!t && !/^Actions\b/.test(t) && !/^(LONG|SHORT)$/.test(t) && !/Fondamental|Règles communes|Métaux précieux/.test(t); }),
    noAchatTable: !document.getElementById('rg-table-achat'),
    noRefFold: !document.getElementById('rg-ref'),
    rsiText,
    rsiNew: /\+9\b/.test(rsiText) && /\+18/.test(rsiText) && /\b27\b/.test(rsiText),  /* APE-25 : × 0,9 */
    macdNew: /\+9\b/.test(macdText) && /\+18/.test(macdText) && /\b27\b/.test(macdText),
    macdText,
    rsiOldGone: !(/±\s*3[,.]75/.test(rsiText) || /clip\s*\(/.test(rsiText) || /5\s*%/.test(rsiText)),
    macdOldGone: !(/±\s*3[,.]75/.test(macdText) || /clip\s*\(/.test(macdText) || /5\s*%/.test(macdText)),
    fiboText, ellText, cciText, totText,
    fiboNew: /38[,.]2/.test(fiboText) && /61[,.]8/.test(fiboText) && /78[,.]6/.test(fiboText) && /\b27\b/.test(fiboText),
    fiboOldGone: !/±\s*6\b/.test(fiboText),
    ellGone: !ellText,
    ellOldGone: true,
    cciNew: /sous 20/.test(cciText) && /\+18/.test(cciText) && /\b18\b/.test(cciText),
    cciOldGone: !(/±\s*3[,.]75/.test(cciText) || /clip\s*\(/.test(cciText)),
    noTotal220: !/\b220\b/.test(text),
    has110: /\b99\b/.test(text),  /* APE-25 : technique 99 */
    has90: /\b81\b/.test(text),  /* APE-25 : fondamental 81 */
    hasFondV2: /dette nette/i.test(text) && /Santé/i.test(text),
    fondText: text.replace(/\s+/g,' '),
    fondOk: (function(){ const s=(text||'').toLowerCase(); return /\+10/.test(s) && /\b90\b/.test(s) && !/à valider/.test(s) && /dette nette/.test(s) && /marge opérationnelle/.test(s) && /cash-flow libre/.test(s) && /\broe\b/.test(s) && /liquidité courante/.test(s) && /bpa année prochaine/.test(s) && /bpa cette année/.test(s) && /ca année prochaine/.test(s) && /ca cette année/.test(s) && /<\s*2/.test(s) && /15\s*%/.test(s) && />\s*10\s*%/.test(s) && />\s*5\s*%/.test(s) && /1[,.]2/.test(s); })(),
    hasSentiment: /Sentiment/i.test(text) && /Fear\s*&\s*Greed/i.test(text),
    sentOk: /milieu\s*50/.test((text||'').toLowerCase()) && /peur/.test((text||'').toLowerCase()) && /avidité/.test((text||'').toLowerCase()) && /±\s*50/.test(text),
    noStructure: !names.some(n => /^Structure\b/i.test(n)),
    noFigure: !names.some(n => /^Figure\b/i.test(n)),
    twoCols: techKids.length>=2 && sameRow(techKids[0], techKids[1]),
    fondSideBySide: fondCols.length>=2 && sameRow(fondCols[0], fondCols[1]),
    noPoids: !root || !/poids/i.test(root.innerText||''),
    noIdeal: !/idéalement/i.test(text),
    hasTechGroup: /Technique/i.test(text) && /Fondamental/i.test(text) && /Santé/i.test(text),
    hash: location.hash
  };
})()
""".strip()


CHECK_REGLES_CLOSE_JS = (
    "(() => {"
    "  const b = document.getElementById('rgBack') || document.getElementById('rgClose');"
    "  if (b) b.click();"
    "  const page = document.getElementById('rg-page');"
    "  const open = !!(document.body.classList.contains('rg-on') && page && !page.hasAttribute('hidden'));"
    "  return {open, hash: location.hash};"
    "})()"
)

CLICK_ACTIONS_JS = (
    "(() => {"
    "  const a = document.getElementById('tactions');"
    "  if (a) a.click();"
    "  if (location.hash !== '#actions') location.hash = '#actions';"
    "  const acc = document.getElementById('accAll');"
    "  if (acc) acc.click();"
    "  return true;"
    "})()"
)


def check_headless(root=ROOT):
    print('[headless] chargement de index.html', flush=True)
    chrome = find_chrome()
    if not chrome:
        _fail(
            'Chrome/Chromium introuvable — impossible de vérifier le rendu. Ne pas publier.'
        )
        raise SystemExit(1)

    http_port = _free_port()
    dbg_port = _free_port()
    prev = os.getcwd()
    srv = _start_http(root, http_port)
    profile = tempfile.mkdtemp(prefix='apex-chrome-')
    log_path = Path(profile) / 'chrome.log'
    url = f'http://127.0.0.1:{http_port}/index.html?garde-fou=1'
    cmd = [
        chrome,
        '--headless=new',
        '--disable-gpu',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        f'--remote-debugging-port={dbg_port}',
        '--remote-debugging-address=127.0.0.1',
        f'--user-data-dir={profile}',
        '--window-size=1440,1100',
        'about:blank',
    ]
    logf = open(log_path, 'w')
    proc = subprocess.Popen(cmd, stdout=logf, stderr=logf)
    try:
        ver = None
        for _ in range(60):
            try:
                ver = json.loads(
                    urllib.request.urlopen(
                        f'http://127.0.0.1:{dbg_port}/json/version', timeout=0.3
                    ).read()
                )
                break
            except Exception:
                time.sleep(0.1)
        if not ver:
            tail = log_path.read_text(encoding='utf-8', errors='replace')[-1500:]
            _fail('Chrome headless n’a pas démarré.\n' + tail)
            raise SystemExit(1)

        browser = Cdp(ver['webSocketDebuggerUrl'])
        created = browser.call('Target.createTarget', {'url': 'about:blank'})
        attached = browser.call(
            'Target.attachToTarget',
            {'targetId': created['targetId'], 'flatten': True},
        )
        sid = attached['sessionId']

        def cs(method, params=None, timeout=30):
            return browser.call(method, params, timeout=timeout, session_id=sid)

        cs('Runtime.enable')
        cs('Page.enable')
        cs('Page.navigate', {'url': url})
        loaded = False
        deadline = time.time() + 25
        while time.time() < deadline and not loaded:
            browser.drain(0.4)
            for ev in browser.events:
                if ev.get('method') == 'Page.loadEventFired':
                    loaded = True
                    break
        time.sleep(3)
        browser.drain(1.0)

        def ev():
            res = cs(
                'Runtime.evaluate',
                {'expression': EVAL_JS, 'returnByValue': True},
            )
            return ((res.get('result') or {}).get('value')) or {}

        accueil = ev()
        regles_open = ((cs(
            'Runtime.evaluate',
            {'expression': CHECK_REGLES_OPEN_JS, 'returnByValue': True},
        ).get('result') or {}).get('value')) or {}
        time.sleep(0.4)
        regles_close = ((cs(
            'Runtime.evaluate',
            {'expression': CHECK_REGLES_CLOSE_JS, 'returnByValue': True},
        ).get('result') or {}).get('value')) or {}
        cs(
            'Runtime.evaluate',
            {'expression': CLICK_ACTIONS_JS, 'returnByValue': True},
        )
        time.sleep(2)
        browser.drain(0.8)
        actions = ev()
        exceptions = _exceptions_from(browser.events)
        browser.close()

        if exceptions:
            for e in exceptions:
                _fail('exception JS : ' + e)
            raise SystemExit(1)

        if not accueil.get('tabs') or not accueil.get('has_actions'):
            _fail(
                'aucun onglet rendu (page vide ?). '
                f"texte : {accueil.get('text_head')!r}"
            )
            raise SystemExit(1)
        if (accueil.get('notes') or 0) < MIN_NOTES_ACCUEIL:
            _fail(
                f"Accueil : seulement {accueil.get('notes') or 0} note(s)/fiche(s) "
                f"(minimum {MIN_NOTES_ACCUEIL}). texte : {accueil.get('text_head')!r}"
            )
            raise SystemExit(1)
        # t339u : un plafond /10 mal converti affichait 10/100 (violet) sur presque toutes les classes.
        if (accueil.get('home_sig_n') or 0) >= 3:
            tens = accueil.get('home_sig_tens') or 0
            mx = accueil.get('home_sig_max')
            if tens >= 3 or (mx is not None and mx <= 10):
                _fail(
                    "Accueil : signaux de classes encore plafonnés à 10/100 "
                    f"(tens={tens}, max={mx}, sigs={accueil.get('home_sigs')!r})."
                )
                raise SystemExit(1)
        if not regles_open.get('vis') or not regles_open.get('covers'):
            _fail(
                "page RÈGLES : la vue plein écran ne s'ouvre pas ou ne couvre pas l'écran "
                f"({regles_open!r})."
            )
            raise SystemExit(1)
        if not regles_open.get('hasTable') or not regles_open.get('hasBack') or not regles_open.get('hasClose'):
            _fail(
                "page RÈGLES : tableau Actions, bouton Retour ou Fermer manquant "
                f"({regles_open!r})."
            )
            raise SystemExit(1)
        if not regles_open.get('hasActions'):
            _fail(
                "page RÈGLES : le tableau Actions est manquant "
                f"({regles_open!r})."
            )
            raise SystemExit(1)
        if not regles_open.get('accBtn'):
            _fail(
                "page RÈGLES : le titre Actions n'est pas un bouton accordéon "
                f"({regles_open!r})."
            )
            raise SystemExit(1)
        if not regles_open.get('hasScale'):
            _fail(
                "page RÈGLES : l'échelle calculée « −50 à 250 » manque à côté du titre Actions "
                f"({regles_open!r})."
            )
            raise SystemExit(1)
        if not regles_open.get('noIntro') or not regles_open.get('noOldIntro'):
            _fail(
                "page RÈGLES : un texte d'intro est encore visible "
                f"({regles_open!r})."
            )
            raise SystemExit(1)
        if not regles_open.get('noOldIntro') or not regles_open.get('noBaseRow'):
            _fail(
                "page RÈGLES : l'intro « part de 50 » / « Actions cotées » ou la ligne Base est encore visible "
                f"({regles_open!r})."
            )
            raise SystemExit(1)
        if not regles_open.get('rsiNew') or not regles_open.get('rsiOldGone'):
            _fail(
                "page RÈGLES : la ligne RSI doit afficher +9 / +18 / max 27 (APE-25), "
                "sans poids 5 %, ±3,75 ni formule clip "
                f"({regles_open.get('rsiText')!r})."
            )
            raise SystemExit(1)
        if not regles_open.get('macdNew') or not regles_open.get('macdOldGone'):
            _fail(
                "page RÈGLES : la ligne MACD doit afficher +9 / +18 / max 27 (APE-25), "
                "sans poids 5 %, ±3,75 ni formule clip "
                f"({regles_open.get('macdText')!r})."
            )
            raise SystemExit(1)
        if not regles_open.get('fiboNew') or not regles_open.get('fiboOldGone'):
            _fail(
                "page RÈGLES : la ligne Fibonacci doit afficher les paliers 38,2 / 61,8 / 78,6, max 27, "
                "sans poids 8 % ni ±6 "
                f"({regles_open.get('fiboText')!r})."
            )
            raise SystemExit(1)
        if not regles_open.get('ellGone'):
            _fail(
                "page RÈGLES : Elliott ne doit plus figurer dans le tableau Actions "
                f"({regles_open.get('ellText')!r})."
            )
            raise SystemExit(1)
        if not regles_open.get('cciNew') or not regles_open.get('cciOldGone'):
            _fail(
                "page RÈGLES : la ligne CCI doit afficher +20 si sous 20, max 20, CCI Stochastic Daveatt, "
                "sans poids 5 %, ±3,75 ni formule clip "
                f"({regles_open.get('cciText')!r})."
            )
            raise SystemExit(1)
        if not regles_open.get('noPoids'):
            _fail(
                "page RÈGLES : la colonne Poids ne doit plus apparaître "
                f"({regles_open!r})."
            )
            raise SystemExit(1)
        if not regles_open.get('ptsLeft') or not regles_open.get('oneLine'):
            _fail(
                "page RÈGLES : chaque critère doit tenir sur une ligne (points à gauche, titre, calcul), sans retour à la ligne "
                f"({regles_open!r})."
            )
            raise SystemExit(1)
        if not regles_open.get('noFigure') or not regles_open.get('noTotal220') or not regles_open.get('noIdeal'):
            _fail(
                "page RÈGLES : Figure, total 220 ou « idéalement > 10 % » encore visibles "
                f"({regles_open!r})."
            )
            raise SystemExit(1)
        if not regles_open.get('hasTechGroup') or not regles_open.get('has110') or not regles_open.get('has90'):
            _fail(
                "page RÈGLES : groupes Technique / Fondamental ou sous-totaux 99 / 81 manquants "
                f"({regles_open!r})."
            )
            raise SystemExit(1)
        if not regles_open.get('hasSentiment') or not regles_open.get('sentOk'):
            _fail(
                "page RÈGLES : le groupe Sentiment (Fear & Greed Index, ±50) est manquant ou incomplet "
                f"({regles_open!r})."
            )
            raise SystemExit(1)
        if not regles_open.get('noStructure'):
            _fail(
                "page RÈGLES : la ligne Structure doit être retirée du tableau Actions "
                f"({regles_open!r})."
            )
            raise SystemExit(1)
        if not regles_open.get('noAchatTable') or not regles_open.get('noRefFold'):
            _fail(
                "page RÈGLES : pas de tableau APEX ACHAT séparé ni de bloc replié "
                f"({regles_open!r})."
            )
            raise SystemExit(1)
        if regles_open.get('otherH2'):
            _fail(
                "page RÈGLES : des sections autres qu'Actions sont présentes "
                f"({regles_open.get('otherH2')!r})."
            )
            raise SystemExit(1)
        if regles_close.get('open'):
            _fail(
                "page RÈGLES : le bouton Retour/Fermer ne referme pas la page "
                f"({regles_close!r})."
            )
            raise SystemExit(1)
        n_fiches = max(actions.get('notes') or 0, actions.get('n_lis') or 0)
        if n_fiches < MIN_FICHES_ACTIONS:
            _fail(
                f"onglet Actions : seulement {n_fiches} fiche(s) rendue(s) "
                f"(minimum {MIN_FICHES_ACTIONS})."
            )
            raise SystemExit(1)
        _ok(
            f'aucune exception, Accueil {accueil.get("notes")} notes, signaux classes max {accueil.get("home_sig_max")}, '
            f'onglet Actions {n_fiches} fiches, page RÈGLES ok (Chrome {Path(chrome).name})'
        )
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        try:
            srv.shutdown()
        except Exception:
            pass
        os.chdir(prev)
        shutil.rmtree(profile, ignore_errors=True)
        try:
            logf.close()
        except Exception:
            pass



def check_positions_root(root=ROOT):
    """t456u : les JSON fetchés à la racine doivent suivre data/ (même relevé)."""
    names = ('positions.json', 'positions_revolut.json', 'positions_revolutx.json')
    print('[positions] JSON à la racine alignés sur data/')
    for fn in names:
        data = root / 'data' / fn
        racine = root / fn
        if not data.exists():
            _fail(f'{fn} : absent de data/, pas de source de vérité')
            raise SystemExit(1)
        if not racine.exists():
            _fail(
                f'{fn} : absent à la racine du dépôt. index.html le recharge au démarrage '
                f'(fetch cache:no-cache) et écraserait le relevé embarqué avec une copie '
                f'obsolète, ou le laisserait manquer.'
            )
            raise SystemExit(1)
        a = data.read_bytes()
        b = racine.read_bytes()
        if a != b:
            _fail(
                f'{fn} à la racine diffère de data/{fn} '
                f'({len(b)} octets vs {len(a)}). Recopier data/ vers la racine '
                f'(build.py le fait) avant de publier.'
            )
            raise SystemExit(1)
        _ok(f'{fn} racine = data/ ({len(a)} octets)')
    try:
        import json
        book = json.loads((root / 'positions.json').read_text(encoding='utf-8'))
        ticks = [(p.get('ticker') or '') for p in (book.get('positions') or [])]
        stale = [t for t in ('NKE', 'STLA', 'PKX', 'BTC', 'BKNG', 'PPX', 'HMI', 'DASH', 'MC', 'XUTL') if t in ticks]
        missing = [t for t in ('XAU', 'CAT', 'ENPH', 'MU', 'LRCX') if t not in ticks]
        if stale or missing:
            _fail(
                'positions.json racine : relevé incomplet ou obsolète '
                f'(encore {stale or "—"} / manque {missing or "—"}).'
            )
            raise SystemExit(1)
        _ok('positions.json : XAU, CAT, ENPH, MU, LRCX présents ; ventes du 25/11 (PPX, BKNG, HMI, DASH, MC, XUTL) et NKE/STLA/PKX/BTC absents')
    except SystemExit:
        raise
    except Exception as e:
        _fail(f'lecture positions.json : {type(e).__name__}: {e}')
        raise SystemExit(1)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description='Garde-fou : syntaxe JS + rendu headless avant publication.'
    )
    ap.add_argument(
        '--syntax',
        action='store_true',
        help='Uniquement node --check + JSON embarqué',
    )
    ap.add_argument(
        '--headless',
        action='store_true',
        help='Uniquement le chargement headless',
    )
    ap.add_argument(
        '--root',
        default=None,
        help='Racine du dépôt (défaut : dossier du dépôt contenant ce script)',
    )
    args = ap.parse_args(argv)
    root = Path(args.root).resolve() if args.root else ROOT
    os.environ['APEX_ROOT'] = str(root)
    both = not args.syntax and not args.headless
    print('== Garde-fou site APEX ==', flush=True)
    print(f'racine {root}', flush=True)
    try:
        if both or args.syntax:
            check_syntax(root)
            check_positions_root(root)
        if both or args.headless:
            check_headless(root)
    except SystemExit as e:
        if e.code not in (0, None):
            print('ÉCHEC — ne pas commiter, ne pas publier.', flush=True)
        raise
    print('OK — publication autorisée.', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
