"""Investigations driven from single POIs.

Mechanism under test = the one the paper describes: a node that appears in
several snapshots belongs to each community it touches; those recurring
(boundary) nodes are the links over which an analyst moves from a community
to its neighbors.

POI set: every in-scope ground-truth PROCESS entity (the realistic alert
anchor); if there are more than MAXPOI of them, a deterministic evenly-spaced
sample of MAXPOI (sorted by node id) - no hand-picking.

Hop 0: open the communities that contain the POI.
Hop h: open every community reachable through a boundary node of an
       already-open community (exhaustive expansion; ground truth is used for
       reporting recall only, never to steer the expansion).

Output per POI: hops to full in-scope recall, candidate set and share at that
hop, plus the full per-hop curve for the median POI.

Env: RUNDIR, MAXPOI (default 20), MAXHOP (default 12)
Output: poi_traversal.json
"""
import os as _os
_ROOT = _os.environ.get('ALGSE_ROOT', _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..')))
import os, json, time
RUN = os.environ.get('RUNDIR', _os.path.join(_ROOT, 'results', 'cadets_e3'))
MAXPOI = int(os.environ.get('MAXPOI', '20'))
MAXHOP = int(os.environ.get('MAXHOP', '12'))
os.chdir(RUN)

t0 = time.time()
multi = json.load(open('multi_membership.json'))   # node -> [labels]
comm_nodes = {}
for n, labs in multi.items():
    for lab in labs:
        comm_nodes.setdefault(lab, []).append(n)

gt = set()
with open('parse_data/groundtruth_nodeId.txt') as f:
    for line in f:
        p = line.split()
        if p:
            gt.add(p[0])
gt_in = gt & set(multi.keys())

# ground-truth PROCESS entities = GT ids present in subject.txt
subj = set()
with open('parse_data/subject.txt') as f:
    for line in f:
        i = line.split(':', 1)[0].strip()
        if i:
            subj.add(i)
gt_proc = sorted(gt_in & subj, key=int)
if not gt_proc:                       # fallback: any in-scope GT node
    gt_proc = sorted(gt_in, key=int)
if len(gt_proc) > MAXPOI:
    step = len(gt_proc) / float(MAXPOI)
    gt_proc = [gt_proc[int(i * step)] for i in range(MAXPOI)]

total_nodes = len(multi)
total_comms = len(comm_nodes)

def expand(poi, hubk=None):
    """hubk=None: exhaustive; otherwise ignore boundary nodes present in
    more than hubk communities (analyst skips ubiquitous system objects)."""
    opened = set(multi.get(poi, []))
    if not opened:
        return None
    cand = set()
    for lab in opened:
        cand.update(comm_nodes[lab])
    curve = []
    full_at = None
    for h in range(MAXHOP + 1):
        cov = len(gt_in & cand)
        curve.append({
            'hop': h,
            'communities_open': len(opened),
            'candidate_nodes': len(cand),
            'candidate_frac_pct': round(100.0 * len(cand) / total_nodes, 3),
            'gt_covered': cov,
            'gt_recall_pct': round(100.0 * cov / len(gt_in), 3) if gt_in else 0.0,
        })
        if full_at is None and gt_in and cov == len(gt_in):
            full_at = h
            break                      # stop at full in-scope recall
        new = set()
        for n in cand:
            labs = multi[n]
            if len(labs) < 2:
                continue
            if hubk is not None and len(labs) > hubk:
                continue
            for lab in labs:
                if lab not in opened:
                    new.add(lab)
        if not new:
            break                      # plateau: no community reachable anymore
        opened |= new
        for lab in new:
            cand.update(comm_nodes[lab])
    final_cov = curve[-1]['gt_covered']
    recall_plateau = next(r['hop'] for r in curve if r['gt_covered'] == final_cov)
    return {'curve': curve, 'full_recall_hop': full_at,
            'plateau_hop': curve[-1]['hop'],
            'recall_plateau_hop': recall_plateau,
            'final': curve[-1],
            'at_recall_plateau': curve[recall_plateau]}

t_bfs = time.time()
per_poi = {}
for poi in gt_proc:
    r = expand(poi)
    if r:
        per_poi[poi] = r

# hub-excluded variants: median recall/candidate tradeoff across the same POIs
hub_sweep = {}
for K in (3, 5, 10):
    rec_list, frac_list, hop_list = [], [], []
    for poi in per_poi:
        r = expand(poi, hubk=K)
        f = r['final']
        rec_list.append(f['gt_recall_pct'])
        frac_list.append(f['candidate_frac_pct'])
        hop_list.append(r['full_recall_hop'])
    rec_list.sort(); frac_list.sort()
    full = [h for h in hop_list if h is not None]
    hub_sweep['K%d' % K] = {
        'median_final_recall_pct': rec_list[len(rec_list) // 2] if rec_list else None,
        'min_final_recall_pct': rec_list[0] if rec_list else None,
        'median_final_candidate_frac_pct': frac_list[len(frac_list) // 2] if frac_list else None,
        'pois_reaching_full_recall': len(full),
        'median_hops_when_full': sorted(full)[len(full) // 2] if full else None,
    }

# summary over POIs that reached full recall
reached = {p: r for p, r in per_poi.items() if r['full_recall_hop'] is not None}
hops = sorted(r['full_recall_hop'] for r in reached.values())
fracs = sorted(r['final']['candidate_frac_pct'] for r in reached.values())
cands = sorted(r['final']['candidate_nodes'] for r in reached.values())
comms = sorted(r['final']['communities_open'] for r in reached.values())

def med(x):
    return x[len(x) // 2] if x else None

# median POI by (hops, frac) for the paper's illustrative curve; when no POI
# reaches full recall, use the plateau ordering over all POIs instead
med_poi = None
med_pool = reached if reached else per_poi
if med_pool:
    ranked = sorted(med_pool.items(),
                    key=lambda kv: (kv[1]['full_recall_hop']
                                    if kv[1]['full_recall_hop'] is not None
                                    else kv[1].get('plateau_hop', 99),
                                    kv[1]['final']['candidate_frac_pct']))
    med_poi = ranked[len(ranked) // 2][0]

plateaus = sorted(r.get('plateau_hop') for r in per_poi.values()
                  if r.get('plateau_hop') is not None)
plateau_recalls = sorted(r['final']['gt_recall_pct'] for r in per_poi.values())
rp_hops = sorted(r['recall_plateau_hop'] for r in per_poi.values())
rp_shares = sorted(r['at_recall_plateau']['candidate_frac_pct']
                   for r in per_poi.values())
rp_comms = sorted(r['at_recall_plateau']['communities_open']
                  for r in per_poi.values())

res = {
    'total_nodes': total_nodes,
    'total_communities_full': total_comms,
    'gt_listed': len(gt),
    'gt_in_graph': len(gt_in),
    'gt_process_pois_run': len(per_poi),
    'pois_reaching_full_recall': len(reached),
    'hops_to_full_recall': {'min': hops[0] if hops else None,
                            'median': med(hops), 'max': hops[-1] if hops else None},
    'candidate_frac_pct_at_full': {'min': fracs[0] if fracs else None,
                                   'median': med(fracs), 'max': fracs[-1] if fracs else None},
    'candidate_nodes_at_full': {'min': cands[0] if cands else None,
                                'median': med(cands), 'max': cands[-1] if cands else None},
    'communities_open_at_full': {'min': comms[0] if comms else None,
                                 'median': med(comms), 'max': comms[-1] if comms else None},
    'median_poi': med_poi,
    'median_poi_curve': med_pool[med_poi]['curve'] if med_poi else None,
    'plateau_hops': {'min': plateaus[0] if plateaus else None,
                     'median': med(plateaus), 'max': plateaus[-1] if plateaus else None},
    'plateau_recall_pct': {'min': plateau_recalls[0] if plateau_recalls else None,
                           'median': med(plateau_recalls),
                           'max': plateau_recalls[-1] if plateau_recalls else None},
    'recall_plateau_hops': {'min': rp_hops[0] if rp_hops else None,
                            'median': med(rp_hops),
                            'max': rp_hops[-1] if rp_hops else None},
    'recall_plateau_candidate_share_pct': {'min': rp_shares[0] if rp_shares else None,
                                           'median': med(rp_shares),
                                           'max': rp_shares[-1] if rp_shares else None},
    'recall_plateau_communities': {'min': rp_comms[0] if rp_comms else None,
                                   'median': med(rp_comms),
                                   'max': rp_comms[-1] if rp_comms else None},
    'hub_excluded_sweep': hub_sweep,
    'not_reaching_full': {p: r['final'] for p, r in per_poi.items()
                          if r['full_recall_hop'] is None},
    'bfs_sec': round(time.time() - t_bfs, 1),
    'sec': round(time.time() - t0, 1),
}
with open('poi_traversal.json', 'w') as f:
    json.dump(res, f, indent=2)
brief = {k: v for k, v in res.items() if k not in ('median_poi_curve', 'not_reaching_full')}
brief['not_reaching_full_count'] = len(res['not_reaching_full'])
print('POI_TRAVERSAL_DONE', json.dumps(brief), flush=True)
