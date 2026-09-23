#!/bin/bash
# Real PostgreSQL storage baseline for one scenario, entirely under ALGSE.
# Loads the same information ALGSE stores (the event 4-tuples plus the node
# attribute tables) into a private Postgres instance and measures heap size.
S="$1"
BIN="${PGBIN:-/usr/lib/postgresql/14/bin}"
ROOT="${ALGSE_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
PGB="${PGB:-$ROOT/pgbaseline}"
PSQL="$BIN/psql -h $PGB -p 5433 -U algse -d postgres -tAq"
RD="$ROOT/results/${S}_e3"/parse_data
$PSQL -c "DROP TABLE IF EXISTS events_$S CASCADE; DROP TABLE IF EXISTS nodes_$S CASCADE;" >/dev/null
$PSQL -c "CREATE TABLE events_$S (srcid int, etype text, dstid int, ts bigint);" >/dev/null
$PSQL -c "\copy events_$S FROM '$RD/event.txt' WITH (FORMAT csv, DELIMITER ' ')" 2>&1 | head -2
cat "$RD/subject.txt" "$RD/file.txt" "$RD/socket.txt" "$RD/other.txt" 2>/dev/null > "$PGB/nodes_$S.txt"
$PSQL -c "CREATE TABLE nodes_$S (line text);" >/dev/null
$PSQL -c "\copy nodes_$S FROM '$PGB/nodes_$S.txt' WITH (FORMAT csv, DELIMITER E'\x01', QUOTE E'\x02')" 2>&1 | head -2
EV=$($PSQL -c "SELECT pg_total_relation_size('events_$S');")
ND=$($PSQL -c "SELECT pg_total_relation_size('nodes_$S');")
ER=$($PSQL -c "SELECT count(*) FROM events_$S;")
NR=$($PSQL -c "SELECT count(*) FROM nodes_$S;")
TOT=$((EV+ND))
echo "PG_BASELINE $S events_bytes=$EV nodes_bytes=$ND total_bytes=$TOT total_MB=$(python3 -c "print(round($TOT/1048576,1))" 2>/dev/null || echo $TOT) event_rows=$ER node_rows=$NR"
rm -f "$PGB/nodes_$S.txt"
$PSQL -c "DROP TABLE events_$S CASCADE; DROP TABLE nodes_$S CASCADE;" >/dev/null
