import { Tabs } from 'expo-router';
import { View } from 'react-native';

import { useI18n } from '@/lib/i18n';
import { colors } from '@/lib/theme';

/**
 * Icône d'onglet : un carré, plein quand l'onglet est actif, en contour sinon.
 *
 * Un `<View>` et non un glyphe : ça évite une dépendance à une fonte d'icônes,
 * et le carré reprend la forme du logo — c'est le lien visuel entre l'icône de
 * l'app et les casiers.
 */
function TabSquare({ focused }: { focused: boolean }) {
  return (
    <View
      style={{
        width: 16,
        height: 16,
        borderRadius: 2,
        backgroundColor: focused ? colors.accent : 'transparent',
        borderWidth: focused ? 0 : 2,
        borderColor: colors.faint,
      }}
    />
  );
}

const icon = ({ focused }: { focused: boolean }) => <TabSquare focused={focused} />;

export default function TabsLayout() {
  const { t } = useI18n();
  return (
    <Tabs
      screenOptions={{
        headerStyle: {
          backgroundColor: colors.bg,
          borderBottomWidth: 1,
          borderBottomColor: colors.border,
          // Un filet net plutôt que l'ombre portée d'Android.
          elevation: 0,
        },
        headerShadowVisible: false,
        headerTintColor: colors.text,
        tabBarStyle: { backgroundColor: colors.chrome, borderTopColor: colors.border },
        tabBarLabelStyle: {
          fontFamily: 'monospace',
          fontSize: 10,
          letterSpacing: 0.8,
          textTransform: 'uppercase',
        },
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.muted,
        sceneStyle: { backgroundColor: colors.bg },
      }}
    >
      {/* `dashboard` et non `index` : `app/index.tsx` occupe déjà « / » comme
          écran d'aiguillage. Deux routes pour le même chemin ne se résolvent pas. */}
      <Tabs.Screen
        name="dashboard"
        options={{ title: t('onglet.casier'), tabBarLabel: t('onglet.casier'), tabBarIcon: icon }}
      />
      <Tabs.Screen
        name="track"
        options={{ title: t('ecran.titre_unite'), tabBarLabel: t('onglet.titre'), tabBarIcon: icon }}
      />
      <Tabs.Screen
        name="result"
        options={{ title: t('onglet.tri'), tabBarLabel: t('onglet.tri'), tabBarIcon: icon }}
      />
      <Tabs.Screen
        name="settings"
        options={{ title: t('onglet.reglages'), tabBarLabel: t('onglet.reglages'), tabBarIcon: icon }}
      />
    </Tabs>
  );
}
