# Demandes au développeur NexTarget-app

Yvain ne modifie jamais ce dépôt. Cette liste sert de demandes prêtes à
transmettre lorsque la conversion d'un brouillon en recette `ready` le justifie.

## Fournir l'artefact à recetter pour NT-140, NT-141, NT-148 et le smoke NT-057

La branche `feature/NT-168-automated-qa` apporte les identifiants `qa.*` et
les fixtures Coach DEBUG nécessaires aux premiers flux.

**Demande :** fournir un APK `DEBUG` produit depuis le commit à recetter, avec
son SHA Git et son hash SHA-256. Yvain l'installera sur l'émulateur puis
exécutera les brouillons Maestro avant de les déclarer `ready`. Cela évite à
Yvain de lancer une construction qui pourrait modifier des fichiers générés du
dépôt applicatif, hors de son autorité.

## Demande future : fixtures locales de sessions et d'exercices

**But :** recetter NT-025, NT-026, NT-027, NT-142 à NT-147 et NT-151 à
NT-155 sans données manuelles.

**Demande :** exposer, uniquement en build `DEBUG`, une action ou un contrat
de fixtures versionné qui, après remise à zéro de l'application, crée :

- des exercices personnels de difficulté absente, débutant, avancé et expert ;
- une session prévue et des sessions réalisées couvrant plusieurs armes,
  calibres, catégories, scores, groupements et ex æquo ;
- les références nécessaires aux parcours de duplication et d'aide au
  groupement.

**Contraintes :** contenu déterministe, pas de compte ni appel réseau,
identifiants `Semantics.identifier` `qa.*` pour l'action DEBUG et les éléments
que Maestro doit cibler ; aucune inclusion dans un build release.
