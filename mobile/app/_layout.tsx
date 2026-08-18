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
import { colors } from '@/lib/theme';

export default function RootLayout() {
  return (
    <AuthProvider>
      <SafeAreaProvider>
        <StatusBar style="light" />
        <Stack
          screenOptions={{
            headerStyle: { backgroundColor: colors.bg },
            headerTintColor: colors.text,
            contentStyle: { backgroundColor: colors.bg },
          }}
        >
          <Stack.Screen name="index" options={{ headerShown: false }} />
          <Stack.Screen name="login" options={{ title: 'Connexion' }} />
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          <Stack.Screen name="job" options={{ title: 'Progression' }} />
        </Stack>
      </SafeAreaProvider>
    </AuthProvider>
  );
}
