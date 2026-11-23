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
  const [falling, bare, leafing] = HABIT[ph.leaf_habit] ?? HABIT.evergreen;
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
