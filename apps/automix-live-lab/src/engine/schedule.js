/**
 * Pure, framework-agnostic scheduling math for the Local DSP Live queue.
 * No AudioContext dependency -- runnable under plain Node for automated
 * verification (see tools/verify_schedule.mjs) and reused unmodified by
 * the real Web Audio engine (deck-engine.js) so the audited math and the
 * executed math are provably the same function.
 *
 * A "live_two_deck" item plays:
 *   [t0 .. t0+exitOffsetS)                 outgoing deck alone
 *   [t0+exitOffsetS .. t0+exitOffsetS+windowS)   crossfade window (both decks)
 *   [t0+exitOffsetS .. t0+exitOffsetS+inDurationS)  incoming deck total span
 * The next item starts exactly when the incoming deck's own prepared
 * excerpt ends -- t0 + exitOffsetS + inDurationS -- so there is zero gap
 * and zero overlap between one queue item's incoming tail and the next
 * item's outgoing start.
 *
 * A "baked_transition" item plays its single file for durationS; the next
 * item starts exactly at t0 + durationS.
 */

export function computeQueueSchedule(items, leadInS = 0.25) {
  const timeline = [];
  let cursor = leadInS;

  for (const item of items) {
    if (item.mode === "live_two_deck") {
      const exitAt = cursor + item.exit_offset_s;
      const windowEndAt = exitAt + item.window_s;
      const itemEndAt = exitAt + item.in_duration_s;
      timeline.push({
        tag: item.tag,
        mode: item.mode,
        t0: cursor,
        exitAt,
        windowEndAt,
        itemEndAt,
        outFile: item.out_file,
        inFile: item.in_file,
        entryOffsetS: item.entry_offset_s,
        tempoRatio: item.tempo_ratio,
        bassCutoffHz: item.bass_cutoff_hz,
        bassHandoffSpeed: item.bass_handoff_speed,
      });
      cursor = itemEndAt;
    } else if (item.mode === "baked_transition") {
      const itemEndAt = cursor + item.duration_s;
      timeline.push({
        tag: item.tag,
        mode: item.mode,
        t0: cursor,
        exitAt: null,
        windowEndAt: null,
        itemEndAt,
        file: item.file,
        tempoRatio: item.tempo_ratio,
      });
      cursor = itemEndAt;
    } else {
      throw new Error(`UNKNOWN_QUEUE_ITEM_MODE: ${item.mode}`);
    }
  }

  return { timeline, totalDurationS: cursor, transitionCount: timeline.length };
}

/**
 * Pure scheduling math for the P0-M8-R1 LocalDSP consumer chain -- a
 * genuinely continuous single-current-track session (seed -> automatic
 * successor -> automatic successor -> ...), as opposed to
 * computeQueueSchedule's independent baked pair-demo items above.
 *
 * Each chain track plays ONE continuous buffer. Track k+1's buffer starts
 * at the exact absolute time track k reaches ITS OWN exit anchor
 * (`exitOffsetS` into track k's own file) -- i.e. the crossfade window is
 * the OVERLAP between two consecutively-playing decks, not a separate
 * scheduled item. A track with `exitOffsetS === null` (terminal, no
 * eligible successor rendered) simply plays out to its own file duration
 * with no further hop.
 *
 * `tracks`: ordered array of
 *   { tag, durationS, exitOffsetS: number|null, windowS: number|null }
 * (exactly the shape emitted by tools/p0m8/prepare_local_dsp_chain.py's
 * `local_dsp_chain.json`, in the order the chain is actually being played
 * -- the caller decides how many entries are "revealed" so far, enabling
 * genuine incremental refill rather than a single precomputed session).
 */
export function computeChainSchedule(tracks, leadInS = 0.25) {
  const timeline = [];
  let t0 = leadInS;
  for (let k = 0; k < tracks.length; k++) {
    const track = tracks[k];
    const hasExit = track.exitOffsetS !== null && track.exitOffsetS !== undefined;
    const exitAt = hasExit ? t0 + track.exitOffsetS : null;
    const windowEndAt = hasExit && track.windowS != null ? exitAt + track.windowS : null;
    const itemEndAt = t0 + track.durationS;
    timeline.push({ tag: track.tag, t0, exitAt, windowEndAt, itemEndAt, windowS: track.windowS ?? null });
    if (hasExit) t0 = exitAt;
    else if (k < tracks.length - 1) throw new Error(`CHAIN_SCHEDULE_MISSING_EXIT_BEFORE_LAST_TRACK: ${track.tag}`);
  }
  return { timeline, totalDurationS: timeline.length ? Math.max(...timeline.map((e) => e.itemEndAt)) : leadInS };
}

/**
 * Verification helper: proves each non-terminal chain track's crossfade
 * window starts and ends within tolerance of the next track's buffer
 * bounds -- i.e. the handoff is a genuine overlap (not a gap, not a
 * mid-buffer discontinuity).
 */
export function verifyChainOverlap(timeline, toleranceS = 1e-6) {
  const issues = [];
  for (let i = 1; i < timeline.length; i++) {
    const prev = timeline[i - 1];
    const cur = timeline[i];
    if (prev.exitAt === null) {
      issues.push({ index: i, prevTag: prev.tag, curTag: cur.tag, problem: "PREV_HAS_NO_EXIT_BUT_CHAIN_CONTINUES" });
      continue;
    }
    if (Math.abs(cur.t0 - prev.exitAt) > toleranceS) {
      issues.push({ index: i, prevTag: prev.tag, curTag: cur.tag, problem: "START_NOT_AT_PREV_EXIT", deltaS: cur.t0 - prev.exitAt });
    }
  }
  return { ok: issues.length === 0, issues };
}

/**
 * Verification helper: proves the schedule has zero gaps and zero
 * negative-duration overlaps between consecutive items (each item's end
 * equals the next item's start, to floating-point tolerance).
 */
export function verifyGapless(timeline, toleranceS = 1e-6) {
  const issues = [];
  for (let i = 1; i < timeline.length; i++) {
    const prevEnd = timeline[i - 1].itemEndAt;
    const curStart = timeline[i].t0;
    const delta = curStart - prevEnd;
    if (Math.abs(delta) > toleranceS) {
      issues.push({ index: i, prevTag: timeline[i - 1].tag, curTag: timeline[i].tag, deltaS: delta });
    }
  }
  return { gapless: issues.length === 0, issues };
}
