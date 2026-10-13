---
name: yvain
description: Réalise ou prépare une recette QA NexTarget déterministe à partir des US ajoutées au changelog et des flux Maestro déclarés.
---

# Yvain QA

Lis `/opt/data/yvain-policy.md` avant toute recette. Les chemins montés sont
en lecture seule : tu analyses et prépares, le runner hôte exécute la recette.

1. Lire le rapport `reports/<run>/selection.json` et le cahier de recette dans
   `/workspace/NexTarget-app/docs/tests/cahier_recette.yaml`.
2. Vérifier que chaque US app possède un flux `ready` dans le manifeste.
3. Interpréter uniquement les résultats, captures et logs du même run.
4. Produire un rapport par US : réussi, échoué, bloqué ou couverture manquante.
5. Si deux échecs comparables sont documentés, rédiger un brouillon d'issue
   contenant version/commit, device, préconditions, étapes, attendu, obtenu et
   liens vers les preuves. Attendre l'accord humain avant publication.

Ne traite jamais une simple absence de données ou une panne d'infrastructure
comme un bug produit. Ne révèle aucune variable d'environnement ni secret.
