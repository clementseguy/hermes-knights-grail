# Matrice d'accès et refus

| Ressource | Hermes | Broker | Motif et refus attendu |
| --- | --- | --- | --- |
| `Downloads` | Aucun montage | Métadonnées, hash, backup, retrait de source après copie vérifiée | Hors racine, lien symbolique et fichier changé refusés |
| `Documents` | Aucun montage | Dossiers/noms locaux ; lecture d'octets pour envoi ; nouvelles cibles de plan | Existant jamais remplacé/supprimé ; seul `a_trier` créé ; rapprochement d'apprentissage désactivé |
| Backups | Aucun montage | Écriture/vérification, restauration ; aucune purge automatique | Chemin hors racine refusé |
| SQLite | Volume Hermes natif privé | Volume broker natif privé | Aucun volume partagé entre agents ; sauvegarde SQLite API |
| Secrets | OAuth dans volume Hermes | Tokens Telegram/Slack et clé interne en fichiers privés montés ro | Valeurs absentes des logs/Git ; aucune clé API OpenAI |
| Réseau | API modèle et API interne | API interne et plateformes | Aucun port public ; pas de filtrage sortant par domaine (exception README) |
| Canaux | Aucun token de canal | Allowlist Telegram privé et Slack canal privé | Autre utilisateur/canal et DM Slack refusés |
| Outils | Aucun toolset sur la surface API | Interface déterministe sans commande libre | `/v1/toolsets` : zéro activé sur image test |

Inspection du 14 octobre 2026 sur la composition d'essai : le broker tourne avec `10000:10000`. Dans l'image Hermes épinglée, le processus principal `hermes` tourne en UID 10000, tandis que le superviseur `s6-svscan` et un processus Python de supervision tournent en UID 0. Le conteneur n'est pas lancé avec `privileged`, possède `no-new-privileges`, n'a ni socket Docker ni montage métier, et ne publie aucun port. Cette présence d'un superviseur root fait partie de l'image Hermes épinglée ; elle doit être réévaluée lors d'une mise à jour de l'image, sans modifier le cœur Hermes pour cet agent.
