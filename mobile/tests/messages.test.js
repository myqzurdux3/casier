/**
 * Catalogue de l'interface : complétude, substitution, détection de langue.
 *
 * Jumeau de `tests/test_i18n.py`. Les deux catalogues sont distincts — chacun
 * traduit ce qu'il produit — sauf les verdicts de classement, que le serveur
 * envoie sous forme de clés et que le client rend lisibles. Ce recouvrement est
 * vérifié explicitement plus bas : une clé de verdict oubliée ici afficherait
 * `verdict.added` brut sur le téléphone.
 */

const test = require('node:test');
const assert = require('node:assert');

const { MESSAGES, translate, detectLang } = require('../dist/lib/messages.js');

const LANGUES = ['fr', 'en'];

/** Noms entre accolades d'un gabarit : `{name}` -> `name`. */
function champs(texte) {
  return new Set([...texte.matchAll(/\{(\w+)\}/g)].map((m) => m[1]));
}

test('chaque clé existe dans toutes les langues', () => {
  for (const [cle, entree] of Object.entries(MESSAGES)) {
    for (const langue of LANGUES) {
      assert.ok(entree[langue], `${cle} manque en ${langue}`);
    }
  }
});

test('les champs à substituer sont les mêmes dans toutes les langues', () => {
  for (const [cle, entree] of Object.entries(MESSAGES)) {
    const attendus = champs(entree.fr);
    for (const langue of LANGUES) {
      if (!entree[langue]) continue;
      assert.deepStrictEqual(
        [...champs(entree[langue])].sort(),
        [...attendus].sort(),
        `${cle} en ${langue}`
      );
    }
  }
});

test('les verdicts du serveur ont tous leur traduction', () => {
  // Doit suivre `spotify_sort/service.py`. Une clé ajoutée là-bas sans être
  // ajoutée ici s'afficherait brute.
  for (const verdict of ['proposed', 'added', 'already_present', 'playlist_missing', 'failed']) {
    assert.ok(MESSAGES[`verdict.${verdict}`], `verdict.${verdict} absent`);
  }
  assert.ok(MESSAGES['verdict.liked_songs']);
});

test('les tâches secondaires ont libellé et aide', () => {
  for (const action of ['fetch', 'import', 'sync-likes', 'reference', 'doctor']) {
    assert.ok(MESSAGES[`tache.${action}`], `tache.${action}`);
    assert.ok(MESSAGES[`tache.${action}.aide`], `tache.${action}.aide`);
  }
});

test('la substitution remplace les paramètres fournis', () => {
  assert.strictEqual(translate('verdict.failed', 'en', { detail: '403' }), 'failed — 403');
  assert.strictEqual(translate('verdict.failed', 'fr', { detail: '403' }), 'échec — 403');
});

test('un paramètre absent laisse le gabarit intact plutôt que « undefined »', () => {
  assert.strictEqual(translate('verdict.failed', 'en', {}), 'failed — {detail}');
});

test('une clé inconnue est rendue telle quelle', () => {
  assert.strictEqual(translate('rien.du.tout', 'en'), 'rien.du.tout');
});

test('la détection de langue ne lève jamais et rend une langue connue', () => {
  // Le vrai risque n'est pas la valeur mais l'exception : si le moteur JS ne
  // fournissait pas Intl, une erreur ici planterait l'app au démarrage.
  assert.ok(LANGUES.includes(detectLang()));
});
