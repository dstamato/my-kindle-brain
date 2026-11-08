"""Reclassify the current library with a local Ollama model.

Run without --apply to review the proposed distribution.  With --apply, the
choices are stored as overrides and survive future Kindle imports.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import re

import httpx

from categorizer import CAT_ORDER
from db import apply_category_overrides, get_conn, init_db


# A small local model is useful for the long tail, while well-known or highly
# explicit titles should be deterministic. These corrections also form a
# reviewable record of decisions made for this library.
CURATED_TITLE_CATEGORIES = {
    "AI Snake Oil: What Artificial Intelligence Can Do, What It Can’t, and How to Tell the Difference": "IA · Automatización",
    "Human + Machine: Reimaging Work in the Age of AI": "IA · Automatización",
    "Inteligencia artificial": "IA · Automatización",
    "LA INTELIGENCIA ARTIFICIAL Y EL FUTURO DE LA HUMANIDAD": "IA · Automatización",
    "La era de la Inteligencia Artificial y nuestro futuro humano": "IA · Automatización",
    "Life 3.0: Being Human in the Age of Artificial Intelligence": "IA · Automatización",
    "Los robots robarán tu empleo, pero está bien": "IA · Automatización",
    "Mente + máquina": "IA · Automatización",
    "Prediction Machines: The Simple Economics of Artificial Intelligence": "IA · Automatización",
    "Rise of the Robots: Technology and the Threat of a Jobless Future": "IA · Automatización",
    "The Sentient Machine": "IA · Automatización",
    "Vida 3.0": "IA · Automatización",
    "¿Qué robot se ha llevado mi queso?": "IA · Automatización",
    "Cómo crear una mente": "IA · Automatización",
    "Blockchain (Alexander Preukschat (Coordinador))": "Economía · Finanzas · Mercados",
    "Criptomonedas para dummies": "Economía · Finanzas · Mercados",
    "Flash Boys: A Wall Street Revolt": "Economía · Finanzas · Mercados",
    "La gran apuesta": "Economía · Finanzas · Mercados",
    "La red antisocial: la verdadera historia del grupo de pequeños inversores, trolls y antisistema que puso de rodillas a Wall Street": "Economía · Finanzas · Mercados",
    "Las trampas del deseo": "Psicología · Conducta · Bienestar",
    "Piensa como un freak": "Psicología · Conducta · Bienestar",
    "Un pequeño empujón": "Psicología · Conducta · Bienestar",
    "El arte de decidir": "Psicología · Conducta · Bienestar",
    "El arte del mínimo esfuerzo": "Psicología · Conducta · Bienestar",
    "El poder de los introvertidos": "Psicología · Conducta · Bienestar",
    "Fuera de serie": "Psicología · Conducta · Bienestar",
    "Ja": "Psicología · Conducta · Bienestar",
    "La nueva ciencia de la mentira": "Psicología · Conducta · Bienestar",
    "La psicología de la Gestalt": "Psicología · Conducta · Bienestar",
    "La vida secreta de la mente": "Psicología · Conducta · Bienestar",
    "Por qué creemos en mierdas": "Psicología · Conducta · Bienestar",
    "Reinventarse": "Psicología · Conducta · Bienestar",
    "¡Deja de chingarte!": "Psicología · Conducta · Bienestar",
    "Aprender a amar": "Relaciones · Sexualidad · Género",
    "Cómo Criar Niños Felices": "Relaciones · Sexualidad · Género",
    "Falos y falacias": "Relaciones · Sexualidad · Género",
    "La mujer invisible": "Relaciones · Sexualidad · Género",
    "S=ex<sup>2</sup>. La ciencia del sexo": "Relaciones · Sexualidad · Género",
    "¿Por qué es divertido el sexo?": "Relaciones · Sexualidad · Género",
    "La muerte de la muerte": "Salud · Medicina · Biología",
    "Pandemia": "Salud · Medicina · Biología",
    "Este virus que nos vuelve locos": "Salud · Medicina · Biología",
    "Desayuno con partículas": "Ciencia · Matemática · Complejidad",
    "Errores geniales que cambiaron el mundo": "Ciencia · Matemática · Complejidad",
    "El Cisne Negro": "Filosofía · Futuro · Humanidad",
    "El lecho de Procusto": "Filosofía · Futuro · Humanidad",
    "En el futuro": "Filosofía · Futuro · Humanidad",
    "En el futuro: perspectivas para la humanidad": "Filosofía · Futuro · Humanidad",
    "El fin del mundo tal y como lo conocemos": "Filosofía · Futuro · Humanidad",
    "Lo imprevisible": "Filosofía · Futuro · Humanidad",
    "Decir no no basta": "Sociedad · Política · Historia",
    "Factfulness": "Sociedad · Política · Historia",
    "Filosofía política del poder mediático": "Sociedad · Política · Historia",
    "La cuarta revolución industrial": "Sociedad · Política · Historia",
    "Una historia diferente del mundo": "Sociedad · Política · Historia",
    "Brandoffon": "Comunicación · Marketing · Medios",
    "El gran libro de las frases célebres": "Comunicación · Marketing · Medios",
    "Freud en Madison Avenue": "Comunicación · Marketing · Medios",
    "Hit Makers": "Comunicación · Marketing · Medios",
    "La verdadera historia de Twitter": "Comunicación · Marketing · Medios",
    "Todos somos un poco raros: el auge de las comunidades y el fin de lo normal": "Comunicación · Marketing · Medios",
    "Armas de destrucción matemática": "Privacidad · Seguridad · Vigilancia",
    "Delitos del futuro": "Privacidad · Seguridad · Vigilancia",
    "Desnudando a Google(c.1)": "Privacidad · Seguridad · Vigilancia",
    "El enemigo conoce el sistema": "Privacidad · Seguridad · Vigilancia",
    "La red oscura": "Privacidad · Seguridad · Vigilancia",
    "¡Sonríe, te están puntuando!": "Privacidad · Seguridad · Vigilancia",
    "¿Quién controla el futuro?": "Privacidad · Seguridad · Vigilancia",
    "Todo va a cambiar": "Tecnología · Internet · Software",
    "Creatividad, S. A.": "Negocios · Innovación · Liderazgo",
    "El Elemento": "Cultura · Creatividad · Arte",
    "El espíritu creativo": "Cultura · Creatividad · Arte",
    "Historia freak de la Música": "Cultura · Creatividad · Arte",
    "Los videojuegos": "Cultura · Creatividad · Arte",
    "Mientras escribo": "Cultura · Creatividad · Arte",
    "Descendiendo hasta el infierno": "Literatura · Ficción",
    "El campamento": "Literatura · Ficción",
    "El ladrón del rayo": "Literatura · Ficción",
    "El príncipe de la niebla": "Literatura · Ficción",
    "Marina": "Literatura · Ficción",
}


def _books() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT b.id, b.raw, b.title, b.author, "
            "COALESCE((SELECT text FROM clippings c WHERE c.book_id=b.id "
            "ORDER BY LENGTH(text) DESC LIMIT 1), '') AS sample "
            "FROM books b ORDER BY b.id"
        ).fetchall()
    return [dict(row) for row in rows]


def _prompt(batch: list[dict]) -> str:
    categories = "\n".join(f"- {category}" for category in CAT_ORDER)
    books = "\n".join(
        f"ID {book['id']} | {book['title']} | {book['author']} | "
        f"Muestra: {re.sub(r'\\s+', ' ', book['sample'])[:220]}"
        for book in batch
    )
    return f"""Clasifica cada libro por su tema principal. Usa exactamente una de estas categorías:
{categories}

Reglas:
- Sociedad · Política · Historia sólo corresponde cuando el tema central es social, político, geopolítico o histórico.
- Literatura · Ficción corresponde a novelas, cuentos, fantasía y thrillers.
- Distingue IA de tecnología general, y economía de negocios/gestión.
- Distingue psicología personal de relaciones/sexualidad.
- La muestra puede ayudar con títulos ambiguos, pero prioriza el tema conocido del libro.
- Devuelve todos los IDs una sola vez y no inventes categorías.

Libros:
{books}

Responde sólo con JSON: {{"ID": "categoría exacta", ...}}"""


def classify(model: str, batch_size: int = 6) -> dict[int, str]:
    books = _books()
    assignments: dict[int, str] = {}
    with httpx.Client(timeout=240) as client:
        for start in range(0, len(books), batch_size):
            batch = books[start:start + batch_size]
            response = client.post(
                "http://127.0.0.1:11434/api/generate",
                json={
                    "model": model,
                    "prompt": _prompt(batch),
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0, "num_predict": 800},
                },
            )
            response.raise_for_status()
            payload = json.loads(response.json()["response"])
            expected = {str(book["id"]) for book in batch}
            # Small local models occasionally answer a one-book batch as
            # {"category": "..."}; accept it when the value is unambiguous.
            if len(batch) == 1 and not expected.issubset(payload):
                values = [value for value in payload.values() if value in CAT_ORDER]
                if len(values) == 1:
                    payload = {next(iter(expected)): values[0]}
            if not expected.issubset(payload):
                missing = sorted(expected - set(payload))
                raise RuntimeError(f"Respuesta incompleta en lote {start}: faltan {missing}")
            for book_id in expected:
                category = payload[book_id]
                if category not in CAT_ORDER:
                    raise RuntimeError(f"Categoría inválida para {book_id}: {category}")
                assignments[int(book_id)] = category
            print(f"Clasificados {min(start + batch_size, len(books))}/{len(books)}")
    return assignments


def curated_assignments() -> dict[str, str]:
    assignments = {}
    for book in _books():
        category = CURATED_TITLE_CATEGORIES.get(book["title"])
        if category:
            assignments[book["raw"]] = category
    return assignments


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="llama3.2:latest")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--curated-only", action="store_true")
    args = parser.parse_args()

    init_db()
    if args.curated_only:
        applied = apply_category_overrides(curated_assignments())
        print(f"Aplicadas {applied} correcciones curadas.")
        return
    books = _books()
    assignments = classify(args.model)
    counts = Counter(assignments.values())
    print("\nDistribución propuesta:")
    for category in CAT_ORDER:
        print(f"{counts[category]:3}  {category}")

    if args.apply:
        raw_categories = {
            book["raw"]: assignments[book["id"]]
            for book in books
        }
        applied = apply_category_overrides(raw_categories)
        print(f"\nAplicadas y guardadas {applied} categorías.")
    else:
        print("\nVista previa solamente. Usá --apply para guardar.")


if __name__ == "__main__":
    main()
