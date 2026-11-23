// What a month looks like, previewed from the sheet's phenology months (spec §6.3, §14).
// Only a preview for the viewer: in the world, pietri.dev's simulator decides with the weather.

export const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
  'August', 'September', 'October', 'November', 'December'];

const next = (m) => (m % 12) + 1;
const prev = (m) => ((m + 10) % 12) + 1;

// Months strictly after a run of `fall` months and before a run of `out` months.
export function dormantMonths(fall, out) {
  if (!fall?.length || !out?.length) return [];
  const end = fall.find((m) => !fall.includes(next(m)));
  const start = out.find((m) => !out.includes(prev(m)));
  if (end === undefined || start === undefined) return [];
  const months = [];
  for (let m = next(end); m !== start && months.length < 12; m = next(m)) {
    if (fall.includes(m) || out.includes(m)) break;
    months.push(m);
  }
  return months;
}

const HABIT = {
  //               falling, bare, leafing out
  evergreen: [1, 1, 1],
  semi_deciduous: [0.6, 0.35, 0.75],
  deciduous: [0.4, 0, 0.6],
};

// Amount of each part shown in `month` (1-12): 0 hides it, 1 shows every clump.
export function partAmounts(sheet, month) {
  const ph = sheet?.plant?.phenology ?? {};
  const has = (phase) => Boolean(phase?.months?.includes(month));
  let [falling, bare, leafing] = HABIT[ph.leaf_habit] ?? HABIT.evergreen;
  const kept = ph.winter_leaf_share;
  if (kept && typeof kept.min === 'number') {
    // A sourced share replaces the habit's default; the months around it scale with it.
    const k = kept.typical ?? (kept.min + kept.max) / 2;
    const scale = bare > 0 ? k / bare : 1;
    [falling, bare, leafing] = [Math.min(1, falling * scale), k, Math.min(1, leafing * scale)];
  }
  let foliage = 1;
  let foliageAutumn = false;
  if (has(ph.leaf_fall)) { foliage = falling; foliageAutumn = true; }
  else if (has(ph.leaf_out)) foliage = leafing;
  else if (dormantMonths(ph.leaf_fall?.months, ph.leaf_out?.months).includes(month)) foliage = bare;
  return {
    foliage,
    foliageAutumn,
    flowers: has(ph.flowering) ? 1 : 0,
    fruit: has(ph.fruiting) ? 1 : 0,
  };
}

// The first month of each run of `months` (a run may wrap past December).
function runStarts(months) {
  return months.filter((m) => !months.includes(prev(m)));
}

// Months from `start` forward to `month`, 0 when equal.
const ahead = (start, month) => (month - start + 12) % 12;

// Leaf colours in `month` from the sheet's leaf_tones (spec §6.4): `from` everywhere,
// `to` on a share of the shown clumps: those with the highest _order (the first to fall,
// the last to come out), or the lowest when new leaves age to mature (the first out age
// first). null without tones.
export function foliageTones(sheet, month) {
  const tones = (sheet?.plant?.phenology?.leaf_tones ?? []).filter((t) => t.months?.includes(month));
  if (!tones.length) return null;
  if (tones.length === 1) return { from: tones[0].tone, to: tones[0].tone, share: 0, lowest: false };
  // The tone whose run started most recently is the one arriving.
  const since = (t) => Math.min(...runStarts(t.months).map((s) => ahead(s, month)));
  const [arriving, leaving] = since(tones[0]) <= since(tones[1]) ? tones : [tones[1], tones[0]];
  let first = month;
  while (arriving.months.includes(prev(first)) && leaving.months.includes(prev(first)) && first !== next(month)) first = prev(first);
  let k = 0;
  for (let m = first; arriving.months.includes(m) && leaving.months.includes(m) && k < 12; m = next(m)) k += 1;
  const i = ahead(first, month) + 1;
  const lowest = leaving.tone === 'new' && arriving.tone === 'mature';
  return { from: leaving.tone, to: arriving.tone, share: i / (k + 1), lowest };
}
