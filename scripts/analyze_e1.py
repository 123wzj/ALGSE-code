"""
Candidate-set analysis (run after membership_only.py).
Computes community-membership precision/recall, per-community attack density,
fragmentation and purity (resolution-limit / absorption evidence), and the
candidate-set reduction.
"""
import os as _os
_ROOT = _os.environ.get('ALGSE_ROOT', _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..')))
import json, os
from collections import defaultdict
RUN = os.environ.get('RUNDIR', _os.path.join(_ROOT, 'results', 'cadets_e3'))
os.chdir(RUN)

membership = json.load(open('node_community.json'))   # node(str) -> "gid.cidx"

gt_listed = set()
with open('parse_data/groundtruth_nodeId.txt') as f:
    for line in f:
        p = line.split()
        if p:
            gt_listed.add(p[0])

comm_nodes = defaultdict(set)
for node, c in membership.items():
    comm_nodes[c].add(node)

gt_in_graph = [n for n in gt_listed if n in membership]
attack_comms = defaultdict(set)
for n in gt_in_graph:
    attack_comms[membership[n]].add(n)

total_nodes = len(membership)
total_comms = len(comm_nodes)
attack_node_count = len(gt_in_graph)
involved_nodes = sum(len(comm_nodes[c]) for c in attack_comms)
fragmentation = len(attack_comms)
precision = attack_node_count / involved_nodes if involved_nodes else 0.0
covered = len(set().union(*attack_comms.values())) if attack_comms else 0
recall = covered / attack_node_count if attack_node_count else 0.0
reduction = involved_nodes / total_nodes if total_nodes else 0.0

per_comm = []
for c, atk in attack_comms.items():
    s = len(comm_nodes[c])
    per_comm.append({'community': c, 'size': s, 'attack': len(atk),
                     'density': round(len(atk)/s, 6), 'purity_benign': round(1-len(atk)/s, 6)})
per_comm.sort(key=lambda d: -d['density'])

sizes = [len(v) for v in comm_nodes.values()]
res = {
    'total_nodes': total_nodes,
    'total_communities': total_comms,
    'gt_total_listed': len(gt_listed),
    'attack_nodes_in_graph': attack_node_count,
    'attack_containing_communities': fragmentation,
    'frac_communities_attack_relevant': round(fragmentation/total_comms, 6) if total_comms else 0,
    'involved_nodes': involved_nodes,
    'candidate_reduction_ratio': round(reduction, 6),
    'candidate_reduction_pct': round((1-reduction)*100, 3),
    'attack_node_precision_in_involved': round(precision, 6),
    'recall_within_retrieved_communities': round(recall, 6),
    'mean_attack_density': round(sum(d['density'] for d in per_comm)/len(per_comm), 6) if per_comm else 0,
    'max_community_size': max(sizes) if sizes else 0,
    'mean_community_size': round(sum(sizes)/len(sizes), 2) if sizes else 0,
    'top_attack_communities': per_comm[:20],
}
with open('e1_result.json', 'w') as f:
    json.dump(res, f, indent=2)
brief = {k: v for k, v in res.items() if k != 'top_attack_communities'}
print('E1_DONE', json.dumps(brief), flush=True)
