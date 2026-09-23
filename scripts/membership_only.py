"""Community membership (Louvain per snapshot, no block storage)."""
import os as _os
_ROOT = _os.environ.get('ALGSE_ROOT', _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..')))
import sys, os, json, time
os.environ.setdefault('MPLBACKEND', 'Agg')
CODE = _os.path.join(_ROOT, 'ALGSE')
RUN = os.environ.get('RUNDIR', _os.path.join(_ROOT, 'results', 'cadets_e3'))
sys.path.insert(0, CODE)
os.chdir(RUN)
from graphBulid import graphBuild
from generator_community_to_graph import load_graph
from networkx.algorithms.community import louvain_communities
t0 = time.time()
ng = graphBuild('parse_data/event.txt', 5000, 'medium/graph2.pkl')
allGraph = load_graph('medium/graph2.pkl')
membership = {}
sizes = []
total = 0
for gid in range(ng):
    G = allGraph.get(gid)
    if not G or G.number_of_nodes() == 0:
        continue
    for cidx, ns in enumerate(louvain_communities(G, weight='weight', seed=42)):
        lab = '%d.%d' % (gid, cidx)
        total += 1
        sizes.append(len(ns))
        for n in ns:
            membership[n] = lab
with open('node_community.json', 'w') as f:
    json.dump(membership, f)
with open('community_sizes.json', 'w') as f:
    json.dump(sizes, f)
print('MEMBERSHIP_DONE communities', total, 'nodes', len(membership),
      'chunks', ng, 'sec', round(time.time()-t0, 1), flush=True)
