# Matrice d’accès

| Ressource | Droits | Justification | Refus prouvé |
| --- | --- | --- | --- |
| Downloads | métadonnées, lecture lors de copie vérifiée | inventaire et classement | hors racine/symlinks refusés |
| Documents | métadonnées ; écriture uniquement `range` | cible validée | contenu non lu, hors plan refusé |
| Quarantaine | écriture d’originaux appliqués | retour arrière | aucune purge automatique |
| SQLite | lecture/écriture locale privée | plans/apprentissages | propriétaire de plan imposé |
| Telegram/Slack | réseau sortant, allowlists | commandes déterministes | utilisateur/canal refusé |
| API locale 8643 | hôte → loopback | proposition seulement | aucune écoute publique |
| Docker | planificateur isolé | modèle sans fichiers | pas de socket/montage personnel |
| LaunchAgents | lancement local | continuité | aucun endpoint réseau |
