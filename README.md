# ALGSE

Code for *ALGSE: An Efficient Provenance Graph Storage System for Attack-Oriented Investigation*.

ALGSE stores a provenance graph as communities. Audit events are parsed into a graph, the graph is cut into 5,000-node snapshots, each snapshot is partitioned with Louvain (weighted by event multiplicity), each community's binary adjacency matrix is reordered with SlashBurn and written as 4x4 blocks, and node attributes are stored with prefix and delta redundancy reduction. An investigation starting from a point of interest fetches the communities that hold it and moves to neighbouring communities through the nodes that recur across snapshots.

This repository has two parts:

- `ALGSE/` is the system implementation: the DARPA TC parsers, graph construction, the Louvain and SlashBurn implementations, block generation, and graph recovery. `ALGSE/main.py` runs the full pipeline on one dataset.
- `scripts/` are the measurement scripts that produce every table in the paper's evaluation. They carry their own single-pass CDM18 parsers (`parse_fast.py`, `parse_fast_theia.py`), reuse the snapshot builder `graphBuild` and the loader `load_graph` from `ALGSE/`, and for community detection call the NetworkX implementation of Louvain (`networkx.algorithms.community.louvain_communities`, NetworkX 3.2.1) with the seed fixed at 42, so that every reported partition can be regenerated exactly.

## Environment

The reported measurements were taken with Python 3.10.12 on Ubuntu 22.04 (two Intel Xeon Silver 4310 CPUs). Install the pinned dependencies:

```
pip install -r requirements.txt
```

The two PostgreSQL baselines need a local PostgreSQL 14 server (`initdb` into a private data directory, no superuser rights required); see below.

Scripts resolve the repository root from their own location. Set `ALGSE_ROOT` to override it, and `RUNDIR` to point a script at a particular scenario directory (default `results/<scenario>_e3`).

## Data

The evaluation uses the DARPA Transparent Computing Engagement 3 traces for CADETS, THEIA, and TRACE (CDM18 JSON, the `ta1-*-e3-official*.json*` files) and the Engagement 5 traces for the end-to-end storage comparison. The traces are distributed by DARPA through the Transparent Computing release; the ground-truth attack entity lists are the per-host files (`cadets.txt`, `theia.txt`, `trace.txt`) published with the ThreaTrace evaluation.

Expected layout:

```
data/cadets/raw/          ta1-cadets-e3-official*.json*
data/theia/               ta1-theia-e3-official-6r.json, .1 ... .12
data/trace/               ta1-trace-e3-official-1.json, .1 ... .6
data/groundtruth/         cadets.txt  theia.txt  trace.txt
```

Point a parser elsewhere with `RAWDIR` and `GTFILE`.

## Reproducing the evaluation

Run the scripts in this order for each scenario. Each step reads the outputs of the previous ones from `results/<scenario>_e3/`.

| Step | Script | Produces | Used for |
|---|---|---|---|
| 1 | `parse_fast.py` (CADETS; file list via `CADETS_FILES`) / `parse_fast_theia.py` (THEIA by default; TRACE via `RUNDIR`, `RAWDIR`, `GTFILE`, `PARSE_FILES`) | `parse_data/{subject,file,socket,other,event}.txt`, `groundtruth_nodeId.txt` | input to everything below |
| 2 | `membership_only.py` | snapshot graphs `medium/graph2.pkl`, `node_community.json`, `community_sizes.json` | the partition; single membership per node |
| 3 | `analyze_e1.py` | `e1_result.json` | candidate-set reduction, precision, attack density, resolution-limit check |
| 4 | `storage_fast2.py` | `T_CG.txt`, `T_c.txt`, `Tn/`, `storage_result.json` | footprint decomposition and the reordering ablation |
| 5 | `ablation_weight.py` | `ablation_weight.json` | weighted against unweighted Louvain |
| 6 | `decode_bench.py` | `decode_bench.json` | reconstruction and read-path cost (five repeats) |
| 7 | `en_louvain_full.py` | `multi_membership.json`, `edges_intra_lastwins.txt`, `louvain_full_summary.json` | full per-snapshot membership; input to steps 9 to 12 |
| 8 | `en_tc_delta.py` | printed | cost of recording the full membership |
| 9 | `pg_baseline.sh <scenario>` and `en_sameinfo_pg.sh <scenario>` | printed | the event-tuple and same-information PostgreSQL baselines |
| 10 | `en_poi_traversal.py` | `poi_traversal.json` | investigations driven from single POIs |
| 11 | `en_bfs_baseline.py` | `bfs_baseline.json` | breadth-first search from the same POIs, on the same recall-versus-share axis |
| 12 | `en_chunk_baseline.py` (chunk size via `S`, default the mean Louvain community size) | `chunk_baseline.json` | fixed-size chunking without Louvain |
| 13 | `en_seed_sweep.py` (`SEEDS`, default `42,1,2,3,4`) | `seed_sweep.json` | the partition under five seeds |
| 14 | `en_theia_missed.py` | printed | the one THEIA entity no boundary traversal reaches |

For example, for CADETS:

```
export RUNDIR=$PWD/results/cadets_e3
python scripts/parse_fast.py
python scripts/membership_only.py
python scripts/analyze_e1.py
python scripts/storage_fast2.py
python scripts/en_louvain_full.py
python scripts/en_poi_traversal.py
python scripts/en_bfs_baseline.py
```

### Parameters

- Snapshot size: 5,000 nodes, closed in log order (`membership_only.py`).
- Community detection: NetworkX 3.2.1 `louvain_communities`, `weight='weight'` (event multiplicity), `seed=42`. The implementation shuffles the node visit order, so a partition is reproducible for a fixed seed and input; `en_seed_sweep.py` reports the variation across seeds.
- Node reordering: `storage_fast2.py`, `decode_bench.py`, and `en_chunk_baseline.py` order the nodes of every community by descending degree, the hub ranking that SlashBurn applies, and report the block volume with and without that ordering. The full SlashBurn permutation (hubs removed in rounds of `k = max(1, int(0.001 * n))`, spokes ordered by component size) is `slashburn` in `ALGSE/utils.py` and is what `ALGSE/generator_block.py` uses.
- Block size: 4.
- POI set for the driven investigations: every in-scope ground-truth process entity, with an evenly spaced sample of 20 when there are more (`MAXPOI`), and an expansion limit of 12 hops (`MAXHOP`).

### PostgreSQL baselines

Both shell scripts expect a PostgreSQL 14 instance reachable through a Unix socket in `pgbaseline/` on port 5433 with a role `algse` (override the binary directory with `PGBIN` and the socket directory with `PGB`). To create one without administrative rights:

```
/usr/lib/postgresql/14/bin/initdb -D pgbaseline/pgdata -U algse
/usr/lib/postgresql/14/bin/pg_ctl -D pgbaseline/pgdata -o "-p 5433 -k $PWD/pgbaseline -c listen_addresses=''" start
```

`pg_baseline.sh` loads the event four-tuples and the node-attribute tables; `en_sameinfo_pg.sh` loads only what ALGSE's counted footprint holds, the node-attribute tables and the intra-community edges written by `en_louvain_full.py`. Both report `pg_total_relation_size` with no secondary indexes and default page settings.

## Running the system end to end

`ALGSE/main.py` parses a THEIA E3 dataset from `data/` (swap the parser import for the other scenarios), builds the graph, partitions it with the implementation in `ALGSE/generator_community_to_graph.py`, reorders and writes the blocks with `ALGSE/generator_block.py`, and reports wall-clock time and memory. `ALGSE/recover_graph.py` reconstructs a community from its stored blocks. `ALGSE/config.py` sets the working directories and `ALGSE/map.txt` holds the prefix dictionary used by the redundancy reduction.

## Third-party code

The SlashBurn and matrix-reordering routines in `ALGSE/utils.py` are adapted from [theeluwin/bear](https://github.com/theeluwin/bear) (GPL-3.0).
