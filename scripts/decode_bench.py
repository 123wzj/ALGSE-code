"""
Read-path benchmark. Encodes each community to a decodable delimited block string
on disk (T_CG_dec.txt), then reconstructs the provenance graph from that stored form
and measures reconstruction latency, decompression throughput, per-community (POI)
latency, and peak memory. Repeats the decode 5 times for mean and standard deviation.
Verifies round-trip correctness. Also measures node-attribute recovery throughput.
"""
import os as _os
_ROOT = _os.environ.get('ALGSE_ROOT', _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..')))
import sys, os, time, json, resource, statistics, glob
os.environ.setdefault('MPLBACKEND', 'Agg')
CODE = _os.path.join(_ROOT, 'ALGSE')
RUN = os.environ.get('RUNDIR', _os.path.join(_ROOT, 'results', 'cadets_e3'))
sys.path.insert(0, CODE)
os.chdir(RUN)
import networkx as nx
from collections import defaultdict
from generator_community_to_graph import load_graph
BS = 4

def degree_perm(n, edges):
    deg = [0]*n
    for u, v in edges:
        deg[u] += 1; deg[v] += 1
    order = sorted(range(n), key=lambda i: -deg[i])
    perm = [0]*n
    for newi, oldi in enumerate(order):
        perm[oldi] = newi
    return perm

def encode(edges, perm):
    blocks = defaultdict(set)
    for u, v in edges:
        r = perm[u]; c = perm[v]
        blocks[(r//BS, c//BS)].add((r % BS, c % BS))
        blocks[(c//BS, r//BS)].add((c % BS, r % BS))
    parts = []
    for (R, C), cells in blocks.items():
        content = ''.join('1' if (i, j) in cells else '0' for i in range(BS) for j in range(BS))
        parts.append(content+'*'+str(R)+'*'+str(C))
    return '#'.join(parts)

def decode_edges(s):
    e = set()
    if not s:
        return e
    for blk in s.split('#'):
        content, R, C = blk.split('*'); R = int(R); C = int(C)
        br = R*BS; bc = C*BS
        for i in range(BS):
            row = content[i*BS:(i+1)*BS]
            for j in range(BS):
                if row[j] == '1':
                    e.add((br+i, bc+j))
    return e

membership = json.load(open('node_community.json'))
comm_nodes = defaultdict(list)
for n, c in membership.items():
    comm_nodes[c].append(n)
allGraph = load_graph('medium/graph2.pkl')

# ENCODE to disk (compression), keep reorder->orig maps
t0 = time.time()
r2o_all = {}
src_edges = {}
with open('T_CG_dec.txt', 'w') as f:
    for label, nodes in comm_nodes.items():
        gid = int(label.split('.')[0]); G = allGraph.get(gid)
        if G is None:
            continue
        nodes = [x for x in nodes if G.has_node(x)]
        if not nodes:
            continue
        idx = {x: i for i, x in enumerate(nodes)}; n = len(nodes)
        edges = [(idx[u], idx[v]) for u, v in G.subgraph(nodes).edges()]
        perm = degree_perm(n, edges)
        r2o = [None]*n
        for x in nodes:
            r2o[perm[idx[x]]] = x
        r2o_all[label] = r2o
        src_edges[label] = set((min(perm[a], perm[b]), max(perm[a], perm[b])) for a, b in edges)
        f.write(label+' '+encode(edges, perm)+'\n')
encode_time = time.time()-t0

# DECODE from disk, rebuild graph, remap (repeat 5x)
def decode_all():
    total_nodes = 0; per = []
    with open('T_CG_dec.txt') as f:
        for line in f:
            sp = line.rstrip('\n').split(' ', 1)
            label = sp[0]; bs = sp[1] if len(sp) > 1 else ''
            r2o = r2o_all.get(label)
            if r2o is None:
                continue
            t = time.perf_counter()
            e = decode_edges(bs)
            G = nx.Graph()
            nn = len(r2o)
            G.add_nodes_from(r2o)
            for r, c in e:
                if r < nn and c < nn:
                    G.add_edge(r2o[r], r2o[c])
            per.append((time.perf_counter()-t)*1000.0)
            total_nodes += nn
    return per, total_nodes

runs = []
per_comm = None; nodes_dec = 0
for k in range(5):
    t = time.time(); per, nodes_dec = decode_all(); runs.append(time.time()-t)
    if k == 0:
        per_comm = per
peak_rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024.0

# round-trip correctness
ok = 0; chk = 0
with open('T_CG_dec.txt') as f:
    for line in f:
        if chk >= 500:
            break
        sp = line.rstrip('\n').split(' ', 1)
        label = sp[0]; bs = sp[1] if len(sp) > 1 else ''
        e = decode_edges(bs)
        dec = set((min(r, c), max(r, c)) for r, c in e)
        if dec == src_edges.get(label, set()):
            ok += 1
        chk += 1

# node-attribute recovery throughput on a sample (reverse map)
def read_mapping(p):
    m = {}
    for line in open(p, encoding='utf-8', errors='ignore'):
        if ':' in line:
            s, t = line.rstrip('\n').split(':', 1); m[s] = t
    return m
mp = {}
for c in (RUN+'/map.txt', CODE+'/map.txt'):
    if os.path.exists(c):
        mp = read_mapping(c); break
rev = [(t, s) for s, t in mp.items()]
attr_mb = 0.0; attr_t = 0.0
tnfiles = glob.glob('Tn/*')
if tnfiles:
    t = time.time(); nb = 0
    for fn in tnfiles:
        for line in open(fn, encoding='utf-8', errors='ignore'):
            for tgt, src in rev:
                line = line.replace(tgt, src)
            nb += len(line)
            if nb > 100*1024*1024:
                break
        if nb > 100*1024*1024:
            break
    attr_t = time.time()-t; attr_mb = nb/1048576.0

per_sorted = sorted(per_comm)
res = {
    'scenario': os.path.basename(RUN),
    'communities': len(r2o_all),
    'nodes_reconstructed': nodes_dec,
    'T_CG_dec_MB': round(os.path.getsize('T_CG_dec.txt')/1048576.0, 2),
    'encode_compress_time_s': round(encode_time, 2),
    'decode_reconstruct_time_mean_s': round(statistics.mean(runs), 3),
    'decode_reconstruct_time_std_s': round(statistics.pstdev(runs), 3),
    'decode_runs_s': [round(r, 3) for r in runs],
    'throughput_nodes_per_s': round(nodes_dec/statistics.mean(runs)),
    'throughput_MB_per_s': round(os.path.getsize('T_CG_dec.txt')/1048576.0/statistics.mean(runs), 2),
    'per_community_ms_mean': round(statistics.mean(per_comm), 4),
    'per_community_ms_median': round(statistics.median(per_comm), 4),
    'per_community_ms_p95': round(per_sorted[int(len(per_sorted)*0.95)], 4),
    'per_community_ms_max': round(max(per_comm), 4),
    'peak_rss_MB': round(peak_rss_mb, 1),
    'roundtrip_ok': ok, 'roundtrip_checked': chk,
    'attr_recovery_MB_per_s': round(attr_mb/attr_t, 2) if attr_t > 0 else None,
}
json.dump(res, open('decode_bench.json', 'w'), indent=2)
print('DECODE_BENCH', json.dumps(res), flush=True)
