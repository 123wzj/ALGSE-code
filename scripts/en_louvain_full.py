"""Full per-snapshot Louvain membership.

Outputs (in RUNDIR):
  multi_membership.json      node -> [every "gid.cidx" it belongs to, snapshot order]
  edges_intra_lastwins.txt   "snap u v" undirected intra-community edges of the
                             last-wins projected communities (= exactly the edge
                             information encoded in the stored T_CG'/T_c/C)
  louvain_full_summary.json  counts for cross-checking against e1_result.json

Louvain call identical to membership_only.py (seed=42, weight='weight'),
so the projection reproduces the numbers of analyze_e1.py.
"""
import os as _os
_ROOT = _os.environ.get('ALGSE_ROOT', _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..')))
import sys, os, json, time
os.environ.setdefault('MPLBACKEND', 'Agg')
CODE = _os.path.join(_ROOT, 'ALGSE')
RUN = os.environ.get('RUNDIR', _os.path.join(_ROOT, 'results', 'cadets_e3'))
sys.path.insert(0, CODE)
os.chdir(RUN)
from generator_community_to_graph import load_graph
from networkx.algorithms.community import louvain_communities

t0 = time.time()
allGraph = load_graph('medium/graph2.pkl')
gids = sorted(allGraph.keys())

multi = {}           # node -> [labels]
lastwins = {}        # node -> label   (projection identical to membership_only.py)
comm_nodes_full = {} # label -> node list (full)
total_comms = 0
for gid in gids:
    G = allGraph.get(gid)
    if not G or G.number_of_nodes() == 0:
        continue
    for cidx, ns in enumerate(louvain_communities(G, weight='weight', seed=42)):
        lab = '%d.%d' % (gid, cidx)
        total_comms += 1
        comm_nodes_full[lab] = list(ns)
        for n in ns:
            multi.setdefault(n, []).append(lab)
            lastwins[n] = lab

# --- projection (last-wins) community members, as analyze_e1/storage_fast2 use ---
proj = {}
for n, lab in lastwins.items():
    proj.setdefault(lab, []).append(n)

# --- intra-community edges of the projected (stored) communities ---
ecount = 0
with open('edges_intra_lastwins.txt', 'w') as f:
    for lab, nodes in proj.items():
        gid = int(lab.split('.')[0])
        G = allGraph[gid]
        nodes = [x for x in nodes if G.has_node(x)]
        sub = G.subgraph(nodes)
        for u, v in sub.edges():
            f.write('%d %s %s\n' % (gid, u, v))
            ecount += 1

with open('multi_membership.json', 'w') as f:
    json.dump(multi, f)

recur = sum(1 for n, labs in multi.items() if len(labs) > 1)
summary = {
    'snapshots': len(gids),
    'total_communities_full': total_comms,
    'total_communities_projected': len(proj),
    'unique_nodes': len(multi),
    'nodes_in_multiple_snapshots': recur,
    'max_memberships': max(len(v) for v in multi.values()),
    'intra_edges_projected': ecount,
    'sec': round(time.time() - t0, 1),
}
with open('louvain_full_summary.json', 'w') as f:
    json.dump(summary, f, indent=2)
print('LOUVAIN_FULL_DONE', json.dumps(summary), flush=True)
