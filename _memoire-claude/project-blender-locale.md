---
name: project-blender-locale
description: Blender tourne en francais sur cette machine, les noms de nodes et sockets sont traduits
metadata:
  type: project
---

Blender 5.2 est installe en **francais** sur cette machine. Le noeud Principled
s'appelle `BSDF guidee`, et **les noms de sockets sont traduits aussi**.

**Why:** un script qui faisait `nodes.get("Principled BSDF")` a plante chez lui
alors qu'il marchait en ligne de commande — parce que `read_factory_settings()`
remettait l'interface en anglais et masquait le probleme. Une heure perdue a
chercher ailleurs.

**How to apply:** dans tout script Blender, acceder aux noeuds par **type**
(`node.type == "BSDF_PRINCIPLED"`) et aux sockets par **identifier**, jamais par
nom. `KaijuHeist/blender/build_map.py` expose `find_node()` et `find_socket()`
pour ca — les reutiliser.

Corollaire : ne pas appeler `read_factory_settings()` dans un script destine a
tourner depuis l'editeur de texte de Blender ; il invalide le contexte et fait
echouer l'export glTF ensuite. Vider la scene manuellement.
