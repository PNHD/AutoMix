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
