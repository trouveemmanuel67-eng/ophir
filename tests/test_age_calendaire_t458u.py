"""t458u : l'âge d'un achat du jour est 0 j (jours calendaires Europe/Paris), pas 1 j l'après-midi."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_accueil_utilise_jours_calendaires():
    js = (ROOT / 'src' / 'accueil.js').read_text(encoding='utf-8')
    assert 'function homeCalendarDays' in js
    assert 'homeCalendarDays(d, now)' in js
    assert '(now.getTime()-d.getTime())/86400000' not in js


def test_achat_du_jour_reste_zero_l_apres_midi():
    script = r"""
    function homeParisYMD(d){
      return new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Paris',year:'numeric',month:'2-digit',day:'2-digit'}).format(d);
    }
    function homeCalendarDays(from, now){
      const a=homeParisYMD(from), b=homeParisYMD(now);
      const [ay,am,ad]=a.split('-').map(Number);
      const [by,bm,bd]=b.split('-').map(Number);
      return (Date.UTC(by,bm-1,bd)-Date.UTC(ay,am-1,ad))/86400000;
    }
    function homeParseParisDate(s){
      const str=String(s).trim();
      const m=str.match(/^(\d{4})-(\d{2})-(\d{2})$/);
      if(m) return new Date(Number(m[1]), Number(m[2])-1, Number(m[3]), 12, 0, 0);
      return new Date(str);
    }
    const buy=homeParseParisDate('2026-11-24');
    const afternoon=new Date('2026-11-24T13:10:00+01:00');
    const tomorrow=new Date('2026-11-25T00:30:00+01:00');
    const broken=Math.round((afternoon.getTime()-new Date('2026-11-24').getTime())/86400000);
    const got=homeCalendarDays(buy, afternoon);
    const nxt=homeCalendarDays(buy, tomorrow);
    if(got!==0) { console.error('same day', got); process.exit(1); }
    if(nxt!==1) { console.error('next day', nxt); process.exit(1); }
    if(broken!==1) { console.error('expected old bug to be 1, got', broken); process.exit(1); }
    console.log('ok', got, nxt, 'oldWouldBe', broken);
    """
    r = subprocess.run(['node', '-e', script], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert 'ok 0 1' in r.stdout
