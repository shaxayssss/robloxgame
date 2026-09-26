---
name: feedback-verification
description: Mesurer et prouver plutot qu'affirmer ; verifier son propre travail
metadata:
  type: feedback
---

Ne jamais annoncer qu'une chose fonctionne sans l'avoir mesuree. Produire le
chiffre ou le rendu qui le prouve.

**Why:** plusieurs bugs n'ont ete trouves que parce qu'on a inspecte la sortie au
lieu de la supposer correcte — des `bounds` inverses par la conversion d'axes qui
auraient fait echouer silencieusement tout test d'appartenance, un trou de 12
studs entre deux zones, un z-fighting invisible dans le code mais flagrant au
rendu. Il valide sans discuter quand le chiffre est la.

**How to apply:** apres un script de generation, re-importer la sortie et mesurer
(dimensions, polycount, bornes). Apres une modification visuelle, faire un rendu
et le regarder. Integrer les controles dans le script quand c'est possible : la
verification du budget triangles tourne a chaque execution de `build_map.py`.
