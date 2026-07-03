# Autonomous edge-extraction run (2026-07-03 → 2026-07-04)

A self-sustaining OS-level daemon mines new bechina/eitza/equation edges from the source text
with Fable (falling back to Sonnet if Fable's quota runs out), writing candidate records to
`ontology/occurrences/ai_extracted/`. Deliberately NOT a Claude-session workflow — it must
outlive the session, reboots, and Wi-Fi gaps.

Resilience:
- **Session end**: runs detached (setsid/nohup) + cron; independent of any Claude conversation.
- **Reboot**: `@reboot` + every-15-min cron relaunch; flock guarantees a single instance.
- **Offline / outage**: chunks are written only on success (atomic rename), so an offline chunk
  is simply retried next cycle. Short backoff, resumes the moment the network returns.
- **Fable exhausted**: on a usage-limit error the daemon switches to Sonnet permanently.
- **HARD DEADLINE 2026-07-04 17:00 local (Sat afternoon)**: no call starts past it; at the
  deadline the daemon removes its own cron lines and writes /tmp/extract_edges_STOP so nothing
  ever restarts afterward.
- **Memory**: concurrency 6 (the box OOM-crashed at 14).

Controls:
- Stop early:   touch /tmp/extract_edges_STOP  (and `crontab -e` to drop the two lines)
- Progress:     tail -f /tmp/extract_edges.log
- Output:       ontology/occurrences/ai_extracted/<book>_<chunk>.json  (candidate edges)
