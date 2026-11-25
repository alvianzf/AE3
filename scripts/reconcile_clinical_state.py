"""Drift-detection safety net for client_clinical_state (specs/v9/03) —
not wired into the app itself (this app has no in-process scheduler,
and standing one up solely for this would be premature infrastructure).
Meant to be run manually or via an external system cron the team sets
up outside this repo.

Re-runs lab-marker extraction over every raw 'lab' record_entries row
for a client, from scratch, and diffs the rebuilt picture against what
client_clinical_state currently holds. A mismatch means the incremental
update path (app/reasoning/clinical_state.py's update_lab_state, run in
the background per entry) drifted from the raw source of truth — the
exact failure mode specs/v9/03 calls non-negotiable to catch before a
practitioner ever sees a wrong trend. This script never writes
anything; it only reports.

Usage:
    PYTHONPATH=. python scripts/reconcile_clinical_state.py \\
        --practitioner-id <id> --client-id <id>
"""
from __future__ import annotations

import argparse
import sys

from app import vault
from app.graph.store import canon
from app.reasoning.clinical_state import extract_lab_markers


def rebuild_from_scratch(practitioner_id: str, client_id: str) -> dict[str, dict]:
    """What client_clinical_state *should* currently contain, recomputed
    from every raw lab entry in chronological order — same upsert logic
    as the live incremental path (app/vault.py's
    upsert_clinical_state_marker), just run in memory against a from-
    scratch rebuild instead of the live table."""
    entries = [e for e in vault.list_entries(practitioner_id, client_id) if e["kind"] == "lab"]
    entries.sort(key=lambda e: e["created_at"])
    current: dict[str, dict] = {}
    for entry in entries:
        try:
            markers, _usage = extract_lab_markers(entry["content"])
        except Exception as exc:
            print(f"  extraction failed for entry {entry['id']}: {exc}", file=sys.stderr)
            continue
        for m in markers:
            label = canon(m["label"])
            current[label] = {
                "display_label": m["label"], "value": m.get("value") or None,
                "unit": m.get("unit") or None, "flag": m.get("flag"),
                "source_entry_id": entry["id"],
            }
    return current


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--practitioner-id", required=True)
    parser.add_argument("--client-id", required=True)
    args = parser.parse_args()

    rebuilt = rebuild_from_scratch(args.practitioner_id, args.client_id)
    live = {m["label"]: m for m in vault.get_clinical_state(args.practitioner_id, args.client_id)}

    mismatches = 0
    for label in sorted(set(rebuilt) | set(live)):
        r, l = rebuilt.get(label), live.get(label)
        if r is None:
            print(f"DRIFT: {label!r} is live but not reproducible from raw entries: {l}")
            mismatches += 1
        elif l is None:
            print(f"DRIFT: {label!r} should exist but is missing from client_clinical_state: {r}")
            mismatches += 1
        elif r["value"] != l["value"]:
            print(f"DRIFT: {label!r} value mismatch — rebuilt={r['value']!r} live={l['value']!r}")
            mismatches += 1

    if mismatches:
        print(f"\n{mismatches} mismatch(es) found.")
        return 1
    print(f"No drift — {len(live)} marker(s) match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
