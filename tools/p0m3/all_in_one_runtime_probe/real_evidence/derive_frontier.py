"""Derive the bounded All-In-One frontier from accepted analyzer evidence."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

OPAQUE_ID = re.compile(r"^RM\d{3}$")
EXPECTED_STARTING_HEAD = "64a78894166b873987de57437b2d74d4d057e97a"
EXPECTED_PAIRS = {
    ("V1", "RM014", "RM010"),
    ("V2", "RM014", "RM081"),
    ("V2", "RM041", "RM014"),
}
EXPECTED_TRACKS = {"RM010", "RM014", "RM041", "RM081"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accepted-evidence", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    accepted = json.loads(Path(args.accepted_evidence).read_text(encoding="utf-8"))
    rows = accepted["near_miss_replay"]
    derived = []
    excluded = []
    observed_texture_statuses = set()
    for row in rows:
        texture = row["confidence_ledger"]["texture_measurement_confidence_source"]
        status = texture["status"]
        observed_texture_statuses.add(status)
        pair = (row["category"], row["outgoing_opaque_id"], row["incoming_opaque_id"])
        if texture["confidence"] != "MEASURED":
            raise ValueError("TEXTURE_EVIDENCE_NOT_MEASURED")
        if status == "INCOMPATIBLE":
            excluded.append(pair)
        else:
            if status != "COMPATIBLE":
                raise ValueError("UNEXPECTED_TEXTURE_STATUS")
            derived.append(pair)

    derived_set = set(derived)
    track_union = {opaque_id for _, out_id, in_id in derived for opaque_id in (out_id, in_id)}
    if not all(OPAQUE_ID.fullmatch(value) for pair in derived for value in pair[1:]):
        raise ValueError("INVALID_OPAQUE_ID")
    if derived_set != EXPECTED_PAIRS or track_union != EXPECTED_TRACKS:
        raise SystemExit("FRONTIER_MISMATCH")

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if head != EXPECTED_STARTING_HEAD:
        raise ValueError("STARTING_HEAD_MISMATCH")

    payload = {
        "schema_version": 1,
        "starting_head": head,
        "source_artifact_result": accepted["result"],
        "derivation_rule": "RETAIN_ONLY_NEAR_MISS_REPLAYS_WITH_MEASURED_TEXTURE_STATUS_COMPATIBLE",
        "source_pair_count": len(rows),
        "observed_texture_statuses": sorted(observed_texture_statuses),
        "measured_texture_incompatible_pair_count": len(excluded),
        "derived_pair_count": len(derived),
        "derived_pairs": [
            {"category": lane, "outgoing_opaque_id": out_id, "incoming_opaque_id": in_id}
            for lane, out_id, in_id in sorted(derived)
        ],
        "derived_track_count": len(track_union),
        "derived_track_ids": sorted(track_union),
        "exact_expected_pair_equality": derived_set == EXPECTED_PAIRS,
        "exact_expected_track_equality": track_union == EXPECTED_TRACKS,
        "frontier_result": "FRONTIER_DERIVED_EXACT",
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
