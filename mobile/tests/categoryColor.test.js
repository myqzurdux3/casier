/**
 * Jumeau de `tests/test_colors.py` : même table de référence, côté TypeScript.
 *
 * Le contrat est la table, pas un appel croisé entre les deux runtimes. Si
 * l'une des deux implémentations dérive — typiquement sur l'encodage UTF-8,
 * que le TypeScript fait à la main — son test tombe de son côté.
 */

const test = require('node:test');
const assert = require('node:assert');

const { CATEGORY_COLORS, categoryColor } = require('../dist/lib/categoryColor.js');

const ATTENDU = {
  chill: '#8E9BFF',
  vibe: '#E8A33D',
  fete: '#F276B8',
  melancolie: '#7CD98A',
  energie: '#F2795E',
  romance: '#7CD98A',
  'rap-us': '#4FC9B0',
  'rap-uk': '#4FC9B0',
  'rap-fr': '#F276B8',
  pop: '#F2795E',
  rock: '#5CB4F2',
  metal: '#5CB4F2',
  electro: '#F276B8',
  'rnb-soul': '#F276B8',
  'jazz-blues': '#F2795E',
  'reggae-afro': '#F276B8',
  latino: '#7CD98A',
  'country-folk': '#7CD98A',
  'classique-instrumental': '#C68CF5',
  'chanson-francaise': '#F2795E',
  '2010s': '#F276B8',
  '2020s': '#7CD98A',
  'white-girl-music': '#8E9BFF',
  'accentué-é': '#E8A33D',
};

test('chaque clé donne la teinte de la table partagée', () => {
  for (const [cle, teinte] of Object.entries(ATTENDU)) {
    assert.strictEqual(categoryColor(cle), teinte, `clé ${cle}`);
  }
});

test("l'encodage UTF-8 fait main donne le même résultat que Python", () => {
  // Le cas qui distingue une implémentation correcte d'une qui hache les
  // unités UTF-16 : « é » vaut deux octets, pas un.
  assert.strictEqual(categoryColor('accentué-é'), '#E8A33D');
});

test('les paires de substitution sont encodées sur quatre octets', () => {
  // Un emoji hors du plan multilingue de base. On ne vérifie pas une valeur
  // figée mais l'absence de plantage et une teinte valide : la clé n'existe
  // pas dans config.py, elle n'est là que pour couvrir le chemin de code.
  const teinte = categoryColor('casier-\u{1F3B5}');
  assert.ok(CATEGORY_COLORS.includes(teinte));
});

test('la teinte est stable entre deux appels', () => {
  assert.strictEqual(categoryColor('rap-uk'), categoryColor('rap-uk'));
});

test("l'accent d'action n'est pas une teinte de casier", () => {
  assert.ok(!CATEGORY_COLORS.includes('#D7E63B'));
});
