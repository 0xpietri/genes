// Replaying one tree's recorded life (pietri.dev's simulator wrote it; genes only reads it).
// Which model shows at each moment follows genes's stages (spec §6.2).

export const STAGE_ORDER = ['seedling', 'sapling', 'young', 'adult', 'old', 'dead_standing', 'fallen'];
export const STAGE_LABEL = {
  seedling: 'Seedling', sapling: 'Sapling', young: 'Young', adult: 'Adult', old: 'Old',
  dead_standing: 'Dead, standing', fallen: 'Fallen',
};
export const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
  'August', 'September', 'October', 'November', 'December'];

/** The genes stage of sample `i` (spec §6.2), limited to the stages the look has. */
export function stageAt(life, i, stages = STAGE_ORDER) {
  const s = life.samples;
  const status = life.statuses[s.status[i]];
  let stage;
  if (status === 'fallen') stage = 'fallen';
  else if (status === 'standing_dead') stage = 'dead_standing';
  else {
    const h = s.h_mm[i] / 1000;
    const own = life.individual.max_height_mm / 1000;
    const age = s.age_days[i] / 365.25;
    if (h < 0.5) stage = 'seedling';
    else if (h < 2) stage = 'sapling';
    else if (h < 0.6 * own) stage = 'young';
    else if (age >= 0.7 * life.individual.max_age_years) stage = 'old';
    else stage = 'adult';
  }
  if (stages.includes(stage)) return stage;
  // The nearest earlier stage the look has, else the first.
  const k = STAGE_ORDER.indexOf(stage);
  for (let j = k; j >= 0; j--) if (stages.includes(STAGE_ORDER[j])) return STAGE_ORDER[j];
  return stages[0];
}

/** Everything the page shows for sample `i`. */
export function sampleAt(life, i) {
  const s = life.samples;
  const date = s.date[i];
  const [year, month] = date.split('-').map(Number);
  const status = life.statuses[s.status[i]];
  // A dead tree keeps the height and crown it died with.
  return {
    i, date, year, month,
    ageYears: s.age_days[i] / 365.25,
    heightM: s.h_mm[i] / 1000,
    crownM: (2 * s.crown_radius_mm[i]) / 1000,
    status,
    alive: status === 'healthy' || status === 'stressed' || status === 'dying',
    health: s.health[i] / 1000,
    decay: s.decay[i] / 1000,
    mature: s.age_days[i] / 365.25 >= life.individual.maturity_years,
  };
}

/** The sample in the same year as `i` for `month` (1–12), or the nearest one. */
export function indexForMonth(life, i, month) {
  const dates = life.samples.date;
  const year = Number(dates[i].slice(0, 4));
  const want = `${year}-${String(month).padStart(2, '0')}`;
  for (let k = Math.max(0, i - 12); k < Math.min(dates.length, i + 13); k++) {
    if (dates[k].startsWith(want)) return k;
  }
  return i;
}
