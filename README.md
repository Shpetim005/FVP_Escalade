# FVP_Escalade 🏁

Application de paris mutuels pour la Course de l'Escalade à Genève.

## Description

Application web permettant de parier entre amis sur le vainqueur de la Course de l'Escalade qui a lieu chaque année le 6 décembre à Genève. L'application utilise un système de paris mutuels où les gains sont redistribués aux gagnants selon les mises totales.

## Fonctionnalités

- **👥 Gestion des participants** : Ajout et suppression des coureurs
- **💸 Système de paris** : Les utilisateurs peuvent placer des paris sur leurs favoris
- **📊 Calcul des cotes** : Affichage des cotes en temps réel basées sur les paris
- **🏆 Résultats** : Déclaration du vainqueur et calcul automatique des gains
- **⚙️ Paramètres configurables** : Date de la course et commission (rake) ajustables

## Installation

1. Cloner le dépôt :
```bash
git clone https://github.com/Shpetim005/FVP_Escalade.git
cd FVP_Escalade
```

2. Installer les dépendances :
```bash
pip install -r requirements.txt
```

## Utilisation

Lancer l'application avec Streamlit :
```bash
streamlit run FVP_Escalade.py
```

L'application s'ouvrira automatiquement dans votre navigateur par défaut.

## Comment ça marche ?

### Pari mutuel
Le système de pari mutuel fonctionne comme suit :
1. Tous les paris sont mis dans un pot commun (pool)
2. Une commission (rake) est prélevée sur le pool total
3. Le montant net est redistribué aux gagnants proportionnellement à leurs mises
4. Chaque gagnant reçoit : `(sa mise / total des mises gagnantes) × pool net`

### Formule de la cote
```
Cote = (Pool net après commission) ÷ (Total des mises sur ce participant)
```

### Calcul du gain
```
Gain = Mise × Cote
```

## Exemple d'utilisation

1. **Ajouter des participants** dans l'onglet "👥 Participants"
2. **Placer des paris** dans l'onglet "💸 Paris"
3. **Consulter les cotes** dans l'onglet "📊 Cotes"
4. **Déclarer le vainqueur** dans l'onglet "🏆 Résultats" une fois la course terminée

## Technologies utilisées

- **Streamlit** : Framework pour l'interface web
- **Pandas** : Manipulation et analyse des données
- **NumPy** : Calculs numériques

## Configuration

Dans la barre latérale, vous pouvez configurer :
- **Date de la course** : Par défaut le 6 décembre de l'année en cours
- **Commission (%)** : Pourcentage prélevé sur le pool (par défaut 5%)

## Licence

Ce projet est un outil de paris amical pour la Course de l'Escalade à Genève.