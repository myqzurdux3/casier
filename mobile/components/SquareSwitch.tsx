/**
 * Interrupteur carré.
 *
 * Le `Switch` de React Native rend le composant Material d'Android : pastille
 * ronde, ombre, animation propre au système. Il jurait avec le reste, où tout
 * est à angles vifs et où le rayon ne dépasse jamais 4.
 */

import { Pressable, View } from 'react-native';

import { colors } from '@/lib/theme';

const LARGEUR = 44;
const HAUTEUR = 26;
const PASTILLE = 20;
const MARGE = (HAUTEUR - PASTILLE) / 2;

export function SquareSwitch({
  value,
  onValueChange,
  disabled,
}: {
  value: boolean;
  onValueChange: (next: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="switch"
      accessibilityState={{ checked: value, disabled: Boolean(disabled) }}
      disabled={disabled}
      onPress={() => onValueChange(!value)}
      style={{
        width: LARGEUR,
        height: HAUTEUR,
        borderRadius: 3,
        borderWidth: 1,
        borderColor: value ? colors.accent : colors.border,
        backgroundColor: value ? colors.accent : 'transparent',
        justifyContent: 'center',
        opacity: disabled ? 0.4 : 1,
      }}
    >
      <View
        style={{
          width: PASTILLE,
          height: PASTILLE,
          borderRadius: 2,
          backgroundColor: value ? colors.onAccent : colors.faint,
          marginLeft: value ? LARGEUR - PASTILLE - MARGE - 2 : MARGE,
        }}
      />
    </Pressable>
  );
}
