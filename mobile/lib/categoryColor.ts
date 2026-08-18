/**
 * Une teinte stable par casier.
 *
 * La couleur vient de la **clé** de catégorie (`rap-uk`, `2010s`…), jamais du
 * nom affiché : les clés de `spotify_sort/config.py` ne bougent pas, donc la
 * couleur d'un casier ne bouge pas non plus, même si la playlist est renommée.
 *
 * `spotify_sort/colors.py` tient la même fonction pour le panel web, et
 * `tests/test_colors.py` / `tests/categoryColor.test.js` vérifient des deux
 * côtés la même table de clés réelles.
 */

/** Huit teintes à luminosité constante. Le jaune-vert manque volontairement :
 *  il appartient à l'accent d'action, qui veut dire « on peut appuyer ». */
export const CATEGORY_COLORS = [
  '#F2795E', '#E8A33D', '#7CD98A', '#4FC9B0',
  '#5CB4F2', '#8E9BFF', '#C68CF5', '#F276B8',
] as const;

/**
 * Octets UTF-8 d'une chaîne.
 *
 * Écrit à la main plutôt qu'avec `TextEncoder` : le runtime d'Expo installe
 * `TextDecoder` et `TextEncoderStream`, mais pas `TextEncoder`. Node l'a en
 * global et TypeScript le déclare dans ses types, donc ni les tests ni le
 * typecheck ne verraient l'absence — seul le téléphone planterait.
 */
function utf8Bytes(text: string): number[] {
  const bytes: number[] = [];
  for (let i = 0; i < text.length; i += 1) {
    let point = text.charCodeAt(i);
    // Paire de substitution : recomposer le point de code avant de l'encoder.
    if (point >= 0xd800 && point <= 0xdbff && i + 1 < text.length) {
      const bas = text.charCodeAt(i + 1);
      if (bas >= 0xdc00 && bas <= 0xdfff) {
        point = (point - 0xd800) * 0x400 + (bas - 0xdc00) + 0x10000;
        i += 1;
      }
    }
    if (point < 0x80) {
      bytes.push(point);
    } else if (point < 0x800) {
      bytes.push(0xc0 | (point >> 6), 0x80 | (point & 0x3f));
    } else if (point < 0x10000) {
      bytes.push(0xe0 | (point >> 12), 0x80 | ((point >> 6) & 0x3f), 0x80 | (point & 0x3f));
    } else {
      bytes.push(
        0xf0 | (point >> 18),
        0x80 | ((point >> 12) & 0x3f),
        0x80 | ((point >> 6) & 0x3f),
        0x80 | (point & 0x3f)
      );
    }
  }
  return bytes;
}

/** FNV-1a 32 bits. Doit donner exactement le même résultat qu'en Python. */
function hash(key: string): number {
  let h = 0x811c9dc5;
  for (const b of utf8Bytes(key)) {
    h ^= b;
    // imul garde la multiplication sur 32 bits ; `>>> 0` la ramène non signée.
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h;
}

export function categoryColor(key: string): string {
  return CATEGORY_COLORS[hash(key) % CATEGORY_COLORS.length];
}
