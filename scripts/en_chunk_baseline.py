"""Fixed-size chunking without Louvain (partition ablation).

Same snapshot stream (graph2.pkl), but each snapshot's nodes are cut into
contiguous chunks of S nodes in arrival order (insertion order of the graph),
with no community detection.  S defaults to the dataset's mean Louvain
community size (granularity-matched), read from e1_result.json.

Candidate-set metrics: computed EXACTLY as analyze_e1.py (last-wins
projection, same formulas), so the rows are directly comparable to the community partition.

Storage side: block encoding (BS=4) with the same degree-based reordering
inside every chunk, mirroring storage_fast2.py, so the character volume and
non-zero block count are directly comparable to the community run.

Env: RUNDIR, S (optional override)
Output: chunk_baseline.json
"""
import os as _os
_ROOT = _os.environ.get('ALGSE_ROOT', _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..')))
import os, sys, json, time
from collections import defaultdict
CODE = _os.path.join(_ROOT, 'ALGSE')
RUN = os.environ.get('RUNDIR', _os.path.join(_ROOT, 'results', 'cadets_e3'))
sys.path.insert(0, CODE)
os.chdir(RUN)
from generator_community_to_graph import load_graph

t0 = time.time()
e1 = json.load(open('e1_result.json'))
S = int(os.environ.get('S', str(int(round(e1['mean_community_size'])))))
BS = 4

allGraph = load_graph('medium/graph2.pkl')
gids = sorted(allGraph.keys())

# ---- chunk assignment: arrival order, last-wins projection ----
lastwins = {}
for gid in gids:
    G = allGraph.get(gid)
    if not G or G.number_of_nodes() == 0:
        continue
    for pos, n in enumerate(G.nodes()):
        lastwins[n] = '%d.%d' % (gid, pos // S)

comm_nodes = defaultdict(set)
for n, c in lastwins.items():
    comm_nodes[c].add(n)

# ---- candidate-set metrics, formulas identical to analyze_e1.py ----
gt_listed = set()
with open('parse_data/groundtruth_nodeId.txt') as f:
    for line in f:
        p = line.split()
        if p:
            gt_listed.add(p[0])
gt_in_graph = [n for n in gt_listed if n in lastwins]
attack_comms = defaultdict(set)
for n in gt_in_graph:
    attack_comms[lastwins[n]].add(n)
total_nodes = len(lastwins)
total_comms = len(comm_nodes)
involved = sum(len(comm_nodes[c]) for c in attack_comms)
per = [len(a) / len(comm_nodes[c]) for c, a in attack_comms.items()]
metrics = {
    'S': S,
    'total_nodes': total_nodes,
    'total_partitions': total_comms,
    'attack_nodes_in_graph': len(gt_in_graph),
    'attack_containing_partitions': len(attack_comms),
    'frac_partitions_attack_relevant': round(len(attack_comms) / total_comms, 6),
    'involved_nodes': involved,
    'candidate_reduction_pct': round((1 - involved / total_nodes) * 100, 3),
    'attack_node_precision_in_involved': round(len(gt_in_graph) / involved, 6) if involved else 0,
    'mean_attack_density': round(sum(per) / len(per), 6) if per else 0,
    'recall_within_retrieved': 1.0 if attack_comms else 0.0,
}

# ---- storage side: block volume under chunk partition ----
def block_encode(edges, perm):
    blocks = defaultdict(set)
    for u, v in edges:
        r = perm[u]; c = perm[v]
        blocks[(r // BS, c // BS)].add((r % BS, c % BS))
        blocks[(c // BS, r // BS)].add((c % BS, r % BS))
    chars = 0
    for (R, C), cells in blocks.items():
        chars += BS * BS + len(str(R)) + len(str(C))
    return chars, len(blocks)

def degree_perm(n, edges):
    deg = [0] * n
    for u, v in edges:
        deg[u] += 1; deg[v] += 1
    order = sorted(range(n), key=lambda i: -deg[i])
    perm = [0] * n
    for newi, oldi in enumerate(order):
        perm[oldi] = newi
    return perm

tot_chars = 0
tot_blocks = 0
tot_edges = 0
done = 0
for lab, nodes in comm_nodes.items():
    gid = int(lab.split('.')[0])
    G = allGraph.get(gid)
    if G is None:
        continue
    nodes = [x for x in nodes if G.has_node(x)]
    if not nodes:
        continue
    idx = {x: i for i, x in enumerate(nodes)}
    sub = G.subgraph(nodes)
    edges = [(idx[u], idx[v]) for u, v in sub.edges()]
    perm = degree_perm(len(nodes), edges)
    ch, bl = block_encode(edges, perm)
    tot_chars += ch
    tot_blocks += bl
    tot_edges += len(edges)
    done += 1

# note: intra-partition edges only, same convention as the community store;
# chunking drops a DIFFERENT (larger) set of inter-partition edges, so the
# retained-edge counts are reported alongside the block volume.
sref = None
try:
    sref = json.load(open('storage_result.json'))
except Exception:
    pass
lref = None
try:
    lref = json.load(open('louvain_full_summary.json'))
except Exception:
    pass
res = {
    'metrics': metrics,
    'storage': {
        'chunk_TCG_chars': tot_chars,
        'chunk_TCG_MB': round(tot_chars / 1e6, 2),
        'chunk_nonzero_blocks': tot_blocks,
        'chunk_intra_edges': tot_edges,
        'community_reference': {
            'T_CG_bytes': sref.get('T_CG_bytes') if sref else None,
            'blocks_degree_reorder': sref.get('blocks_degree_reorder') if sref else None,
            'intra_edges_projected': lref.get('intra_edges_projected') if lref else None,
        },
        'partitions_encoded': done,
    },
    'sec': round(time.time() - t0, 1),
}
with open('chunk_baseline.json', 'w') as f:
    json.dump(res, f, indent=2)
print('CHUNK_BASELINE_DONE', json.dumps(res), flush=True)
