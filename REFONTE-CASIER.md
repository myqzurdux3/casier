# Refonte « Casier » — consigne d'implémentation

À coller dans Claude Code à la racine du dépôt. **Refonte visuelle uniquement : aucun changement de comportement, d'API, de schéma de job ou de logique de classification.** Un commit par section.

Stack réelle : app mobile Expo / React Native (`mobile/`, expo-router, styles dans `mobile/lib/theme.ts`) + panel web Flask (`templates/`, `static/style.css`). Le vert `#1db954` et le nom « spotify-sort » sont présents dans les deux : les deux doivent suivre.

---

## 0. Renommage — lire avant d'agir

Nom retenu : **Casier**.

À changer :
- `mobile/app.config.js` → `expo.name: 'Casier'` (c'est le label affiché sous l'icône).
- Titres d'écran dans `mobile/app/(tabs)/_layout.tsx`, textes UI, `templates/base.html` (`nav .brand`), `README.md`, en-têtes du panel.
- Toute mention de « spotify-sort » visible par l'utilisateur, y compris le texte « partage un titre depuis Spotify vers spotify-sort » dans `mobile/app/(tabs)/track.tsx`.

**À ne pas changer sans y penser à deux fois** (ça casse l'installation existante et l'OAuth) :
- `expo.slug`, `expo.scheme` (`spotifysort`) et `android.package` (`fr.spotifysort.app`). Changer le package = nouvelle app, réinstallation, nouveau versionCode ; changer le scheme = redirect URI à re-déclarer côté Spotify et côté `BASE_URL`. Garde-les tels quels : ce sont des identifiants techniques que personne ne voit.
- Le fichier keystore et son nom.

Le mot « Spotify » reste uniquement dans les libellés qui décrivent le service tiers (« Compte Spotify lié », « Relit la bibliothèque Spotify »). Il disparaît du nom, de l'icône et de la couleur d'accent — c'est une marque déposée et leurs Developer Terms l'interdisent comme identité d'app.

---

## 1. Thème mobile — `mobile/lib/theme.ts`

Remplace le bloc `colors` par :

```ts
export const colors = {
  bg: '#1B1D20',
  surface: '#23262A',
  border: '#33373C',
  text: '#F2F3F4',
  muted: '#8E959C',
  faint: '#6E757C',
  accent: '#D7E63B',
  onAccent: '#1B1D20',
  error: '#F2795E',
  warn: '#E8A33D',
  ok: '#D7E63B',
};
```

Règles de style à propager dans `styles` :
- `card` → devient une **section** : plus de `borderRadius: 12`, plus de `backgroundColor` ; `borderTopWidth: 1, borderColor: colors.border`, `paddingVertical: 16`. Le fond reste `colors.bg` partout. Rayon maximum dans toute l'app : **4**.
- `content` → `padding: 0`, `paddingHorizontal: 20` géré par les sections, `gap: 0`.
- `title` → 26, `fontWeight: '700'`, `letterSpacing: -0.6`.
- `heading` → 20, `fontWeight: '700'`, `letterSpacing: -0.4`.
- `text` → 15.5. `muted` → 12.5.
- Ajoute `label` : `fontFamily: 'monospace', fontSize: 10.5, letterSpacing: 1.2, color: colors.muted` + les textes correspondants passés en `toUpperCase()` dans le JSX (RN n'applique `textTransform` que sur `Text`, utilise `textTransform: 'uppercase'` dans le style).
- Ajoute `metric` : `fontFamily: 'monospace', fontSize: 34, color: colors.text, letterSpacing: -1`.
- `button` → `borderRadius: 4`, `backgroundColor: colors.accent`, `paddingVertical: 15`, texte `colors.onAccent`, `fontWeight: '700'`. `buttonText` : plus de `#04170c`.
- `buttonGhost` → à supprimer de l'usage courant : les tâches secondaires deviennent des lignes de liste (voir §4).
- `input` → `borderRadius: 4`, `fontFamily: 'monospace'`, `fontSize: 12.5`.
- `banner` → `borderRadius: 4`, `borderLeftWidth: 1` (pas de barre d'accent épaisse à gauche).
- `bannerStyle` : fonds `{ error: '#2A1C19', warn: '#2A2418', ok: '#242A15' }`, bordures inchangées dans leur rôle.
- Supprime les couleurs littérales `'#30d158'`, `'#ffd60a'`, `'#1db954'`, `'#fff'` de `dashboard.tsx`, `result.tsx`, `track.tsx`, `settings.tsx`, `job.tsx`, `Feedback.tsx` : tout passe par `colors`. Grep `#1db954` et `#` en général doit ne plus rien retourner hors `theme.ts` et `categoryColor.ts`.

Typographie : garde la fonte système (Roboto) pour l'UI — n'ajoute pas `expo-font`. Tous les **nombres, états et libellés techniques** passent en `fontFamily: 'monospace'` : c'est ce qui donne l'alignement des colonnes de chiffres, ne compte pas sur `fontVariant: ['tabular-nums']` (support Android inégal).

---

## 2. Une couleur par casier — nouveau `mobile/lib/categoryColor.ts`

Huit teintes à luminosité constante. La bande jaune-vert est volontairement absente : elle appartient à l'accent d'action.

```ts
export const CATEGORY_COLORS = [
  '#F2795E', '#E8A33D', '#7CD98A', '#4FC9B0',
  '#5CB4F2', '#8E9BFF', '#C68CF5', '#F276B8',
] as const;

/** FNV-1a 32 bits sur les octets UTF-8 — doit donner le même résultat qu'en Python. */
function hash(key: string): number {
  const bytes = new TextEncoder().encode(key);
  let h = 0x811c9dc5;
  for (const b of bytes) {
    h ^= b;
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h;
}

export function categoryColor(key: string): string {
  return CATEGORY_COLORS[hash(key) % CATEGORY_COLORS.length];
}
```

La couleur est dérivée de la **clé** de catégorie (`rap-uk`, `white-girl-music`, `2010s`…), pas du nom affiché : les clés de `spotify_sort/config.py` sont stables, donc la couleur d'un casier ne bougera jamais, même si tu renommes la playlist ou en ajoutes vingt. Ne mets pas de cache, ne persiste rien côté mobile.

Côté serveur, ajoute `spotify_sort/colors.py` avec la même fonction pour que le panel web affiche exactement les mêmes teintes :

```python
CATEGORY_COLORS = [
    "#F2795E", "#E8A33D", "#7CD98A", "#4FC9B0",
    "#5CB4F2", "#8E9BFF", "#C68CF5", "#F276B8",
]

def category_color(key: str) -> str:
    h = 0x811C9DC5
    for b in key.encode("utf-8"):
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return CATEGORY_COLORS[h % len(CATEGORY_COLORS)]
```

Expose-la comme filtre Jinja (`app.jinja_env.filters["category_color"]`) dans `webapp.py`. Ajoute un test qui vérifie que Python et TS donnent le même index pour une dizaine de clés réelles.

Optionnel, si tu veux pouvoir corriger une teinte à la main plus tard : `apply_settings` accepte un champ `color` par catégorie dans `settings.json` et il prime sur le hash. Ne l'expose pas encore dans l'UI.

### Deux rôles de couleur qui ne se croisent jamais

- `colors.accent` (`#D7E63B`) veut dire **« on peut appuyer »** : bouton d'action principale, onglet actif, état OK. Rien d'autre.
- Les huit teintes veulent dire **« appartenance à un casier »**. Elles apparaissent uniquement :
  1. en **carré plein 12×12, rayon 0**, devant chaque nom de casier, dans toutes les listes ;
  2. en **soulignement de 3px** sous le titre d'une section de casier (écran Résultat) ;
  3. en **rangée de carrés 8×8** en fin de ligne de titre, un par autre casier auquel le titre appartient (maximum 4, puis `+n` en mono) ;
  4. en **contour + couleur de texte** de la puce de filtre active.

Jamais en fond de bouton, jamais en fond de bloc, jamais comme couleur de texte courant. Le carré reprend la forme du logo, c'est le lien visuel entre l'icône et la donnée.

---

## 3. Onglets — `mobile/app/(tabs)/_layout.tsx`

Supprime les emoji (`🏠🎵📋⚙️`). L'icône devient un carré de 16×16, rayon 2 : rempli en `colors.accent` si actif, contour 2px `colors.faint` sinon — un `<View>`, pas de dépendance de fonte d'icônes.

- `tabBarLabelStyle` : `fontFamily: 'monospace', fontSize: 10, letterSpacing: 0.8, textTransform: 'uppercase'`.
- Libellés : `Casier` / `Titre` / `Tri` / `Réglages`. Titres d'écran (`title`) : `Casier`, `Titre à l'unité`, `Tri`, `Réglages`.
- `headerStyle` : fond `colors.bg` (plus de `colors.card`), pas d'ombre (`elevation: 0`, `borderBottomWidth: 1`, `borderBottomColor: colors.border`).
- `tabBarStyle` : fond `#16181A`, `borderTopColor: colors.border`.

---

## 4. Écran Accueil — `mobile/app/(tabs)/dashboard.tsx`

Ordre imposé, de haut en bas :

1. **Métriques** en grille 2 colonnes séparées par des filets 1px : `status.liked_count` et `status.playlist_count`, chiffre en `styles.metric` au-dessus d'un libellé `styles.label` (`TITRES EN CACHE`, `CASIERS`). `v{status.version}` en mono discret dans l'en-tête.
2. **Puces d'état** rectangulaires (rayon 2, padding 4/8, mono 10.5 capitales) : `COMPTE LIÉ` pleine en accent si `spotify_ready`, sinon contour `colors.warn` et libellé `COMPTE NON LIÉ` ; idem `CLÉ CLAUDE OK`. Plus de coches `✓/✗` colorées en texte.
3. **Une seule action pleine** : `Trier`, avec son coût estimé en sous-titre (`{n} titres · ~{estimation} s`, calculée depuis `liked_count` et `BATCH_SIZE`, sans nouvel appel réseau). Si un job est en cours, cette carte devient « suivre le job en cours ».
4. **Derniers casiers remplis** : 4 lignes cliquables (carré de couleur + nom + compteur en mono) qui poussent vers l'onglet Tri. Lit `getResult()` déjà exposé ; si aucun résultat, cette section n'apparaît pas.
5. **Tâches secondaires** : les 5 autres entrées de `ACTIONS` deviennent des lignes de liste de 44px minimum — libellé 16, `hint` en `styles.label` sous le libellé, chevron `▸` en `colors.faint` à droite. Plus de `buttonGhost` empilés.
6. **Déconnexion** : ligne de liste discrète en bas, texte `colors.muted`.

---

## 5. Écran Tri — `mobile/app/(tabs)/result.tsx`

- En-tête : `Tri` + `{n} casiers · {m} titres` en mono à droite.
- Bandeau de puces de filtre horizontalement scrollable, une par casier : carré 8×8 de la teinte + nom + compteur en mono. La puce active prend le contour et la couleur de texte de sa teinte.
- Les cartes de playlist deviennent des sections : carré 12×12 + nom en `heading` **souligné de 3px de sa teinte** + `{n} TITRES` en mono à droite.
- Lignes de titre : index `01`, `02`… en mono `colors.faint` (largeur fixe 20), titre 15.5, artistes 12.5 `colors.muted` en dessous, puis la rangée de carrés 8×8 des autres casiers du titre (calculée depuis `document.playlists`, max 4 puis `+n`). Garde l'appui long pour retirer, mais remplace le texte « appui long » de chaque ligne par une seule mention en `styles.label` sous l'en-tête de section — répété 114 fois c'est du bruit.
- Le texte d'aide (« Le retrait ne touche que le classement local… ») passe en `styles.muted` sous l'en-tête, sans encadré.

---

## 6. Écran Titre — `mobile/app/(tabs)/track.tsx`

- Section de saisie : aide en `styles.label`, champ en mono, interrupteur « Ajouter réellement » **carré** (44×26, rayon 3, pastille carrée 20×20 rayon 2 — un `Pressable` custom, pas le `Switch` Material), puis le bouton plein `Classer`.
- Résultat : nom du titre en `heading`, `{artistes} · {année} · {n} CASIERS` en mono capitales, puis une ligne par casier — carré 12×12 de la teinte + nom + `AJOUTÉ` en mono `colors.accent` à droite.

---

## 7. Écran Réglages — `mobile/app/(tabs)/settings.tsx`

- Tolérance : un segmenté de deux moitiés dans un cadre 1px rayon 4, moitié active pleine en accent, texte `colors.onAccent` — pas deux boutons côte à côte.
- Préfixe / Publiques : lignes de liste, interrupteur carré comme en §6.
- Les groupes (Moods, Genres, Catégories spéciales) deviennent des sections à filet, chaque catégorie affichée avec son **carré de couleur** aligné sur la première ligne de texte, nom 15.5, description 12.5 `colors.muted`, compteur en mono à droite si disponible.
- La mention « appui long pour supprimer » remonte une seule fois en `styles.label` dans l'en-tête de groupe, avec le compteur de catégories.

---

## 8. Panel web — `static/style.css` + `templates/`

Aligne le panel sur le même thème, il sert de référence à l'app :

```css
:root {
  --bg: #1B1D20;
  --card: #23262A;
  --line: #33373C;
  --text: #F2F3F4;
  --muted: #8E959C;
  --faint: #6E757C;
  --accent: #D7E63B;
  --on-accent: #1B1D20;
  --danger: #F2795E;
  --warn: #E8A33D;
}
```

- `.card` → rayon 4, `border-top: 1px solid var(--line)` et fond `var(--bg)` pour les sections de contenu ; garde un fond `--card` uniquement pour les blocs de formulaire.
- `button` → `color: var(--on-accent)`, rayon 4. `nav .brand` → `color: var(--text)` avec le carré du logo en `--accent` à côté, pas un mot vert.
- Ajoute `.swatch { width: 12px; height: 12px; display: inline-block; flex: none; }` et utilise-la dans `templates/settings.html`, `result.html` et `track.html` via le filtre `category_color`.
- Tous les nombres et libellés d'état en `ui-monospace, SFMono-Regular, Menlo, monospace`, `font-variant-numeric: tabular-nums`.
- Le nom de casier dans `result.html` reçoit `border-bottom: 3px solid` de sa teinte.

---

## 9. Icône et splash

Le mark : carré `#23262A` rayon 14 (soit 22 % du côté), grille 2×2 de carrés avec 4 px de gouttière sur 64 — trois carrés en contour 2px `#6E757C`, le quatrième (en bas à gauche) plein `#D7E63B`.

- Réécris `mobile/tools/make-icons.py` pour dessiner ce mark et régénérer `assets/icon.png` (1024), `assets/adaptive-icon.png` (foreground 1024 avec la marge de sécurité de 25 %) et `assets/splash-icon.png`.
- `app.config.js` : `android.adaptiveIcon.backgroundColor` et le `backgroundColor` du splash passent à `#1B1D20`. `userInterfaceStyle` reste `dark`.
- Regénère : `npx expo prebuild --clean` puis build.

---

## 10. Vérification

- `grep -rn "1db954\|30d158\|ffd60a\|121212\|1c1c1e" mobile/ static/ templates/` ne retourne rien.
- Aucune couleur littérale hors `mobile/lib/theme.ts`, `mobile/lib/categoryColor.ts`, `static/style.css`, `spotify_sort/colors.py`.
- `npx tsc --noEmit` et les tests (`pytest`, `mobile/tests`) passent inchangés — la refonte ne touche à aucune signature.
- Sur un écran : un seul bouton plein visible, un seul élément en jaune acide par écran hors onglet actif.
