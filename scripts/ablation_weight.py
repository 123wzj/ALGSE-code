"""Ablation: multiplicity-weighted vs unweighted Louvain, measured by attack-node
concentration. Reuses the snapshot graphs and the ground-truth node ids."""
import os as _os
_ROOT = _os.environ.get('ALGSE_ROOT', _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..')))
import json, os, sys
from collections import defaultdict
os.environ.setdefault('MPLBACKEND', 'Agg')
CODE = _os.path.join(_ROOT, 'ALGSE')
RUN = os.environ.get('RUNDIR', _os.path.join(_ROOT, 'results', 'cadets_e3'))
sys.path.insert(0, CODE)
os.chdir(RUN)
from generator_community_to_graph import load_graph
from networkx.algorithms.community import louvain_communities

gt = set()
for l in open('parse_data/groundtruth_nodeId.txt'):
    p = l.split()
    if p:
        gt.add(p[0])
allGraph = load_graph('medium/graph2.pkl')

def run(weight):
    membership = {}
    for gid in allGraph:
        G = allGraph[gid]
        if not G or G.number_of_nodes() == 0:
            continue
        for cidx, ns in enumerate(louvain_communities(G, weight=weight, seed=42)):
            for n in ns:
                membership[n] = '%s.%d' % (gid, cidx)
    comm = defaultdict(set)
    for n, c in membership.items():
        comm[c].add(n)
    gtg = [n for n in gt if n in membership]
    ac = defaultdict(set)
    for n in gtg:
        ac[membership[n]].add(n)
    involved = sum(len(comm[c]) for c in ac)
    return {'weight': str(weight), 'total_communities': len(comm), 'attack_nodes': len(gtg),
            'attack_communities': len(ac), 'involved_nodes': involved,
            'reduction_pct': round((1-involved/len(membership))*100, 2) if membership else 0,
            'mean_density': round(sum(len(a)/len(comm[c]) for c, a in ac.items())/len(ac), 5) if ac else 0,
            'precision': round(len(gtg)/involved, 5) if involved else 0}

w = run('weight')
u = run(None)
print('WEIGHTED', json.dumps(w), flush=True)
print('UNWEIGHTED', json.dumps(u), flush=True)
with open('ablation_weight.json', 'w') as f:
    json.dump({'weighted': w, 'unweighted': u}, f, indent=2)
print('ABLATION_DONE', flush=True)
