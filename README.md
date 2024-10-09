# Transcription et Rédaction d'Email Automatisée

Ce projet utilise Python 3.9 pour réaliser la transcription d'audio et la rédaction automatique d'emails.

## Comment ça fonctionne ?

1. **Téléchargement ou Enregistrement d'Audio** :
   - Téléchargez une vidéo ou un fichier audio pour générer une transcription automatique en quelques secondes.
   - Vous pouvez également enregistrer votre audio en cliquant sur le bouton "Commencer l'enregistrement". Une fois l'enregistrement terminé, cliquez à nouveau pour lancer la génération automatique de la transcription.

2. **Analyse et Résumé** :
   - Une fois la transcription générée, appuyez sur "Analyser et résumer". Le système générera un résumé concis et des éléments clés.

3. **Rédaction et Envoi d'Email** :
   - Un email professionnel est rédigé automatiquement à partir du résumé.
   - Remplissez les champs destinataires et objet, puis ajustez l'email selon vos préférences.
   - Appuyez sur "Envoyer l'email" pour envoyer directement l'email.

## Technologies Utilisées :
- **Python 3.9** : Langage de programmation principal du projet.
- **Whisper** : Modèle de transcription automatique basé sur l'IA, implémenté sur Groq pour une performance accrue.
- **OpenAI** : API pour la génération de texte et la compréhension du langage naturel, utilisé pour résumer le contenu transcrit et rédiger l'email.

## Fonctionnalités :
- **Transcription Audio** : Le système transcrit l'audio en texte grâce à Whisper.
- **Résumé de Texte** : OpenAI résume le texte transcrit en un format concis.
- **Rédaction d'Email** : OpenAI rédige un email professionnel basé sur le résumé du contenu transcrit.

## Installation :
1. Assurez-vous que Python 3.9 est installé.
2. Installez les packages requis à l'aide de :
   ```bash
   pip install -r requirements.txt
3. Créez un fichier .env à la racine du projet et ajoutez les clés suivantes :
   ```bash
   API_KEY="votre_clé_openai"
   GROQ_API="votre_clé_groq"
   SECRET_KEY="votre_clé_secrète"
   MAIL_SERVER="smtp.votre_fournisseur.com"
   MAIL_PORT=587
   MAIL_USERNAME="votre_email"
   MAIL_PASSWORD="votre_mot"
   MAIL_DEFAULT_SENDER="votre_email"

## Utilisation :
1. Exécutez le script main.py.
2. Sélectionnez le fichier audio à transcrire ou utilisez l'option d'enregistrement direct.
3. Le système transcrira l'audio, générera un résumé et rédigera un email.
4. Modifiez l'email généré avant de l'envoyer.


## Démonstration Vidéo :
https://github.com/user-attachments/assets/f65df275-c2fb-4e84-8642-a5ef98e4e63e

