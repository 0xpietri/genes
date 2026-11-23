"""The public pages in English (/) and Spanish (/es/): one language per page, never mixed.

The page code is written in English and passes every visible text through `T`. On a Spanish
page, `T` looks the text up in `UI_ES` (the site's own words) and then in the species'
`i18n/es.json` (its sheet's and look's English texts). A text with no Spanish is kept in
English and remembered in `MISSING`, which the tests require to be empty.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from genes import jsonio

LANGS = ("en", "es")
LANG_NAME = {"en": "English", "es": "Español"}
LOCALE = {"en": "en_GB", "es": "es_AR"}

_lang: ContextVar[str] = ContextVar("lang", default="en")
_texts: ContextVar[dict[str, str]] = ContextVar("texts", default={})  # noqa: B039
MISSING: set[str] = set()


def lang() -> str:
    return _lang.get()


def prefix(lang_: str | None = None) -> str:
    """The URL prefix of a language: English at the root, Spanish under /es."""
    return "" if (lang_ or _lang.get()) == "en" else f"/{lang_ or _lang.get()}"


def species_texts(folder: Path, lang_: str) -> dict[str, str]:
    p = folder / "i18n" / f"{lang_}.json"
    if lang_ == "en" or not p.exists():
        return {}
    data: dict[str, Any] = jsonio.load(p)
    texts: dict[str, str] = data.get("texts", {})
    return texts


@contextmanager
def speaking(lang_: str, texts: dict[str, str] | None = None) -> Iterator[None]:
    a = _lang.set(lang_)
    b = _texts.set(texts or {})
    try:
        yield
    finally:
        _lang.reset(a)
        _texts.reset(b)


def T(text: str) -> str:
    """`text` in the page's language."""
    if _lang.get() == "en" or not text:
        return text
    found = UI_ES.get(text) or _texts.get().get(text)
    if found is None:
        MISSING.add(text)
        return text
    return found


def num(x: float, spec: str = "g") -> str:
    """A number for reading: 1,200.5 in English, 1.200,5 in Spanish."""
    text = format(x, spec)
    if _lang.get() == "es":
        text = text.replace(",", "\0").replace(".", ",").replace("\0", ".")
    return text


UI_ES: dict[str, str] = {
    # units stay as they are
    "m": "m",
    "°C": "°C",
    "kg/m³": "kg/m³",
    # header, footer, index
    "Plants": "Plantas",
    "Animals": "Animales",
    "About": "Acerca",
    "Coming later": "Más adelante",
    "Sections": "Secciones",
    "Language": "Idioma",
    "Catalog": "Catálogo",
    "species": "especies",
    "1 species": "1 especie",
    "release": "versión",
    "Living things of the pietri.dev world": "Los seres vivos del mundo de pietri.dev",
    "Trees, grasses and, later, animals of the pietri.dev world. Each one with its facts and sources, a 3D model to turn and zoom, its year and one whole simulated life.": "Árboles, pastos y, más adelante, animales del mundo de pietri.dev. Cada uno con sus datos y fuentes, un modelo 3D para girar y acercar, su año y una vida entera simulada.",
    "Show": "Mostrar",
    "All": "Todos",
    "Trees": "Árboles",
    "Grasses": "Pastos",
    "About genes": "Sobre genes",
    "genes is where the species of pietri.dev's little world are defined: what each one is in reality, with sources (how tall it grows, when it flowers, how much frost it takes), and how it looks, as 3D models for every stage of its life. The world's simulator reads these facts; this site shows them to anyone. Nothing here needs an account.": "genes es donde se definen las especies del pequeño mundo de pietri.dev: qué es cada una en la realidad, con fuentes (cuánto crece, cuándo florece, cuánta helada aguanta), y cómo se ve, con modelos 3D de cada etapa de su vida. El simulador del mundo lee estos datos; este sitio se los muestra a cualquiera. Nada acá necesita cuenta.",
    "Coming": "Próximamente",
    "More species": "Más especies",
    "Trees, grasses and later animals, one by one.": "Árboles, pastos y después animales, de a uno.",
    "More species coming": "Vienen más especies",
    "cut out": "recortado",
    "genes · species of the pietri.dev world": "genes · especies del mundo de pietri.dev",
    "Species of the pietri.dev world: real biology with sources, rotatable 3D trees, their simulated life and where they grow.": "Especies del mundo de pietri.dev: biología real con fuentes, árboles 3D para girar, su vida simulada y dónde crecen.",
    "Catalog of the living things of the pietri.dev world: real biology with sources and 3D models.": "Catálogo de los seres vivos del mundo de pietri.dev: biología real con fuentes y modelos 3D.",
    "is the catalog of living things of": "es el catálogo de seres vivos del mundo de",
    "'s world. Facts carry their sources; models are made by a procedural generator to resemble the real species.": ". Los datos llevan sus fuentes; los modelos los hace un generador procedural para que se parezcan a la especie real.",
    "Sheets and looks: CC BY 4.0 · code: MIT · photos keep their own licence.": "Fichas y apariencias: CC BY 4.0 · código: MIT · las fotos mantienen su licencia.",
    "Data (JSON)": "Datos (JSON)",
    "Sitemap": "Mapa del sitio",
    "Source": "Código",
    # species page: hero and simulator
    "Breadcrumb": "Ruta",
    "3D model of the": "Modelo 3D del",
    "drag to turn, scroll or pinch to zoom": "arrastrá para girar, rueda o pellizco para acercar",
    "The 3D model needs JavaScript.": "El modelo 3D necesita JavaScript.",
    "Growing the tree…": "Creciendo el árbol…",
    "Day or night": "Día o noche",
    "Night": "Noche",
    "Back to the whole tree": "Volver al árbol entero",
    "Play the tree's life": "Reproducir la vida del árbol",
    "Age": "Edad",
    "Speed": "Velocidad",
    "Year 0": "Año 0",
    " to ": " a ",
    "Season": "Estación",
    "Summer": "Verano",
    "Autumn": "Otoño",
    "Winter": "Invierno",
    "Spring": "Primavera",
    "Stages": "Etapas",
    "Seedling": "Plántula",
    "Sapling": "Renoval",
    "Young": "Joven",
    "Adult": "Adulto",
    "Old": "Viejo",
    "Dead, standing": "Muerto en pie",
    "Fallen": "Caído",
    "Evergreen": "Perenne",
    "Semi-deciduous": "Semicaducifolio",
    "Deciduous": "Caducifolio",
    "Tree": "Árbol",
    "Shrub": "Arbusto",
    "Grass": "Pasto",
    "Conservation": "Conservación",
    "Leaves": "Hojas",
    "Form": "Forma",
    # tiles
    "Height": "Altura",
    "Crown": "Copa",
    "Trunk": "Tronco",
    "Wood": "Madera",
    "Frost": "Helada",
    "Rain": "Lluvia",
    "mm/yr": "mm/año",
    "usually": "habitual",
    "Simulated life": "Vida simulada",
    "years": "años",
    "one tree in pietri.dev's simulator": "un árbol en el simulador de pietri.dev",
    # life
    "Its life": "Su vida",
    "Age, height and death of one tree, simulated once and replayed.": "Edad, altura y muerte de un árbol, simulado una vez y repetido.",
    "lived": "vivió",
    "its tallest": "su altura máxima",
    "Old age": "Vejez",
    "is what it dies of": "es de lo que muere",
    "gone into the soil": "desaparece en el suelo",
    "Its stages: jump to one": "Sus etapas: saltá a una",
    "Alive": "Vivo",
    "Fallen, rotting": "Caído, pudriéndose",
    "Height over the life of one simulated tree": "Altura a lo largo de la vida de un árbol simulado",
    "y": "a",
    # size and wood
    "How big": "Qué tan grande",
    "Adult trees to scale, next to a person.": "Árboles adultos a escala, al lado de una persona.",
    "Crown width": "Ancho de copa",
    "Wood and trunk": "Madera y tronco",
    "How heavy the wood is, and how thick the trunk grows.": "Cuánto pesa la madera y cuán grueso crece el tronco.",
    "you, 1.75 m": "vos, 1,75 m",
    "small": "chico",
    "tallest": "el más alto",
    "biggest": "el más grueso",
    "Lighter than water": "Más liviana que el agua",
    "Heavier than water": "Más pesada que el agua",
    "kg/m³ usually": "kg/m³ habitual",
    "water: 1,000": "agua: 1.000",
    "Adult height": "Altura adulta",
    "next to a 1.75 m person": "al lado de una persona de 1,75 m",
    "Wood density": "Densidad de la madera",
    "kg per cubic metre": "kg por metro cúbico",
    "water is 1,000": "el agua es 1.000",
    "Trunk diameter at breast height": "Diámetro del tronco a la altura del pecho",
    # climate
    "Water and cold": "Agua y frío",
    "The ranges the sources give.": "Los rangos que dan las fuentes.",
    "Rain it lives with": "Lluvia con la que vive",
    "Frost that kills an adult": "Helada que mata a un adulto",
    "mm a year": "mm por año",
    "Drought tolerance": "Tolerancia a la sequía",
    "Shade, seedling": "Sombra, plántula",
    "Shade, adult": "Sombra, adulto",
    "high": "alta",
    "medium": "media",
    "low": "baja",
    "to": "a",
    # year
    "The year": "El año",
    "Months for the southern hemisphere.": "Meses del hemisferio sur.",
    "The year of the tree: leaves, flowers, pods and leaf fall by month": "El año del árbol: hojas, flores, vainas y caída de hojas por mes",
    "Leaves (outer ring: new, mature, dry)": "Hojas (anillo exterior: nuevas, maduras, secas)",
    "Flowers": "Flores",
    "Pods": "Vainas",
    "Leaf fall": "Caída de hojas",
    "no leaves": "sin hojas",
    "new leaves": "hojas nuevas",
    "mature leaves": "hojas maduras",
    "dry leaves": "hojas secas",
    "flowers": "flores",
    "pods": "vainas",
    "leaf fall": "caída de hojas",
    "no flowers": "sin flores",
    "no pods": "sin vainas",
    "no leaf fall": "sin caída de hojas",
    # map, leaf
    "Where it lives": "Dónde vive",
    "Zoom in": "Acercar",
    "Zoom out": "Alejar",
    "Whole range": "Todo el rango",
    "Loading the map…": "Cargando el mapa…",
    "Map: Natural Earth.": "Mapa: Natural Earth.",
    "For now each little tree marks a province where a reference photo was taken; real sightings from GBIF replace them once they are fetched.": "Por ahora cada arbolito marca una provincia donde se sacó una foto de referencia; los avistajes reales de GBIF los reemplazan cuando se descarguen.",
    "Each little tree marks a half-degree area with GBIF sightings": "Cada arbolito marca un área de medio grado con avistajes en GBIF",
    "in": "en",
    "areas": "áreas",
    "accessed": "consultado",
    "The leaf": "La hoja",
    "each leaf splits into pinnae lined with small leaflets. Drag to turn it.": "cada hoja se divide en pinnas cubiertas de folíolos chicos. Arrastrala para girarla.",
    "Animated 3D leaf": "Hoja 3D animada",
    # gives, people
    "What it gives": "Qué da",
    "To animals, people and the soil.": "A los animales, a la gente y al suelo.",
    "Fruit": "Fruto",
    "Nectar": "Néctar",
    "Pollen": "Polen",
    "Browse": "Ramoneo",
    "Shade": "Sombra",
    "Fixes nitrogen": "Fija nitrógeno",
    "Firewood": "Leña",
    "Nest sites": "Lugar de nidos",
    "people": "la gente",
    "livestock": "el ganado",
    "bees": "las abejas",
    "goats": "las cabras",
    "People and the algarrobo": "La gente y el algarrobo",
    "Uses the sources record": "Usos que registran las fuentes",
    "How to recognise it": "Cómo reconocerlo",
    # photos, details
    "Reference photos": "Fotos de referencia",
    "Real trees the model was checked against, with where each was taken. Each keeps its author and licence.": "Árboles reales contra los que se comparó el modelo, con el lugar de cada foto. Cada una mantiene su autor y licencia.",
    "whole": "entero",
    "summer": "verano",
    "autumn": "otoño",
    "winter": "invierno",
    "spring": "primavera",
    "bark": "corteza",
    "trunk": "tronco",
    "crown": "copa",
    "leaf": "hoja",
    "leaves": "hojas",
    "flower": "flor",
    "fruit": "fruto",
    "seedling": "plántula",
    "young": "joven",
    "old": "viejo",
    "adult": "adulto",
    "branch": "rama",
    "pod": "chaucha",
    "dead": "muerto",
    "roots": "raíces",
    "Technical details": "Detalles técnicos",
    "Every number is a sourced range in real units.": "Cada número es un rango con fuente, en unidades reales.",
    "Fact": "Dato",
    "Value": "Valor",
    "Sources": "Fuentes",
    "Crown width ": "Ancho de copa",
    "Trunk diameter (breast height)": "Diámetro del tronco (a la altura del pecho)",
    "Trunks": "Troncos",
    "Rainfall it lives with": "Lluvia con la que vive",
    "Shade tolerance, seedling": "Tolerancia a la sombra, plántula",
    "Shade tolerance, adult": "Tolerancia a la sombra, adulto",
    "New leaves": "Hojas nuevas",
    "Trees differ by": "Los árboles difieren en",
    "after the": "después de la",
    "first frost": "primera helada",
    "days": "días",
    "Scientific name": "Nombre científico",
    "Family": "Familia",
    "Versions": "Versiones",
    "sheet": "ficha",
    "look": "apariencia",
    "catalog": "catálogo",
    "3D models": "Modelos 3D",
    "stages × variants, generator": "etapas × variantes, generador",
    "Data": "Datos",
    "sheet JSON": "ficha JSON",
    "look JSON": "apariencia JSON",
    "simulated life JSON": "vida simulada JSON",
    "model review": "revisión del modelo",
    "One algarrobo grown alone by": "Un algarrobo que crece solo en el simulador de",
    "'s simulator, day by day with the real weather of central Argentina since": ", día a día con el clima real del centro de Argentina desde",
    "its own limit is": "su propio límite es",
    "It dies of old age in": "Muere de viejo en",
    "years old, stands dead and then falls and rots until": "años, queda muerto en pie y después cae y se pudre hasta",
    "Every page shows the same tree.": "Todas las páginas muestran el mismo árbol.",
}

for _i, _m in enumerate(
    (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    )
):
    UI_ES[_m] = (
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    )[_i]
