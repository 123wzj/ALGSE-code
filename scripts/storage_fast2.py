"""
Storage-footprint computation. Encodes the blocks in O(edges) per community
(ALGSE/generator_block.py enumerates every block position, which is O((n/4)^2)
per community). Nodes are ordered by descending degree, the hub ranking that
SlashBurn applies, and the block volume is also reported with no reordering,
which gives the reordering ablation.
Produces T_CG.txt, T_c.txt, T_n' and storage_result.json.
"""
import os as _os
_ROOT = _os.environ.get('ALGSE_ROOT', _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..')))
import sys, os, time, json, glob
from collections import defaultdict
CODE = _os.path.join(_ROOT, 'ALGSE')
RUN = os.environ.get('RUNDIR', _os.path.join(_ROOT, 'results', 'cadets_e3'))
sys.path.insert(0, CODE)
os.chdir(RUN)
from generator_community_to_graph import load_graph
BS = 4
t0 = time.time()
membership = json.load(open('node_community.json'))
comm_nodes = defaultdict(list)
for n, c in membership.items():
    comm_nodes[c].append(n)
allGraph = load_graph('medium/graph2.pkl')

def block_string(edges, perm):
    blocks = defaultdict(set)
    for u, v in edges:
        r = perm[u]; c = perm[v]
        blocks[(r // BS, c // BS)].add((r % BS, c % BS))
        blocks[(c // BS, r // BS)].add((c % BS, r % BS))  # symmetric (undirected)
    parts = []
    for (R, C), cells in blocks.items():
        content = ''.join('1' if (i, j) in cells else '0' for i in range(BS) for j in range(BS))
        parts.append(content + str(R) + str(C))
    return ''.join(parts), len(blocks)

def degree_perm(n, edges):
    deg = [0] * n
    for u, v in edges:
        deg[u] += 1; deg[v] += 1
    order = sorted(range(n), key=lambda i: -deg[i])
    perm = [0] * n
    for newi, oldi in enumerate(order):
        perm[oldi] = newi
    return perm

tcg_orig_chars = 0
tcg_deg_chars = 0
blocks_orig = 0
blocks_deg = 0
tc_lines = 0
done = 0
blockf = open('T_CG.txt', 'w')
tcf = open('T_c.txt', 'w')
for label, nodes in comm_nodes.items():
    gid = int(label.split('.')[0])
    G = allGraph.get(gid)
    if G is None:
        continue
    nodes = [x for x in nodes if G.has_node(x)]
    if not nodes:
        continue
    idx = {x: i for i, x in enumerate(nodes)}
    n = len(nodes)
    sub = G.subgraph(nodes)
    edges = [(idx[u], idx[v]) for u, v in sub.edges()]
    ident = list(range(n))
    s_o, b_o = block_string(edges, ident)
    perm = degree_perm(n, edges)
    s_d, b_d = block_string(edges, perm)
    tcg_orig_chars += len(s_o); tcg_deg_chars += len(s_d)
    blocks_orig += b_o; blocks_deg += b_d
    blockf.write(label + ' ' + s_d + '\n')
    for x in nodes:
        tcf.write('%s %s %d\n' % (label, x, perm[idx[x]]))
        tc_lines += 1
    done += 1
    if done % 300 == 0:
        with open('storage_checkpoint.json', 'w') as f:
            json.dump({'done': done, 'sec': round(time.time()-t0, 1)}, f)
blockf.close(); tcf.close()

def read_mapping(p):
    m = {}
    for line in open(p, encoding='utf-8', errors='ignore'):
        if ':' in line:
            s, t = line.rstrip('\n').split(':', 1); m[s] = t
    return m
mp = {}; mapfile = None
for c in (RUN+'/map.txt', CODE+'/map.txt'):
    if os.path.exists(c):
        mp = read_mapping(c); mapfile = c; break
def reduce_file(src, dst):
    with open(dst, 'w', encoding='utf-8') as wf:
        for line in open(src, encoding='utf-8', errors='ignore'):
            for s, t in mp.items():
                line = line.replace(s, t)
            wf.write(line)
os.makedirs('Tn', exist_ok=True)
for nm in ['subject', 'file', 'socket', 'other']:
    if os.path.exists('parse_data/'+nm+'.txt'):
        reduce_file('parse_data/'+nm+'.txt', 'Tn/'+nm+'_reduced.txt')

def sz(p): return os.path.getsize(p) if os.path.exists(p) else 0
Tn = sum(sz(f) for f in glob.glob('Tn/*'))
Tn_raw = sum(sz('parse_data/'+n+'.txt') for n in ['subject', 'file', 'socket', 'other'])
TCG = sz('T_CG.txt'); Tc = sz('T_c.txt'); mapb = sz(mapfile) if mapfile else 0
total = Tn + TCG + Tc + mapb
res = {'T_n_prime_bytes': Tn, 'T_n_raw_bytes': Tn_raw, 'T_CG_bytes': TCG, 'T_c_bytes': Tc,
       'map_bytes': mapb, 'total_bytes': total, 'total_MB': round(total/1048576, 3),
       'event_raw_bytes': sz('parse_data/event.txt'),
       'event_raw_MB': round(sz('parse_data/event.txt')/1048576, 3),
       'blocks_no_reorder': blocks_orig, 'blocks_degree_reorder': blocks_deg,
       'reorder_block_reduction_pct': round((1 - blocks_deg/blocks_orig)*100, 3) if blocks_orig else 0,
       'communities_stored': done, 'sec': round(time.time()-t0, 1)}
with open('storage_result.json', 'w') as f:
    json.dump(res, f, indent=2)
print('STORAGE_DONE', json.dumps(res), flush=True)
