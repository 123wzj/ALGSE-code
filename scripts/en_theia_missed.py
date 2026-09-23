"""Identify the THEIA in-scope GT entity unreachable by boundary traversal:
compute connected components of the community-share relation via union-find
over each node's membership list, then check every GT node and POI."""
import os as _os
_ROOT = _os.environ.get('ALGSE_ROOT', _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..')))
import os, json
RUN = _os.path.join(_ROOT, 'results', 'theia_e3')
os.chdir(RUN)
multi = json.load(open('multi_membership.json'))

parent = {}
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[ra] = rb

for n, labs in multi.items():
    for lab in labs:
        if lab not in parent:
            parent[lab] = lab
    for i in range(1, len(labs)):
        union(labs[0], labs[i])

gt = set()
with open('parse_data/groundtruth_nodeId.txt') as f:
    for line in f:
        p = line.split()
        if p:
            gt.add(p[0])
gt_in = [n for n in gt if n in multi]

from collections import Counter
comp_of_node = {}
for n in gt_in:
    comp_of_node[n] = find(multi[n][0])
comp_counts = Counter(comp_of_node.values())
main_comp, main_n = comp_counts.most_common(1)[0]
outliers = {n: c for n, c in comp_of_node.items() if c != main_comp}
lab_size = Counter()
for n, labs in multi.items():
    for lab in labs:
        lab_size[lab] += 1
print('gt_in', len(gt_in), 'main component holds', main_n)
print('outlier GT nodes:', outliers)
for n in outliers:
    print('  node', n, 'memberships', multi[n],
          'community sizes', [lab_size[lab] for lab in multi[n]])
# is the outlier's whole component detached from the main one?
for n in outliers:
    comp = comp_of_node[n]
    comp_labels = sum(1 for lab in parent if find(lab) == comp)
    comp_nodes = sum(sz for lab, sz in lab_size.items() if find(lab) == comp)
    print('  its component: labels', comp_labels, 'node slots', comp_nodes)
