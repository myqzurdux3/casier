/**
 * Racine de l'app.
 *
 * Rend `<Stack>` dès le premier rendu et ne le démonte jamais : Expo Router
 * exige un navigateur en permanence à la racine. Substituer un écran d'attente
 * le temps de relire le jeton faisait boucler React — « Maximum update depth
 * exceeded » dans SceneView — et l'app se fermait au lancement.
 *
 * L'état d'authentification vit donc dans un contexte, et c'est `app/index.tsx`
 * — un écran, donc monté après le navigateur — qui redirige.
 */

import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { AuthProvider } from '@/lib/auth';
import { I18nProvider, useI18n } from '@/lib/i18n';
import { colors } from '@/lib/theme';

/** Séparé de la racine pour pouvoir appeler `useI18n`, qui exige d'être sous
 *  le fournisseur. */
function Navigateur() {
  const { t } = useI18n();
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: colors.bg },
        headerTintColor: colors.text,
        contentStyle: { backgroundColor: colors.bg },
      }}
    >
      <Stack.Screen name="index" options={{ headerShown: false }} />
      <Stack.Screen name="login" options={{ title: t('ecran.connexion') }} />
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen name="job" options={{ title: t('ecran.progression') }} />
    </Stack>
  );
}

export default function RootLayout() {
  return (
    <I18nProvider>
      <AuthProvider>
        <SafeAreaProvider>
          <StatusBar style="light" />
          <Navigateur />
        </SafeAreaProvider>
      </AuthProvider>
    </I18nProvider>
  );
}
