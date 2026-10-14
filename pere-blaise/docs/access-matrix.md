# Matrice d'accès et refus

| Ressource | Hermes | Broker | Motif et refus attendu |
| --- | --- | --- | --- |
| `Downloads` | Aucun montage | Métadonnées, hash, backup, retrait de source après copie vérifiée | Hors racine, lien symbolique et fichier changé refusés |
| `Documents` | Aucun montage | Dossiers/noms locaux ; lecture d'octets pour hash de rapprochement et envoi ; nouvelles cibles de plan | Existant jamais remplacé/supprimé ; seul `a_trier` créé |
| Backups | Aucun montage | Écriture/vérification, restauration ; aucune purge automatique | Chemin hors racine refusé |
| SQLite | Volume Hermes natif privé | Volume broker natif privé | Aucun volume partagé entre agents ; sauvegarde SQLite API |
| Secrets | OAuth dans volume Hermes | Tokens Telegram/Slack et clé interne en fichiers privés montés ro | Valeurs absentes des logs/Git ; aucune clé API OpenAI |
| Réseau | API modèle et API interne | API interne et plateformes | Aucun port public ; allowlist egress par domaine non encore prouvée |
| Canaux | Aucun token de canal | Allowlist Telegram privé et Slack canal privé | Autre utilisateur/canal et DM Slack refusés |
| Outils | Aucun toolset sur la surface API | Interface déterministe sans commande libre | `/v1/toolsets` : zéro activé sur image test |
