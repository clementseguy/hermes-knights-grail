# Traçabilité F-001…F-018 — état au 14 octobre 2026

« Local passé » désigne les 36 tests `unittest` sur arbres temporaires. « Docker partiel » désigne le test de transaction du broker, le démarrage de Hermes isolé, les healthchecks `healthy`, le contrôle API/volumes ; cela ne valide aucun canal réel. « Non vérifié » reste un blocage avant mise en service.

| ID | Réalisation | Test / résultat |
| --- | --- | --- |
| F-001 | `telegram_gateway.py`, `slack_gateway.py`, `broker.py` | `test_apply_backups_and_owner` local passé ; refus E2E par canal non vérifié |
| F-002 | `scanner.py`, `planning.py`, `workflow.py` | `test_analysis_minimizes_data_and_does_not_move` local passé |
| F-003 | `broker.py`, `telegram_gateway.py` | `test_apply_backups_and_owner` local passé ; détail exhaustif E2E non vérifié |
| F-004 | `store.py`, `broker.py`, `workflow.py` | `test_plan_expiry_and_invalidation`, `test_changed_download_and_directory_invalidate` locaux passés ; horloge/redémarrage réel partiels |
| F-005 | `contracts.py`, `store.py` | IDs à deux mots dans plans locaux passés ; collision sous charge non vérifiée |
| F-006 | `executor.py`, `broker.py` | `test_apply_backups_and_owner` local passé ; aucune voie libre depuis le modèle |
| F-007 | `executor.py` | `test_apply_backups_and_owner`, `test_rollback_after_first_move`, `test_backup_space_refusal_precedes_first_movement` locaux passés ; espace insuffisant Docker non vérifié |
| F-008 | `executor.py` | `test_rollback_after_first_move`, `test_recovery_after_interrupted_move`, `test_recovery_blocks_concurrent_edit`, `test_hard_process_crash_and_restart` locaux passés ; coupure électrique réelle non vérifiée |
| F-009 | `planning.py`, `executor.py` | `test_proposal_requires_complete_and_existing_directory`, `test_unknown_matching_target_is_never_removed` locaux passés ; broker UID 10000 et `/root` refusé sous Docker ; matrice de permissions complète non vérifiée |
| F-010 | `planning.py`, `executor.py` | `test_a_trier_hash_after_rename_and_duplicate` local passé ; sous-dossiers absents refusés en validation |
| F-011 | `file_delivery.py`, `telegram_gateway.py`, `slack_gateway.py` | `test_send_zero_one_many_and_symlink`, `test_send_choice_owner_and_revalidation`, `test_send_one_passes_only_selected_bytes`, `test_slack_native_upload_uses_only_original_thread` locaux passés ; uploads natifs E2E non vérifiés |
| F-012 | `planning.py`, `file_delivery.py`, `config/planner.config.yaml` | Contexte local minimisé passé ; Hermes API testée à zéro toolset ; test de fuite E2E non vérifié |
| F-013 | `store.py` | `test_a_trier_hash_after_rename_and_duplicate` et `test_learning_duplicate_hash_remains_pending` locaux passés ; édition à ajouter |
| F-014 | `store.py`, `scripts/learning-admin.py` | `test_operator_learning_correction_and_erasure` local passé ; procédure opérateur Docker non vérifiée en E2E |
| F-015 | `scheduler.py`, `app.py` | `test_scheduler_and_channel_failure`, `test_weekly_notifies_both_before_analysis_without_range` locaux passés, DST été/hiver simulé ; tâche réelle et notifications E2E non vérifiées ; désactivée |
| F-016 | `_user_error` dans `telegram_gateway.py`, journal `executor.py` | Codes stables partiels ; corrélation/logs et catalogue complet non couverts |
| F-017 | `store.py`, `executor.py`, `scripts/state-backup.py`, `scripts/volume-backup.sh`, `compose.yaml` | reprise de journal avant mouvement, après premier mouvement et après commit, backup/restauration SQLite locale passés, deux volumes Docker natifs et healthchecks `healthy` ; sauvegarde/restauration chiffrée de volume/OAuth non vérifiée (`age` absent) |
| F-018 | `infra/slack/app-manifest.json`, `docs/runbook.md` | bot/app existants préservés ; audit scopes, token, unique consommateur et E2E réels non vérifiés |

## Commandes réellement exécutées

```text
python3 -m unittest discover -s pere-blaise/tests -v      36 tests OK
PB_... docker compose -f pere-blaise/compose.yaml config --quiet   OK avec chemins temporaires
docker image inspect nousresearch/hermes-agent@sha256:9774...   digest présent
docker run --rm --entrypoint hermes <digest> --version   v0.21.6/upstream 818c13be
docker build -f Dockerfile.broker -t pere-blaise-broker:test .   OK
docker run --rm --read-only --user 10000:10000 ... pere-blaise-broker:test python /fixture/check.py   APPLIED et backup vérifié
docker run ... <digest> gateway run   démarrage test OK
GET /v1/toolsets avec clé   zéro toolset activé
GET /v1/toolsets sans clé   HTTP 401
docker inspect ... .Mounts   /opt/data de type volume ; conteneur et volume de test supprimés
docker compose -p pb-compose-test-20261014 ... up -d --build   Hermes/broker healthy, secrets factices
docker exec pb-broker-compose-test-20261014 python -c ...   APPLIED et backup vérifié sur montages /tmp
docker exec ... uid/montages   UID 10000, /root refusé, Hermes sans /downloads ni /documents
docker compose -p pb-compose-test-20261014 ... down -v   volumes éphémères supprimés
scripts/lifecycle.sh install --dry-run --budget-kib 2048   aperçu seulement, 231165 octets sous budget
scripts/lifecycle.sh uninstall --dry-run ; purge --dry-run   chemins/volumes/tailles affichés, aucune suppression
scripts/lifecycle.sh backup|restore --path ... --dry-run   périmètre affiché, aucun flux chiffré exécuté
```

`PYTHONPYCACHEPREFIX=/tmp/pb-pycache python3 -m compileall -q pere-blaise/src pere-blaise/scripts` et `bash -n` : passés. Un premier `compileall` sans ce préfixe avait échoué à écrire dans le cache Python macOS hors workspace (restriction de sandbox).

## Recette encore nécessaire

- Vrais comptes de test Telegram/Slack, OAuth Codex, modèle/quotas, permissions macOS de Docker Desktop ; aucun token réel n'a été fourni ici.
- `docker compose up` avec comptes de test réels, E2E des deux canaux, test de taille native et injection des défaillances réseau. La composition avec secrets factices est passée et a été retirée.
- Coupure de processus à chaque phase de journal, disque plein, source/cible concurrentes, backup SQLite puis restauration réelle, changement de digest et retour arrière de schéma.
- Exécution et vérification sur volumes de test du flux `volume-backup.sh` avec `age` (absent sur cette machine), puis revue des scripts de désinstallation/purge ; allowlist réseau sortante vérifiée ; contrôles de rétention ; revue finale du propriétaire.
