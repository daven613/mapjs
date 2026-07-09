#!/usr/bin/env bash
# Unattended edge-extraction daemon — v2 resume (schema 2: polarity/via, see specs/extraction_v2.md).
# Runs Sonnet over the remaining source chunks. Survives Wi-Fi outages and reboots.
#
#   * BACKSTOP DEADLINE: 2026-07-08 17:00 local. Nothing runs past it; daemon removes its own
#     cron lines and writes a STOP flag. It ALSO self-terminates early once all chunks are done.
#   * OFFLINE-TOLERANT: extract_edges.py only writes finished chunks; failures are retried
#     next cycle. Usage-limit -> long sleep (subscription window resets on its own).
#   * SINGLE INSTANCE: flock, so cron (@reboot + every 15 min) can never stack two daemons.
#   * MEMORY-SAFE: concurrency 6 (the box OOM-crashed at 14).
set -u
export PATH="/home/smiles/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"   # cron has a minimal PATH

DEADLINE_EPOCH=$(date -d "2026-07-08 17:00:00" +%s)   # backstop hard stop
export EXTRACT_DEADLINE="$DEADLINE_EPOCH"
STOP=/tmp/extract_edges_STOP
LOCK=/tmp/extract_edges.lock
LOG=/tmp/extract_edges.log
CONC=6
MODEL_PRIMARY="claude-sonnet-5"
SELF="/home/smiles/dev/mapjs/scripts/extract_edges_daemon.sh"

log(){ echo "$(date '+%F %T') $*" >> "$LOG"; }

remove_cron(){
  crontab -l 2>/dev/null | grep -v "extract_edges_daemon.sh" | crontab - 2>/dev/null || true
}

past_deadline(){ [ "$(date +%s)" -ge "$DEADLINE_EPOCH" ]; }

# ---- hard stops --------------------------------------------------------------
if past_deadline; then remove_cron; touch "$STOP"; log "past deadline at startup; cron removed; exit"; exit 0; fi
[ -f "$STOP" ] && exit 0

# ---- single instance ---------------------------------------------------------
exec 9>"$LOCK"
flock -n 9 || exit 0

cd /home/smiles/dev/new-sefer || exit 1
log "daemon start v2 (deadline $(date -d @"$DEADLINE_EPOCH" '+%F %T'), model=$MODEL_PRIMARY, conc=$CONC)"

AIX=/home/smiles/dev/mapjs/ontology/occurrences/ai_extracted
count_done(){ ls "$AIX" 2>/dev/null | grep -c '\.json$'; }
remaining_chunks(){ python3 - <<'PY'
import json
from pathlib import Path
base=Path.home()/'dev'/'new-sefer'/'graph_poc'
out=Path.home()/'dev'/'mapjs'/'ontology'/'occurrences'/'ai_extracted'
tot=0
for b in ('lm1','lm2'):
    p=base/b/'reading.json'
    if not p.exists(): continue
    d=json.loads(p.read_text())
    for t in d['torahs']:
        for s in t['sections']:
            for sub in s['subsections']:
                if not (out/f"{b}_{sub['key']}.json").exists(): tot+=1
print(tot)
PY
}

while ! past_deadline; do
  before=$(count_done)
  : > /tmp/extract_edges_pass.log
  MODEL="$MODEL_PRIMARY" uv run python -u /home/smiles/dev/mapjs/scripts/extract_edges.py "$CONC" 120 \
      > /tmp/extract_edges_pass.log 2>&1
  cat /tmp/extract_edges_pass.log >> "$LOG"
  past_deadline && break
  after=$(count_done)
  progressed=$((after - before))

  # done? finish for good — no idling until an arbitrary deadline
  if [ "$(remaining_chunks)" -eq 0 ]; then
    remove_cron; touch "$STOP"; log "ALL $after chunks extracted; daemon finished and disarmed"; exit 0
  fi

  if [ "$progressed" -gt 0 ]; then
    log "pass finished: +$progressed chunks (total $after)"
    sleep 5
    continue
  fi

  # --- no progress: figure out why -------------------------------------------
  if grep -qi "usage limit\|rate_limit\|quota\|overloaded" /tmp/extract_edges_pass.log; then
    log "usage-limited (remaining $(remaining_chunks)); sleeping 30 min for the window to reset"
    sleep 1800; continue
  fi
  # offline / transient outage -> short backoff, resume when back
  log "no progress (remaining $(remaining_chunks)) — offline/outage? retry in 60s"
  sleep 60
done

remove_cron
touch "$STOP"
log "deadline reached; cron removed; STOP flag set; daemon exit"
