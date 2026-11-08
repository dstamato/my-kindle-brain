from __future__ import annotations

import re
import unicodedata

import numpy as np


# Bilingual, deliberately narrow profiles. The previous taxonomy mixed broad
# concepts ("future", "humanity", "society", "culture") and therefore acted as
# a catch-all. These profiles separate subjects useful when browsing a library.
CATEGORIES: dict[str, str] = {
    "IA · Automatización":
        "inteligencia artificial modelos de lenguaje aprendizaje automático robots automatización; "
        "artificial intelligence machine learning language models robotics automation",
    "Tecnología · Internet · Software":
        "tecnología internet software programación plataformas redes sociales computación digital; "
        "technology internet software programming platforms social networks computing digital",
    "Economía · Finanzas · Mercados":
        "economía finanzas dinero inversión bolsa mercados capitalismo desigualdad; "
        "economics finance money investing stock market capitalism inequality",
    "Negocios · Innovación · Liderazgo":
        "negocios empresas estrategia gestión innovación emprendimiento liderazgo trabajo; "
        "business companies strategy management innovation entrepreneurship leadership work",
    "Psicología · Conducta · Bienestar":
        "psicología mente emociones hábitos decisiones felicidad bienestar autoayuda; "
        "psychology mind emotions habits decisions happiness wellbeing self help",
    "Relaciones · Sexualidad · Género":
        "pareja amor relaciones sexualidad sexo género feminismo crianza familia; "
        "relationships love sexuality sex gender feminism parenting family",
    "Salud · Medicina · Biología":
        "salud medicina enfermedad biología genética cuerpo nutrición longevidad pandemia; "
        "health medicine disease biology genetics body nutrition longevity pandemic",
    "Ciencia · Matemática · Complejidad":
        "ciencia física matemática universo sistemas complejidad caos evolución tiempo; "
        "science physics mathematics universe systems complexity chaos evolution time",
    "Filosofía · Futuro · Humanidad":
        "filosofía ética sentido existencia humanidad futuro civilización transhumanismo; "
        "philosophy ethics meaning existence humanity future civilization transhumanism",
    "Sociedad · Política · Historia":
        "sociedad política gobierno democracia historia geopolítica guerra nación desigualdad; "
        "society politics government democracy history geopolitics war nation inequality",
    "Comunicación · Marketing · Medios":
        "comunicación marketing publicidad persuasión ventas marcas medios periodismo narrativa; "
        "communication marketing advertising persuasion sales brands media journalism storytelling",
    "Privacidad · Seguridad · Vigilancia":
        "privacidad seguridad vigilancia hackers ciberdelito control datos espionaje; "
        "privacy security surveillance hackers cybercrime control data espionage",
    "Cultura · Creatividad · Arte":
        "cultura creatividad arte música escritura cine diseño entretenimiento; "
        "culture creativity art music writing cinema design entertainment",
    "Literatura · Ficción":
        "novela ficción cuento thriller fantasía aventura literatura; "
        "novel fiction story thriller fantasy adventure literature",
}


# High-precision lexical signals. They are a bonus, not the whole classifier,
# so an ambiguous word cannot decide a category by itself.
CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "IA · Automatización": (
        "inteligencia artificial", "machine learning", "deep learning", "language model",
        "robot", "robots", "algoritmo", "automatizacion", "artificial intelligence",
    ),
    "Tecnología · Internet · Software": (
        "internet", "software", "programador", "programacion", "codigo", "plataforma",
        "redes sociales", "blockchain", "criptomoneda", "digital", "tecnologia",
    ),
    "Economía · Finanzas · Mercados": (
        "economia", "finanzas", "capitalismo", "wall street", "bolsa", "mercado",
        "inversion", "dinero", "banco", "precio", "coste", "desigualdad",
    ),
    "Negocios · Innovación · Liderazgo": (
        "lider", "liderazgo", "empresa", "negocio", "gestion", "management", "estrategia",
        "innovacion", "emprend", "canvas", "startup", "trabajo",
    ),
    "Psicología · Conducta · Bienestar": (
        "psicologia", "mente", "emocion", "feliz", "felicidad", "habito", "conducta",
        "decidir", "decision", "pensar", "mindset", "introvertido", "autoayuda",
    ),
    "Relaciones · Sexualidad · Género": (
        "sexo", "sexual", "orgasmo", "pareja", "amor", "vagina", "genero", "mujer",
        "feminismo", "criar", "ninos", "familia", "kama sutra",
    ),
    "Salud · Medicina · Biología": (
        "salud", "medicina", "paciente", "virus", "pandemia", "epidemia", "biologia",
        "genes", "genetica", "healthcare", "enfermedad", "longevidad", "nutricion",
    ),
    "Ciencia · Matemática · Complejidad": (
        "fisica", "cuantica", "matematica", "particula", "universo", "ciencia",
        "complejidad", "sistemas", "azar", "tiempo", "turing", "evolucion",
    ),
    "Filosofía · Futuro · Humanidad": (
        "filosofia", "humanidad", "homo deus", "sapiens", "civilizacion", "etica",
        "existencia", "transhuman", "futuro humano", "future of humanity",
    ),
    "Sociedad · Política · Historia": (
        "politica", "gobierno", "democracia", "historia", "china", "guerra", "sociedad",
        "revolucion industrial", "geopolitica", "poder mediatico",
    ),
    "Comunicación · Marketing · Medios": (
        "marketing", "publicidad", "comunicacion", "persuasion", "marca", "ventas",
        "medios", "twitter", "radio", "social media", "frases celebres",
    ),
    "Privacidad · Seguridad · Vigilancia": (
        "privacidad", "vigilancia", "hacker", "seguridad", "snowden", "ciberdelito",
        "delitos del futuro", "red oscura", "te estan puntuando",
    ),
    "Cultura · Creatividad · Arte": (
        "creatividad", "creativo", "arte", "cultura", "musica", "escribir", "escritura",
        "cine", "entretenimiento", "mainstream",
    ),
    "Literatura · Ficción": (
        "novela", "ficcion", "cuento", "thriller", "fantasia", "aventura",
    ),
}


CAT_META: dict[str, dict] = {
    "IA · Automatización":                 {"icon": "🤖", "color": "#2d5a8e", "bg": "#E6F1FB"},
    "Tecnología · Internet · Software":    {"icon": "💻", "color": "#0C447C", "bg": "#E6F1FB"},
    "Economía · Finanzas · Mercados":      {"icon": "📊", "color": "#085041", "bg": "#E1F5EE"},
    "Negocios · Innovación · Liderazgo":   {"icon": "💡", "color": "#633806", "bg": "#FAEEDA"},
    "Psicología · Conducta · Bienestar":   {"icon": "🧠", "color": "#3C3489", "bg": "#EEEDFE"},
    "Relaciones · Sexualidad · Género":    {"icon": "♥",  "color": "#8C1D40", "bg": "#FBEAF0"},
    "Salud · Medicina · Biología":         {"icon": "🔬", "color": "#173404", "bg": "#EAF3DE"},
    "Ciencia · Matemática · Complejidad":  {"icon": "🔭", "color": "#185FA5", "bg": "#EAF3FA"},
    "Filosofía · Futuro · Humanidad":      {"icon": "◉",  "color": "#4A1B0C", "bg": "#FAECE7"},
    "Sociedad · Política · Historia":      {"icon": "🌍", "color": "#2C2C2A", "bg": "#F1EFE8"},
    "Comunicación · Marketing · Medios":   {"icon": "📣", "color": "#4B1528", "bg": "#FBEAF0"},
    "Privacidad · Seguridad · Vigilancia": {"icon": "🔒", "color": "#5C2D91", "bg": "#F3EEFF"},
    "Cultura · Creatividad · Arte":        {"icon": "✦",  "color": "#854F0B", "bg": "#FAEEDA"},
    "Literatura · Ficción":                {"icon": "📖", "color": "#5F5E5A", "bg": "#F1EFE8"},
}

CAT_ORDER = list(CATEGORIES.keys())

_cat_vecs: np.ndarray | None = None


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _lexical_scores(book: dict) -> np.ndarray:
    title_text = f"{book.get('bookTitle', '')} {book.get('bookAuthor', '')}"
    title = f" {_normalize(title_text)} "
    scores = np.zeros(len(CAT_ORDER), dtype=np.float32)
    for idx, category in enumerate(CAT_ORDER):
        for keyword in CATEGORY_KEYWORDS[category]:
            needle = f" {_normalize(keyword)} "
            if needle in title:
                scores[idx] += 3.0 + min(2.0, keyword.count(" "))
    return scores


def assign_categories(
    books: list[dict],
    model,
    clippings: list[dict] | None = None,
    embeddings: np.ndarray | None = None,
) -> list[str]:
    """Classify books from title/author, clipping content, and lexical signals."""
    global _cat_vecs

    if not books:
        return []

    if _cat_vecs is None:
        _cat_vecs = model.encode(
            [CATEGORIES[c] for c in CAT_ORDER],
            normalize_embeddings=True,
            show_progress_bar=False,
        )

    queries = [f"{b.get('bookTitle', '')}. {b.get('bookAuthor', '')}" for b in books]
    title_vecs = model.encode(
        queries, normalize_embeddings=True, show_progress_bar=False, batch_size=64
    )
    scores = title_vecs @ _cat_vecs.T

    vecs_by_book: dict[str, list[np.ndarray]] = {}
    if clippings:
        for i, clip in enumerate(clippings):
            raw = clip["bookRaw"]
            if embeddings is not None and i < len(embeddings):
                vecs_by_book.setdefault(raw, []).append(embeddings[i])

    results: list[str] = []
    for row, book in enumerate(books):
        raw = book["bookRaw"]

        # The clipping centroid disambiguates generic titles. Title and author
        # remain dominant because highlights can span several subjects.
        book_vecs = vecs_by_book.get(raw)
        if book_vecs:
            centroid = np.mean(book_vecs, axis=0)
            norm = np.linalg.norm(centroid)
            if norm:
                content_scores = (centroid / norm) @ _cat_vecs.T
                scores[row] = 0.68 * scores[row] + 0.32 * content_scores

        lexical = _lexical_scores(book)
        if lexical.max() > 0:
            scores[row] += np.minimum(lexical, 8.0) * 0.10

        ranked = np.argsort(scores[row])
        top, second = int(ranked[-1]), int(ranked[-2])
        # Explicit title terms are decisive. For opaque titles, avoid forcing a
        # weak guess into a broad category; the UI exposes these for correction.
        if lexical.max() < 3.0 and scores[row, top] - scores[row, second] < 0.025:
            results.append("Sin categoría")
        else:
            results.append(CAT_ORDER[top])

    return results
