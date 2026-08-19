/**
 * Écran d'entrée : aiguille vers la connexion ou le tableau de bord.
 *
 * La redirection est déclarative (`<Redirect>`) et non impérative : appeler
 * `router.replace` avant que le navigateur soit monté lève « Attempted to
 * navigate before mounting the Root Layout ».
 */

import { Redirect } from 'expo-router';
import { View } from 'react-native';

import { Loading } from '@/components/Feedback';
import { useAuth } from '@/lib/auth';
import { useI18n } from '@/lib/i18n';
import { styles } from '@/lib/theme';

export default function Index() {
  const { ready, signedIn } = useAuth();
  const { t } = useI18n();

  if (!ready) {
    return (
      <View style={[styles.screen, { justifyContent: 'center' }]}>
        <Loading label={t('commun.ouverture')} />
      </View>
    );
  }

  return <Redirect href={signedIn ? '/dashboard' : '/login'} />;
}
