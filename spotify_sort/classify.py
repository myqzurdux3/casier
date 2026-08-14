"""Classification des titres en playlists.

Deux étages :
  1. règles déterministes  — décennie, « très vieux » (métadonnées Spotify)
  2. Claude                — mood, genre, et toutes les catégories qui demandent
                             un jugement sémantique (troll, films/séries, etc.)
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor

import anthropic

from . import config
from .export import plural

def _schema() -> dict:
    """Construit le schéma à l'appel : la taxonomie est éditable à chaud."""
    return {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "i": {
                            "type": "integer",
                            "description": "Index du titre tel que fourni en entrée.",
                        },
                        "playlists": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": sorted(config.LLM_CATEGORIES),
                            },
                            "description": "Toutes les playlists auxquelles ce titre appartient.",
                        },
                    },
                    "required": ["i", "playlists"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["results"],
        "additionalProperties": False,
    }


_TOLERANCE_RULES = {
    "large": """# Seuil d'inclusion : LARGE
Les playlists doivent être bien remplies. En cas d'hésitation, INCLUS.
- Attribue un ou deux moods : si un titre est autant chill que mélancolique,
  mets les deux plutôt que d'en sacrifier un.
- Attribue tous les genres pertinents : un morceau à cheval sur deux genres va
  dans les deux.
- Pour les catégories spéciales, une correspondance raisonnable suffit — le
  titre n'a pas à être un exemple parfait. Ne t'abstiens que si l'appartenance
  serait franchement fausse.
- Deux garde-fous, où la précision prime encore : `troll` demande un humour
  volontaire, et `films-et-series` un lien réel et identifiable avec une œuvre.""",
    "stricte": """# Seuil d'inclusion : STRICTE
Ne retiens que les appartenances évidentes.
- Un seul mood, le dominant. Un seul genre principal.
- Pour les catégories spéciales, n'attribue que si le titre en est un exemple
  incontestable. Dans le doute, abstiens-toi.""",
}


def _format_references(references: dict[str, list[dict]]) -> str:
    """Exemples validés à la main par l'utilisateur, injectés comme référence."""
    if not references:
        return ""

    blocks = []
    for key, examples in references.items():
        if not examples:
            continue
        listing = "\n".join(
            f"- « {e.get('title', '?')} » — {', '.join(e.get('artists') or []) or '?'}"
            for e in examples[: config.MAX_REFERENCE_EXAMPLES]
        )
        blocks.append(
            f"## Référence pour `{key}`\n"
            f"L'utilisateur a lui-même classé ces titres dans cette catégorie. "
            f"Ils font autorité : ils définissent le périmètre réel, qui est plus "
            f"large que la description ci-dessus. Déduis-en l'esprit commun "
            f"(époques, artistes, sonorités, usage) et applique-le généreusement "
            f"aux titres à classer, y compris à des artistes absents de la liste.\n"
            f"{listing}"
        )

    if not blocks:
        return ""
    return "\n\n# Exemples fournis par l'utilisateur\n\n" + "\n\n".join(blocks)


def _build_system_prompt(references: dict[str, list[dict]] | None = None) -> str:
    def section(title: str, items: dict) -> str:
        lines = [f"## {title}"]
        lines += [f"- `{key}` : {desc}" for key, desc in items.items()]
        return "\n".join(lines)

    tolerance = _TOLERANCE_RULES.get(config.TOLERANCE, _TOLERANCE_RULES["large"])
    references_block = _format_references(references or {})

    return f"""Tu es un expert en musique qui trie une bibliothèque personnelle en playlists.

On te donne un lot de titres (titre, artiste(s), album, année, genres Spotify de
l'artiste, popularité). Pour chacun, tu renvoies la liste des playlists
auxquelles il appartient.

# Règles
- Un titre peut appartenir à PLUSIEURS playlists — c'est même le cas normal.
- Chaque titre reçoit au moins un mood ET au moins un genre.
- Les genres Spotify fournis sont indicatifs et souvent trop granulaires
  (« melodic drill », « escape room ») : sers-t'en, mais tranche toi-même.
- Si tu ne connais pas un titre, déduis-le de l'artiste et des genres Spotify.
- Réponds pour TOUS les titres du lot, en réutilisant l'index `i` fourni.

{tolerance}

{section("Moods", config.MOODS)}

{section("Genres", config.GENRES)}

{section("Catégories spéciales", config.SPECIALS)}

# Précisions sur les catégories délicates
- `classiques` : le morceau est un monument reconnu bien au-delà de son public
  d'origine. Un tube récent n'est pas encore un classique.
- `classiques-francais` : patrimoine francophone. Un rap FR récent n'en fait pas
  partie ; NTM « Ma Benz » ou IAM « Je danse le Mia », oui.
- `rap-us` / `rap-uk` / `rap-fr` : distingue-les par l'origine de l'artiste, pas
  par la sonorité. La drill existe des deux côtés de l'Atlantique — Pop Smoke est
  `rap-us`, Central Cee est `rap-uk`. Un featuring entre les deux va dans les deux.
- `white-girl-music` : label mème, pas un genre — et le périmètre est LARGE.
  Le test : est-ce que ça se chante à tue-tête en soirée ou en voiture, avec
  un refrain que tout le monde reprend ? Si oui, inclus, quelle que soit
  l'époque. Toute la pop n'en fait pas partie pour autant : le rap, l'électro
  pure et la variété française en sont exclus.
- `troll` : humour volontaire, mème internet, parodie, nanar assumé. Pas
  simplement une chanson kitsch ou datée.
- `films-et-series` : bande originale composée pour l'œuvre, OU titre
  préexistant devenu indissociable d'une scène célèbre (« Stuck in the Middle
  with You », « Running Up That Hill », « Bohemian Rhapsody » dans Wayne's
  World). Il faut un lien identifiable, pas une apparition anecdotique.{references_block}"""


# --- étage 1 : règles --------------------------------------------------------


def _year(track: dict) -> int | None:
    match = re.match(r"(\d{4})", track.get("release_date") or "")
    return int(match.group(1)) if match else None


def rule_based(track: dict) -> list[str]:
    """Playlists déductibles des seules métadonnées."""
    keys = []
    year = _year(track)
    if year:
        decade = f"{year // 10 * 10}s"
        if decade in config.DECADES:
            keys.append(decade)
        if year < 1980:
            keys.append("tres-vieux")
    return keys


# --- étage 2 : Claude --------------------------------------------------------


def _format_track(index: int, track: dict) -> str:
    genres = ", ".join(track["genres"][:6]) or "inconnus"
    return (
        f"[{index}] « {track['title'] or '?'} » — {', '.join(track['artists']) or '?'}"
        f" | album: {track['album'] or '?'}"
        f" | année: {_year(track) or '?'}"
        f" | genres Spotify: {genres}"
        f" | popularité: {track['popularity']}"
    )


def _classify_batch(
    client, tracks: list[dict], offset: int, system_prompt: str
) -> dict[int, list[str]]:
    listing = "\n".join(_format_track(offset + i, t) for i, t in enumerate(tracks))
    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={
            "effort": config.CLAUDE_EFFORT,
            "format": {"type": "json_schema", "schema": _schema()},
        },
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": f"Classe ces titres :\n\n{listing}"}],
    )

    if response.stop_reason == "refusal":
        raise RuntimeError("Claude a refusé la requête de classification.")

    text = next(b.text for b in response.content if b.type == "text")
    payload = json.loads(text)
    return {
        entry["i"]: [k for k in entry["playlists"] if k in config.LLM_CATEGORIES]
        for entry in payload["results"]
    }


class ClassificationError(RuntimeError):
    """Échec de classification — le résultat serait faux, pas seulement partiel."""


def _client():
    """Construit le client Claude, en échouant tôt si aucune clé n'est résolue."""
    client = anthropic.Anthropic()
    if not (getattr(client, "api_key", None) or getattr(client, "auth_token", None)):
        raise ClassificationError(
            "Aucune clé API Claude trouvée.\n"
            "  export ANTHROPIC_API_KEY=sk-ant-...\n"
            "  (ou `ant auth login`, que le SDK détecte tout seul)\n"
            "Sans elle, seules les règles de décennie s'appliqueraient — "
            "le classement serait faux."
        )
    return client


def classify(
    tracks: list[dict], references: dict[str, list[dict]] | None = None
) -> dict[str, list[str]]:
    """Retourne track_id -> liste des clés de playlists."""
    client = _client()
    system_prompt = _build_system_prompt(references)
    batches = [
        (i, tracks[i : i + config.BATCH_SIZE])
        for i in range(0, len(tracks), config.BATCH_SIZE)
    ]

    for key, examples in (references or {}).items():
        used = min(len(examples), config.MAX_REFERENCE_EXAMPLES)
        note = f" (sur {len(examples)})" if len(examples) > used else ""
        print(f"Référence `{key}` : {used} exemples{note}.")
    lots = f"{len(batches)} lot" + ("s" if len(batches) > 1 else "")
    print(f"Classification de {plural(len(tracks))} en {lots} (tolérance {config.TOLERANCE})…")

    by_index: dict[int, list[str]] = {}
    failures: list[str] = []

    def run(job):
        offset, batch = job
        try:
            result = _classify_batch(client, batch, offset, system_prompt)
            print(f"  lot {offset // config.BATCH_SIZE + 1}/{len(batches)} ✓")
            return result
        except Exception as exc:  # un lot raté ne doit pas tuer les autres
            print(f"  lot {offset // config.BATCH_SIZE + 1} échoué : {exc}")
            failures.append(str(exc))
            return {}

    if batches:
        # Premier lot en solo : il amorce le cache de prompt, les suivants le lisent.
        by_index.update(run(batches[0]))
        if len(batches) > 1:
            with ThreadPoolExecutor(max_workers=config.MAX_CONCURRENCY) as pool:
                for result in pool.map(run, batches[1:]):
                    by_index.update(result)

    # Aucun lot abouti : le classement se réduirait aux décennies. Autant s'arrêter.
    if batches and not by_index:
        raise ClassificationError(
            f"Tous les lots ont échoué ({len(failures)}/{len(batches)}). "
            f"Première erreur :\n  {failures[0] if failures else 'inconnue'}"
        )
    if failures:
        print(f"  {len(failures)}/{len(batches)} lots échoués — titres concernés "
              f"classés par décennie uniquement.")

    assignments: dict[str, list[str]] = {}
    for index, track in enumerate(tracks):
        keys = rule_based(track) + by_index.get(index, [])
        deduped = list(dict.fromkeys(keys))
        # Garantie : aucun titre orphelin.
        if not deduped:
            deduped = ["divers"]
        assignments[track["id"]] = deduped
    return assignments
