// The page's language for the few words the scripts write; everything else is in the HTML.
// The language comes from <html lang>, which the build sets (English at /, Spanish at /es/).

export const LANG = (document.documentElement.lang || 'en').slice(0, 2);

const ES = {
  Seedling: 'Plántula', Sapling: 'Renoval', Young: 'Joven', Adult: 'Adulto', Old: 'Viejo',
  'Dead, standing': 'Muerto en pie', Fallen: 'Caído',
  January: 'enero', February: 'febrero', March: 'marzo', April: 'abril', May: 'mayo',
  June: 'junio', July: 'julio', August: 'agosto', September: 'septiembre', October: 'octubre',
  November: 'noviembre', December: 'diciembre',
  Day: 'Día', Night: 'Noche', 'Year ': 'Año ', ' tall': ' de alto', 'crown ': 'copa ',
  Pause: 'Pausa', "Play the tree's life": 'Reproducir la vida del árbol',
  'The 3D model could not load.': 'No se pudo cargar el modelo 3D.',
  'The map could not load.': 'No se pudo cargar el mapa.',
  stressed: 'estresado', dying: 'muriendo',
  'Map of where the species grows': 'Mapa de dónde crece la especie',
  'sighting here': 'avistaje acá', 'sightings here': 'avistajes acá',
  'reference photo': 'foto de referencia', 'reference photos': 'fotos de referencia',
};

/** `text` in the page's language. */
export function t(text) {
  return LANG === 'es' ? (ES[text] ?? text) : text;
}

/** A number for reading, with the page's decimal mark. */
export function num(x, digits = 1) {
  return x.toLocaleString(LANG === 'es' ? 'es-AR' : 'en-GB',
    { minimumFractionDigits: digits, maximumFractionDigits: digits });
}
