"""Disponibilité au comptant (Revolut ou XTB OMI), sans CFD.
Source XTB : table OMI France, PDF du 24/09/2026, intégrée le 18/11/2026."""
import json, os
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D=json.load(open(os.path.join(R,'data/disponibilites.json')))
SYM=D.get('symbols') or {}
def of(tv):
    return SYM.get(tv) or {}
def cash_ok(tv):
    if not tv: return False
    d=of(tv)
    return d.get('revolut') is True or d.get('xtb') is True
