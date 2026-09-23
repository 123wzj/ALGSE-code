"""Plain breadth-first search on the raw provenance graph,
from the same POIs as the community-driven replay, with the same
recall-versus-fraction-of-graph curve, so the two can be read at equal budget.

Both methods are run here on identical POIs and identical ground truth:
  bfs        hop-by-hop BFS over the union of all snapshot graphs (all edges)
  community  the Section 4.4 expansion (open the POI's communities, then every
             community reachable through a recurring boundary node), with the
             communities of a hop opened one at a time in label order so that a
             fine-grained curve exists for it too
For each POI and method we keep the visitation index of every ground-truth
node, so recall at any budget and the budget at any recall follow exactly.

Env: RUNDIR, MAXPOI (20), MAXHOP (12)
Output: bfs_baseline.json
"""
import os as _os
_ROOT = _os.environ.get('ALGSE_ROOT', _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..')))
import os, sys, json, time
CODE = _os.path.join(_ROOT, 'ALGSE')
RUN = os.environ.get('RUNDIR', _os.path.join(_ROOT, 'results', 'cadets_e3'))
MAXPOI = int(os.environ.get('MAXPOI', '20'))
MAXHOP = int(os.environ.get('MAXHOP', '12'))
sys.path.insert(0, CODE)
os.chdir(RUN)
from generator_community_to_graph import load_graph

t0 = time.time()


def S(x):
    return x if isinstance(x, str) else str(x)


# ---- raw graph: union of all snapshots ----
allGraph = load_graph('medium/graph2.pkl')
adj = {}
for gid, G in allGraph.items():
    if G is None:
        continue
    for n in G.nodes():
        adj.setdefault(S(n), set())
    for u, v in G.edges():
        u, v = S(u), S(v)
        adj[u].add(v)
        adj[v].add(u)
del allGraph
N = len(adj)
E = sum(len(v) for v in adj.values()) // 2
print('graph loaded nodes', N, 'edges', E, 'sec', round(time.time() - t0, 1), flush=True)

# ---- same POIs and ground truth as en_poi_traversal.py ----
multi = json.load(open('multi_membership.json'))
comm_nodes = {}
for n, labs in multi.items():
    for lab in labs:
        comm_nodes.setdefault(lab, []).append(n)
assert len(multi) == N, (len(multi), N)

gt = set()
with open('parse_data/groundtruth_nodeId.txt') as f:
    for line in f:
        p = line.split()
        if p:
            gt.add(p[0])
gt_in = gt & set(adj.keys())
subj = set()
with open('parse_data/subject.txt') as f:
    for line in f:
        i = line.split(':', 1)[0].strip()
        if i:
            subj.add(i)
gt_proc = sorted(gt_in & subj, key=int) or sorted(gt_in, key=int)
if len(gt_proc) > MAXPOI:
    step = len(gt_proc) / float(MAXPOI)
    gt_proc = [gt_proc[int(i * step)] for i in range(MAXPOI)]
G_IN = len(gt_in)


def rec(hop, visited, cov):
    return {'hop': hop, 'visited': visited, 'frac_pct': round(100.0 * visited / N, 3),
            'gt_covered': cov, 'gt_recall_pct': round(100.0 * cov / G_IN, 3)}


def bfs(poi):
    seen = {poi}
    visited = 1
    hits = [1] if poi in gt_in else []
    frontier = [poi]
    hop = 0
    curve = []
    while True:
        curve.append(rec(hop, visited, len(hits)))
        if len(hits) == G_IN or hop >= MAXHOP or not frontier:
            break
        nxt = []
        for u in frontier:
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    visited += 1
                    nxt.append(v)
                    if v in gt_in:
                        hits.append(visited)
        frontier = nxt
        hop += 1
    return curve, hits, visited


def community(poi):
    labs0 = sorted(multi.get(poi, []))
    if not labs0:
        return None
    opened = set()
    cand = set()
    hits = []

    def open_comm(lab):
        opened.add(lab)
        for n in comm_nodes[lab]:
            if n not in cand:
                cand.add(n)
                if n in gt_in:
                    hits.append(len(cand))

    for lab in labs0:
        open_comm(lab)
    hop = 0
    curve = []
    while True:
        curve.append(rec(hop, len(cand), len(hits)))
        if len(hits) == G_IN or hop >= MAXHOP:
            break
        new = set()
        for n in cand:
            labs = multi[n]
            if len(labs) > 1:
                for lab in labs:
                    if lab not in opened:
                        new.add(lab)
        if not new:
            break
        for lab in sorted(new):
            open_comm(lab)
        hop += 1
    return curve, hits, len(cand)


BUDGETS = [0.5, 1, 2, 5, 10, 20, 50]
THRESH = [50, 90, 100]


def analyse(curve, hits, visited):
    final = curve[-1]['gt_covered']
    plateau = next(r for r in curve if r['gt_covered'] == final)
    out = {'hops_to_plateau': plateau['hop'], 'frac_pct_at_plateau': plateau['frac_pct'],
           'final_recall_pct': curve[-1]['gt_recall_pct'], 'final_hop': curve[-1]['hop'],
           'visited_final': visited}
    for r in THRESH:
        need = -(-r * G_IN // 100)
        out['frac_pct_to_recall_%d' % r] = round(100.0 * hits[need - 1] / N, 3) if len(hits) >= need else None
    for b in BUDGETS:
        lim = b * N / 100.0
        k = sum(1 for h in hits if h <= lim)
        out['recall_pct_at_%s' % str(b).replace('.', '_')] = round(100.0 * k / G_IN, 3)
    return out


per = {'bfs': {}, 'community': {}}
curves = {'bfs': {}, 'community': {}}
for poi in gt_proc:
    c, h, v = bfs(poi)
    per['bfs'][poi] = analyse(c, h, v)
    curves['bfs'][poi] = c
    r = community(poi)
    if r:
        c2, h2, v2 = r
        per['community'][poi] = analyse(c2, h2, v2)
        curves['community'][poi] = c2
    print('poi', poi,
          'bfs', per['bfs'][poi]['hops_to_plateau'], per['bfs'][poi]['frac_pct_at_plateau'],
          'comm', per['community'].get(poi, {}).get('hops_to_plateau'),
          per['community'].get(poi, {}).get('frac_pct_at_plateau'), flush=True)


def med(x):
    x = sorted(v for v in x if v is not None)
    return x[len(x) // 2] if x else None


def summary(d):
    keys = sorted({k for v in d.values() for k in v})
    s = {}
    for k in keys:
        vals = [v[k] for v in d.values()]
        present = [x for x in vals if x is not None]
        s[k] = {'min': min(present) if present else None,
                'median': med(vals),
                'max': max(present) if present else None,
                'n_none': sum(1 for x in vals if x is None)}
    return s


def median_poi(d):
    ranked = sorted(d.items(), key=lambda kv: (kv[1]['hops_to_plateau'], kv[1]['frac_pct_at_plateau']))
    return ranked[len(ranked) // 2][0] if ranked else None


mb, mc = median_poi(per['bfs']), median_poi(per['community'])
res = {
    'total_nodes': N, 'total_edges_union': E, 'gt_in_graph': G_IN,
    'pois_run': len(gt_proc), 'pois': gt_proc,
    'bfs': {'summary': summary(per['bfs']), 'median_poi': mb,
            'median_poi_curve': curves['bfs'].get(mb), 'per_poi': per['bfs']},
    'community': {'summary': summary(per['community']), 'median_poi': mc,
                  'median_poi_curve': curves['community'].get(mc), 'per_poi': per['community']},
    'sec': round(time.time() - t0, 1),
}
with open('bfs_baseline.json', 'w') as f:
    json.dump(res, f, indent=2)
KEYS = ('hops_to_plateau', 'frac_pct_at_plateau', 'final_recall_pct', 'frac_pct_to_recall_100',
        'frac_pct_to_recall_90', 'recall_pct_at_1', 'recall_pct_at_5', 'recall_pct_at_20')
brief = {m: {k: res[m]['summary'][k]['median'] for k in KEYS} for m in ('bfs', 'community')}
print('BFS_BASELINE_DONE', json.dumps(brief), flush=True)
