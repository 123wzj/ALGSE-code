"""How much the reported partition depends on the Louvain
seed. Re-runs the community detection of membership_only.py (NetworkX
louvain_communities, weight = event multiplicity) with several seeds on the
existing snapshot graphs and recomputes the candidate-set metrics of
analyze_e1.py for each. Seed 42 is the one used for the paper's tables, so its
row doubles as a reproduction check.

Env: RUNDIR, SEEDS (default "42,1,2,3,4")
Output: seed_sweep.json (checkpointed after every seed)
"""
import os as _os
_ROOT = _os.environ.get('ALGSE_ROOT', _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..')))
import os, sys, json, time, statistics
from collections import defaultdict
CODE = _os.path.join(_ROOT, 'ALGSE')
RUN = os.environ.get('RUNDIR', _os.path.join(_ROOT, 'results', 'cadets_e3'))
sys.path.insert(0, CODE)
os.chdir(RUN)
from generator_community_to_graph import load_graph
from networkx.algorithms.community import louvain_communities
import networkx
SEEDS = [int(x) for x in os.environ.get('SEEDS', '42,1,2,3,4').split(',')]

allGraph = load_graph('medium/graph2.pkl')
gt = set()
with open('parse_data/groundtruth_nodeId.txt') as f:
    for line in f:
        p = line.split()
        if p:
            gt.add(p[0])

per = {}
for seed in SEEDS:
    t = time.time()
    membership = {}
    sizes = []
    total = 0
    for gid in sorted(allGraph):
        G = allGraph[gid]
        if G is None or G.number_of_nodes() == 0:
            continue
        for cidx, ns in enumerate(louvain_communities(G, weight='weight', seed=seed)):
            lab = '%d.%d' % (gid, cidx)
            total += 1
            sizes.append(len(ns))
            for n in ns:
                membership[str(n)] = lab
    comm_nodes = defaultdict(set)
    for n, c in membership.items():
        comm_nodes[c].add(n)
    gt_in = [n for n in gt if n in membership]
    attack = defaultdict(set)
    for n in gt_in:
        attack[membership[n]].add(n)
    involved = sum(len(comm_nodes[c]) for c in attack)
    dens = [len(a) / len(comm_nodes[c]) for c, a in attack.items()]
    per[str(seed)] = {
        'communities': total,
        'attack_containing_communities': len(attack),
        'attack_nodes_in_graph': len(gt_in),
        'involved_nodes': involved,
        'candidate_reduction_pct': round((1 - involved / len(membership)) * 100, 3),
        'precision_pct': round(100.0 * len(gt_in) / involved, 3) if involved else 0.0,
        'mean_attack_density_pct': round(100.0 * sum(dens) / len(dens), 3) if dens else 0.0,
        'max_community_size': max(sizes),
        'mean_community_size': round(sum(sizes) / len(sizes), 2),
        'sec': round(time.time() - t, 1),
    }
    print('SEED_DONE', seed, json.dumps(per[str(seed)]), flush=True)
    with open('seed_sweep.json', 'w') as f:
        json.dump({'networkx': networkx.__version__, 'seeds': SEEDS, 'per_seed': per}, f, indent=2)

KEYS = ['communities', 'attack_containing_communities', 'involved_nodes',
        'candidate_reduction_pct', 'precision_pct', 'mean_attack_density_pct', 'mean_community_size']
spread = {}
for k in KEYS:
    v = [per[s][k] for s in per]
    spread[k] = {'min': min(v), 'max': max(v), 'mean': round(statistics.mean(v), 3),
                 'std': round(statistics.pstdev(v), 3)}
with open('seed_sweep.json', 'w') as f:
    json.dump({'networkx': networkx.__version__, 'seeds': SEEDS, 'per_seed': per, 'spread': spread}, f, indent=2)
print('SEED_SWEEP_DONE', json.dumps(spread), flush=True)
