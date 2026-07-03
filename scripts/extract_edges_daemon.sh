#!/usr/bin/env bash
# Unattended edge-extraction daemon — runs Fable over the source text until a HARD deadline
# (Saturday afternoon), then stops for good. Built to survive Wi-Fi outages and reboots.
#
#   * HARD DEADLINE: 2026-07-04 17:00 local. Nothing runs past it. After it, the daemon removes
#     its own cron lines and writes a STOP flag so it never starts again.
#   * OFFLINE-TOLERANT: extract_edges.py only writes finished chunks; a chunk that fails while
#     offline is retried next cycle. Between cycles we sleep, so no-Wi-Fi just means idle waiting.
#   * SINGLE INSTANCE: flock, so cron (@reboot + every 15 min) can never stack two daemons.
#   * MEMORY-SAFE: concurrency 6 (the box OOM-crashed at 14).
set -u
export PATH="/home/smiles/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"   # cron has a minimal PATH

DEADLINE_EPOCH=$(date -d "2026-07-04 17:00:00" +%s)   # Saturday afternoon — hard stop
export EXTRACT_DEADLINE="$DEADLINE_EPOCH"
STOP=/tmp/extract_edges_STOP
LOCK=/tmp/extract_edges.lock
LOG=/tmp/extract_edges.log
CONC=6
MODEL_PRIMARY="claude-fable-5"
MODEL_FALLBACK="claude-sonnet-5"
SELF="/home/smiles/dev/mapjs/scripts/extract_edges_daemon.sh"

log(){ echo "$(date '+%F %T') $*" >> "$LOG"; }

remove_cron(){
  # drop our own cron lines so nothing relaunches after the deadline
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
log "daemon start (deadline $(date -d @"$DEADLINE_EPOCH" '+%F %T'), conc=$CONC)"

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

model="$MODEL_PRIMARY"
fable_dead=0
while ! past_deadline; do
  before=$(count_done)
  : > /tmp/extract_edges_pass.log
  MODEL="$model" CONC="$CONC" uv run python -u /home/smiles/dev/mapjs/scripts/extract_edges.py "$CONC" 120 \
      > /tmp/extract_edges_pass.log 2>&1
  cat /tmp/extract_edges_pass.log >> "$LOG"
  after=$(count_done)
  past_deadline && break
  progressed=$((after - before))

  if [ "$progressed" -gt 0 ]; then
    log "pass finished: +$progressed chunks (total $after) on $model"
    sleep 5
    continue
  fi

  # --- no progress: figure out why -------------------------------------------
  if [ "$(remaining_chunks)" -eq 0 ]; then
    log "all chunks extracted; idle until deadline"; sleep 600; continue
  fi
  # Fable token exhaustion -> switch to Sonnet PERMANENTLY (per user: keep going on Sonnet)
  if [ "$fable_dead" -eq 0 ] && [ "$model" = "$MODEL_PRIMARY" ] \
       && grep -qi "usage limit\|rate_limit\|quota" /tmp/extract_edges_pass.log; then
    fable_dead=1; model="$MODEL_FALLBACK"
    log "Fable exhausted/limited -> switching to $model for the remainder"
    sleep 5; continue
  fi
  # otherwise: offline / transient outage -> keep same model, short backoff, resume when back
  log "no progress (remaining $(remaining_chunks)) on $model — offline/outage? retry in 45s"
  sleep 45
done

remove_cron
touch "$STOP"
log "deadline reached; cron removed; STOP flag set; daemon exit"
