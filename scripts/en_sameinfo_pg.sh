#!/bin/bash
# Same-information PostgreSQL baseline.
# PG stores EXACTLY the information content of ALGSE's counted footprint C:
#   - the raw node-attribute tables (what T_n' + map.txt encode), and
#   - per snapshot, the undirected intra-community edges that T_CG' + T_c encode
#     (edges_intra_lastwins.txt produced by en_louvain_full.py).
# No secondary indexes, default page settings; size = pg_total_relation_size.
S="$1"
BIN="${PGBIN:-/usr/lib/postgresql/14/bin}"
ROOT="${ALGSE_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
PGB="${PGB:-$ROOT/pgbaseline}"
PSQL="$BIN/psql -h $PGB -p 5433 -U algse -d postgres -tAq"
RD="$ROOT/results/${S}_e3"
$PSQL -c "DROP TABLE IF EXISTS si_edges_$S CASCADE; DROP TABLE IF EXISTS si_nodes_$S CASCADE;" >/dev/null
$PSQL -c "CREATE TABLE si_edges_$S (snap int, u int, v int);" >/dev/null
$PSQL -c "\copy si_edges_$S FROM '$RD/edges_intra_lastwins.txt' WITH (FORMAT csv, DELIMITER ' ')" 2>&1 | head -2
cat "$RD/parse_data/subject.txt" "$RD/parse_data/file.txt" "$RD/parse_data/socket.txt" "$RD/parse_data/other.txt" 2>/dev/null > "$PGB/si_nodes_$S.txt"
$PSQL -c "CREATE TABLE si_nodes_$S (line text);" >/dev/null
$PSQL -c "\copy si_nodes_$S FROM '$PGB/si_nodes_$S.txt' WITH (FORMAT csv, DELIMITER E'\x01', QUOTE E'\x02')" 2>&1 | head -2
EV=$($PSQL -c "SELECT pg_total_relation_size('si_edges_$S');")
ND=$($PSQL -c "SELECT pg_total_relation_size('si_nodes_$S');")
ER=$($PSQL -c "SELECT count(*) FROM si_edges_$S;")
NR=$($PSQL -c "SELECT count(*) FROM si_nodes_$S;")
TOT=$((EV+ND))
echo "SAMEINFO_PG $S edges_bytes=$EV nodes_bytes=$ND total_bytes=$TOT total_MB=$(python3 -c "print(round($TOT/1048576,1))" 2>/dev/null || echo $TOT) edge_rows=$ER node_rows=$NR"
rm -f "$PGB/si_nodes_$S.txt"
$PSQL -c "DROP TABLE si_edges_$S CASCADE; DROP TABLE si_nodes_$S CASCADE;" >/dev/null
