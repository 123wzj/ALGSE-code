"""Membership-slot accounting: cost of storing the FULL per-snapshot
membership (needed by boundary traversal) versus the disjoint projection
used in the measured footprint C."""
import os as _os
_ROOT = _os.environ.get('ALGSE_ROOT', _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..')))
import sys, json
sys.path.insert(0, _os.path.join(_ROOT, 'ALGSE'))
from generator_community_to_graph import load_graph
for s in ('cadets', 'theia', 'trace'):
    ag = load_graph(_os.path.join(_ROOT, 'results', '%s_e3', 'medium', 'graph2.pkl') % s)
    slots = sum(g.number_of_nodes() for g in ag.values() if g)
    uniq = set()
    for g in ag.values():
        if g:
            uniq.update(g.nodes())
    tc = _os.path.join(_ROOT, 'results', '%s_e3', 'T_c.txt') % s
    import os
    tc_bytes = os.path.getsize(tc) if os.path.exists(tc) else None
    row = {'scenario': s, 'slots': slots, 'unique': len(uniq),
           'extra_rows': slots - len(uniq),
           'extra_pct_of_rows': round(100.0 * (slots - len(uniq)) / slots, 2),
           'T_c_bytes_projected': tc_bytes}
    print('TC_DELTA', json.dumps(row), flush=True)
