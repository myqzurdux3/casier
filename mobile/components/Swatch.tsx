/**
 * Carré de couleur d'un casier.
 *
 * Toujours un carré à angles vifs : c'est la forme du logo, et c'est le seul
 * endroit où les huit teintes de `categoryColor` ont le droit d'apparaître en
 * aplat. Le jaune de l'accent, lui, veut dire « on peut appuyer » — les deux
 * vocabulaires ne se croisent jamais.
 */

import { View } from 'react-native';

import { categoryColor } from '@/lib/categoryColor';

export function Swatch({ keyName, size = 12 }: { keyName: string; size?: number }) {
  return (
    <View
      style={{
        width: size,
        height: size,
        backgroundColor: categoryColor(keyName),
        flexShrink: 0,
      }}
    />
  );
}
