# Yvain — passage de MVP à PROD ready

Cette liste est ordonnée par priorité. Ne pas commencer l'étape suivante tant
que les critères de sortie de l'étape courante ne sont pas remplis.

> **Limite de responsabilité :** Yvain peut démarrer et utiliser le staging
> existant, mais ne modifie jamais `NexTarget-server` ni 'Nextarget-app'. 
> Toute évolution de ces projets (fixtures, reset, API ou Docker) est 
> demandée au développeur du serveur ; Yvain décrit le besoin et vérifie 
> ensuite le résultat.

## P0 — Rendre la recette `dev → main` complète et fiable

- [x] Produire le backlog des US présentes dans `origin/main...dev` qui n'ont
  pas de recette : critères d'acceptation, écran/parcours concerné, données
  nécessaires et dépendance serveur éventuelle.
- [ ] Pour chaque US `app` ou `app+server`, écrire un flux Maestro dans
  `qa/flows/`, l'exécuter sur l'émulateur, puis l'ajouter à
  `qa/manifest.json` avec le statut `ready`. La matrice initiale est dans
  `qa/coverage.md` ; le brouillon NT-141/NT-148 a confirmé le besoin de
  sélecteurs `Semantics` stables avant validation.
- [x] Déclarer explicitement chaque US strictement serveur comme
  `out_of_scope`, avec sa justification dans le manifeste ou le rapport.
- [x] Ajouter une matrice de couverture lisible : `NT-XXX → flux Maestro →
  données de recette → preuves`.
- [ ] Vérifier que `bash scripts/run-recipe.sh origin/main dev true` ne
  signale plus aucune couverture manquante pour les US dans le périmètre app.
  Le gate de PR est maintenant explicite : `scripts/run-pr-gate.sh`
  compare toujours `origin/dev → branche` avec `enforce=true`. Le rapport
  `dev → main` reste non bloquant via `scripts/run-release-report.sh` jusqu'à
  extinction de la dette historique.

**Critère de sortie :** une recette complète de `dev → main` est possible ;
toute US app/app+server est recettée par au moins un flux Maestro réellement
exécuté, et toute US serveur est explicitement exclue.

## P1 — Rendre les scénarios déterministes

- [ ] Étendre les fixtures de recette déterministes, privées et non publiées
  à chaque parcours qui en a besoin. La première fixture locale Flutter est
  disponible en `DEBUG` pour le Coach (date, contenu et pseudo-aléa fixes) ;
  le reset complet est assuré par `adb pm clear`. Les fixtures catalogue
  serveur `qa-catalog-precision-001` et `qa-catalog-inactive-001` sont aussi
  disponibles.
- [x] Ajouter une remise à zéro complète et explicite du staging : données,
  comptes et état applicatif nécessaire aux scénarios.
  La base SQLite staging est recréée et ses fixtures sont réinstallées avant
  chaque recette Yvain.
- [ ] Ajouter des réponses réseau contrôlables pour les scénarios d'erreur
  pertinents : indisponibilité, erreurs 4xx/5xx et latence.
- [x] Ajouter des identifiants `Semantics` stables aux premiers éléments
  Flutter à tester (`qa.settings.*`, `qa.debug.seed_coach_fixtures`). Tout
  nouveau flux Maestro doit ajouter son identifiant si un sélecteur textuel ou
  visuel serait fragile.
- [ ] Ajouter au moins un parcours `app+server` qui démontre qu'une requête de
  l'APK atteint le staging local, et non seulement que le `dart-define` est
  présent lors de la compilation.

**Critère de sortie :** chaque scénario peut être rejoué à l'identique après
reset, sur un émulateur propre, sans dépendre de données manuelles persistantes.

## P2 — Consolider le runner et les preuves

- [ ] Éviter les reconstructions inutiles de l'APK ou du staging pendant un
  même run.
- [ ] Ajouter un pré-vol : espace disque, AVD disponible, `adb` prêt, staging
  sain, APK installable et version de l'outillage connue.
- [ ] Produire un rapport Markdown par run et par US : statut, critères
  couverts, environnement, étapes, liens vers preuves et blocages.
- [ ] Conserver systématiquement JUnit, captures et logcat ; ajouter une
  vidéo lorsqu'elle apporte une preuve utile.
- [ ] Tester le runner après redémarrage du Mac, de Docker Desktop et de
  l'émulateur.

**Critère de sortie :** un échec ou un succès est compréhensible et
reproductible depuis le seul dossier de rapport.

## P3 — Mettre Yvain à disposition de l'équipe

- [ ] Choisir et configurer un canal de discussion distant pour Yvain
  (Mattermost si l'équipe l'utilise déjà, sinon Slack).
- [ ] Exposer des commandes explicites : recette `dev → main`, recette d'une
  `NT-XXX`, génération des scénarios manquants et état du dernier run.
- [ ] Donner à l'agent les accès lecture nécessaires aux dépôts et un accès
  strictement contrôlé au runner macOS hôte.
- [ ] Documenter l'installation et l'exploitation depuis un second poste.

**Critère de sortie :** un membre de l'équipe peut demander une recette ou
consulter son résultat sans se connecter au Mac de recette.

## P4 — Déclenchement GitHub et traitement des anomalies

- [ ] Configurer le déclenchement lors des PR `feature/* → dev` et `dev → main`.
- [ ] Définir la règle d'échec bloquant et le statut `bloqué`.
- [ ] Rejouer automatiquement un échec après reset avant de le déclarer
  reproductible.
- [ ] Rechercher les issues GitHub similaires avant création.
- [ ] Créer les issues reproductibles avec les labels `automated-qa` et `bug`,
  les étapes, attendu/obtenu, version APK, appareil et preuves.
- [ ] Démarrer avec validation humaine des créations d'issues, puis passer à
  la création directe après une période de fiabilisation.

**Critère de sortie :** une PR reçoit un verdict de recette exploitable et les
anomalies reproductibles sont suivies sans bruit ni doublons.

## P5 — Validation de préparation production

- [ ] Introduire volontairement une anomalie connue et vérifier qu'Yvain la
  détecte, conserve les preuves et prépare un ticket conforme.
- [ ] Réaliser une recette complète sur un second poste ou après restauration
  du poste de recette.
- [ ] Faire relire la documentation d'exploitation par une personne qui n'a
  pas construit Yvain.
- [ ] Valider que les secrets de production ne sont accessibles ni à
  l'émulateur, ni au staging, ni au conteneur Hermes.

**Critère de sortie :** Yvain peut être considéré `PROD ready` lorsque P0 à
P4 sont cochées et que cette validation finale a réussi.

## P6 — Parcours connectés, seulement lorsque la couverture hors ligne est stable

- [ ] Demander au développeur de `NexTarget-server` la mise à disposition de
  comptes et d'un mécanisme OAuth de recette dédiés.
- [ ] Ajouter les scénarios authentifiés seulement après validation de ce
  dispositif : consentement, erreurs réseau, Coach et catalogue distant.

**Critère de sortie :** les parcours connectés disposent de comptes isolés,
de données réinitialisables et d'aucun contournement local d'authentification.
