import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import whisper
from pydub import AudioSegment
from moviepy.editor import VideoFileClip
import sqlite3
import time
import winsound  # Pour notification sonore sur Windows (utiliser "os.system('afplay')" sur macOS)

# Connexion à la base de données SQLite pour stocker les transcriptions
def init_db():
    conn = sqlite3.connect('transcriptions.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transcriptions
                 (id INTEGER PRIMARY KEY, filename TEXT, language TEXT, transcription TEXT)''')
    conn.commit()
    return conn, c

conn, c = init_db()

def save_transcription(filename, language, transcription):
    c.execute("INSERT INTO transcriptions (filename, language, transcription) VALUES (?, ?, ?)", 
              (filename, language, transcription))
    conn.commit()

def load_transcriptions():
    c.execute("SELECT * FROM transcriptions")
    return c.fetchall()

# Fonction pour charger le modèle Whisper avec options avancées
def load_model(precision):
    print(f"Chargement du modèle Whisper ({precision})...")
    return whisper.load_model(precision)

# Fonction pour extraire l'audio d'une vidéo (MP4, AVI, etc.)
def extract_audio_from_video(filepath):
    video = VideoFileClip(filepath)
    audio_path = filepath.replace(os.path.splitext(filepath)[1], ".wav")
    video.audio.write_audiofile(audio_path)
    return audio_path

# Fonction pour convertir et transcrire un fichier audio avec options avancées
def transcribe_audio(filepath, model, temperature=0.0, best_of=5):
    ext = os.path.splitext(filepath)[1]
    if ext in ['.mp4', '.avi', '.mkv']:
        # Extraire l'audio si c'est un fichier vidéo
        filepath = extract_audio_from_video(filepath)

    audio = AudioSegment.from_file(filepath)
    wav_path = filepath.replace(ext, ".wav")
    audio.export(wav_path, format="wav")

    # Transcrire avec Whisper en utilisant les options avancées
    result = model.transcribe(wav_path, temperature=temperature, best_of=best_of)
    detected_lang = result['language']
    transcription = result['text']
    
    return detected_lang, transcription

# Fonction pour sélectionner un répertoire
def select_directory():
    directory = filedialog.askdirectory()
    if directory:
        precision = precision_var.get()
        temperature = float(temp_var.get())
        best_of = int(best_of_var.get())
        model = load_model(precision)
        transcribe_directory(directory, model, temperature, best_of)

# Fonction pour transcrire tous les fichiers d'un répertoire avec barre de progression
def transcribe_directory(directory, model, temperature, best_of):
    supported_formats = (".mp3", ".wav", ".ogg", ".mp4", ".avi", ".mkv")
    files = [f for f in os.listdir(directory) if f.endswith(supported_formats)]
    
    output = ""
    progress['maximum'] = len(files)

    for i, filename in enumerate(files):
        filepath = os.path.join(directory, filename)
        detected_lang, transcription = transcribe_audio(filepath, model, temperature, best_of)
        output += f"Fichier: {filename}\nLangue détectée: {detected_lang}\nTranscription:\n{transcription}\n\n"
        save_transcription(filename, detected_lang, transcription)  # Sauvegarder dans la base de données

        # Mettre à jour la barre de progression
        progress['value'] = i + 1
        root.update_idletasks()

    # Sauvegarder la transcription dans un fichier texte
    with open(os.path.join(directory, "transcription_multilangue.txt"), "w", encoding="utf-8") as f:
        f.write(output)

    # Notification sonore à la fin
    winsound.Beep(1000, 500)
    
    messagebox.showinfo("Succès", "Transcription multilingue terminée avec succès!")

# Fonction pour afficher l'historique des transcriptions
def show_history():
    history_window = tk.Toplevel(root)
    history_window.title("Historique des transcriptions")
    history_text = tk.Text(history_window, wrap="word", height=20, width=80)
    history_text.pack(pady=10)

    transcriptions = load_transcriptions()
    for t in transcriptions:
        history_text.insert(tk.END, f"ID: {t[0]}\nFichier: {t[1]}\nLangue: {t[2]}\nTranscription:\n{t[3]}\n\n")

# Interface graphique
root = tk.Tk()
root.title("Transcription Multilingue avec Whisper")

# Menu pour sélectionner la précision du modèle Whisper
precision_var = tk.StringVar(value="base")
precision_label = tk.Label(root, text="Sélectionner la précision du modèle Whisper :")
precision_label.pack(pady=10)
precision_menu = tk.OptionMenu(root, precision_var, "tiny", "base", "small", "medium", "large")
precision_menu.pack(pady=10)

# Options pour ajuster la vitesse et le filtre du bruit
temp_var = tk.StringVar(value="0.0")
temp_label = tk.Label(root, text="Température (vitesse de transcription, 0.0 à 1.0) :")
temp_label.pack(pady=10)
temp_entry = tk.Entry(root, textvariable=temp_var)
temp_entry.pack(pady=10)

best_of_var = tk.StringVar(value="5")
best_of_label = tk.Label(root, text="Best Of (nombre d'essais pour les meilleures options) :")
best_of_label.pack(pady=10)
best_of_entry = tk.Entry(root, textvariable=best_of_var)
best_of_entry.pack(pady=10)

# Barre de progression
progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
progress.pack(pady=20)

# Bouton pour sélectionner le répertoire
directory_button = tk.Button(root, text="Sélectionner un répertoire", command=select_directory)
directory_button.pack(pady=20)

# Bouton pour afficher l'historique des transcriptions
history_button = tk.Button(root, text="Voir l'historique", command=show_history)
history_button.pack(pady=10)

# Lancer l'application
root.mainloop()

# Fermer la connexion à la base de données à la fin du programme
conn.close()

