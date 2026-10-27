# Grille de recette éditoriale (T-STYLE et T-CRIT)

Clément décide si chaque brouillon est « utilisable après révision ». Le seuil des spécifications est **au moins 4 sur 5**. L'agent ne peut pas s'attribuer cette note. Consigner pour chaque dossier l'identifiant, le lien consulté, la version évaluée, la date, le verdict et les motifs ; ne pas déduire la qualité des impressions ou réactions LinkedIn.

| Dossier | Sujet distinct | Identifiant / source | État |
| --- | --- | --- | --- |
| 1 | Sécurité des agents IA et « Lethal Trifecta » | `silex-bleu` / article Martin Fowler du 15 octobre | Post et prompt disponibles ; jugement de Clément attendu. |
| 2 | Politique zero trust appliquée aux agents | `citadelle-agentique` / même source, angle distinct | Reprise demandée ; juger aussi si l'angle diffère réellement du dossier 1. |
| 3 | Productivité des équipes techniques et coût de contrôle | Intention et article à choisir avec Clément | À produire. |
| 4 | Gouvernance des données et responsabilité DSI | Intention et article à choisir avec Clément | À produire. |
| 5 | Arbitrage entre autonomie, observabilité et coût d'exploitation | Intention et article à choisir avec Clément | À produire. |

Pour chaque version, noter séparément :

| Critère | À examiner | Résultat |
| --- | --- | --- |
| Accroche | Fait, scène ou contradiction concrète ; dialogue seulement s'il sert le sujet ; aucune réplique copiée | Oui / à revoir + motif |
| Déroulé | Fait déclencheur → lecture trop simple corrigée → conséquence concrète → pas de recul ; progression lisible sans plan plaqué | Oui / à revoir + motif |
| Ton et lexique | Ironie parfois mordante, registre familier quand utile, verbes et objets concrets, vocabulaire technique juste ; aucune expression marketing ou expérience terrain inventée | Oui / à revoir + motif |
| Raisonnement | Thèse défendable, objection CTO/DSI concrète ou enjeu humain et collectif pertinent, décision ou question précise pour la direction | Oui / à revoir + motif |
| Nuance | Faits, opinion et analyse séparés ; limites et incertitudes visibles ; aucun chiffre inventé | Oui / à revoir + motif |
| Utilité | Post copiable, moins de 3 000 unités UTF-16, prompt d'image distinct et exploitable | Oui / à revoir + motif |
| Chute | Conséquence de décision, vérification qui tranche, question précise ou invitation à lire la source ; pas de slogan ou d'appel générique aux commentaires | Oui / à revoir + motif |
| Verdict | « utilisable après révision » ou « non utilisable », avec la correction prioritaire explicite | À renseigner par Clément |

Le rapport de `editorial_review` contient `voice_check`, une vérification LLM séparée du travail de rédaction. Elle peut bloquer l'enregistrement d'une nouvelle version, mais elle ne remplace pas le verdict de Clément pour T-STYLE. Les brouillons historiques sont évalués comme références de départ ; ne pas les écraser pour faire monter artificiellement le score.

T-CRIT exige en plus deux articles de qualité différente. Pour chaque article, consulter la note enregistrée (`editorial_get`) et vérifier que thèse, preuves, limites, objection technique et impact dirigeant ont réellement influencé le post. Le dossier 1 satisfait la présence de ces champs, sans jugement éditorial indépendant ; le second article reste à choisir et à tester.
