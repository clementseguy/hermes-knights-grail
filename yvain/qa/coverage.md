# Matrice de couverture `origin/main...dev`

Générée à partir des identifiants ajoutés à `CHANGELOG.md` et du cahier de
recette de NexTarget-app. Un scénario n'est marqué **ready** qu'après une
exécution Maestro réussie sur l'AVD de recette.

| US | Portée | Référence fonctionnelle | Flux QA à automatiser | Préconditions | État |
| --- | --- | --- | --- | --- | --- |
| NT-025 | app | Difficulté des exercices | Créer, filtrer, dupliquer puis exporter/importer un exercice | Jeu d'exercices | À écrire |
| NT-026 | app | Suppression d'exercice | Refus si lié, annulation puis suppression autorisée | Exercices liés et non liés | À écrire |
| NT-027 | app | Duplication d'exercice | Dupliquer, modifier, annuler puis enregistrer une copie | Exercice complet | À écrire |
| NT-056 | app | Erreurs réseau | Auth, profil et Coach : retry, reconnexion et absence de fuite technique | Stub réseau contrôlé | Bloqué par P1 |
| NT-057 | app technique | Non-régression UI | Smoke Sessions, Statistiques, Exercices, Objectifs et Paramètres | Aucune | Brouillon : navigation minimale |
| NT-059 | app technique | Exports déterministes | Enregistrer, annuler, importer et contrôler l'erreur d'écriture | Faux sélecteur + fichier | Partiel : NT-149 |
| NT-077 | app technique | Schéma Hive | Vérificateur de schéma et cas de dérive | Cas CLI déterministes | Hors Maestro : preuve CLI à intégrer |
| NT-140 | app | Démarrage | Démarrage froid, onboarding et destination sans splash Flutter | Variantes d'état local | Brouillon : premier lancement |
| NT-141 | app | Ordre Paramètres | Parcours vertical des cinq sections dans les deux thèmes | Données locales | Brouillon : IDs `qa.settings.*` |
| NT-142 | app | Tirs par arme | Contrôler la carte dans Synthèse, pas Avancé | Sessions avec armes | À écrire |
| NT-143 | app | Duplication de session | Copier détaillée et libre, annuler, enregistrer et vérifier indépendance | Sessions complètes + photo | Bloqué par fixtures |
| NT-144 | documentation | Backlog | Vérification documentaire, pas de parcours mobile | — | Preuve documentaire à intégrer |
| NT-145 | app | Navigation depuis records | Ouvrir score/groupement, retour, suppression et ex æquo | Sessions de statistiques | Bloqué par fixtures |
| NT-146 | app | Aide groupement | Ouvrir/fermer l'aide dans les deux parcours | Session guidée + prévue | À écrire |
| NT-147 | app | Ordre des répartitions | Contrôler les trois cartes et l'état vide | Sessions catégorisées | Bloqué par fixtures |
| NT-148 | app | Séparateurs préférences | Contrôler ordre et séparateurs dans les deux thèmes | Aucune | Brouillon : partagé avec NT-141 |
| NT-149 | app | Nom d'export | Enregistrement et partage Android du JSON | Aucune | **ready** |
| NT-150 | app | État Auth | Migration, hors ligne, retry, invalidation et reconnexion | Fixtures Secure Storage + serveur | Bloqué par P1 |
| NT-151 | app | Cartes d'exercice | Variantes Stand/Maison, données minimales/complètes et session prévue | Exercices + session prévue | Bloqué par fixtures |
| NT-152 | app + server | Exercice principal unique | Création/édition, import historique et requête Coach | Sauvegarde historique + stub | Bloqué par fixtures |
| NT-153 | app | Consentement Coach | Consentement, refus de requête et retrait | Endpoint d'observation | Bloqué par P1 |
| NT-154 | app | Qualification session prévue | Saisie facultative, persistance et session sans exercice | Session prévue avec exercice | Bloqué par fixtures |
| NT-155 | app | Niveau Coach local | Migration, persistance hors ligne et absence volontaire | État Hive historique | Bloqué par fixtures |
| NT-156 | app + server | Débrief Coach | Consentement, requête, idempotence et rendu du débrief | Compte + staging contrôlé | Bloqué par P1 |
| NT-159 | app + server | Provenance exercice | Création, import/export et contrat de provenance | Fixture d'exercice | Bloqué par fixtures |
| NT-160 | app + server | Catalogue Coach ciblé | Téléchargement DEBUG, cache et lecture seule | Fixture staging active | Bloqué par P1 |
| NT-161 | app + server | Exercice personnel | Débrief borné sans écriture catalogue | Compte + staging contrôlé | Bloqué par P1 |

## Décisions de périmètre

- Aucune US exclusivement serveur n'est présente dans ce diff : aucune n'est
  donc exclue au titre du périmètre serveur.
- NT-077 et NT-144 n'ont pas de comportement mobile nouveau à piloter ; leur
  preuve devra être intégrée au rapport comme contrôle CLI/documentaire, sans
  les faire passer abusivement pour une recette UI.
- Les US `app technique` conservent un smoke mobile lorsque le changement peut
  affecter des parcours existants ; leurs contrôles techniques restent des
  preuves complémentaires.

## Ordre de conversion en flux exécutables

1. NT-140, NT-141, NT-148 et NT-057 : aucun compte ni fixture serveur.
2. NT-025, NT-026, NT-027, NT-142, NT-146, NT-147, NT-151 et NT-154 : après
   fixtures locales.
3. NT-143, NT-145, NT-152, NT-155 et NT-159 : après fixtures/migrations
   historiques contrôlées.
4. NT-056, NT-150, NT-153, NT-156, NT-160 et NT-161 : après contrats réseau,
   comptes et fixtures de staging.
