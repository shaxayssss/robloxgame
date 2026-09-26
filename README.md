# 🤖 Studio d'agents Roblox — Guide d'utilisation

Une équipe d'agents IA spécialisés pour développer des jeux Roblox à fort
potentiel (+1M joueurs), pilotée depuis Claude Code.

## 🗂️ Ce qui a été créé

```
.
├── CLAUDE.md                        ← Source de vérité du projet (vision, règles)
├── README.md                        ← Ce guide
└── .claude/
    ├── agents/                      ← 14 agents spécialisés
    │   ├── lead.md                  ← Chef d'orchestre (point d'entrée)
    │   ├── gameplay.md              ← Mécaniques de jeu
    │   ├── gui.md                   ← UI/UX
    │   ├── map.md                   ← Level design / environnement
    │   ├── data.md                  ← DataStore / persistance / économie
    │   ├── networking.md            ← Client/serveur / réplication
    │   ├── art.md                   ← Assets / animation / VFX / sons
    │   ├── monetization.md          ← Monétisation / équilibrage
    │   ├── performance.md           ← Optimisation
    │   ├── security.md              ← Anti-cheat / durcissement
    │   ├── qa.md                    ← Revue de code / tests
    │   ├── onboarding.md            ← Tutoriel / rétention
    │   ├── localization.md          ← i18n / traduction
    │   └── analytics.md             ← Télémétrie / live-ops
    └── skills/                      ← 10 packs de connaissances
        ├── luau-best-practices/
        ├── roblox-api-reference/
        ├── client-server-architecture/
        ├── datastore-patterns/
        ├── performance-optimization/
        ├── monetization-economy/
        ├── retention-engagement/
        ├── security-hardening/
        ├── map-reference-analysis/
        └── higgsfield-3d-assets/
```

## 🚀 Comment l'utiliser

### 1. Parler au chef d'orchestre

Dans Claude Code, lance simplement ta demande. L'agent `lead` découpe et délègue :

```
Je veux un système de double saut + un inventaire + une map de forêt.
```

### 2. Appeler un agent directement

Préfixe avec `@` pour cibler un spécialiste :

```
@performance  Optimise ma map, elle lag sur mobile.
@security     Audite mon système d'achat de devises.
@gui          Crée le menu principal responsive.
```

### 3. Consulter un skill

Les agents chargent automatiquement les skills pertinents. Tu peux aussi demander
explicitement :

```
Utilise le skill datastore-patterns pour implémenter la sauvegarde.
```

## 🧭 Le flux de travail type

```
Toi → lead (découpe) → agents spécialisés (implémentent)
                     → qa (vérifie) → lead (intègre + synthèse) → Toi
```

## 🎯 Conseils pour viser le +1M joueurs

1. **Performance d'abord** — un jeu qui lag perd ses joueurs. Teste sur mobile.
2. **Sécurité par défaut** — jamais de confiance au client.
3. **Fiabilité des données** — aucune perte de progression.
4. **Rétention avant monétisation** — fidélise, puis monétise.
5. **Itère par la donnée** — mesure (analytics), corrige, re-mesure.

## ⚙️ Personnalisation

- Mets à jour `CLAUDE.md` avec ton type de jeu et tes décisions d'architecture.
- Ajoute des agents si besoin (ex. un agent `sound-design` dédié).
- Ajuste le `model` de chaque agent (`opus` pour le lead, `sonnet` pour les autres,
  `haiku` pour les tâches simples) selon ton budget.
