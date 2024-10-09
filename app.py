from flask import Flask, render_template, request, jsonify
import os
from werkzeug.utils import secure_filename
import openai
from groq import Groq
from moviepy.editor import VideoFileClip
from dotenv import load_dotenv
import tempfile
from flask_cors import CORS

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor


# Charger les variables d'environnement
load_dotenv()
app = Flask(__name__)
CORS(app, supports_credentials=True)

# Configuration de la session
app.config['SESSION_TYPE'] = 'filesystem'




# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'votre_clé_secrète_par_défaut')
app.config['UPLOAD_FOLDER'] = os.path.join(tempfile.gettempdir(), 'transcription_uploads')
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

print("MAIL_SERVER:", app.config['MAIL_SERVER'])
print("MAIL_PORT:", app.config['MAIL_PORT'])
print("MAIL_USERNAME:", app.config['MAIL_USERNAME'])

Session(app)


os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialisation des clients API
openai.api_key = os.getenv('API_KEY')
groq_client = Groq(api_key=os.getenv('GROQ_API'))

# Pool d'exécution pour gérer plusieurs requêtes simultanément
executor = ThreadPoolExecutor(max_workers=3)

# Dictionnaire pour stocker les tâches en cours
active_tasks = {}


# Extensions de fichiers autorisées
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'mp4', 'avi', 'mov'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_file(file):
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    return filepath

def extract_audio_from_video(video_path, audio_path):
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(audio_path)
    return audio_path

def process_audio(input_filepath, user_id):
    try:
        audio_filepath = input_filepath
        # Si c'est une vidéo, extraire l'audio
        if input_filepath.lower().endswith(('.mp4', '.avi', '.mov')):
            audio_filepath = os.path.join(os.path.dirname(input_filepath), f'audio_{user_id}.mp3')
            extract_audio_from_video(input_filepath, audio_filepath)

        # Transcrire l'audio
        transcription_text = transcribe_audio(audio_filepath)
        
        return transcription_text
    finally:
        # Nettoyer les fichiers
        cleanup_files(input_filepath)
        if audio_filepath != input_filepath:
            cleanup_files(audio_filepath)


def cleanup_files(*filepaths):
    for filepath in filepaths:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            app.logger.error(f"Erreur lors du nettoyage du fichier {filepath}: {e}")

def transcribe_audio(filepath):
    try:
        with open(filepath, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                file=(os.path.basename(filepath), audio_file.read()),
                model="whisper-large-v3",
                response_format="verbose_json",
                temperature=0.0
            )
        
        # Formater la transcription en texte
        segments = []
        for segment in transcription.segments:
            start_time = segment.get('start', 0)
            end_time = segment.get('end', 0)
            text = segment.get('text', '')
            segments.append(f"[{start_time:.2f} - {end_time:.2f}] {text}")
        
        return "\n".join(segments)
    except Exception as e:
        app.logger.error(f"Erreur lors de la transcription : {e}")
        raise

def generate_summary(text):
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """Vous êtes un assistant spécialisé dans l'analyse et le résumé de transcriptions.
                 Fournissez un résumé concis suivi d'une liste d'éléments clés.
                 Format de réponse :
                 [Résumé en un paragraphe]

                 Éléments clés:
                 • Point clé 1
                 • Point clé 2
                 [etc.]"""},
                {"role": "user", "content": f"Analysez et résumez la transcription suivante :\n\n{text}"}
            ],
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        app.logger.error(f"Erreur lors de la génération du résumé : {e}")
        raise

def generate_email_report(summary, key_elements):
    try:
        # Préparer le prompt pour l'API OpenAI
        prompt = f"""
        Vous êtes un assistant qui aide à rédiger des emails professionnels pour des rendez-vous immobiliers. 

        Basé sur le résumé suivant et les éléments clés, rédigez un email de suivi professionnel pour le client :

        Résumé :
        {summary}

        Éléments clés :
        {key_elements}

        L'email doit être poli, clair et adapté au contexte immobilier.
        """

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Vous êtes un assistant d'email professionnel."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        app.logger.error(f"Erreur lors de la génération du rapport d'email : {e}")
        raise


@app.route('/')
def index():
    return render_template('transcription.html')


@app.route('/get-session-id', methods=['GET'])
def get_session_id():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return jsonify({'session_id': session['user_id']})

@app.route('/transcription', methods=['POST'])
def transcription():
    user_id = session.get('user_id', str(uuid.uuid4()))
    if 'audio_file' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni'}), 400
    
    file = request.files['audio_file']
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Type de fichier non autorisé'}), 400

    try:
        # Créer un dossier unique pour l'utilisateur
        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], user_id)
        os.makedirs(user_folder, exist_ok=True)

        # Sauvegarder le fichier
        input_filepath = os.path.join(user_folder, secure_filename(file.filename))
        file.save(input_filepath)
        
        # Lancer la transcription de manière asynchrone
        future = executor.submit(process_audio, input_filepath, user_id)
        active_tasks[user_id] = future
        
        return jsonify({
            'task_id': user_id,
            'status': 'processing'
        })

    except Exception as e:
        app.logger.error(f"Erreur lors du traitement pour l'utilisateur {user_id}: {e}")
        return jsonify({'error': str(e)}), 500



@app.route('/check-transcription', methods=['GET'])
def check_transcription():
    user_id = session.get('user_id')
    if not user_id or user_id not in active_tasks:
        return jsonify({'status': 'not_found'})

    future = active_tasks[user_id]
    if future.done():
        try:
            result = future.result()
            del active_tasks[user_id]
            return jsonify({
                'status': 'completed',
                'transcription': result
            })
        except Exception as e:
            del active_tasks[user_id]
            return jsonify({
                'status': 'error',
                'error': str(e)
            })
    return jsonify({'status': 'processing'})



@app.route('/summarize', methods=['POST'])
def summarize():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Session invalide'}), 401

    data = request.get_json()
    if not data or 'transcription_text' not in data:
        return jsonify({'error': 'Aucun texte de transcription fourni'}), 400

    transcription_text = data['transcription_text']
    
    try:
        # Générer le résumé et les éléments clés
        summary = generate_summary(transcription_text)
        
        # Séparer le résumé et les éléments clés
        summary_parts = summary.split('\n\nÉléments clés:\n')
        summary_text = summary_parts[0]
        key_elements = summary_parts[1] if len(summary_parts) > 1 else ''

        # Générer le rapport d'email
        email_content = generate_email_report(summary_text, key_elements)

        return jsonify({
            'status': 'completed',
            'summary': summary_text,
            'key_elements': key_elements,
            'email_content': email_content
        })
    except Exception as e:
        app.logger.error(f"Erreur lors de la génération du résumé pour l'utilisateur {user_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/check-summary', methods=['GET'])
def check_summary():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'status': 'not_found'})

    task_id = f"{user_id}_summary"
    if task_id not in active_tasks:
        return jsonify({'status': 'not_found'})

    future = active_tasks[task_id]
    if future.done():
        try:
            result = future.result()
            del active_tasks[task_id]
            return jsonify({
                'status': 'completed',
                'summary': result
            })
        except Exception as e:
            del active_tasks[task_id]
            return jsonify({
                'status': 'error',
                'error': str(e)
            })
    return jsonify({'status': 'processing'})



@app.route('/send-email', methods=['POST'])
def send_email():
    data = request.get_json()
    if not data or 'recipients' not in data or 'subject' not in data or 'content' not in data:
        return jsonify({'error': 'Données email manquantes'}), 400

    recipients = data['recipients']
    subject = data['subject']
    content = data['content']

    try:
        # Création du message
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = subject

        # Ajout du contenu
        msg.attach(MIMEText(content, 'plain'))

        # Connexion au serveur SMTP et envoi
        with smtplib.SMTP_SSL(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)

        return jsonify({'message': 'Email envoyé avec succès'})
    except Exception as e:
        app.logger.error(f"Erreur lors de l'envoi de l'email : {e}")
        return jsonify({'error': str(e)}), 500

    







@app.errorhandler(Exception)
def handle_error(error):
    app.logger.error(f"Erreur non gérée : {error}")
    return jsonify({'error': 'Une erreur inattendue est survenue'}), 500




if __name__ == '__main__':
    app.run(debug=True)
