# Chevaliers du Graal (Knights of the Grail)

Projet personnel consacré à la conception, la configuration et l'exploitation
d'agents Hermes.

Ce dépôt rassemble les sources versionnées des agents, leurs politiques, leurs
prompts, leurs scripts d'exploitation et leurs tests. Chaque agent reste
indépendant : son runtime, sa mémoire, ses journaux et ses secrets sont locaux
et ne sont pas versionnés.

## Agents

- **Père Blaise** : assistant personnel local pour proposer puis appliquer,
  après validation, le classement de fichiers et leur envoi depuis un périmètre
  défini.
- **Léodagan** : agent de veille qui prépare des posts sourcées, sans publication automatique.
- **Yvain** : agent de recette pour les parcours mobiles et les rapports de
  validation associés.

## Organisation

- `AGENTS.md` définit les conventions communes de conception, d'isolation et
  d'exploitation.
- `docs/` contient les documents partagés, notamment la checklist de création
  d'un agent.
- Chaque dossier d'agent contient sa documentation et les éléments nécessaires
  à son fonctionnement.

## Principes

Les agents utilisent des environnements isolés, des configurations explicites
et des permissions limitées à leur mission. Les actions externes ou
irréversibles restent soumises à validation humaine, sauf exception documentée.

Ce dépôt est en évolution continue.
