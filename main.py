import os
import threading
import subprocess
import json
import re
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from yt_dlp import YoutubeDL

# ----- CONFIG FILE -----
CONFIG_FILE = "config.json"

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)

def load_config():
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    else:
        return {}

# ----------------------------------

class VideoToolApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("VideoTool - Downloader, Compressor, Converter")
        self.geometry("700x700")
        self.config_data = load_config()
        self.ffmpeg_path = self.config_data.get("ffmpeg_path", "")
        self.cookie_file = "cookieyt.txt" 
        self.notebook = ctk.CTkTabview(self, width=680, height=650)
        self.notebook.pack(padx=10, pady=10, fill="both", expand=True)
        self.notebook.add("Téléchargement")
        self.notebook.add("Compression")
        self.notebook.add("Conversion")
        self.notebook.add("Configuration")
        self.create_download_tab()
        self.create_compression_tab()
        self.create_conversion_tab()
        self.create_config_tab()
        self.format_map = {
            'video': ['mp4','mkv','avi','mov','webm','flv'],
            'audio': ['mp3','aac','wav','flac','ogg','m4a'],
            'image': ['jpg','jpeg','png','gif','bmp','webp'],
            'doc':   ['pdf','docx','txt','xlsx','pptx'],
            'archive': ['zip','tar','gz','rar','7z']
        }

    # ----------- Onglet Téléchargement -----------
    def create_download_tab(self):
        frame = self.notebook.tab("Téléchargement")

        ctk.CTkLabel(frame, text="Collez vos URLs (Youtube ou autre) ici :").pack(pady=5)
        self.download_text = ctk.CTkTextbox(frame, height=8)
        self.download_text.pack(fill="x", padx=10)

        ctk.CTkLabel(frame, text="Choisissez la résolution :").pack(pady=5)
        self.download_res_var = ctk.StringVar(value="best")
        self.download_res_menu = ctk.CTkOptionMenu(frame, values=[
            "best", "1080p", "720p", "480p", "360p", "240p", "144p"
        ], variable=self.download_res_var)
        self.download_res_menu.pack()

        ctk.CTkLabel(frame, text="Type à télécharger :").pack(pady=5)
        self.download_type_var = ctk.StringVar(value="video")
        self.download_type_menu = ctk.CTkOptionMenu(frame, values=["audio", "video", "both"], variable=self.download_type_var)
        self.download_type_menu.pack()

        ctk.CTkLabel(frame, text="Dossier de destination :").pack(pady=5)
        self.download_dest_entry = ctk.CTkEntry(frame)
        self.download_dest_entry.pack(fill="x", padx=20)

        last_dest = self.config_data.get("download_dest", "")
        if last_dest and os.path.isdir(last_dest):
            self.download_dest_entry.insert(0, last_dest)

        btn_browse = ctk.CTkButton(frame, text="Choisir dossier", command=self.browse_download_folder)
        btn_browse.pack(pady=5)

        self.download_btn = ctk.CTkButton(frame, text="Télécharger", command=self.start_download_thread)
        self.download_btn.pack(pady=10)

        self.download_progress = ctk.CTkProgressBar(frame)
        self.download_progress.pack(fill="x", padx=20)

        self.download_log = ctk.CTkTextbox(frame, height=8)
        self.download_log.pack(fill="both", padx=10, pady=10, expand=True)

    def is_ffmpeg_available(self):
        try:
            subprocess.run([self.ffmpeg_path, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False


    def browse_download_folder(self):
        folder = filedialog.askdirectory(title="Choisir dossier destination téléchargement")
        if folder:
            self.download_dest_entry.delete(0, "end")
            self.download_dest_entry.insert(0, folder)
            self.config_data["download_dest"] = folder
            save_config(self.config_data)

    def log_download(self, msg):
        self.download_log.configure(state="normal")
        self.download_log.insert("end", msg + "\n")
        self.download_log.see("end")
        self.download_log.configure(state="disabled")

    def set_progress_download(self, progress):
        self.download_progress.set(progress)

    def extract_urls(self, text):
        urls = re.findall(r'(https?://[^\s]+)', text)
        return urls

    def start_download_thread(self):
        threading.Thread(target=self.download_videos, daemon=True).start()

    def download_videos(self):
        self.download_log.configure(state="normal")
        self.download_log.delete("1.0", "end")
        self.download_log.configure(state="disabled")
        self.set_progress_download(0)
        text = self.download_text.get("1.0", "end").strip()
        urls = self.extract_urls(text)
        if not urls:
            self.log_download("⚠️ Aucune URL valide détectée.")
            return

        dest = self.download_dest_entry.get().strip()
        if not os.path.isdir(dest):
            self.log_download("⚠️ Le dossier de destination est invalide.")
            return

        if not self.is_ffmpeg_available():
            self.log_download("❌ FFmpeg est requis pour fusionner l'audio et la vidéo, mais il est introuvable.")
            self.log_download("👉 Installez-le depuis https://ffmpeg.org/download.html ou ajoutez-le au PATH.")
            return

        self.config_data["download_dest"] = dest
        save_config(self.config_data)

        res = self.download_res_var.get()
        typ = self.download_type_var.get()

        ydl_opts_base = {
            "outtmpl": os.path.join(dest, "%(title)s.%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [self.ydl_hook],
            "cookiefile": self.cookie_file if os.path.isfile(self.cookie_file) else None,
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "ffmpeg_location": self.ffmpeg_path, 
        }

        for url in urls:
            self.log_download(f"⬇️ Début téléchargement : {url}")

            ydl_opts = ydl_opts_base.copy()

            if typ == "audio":
                ydl_opts["format"] = "bestaudio/best"
                ydl_opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]
            elif typ == "video":
                if res == "best":
                    ydl_opts["format"] = "bestvideo+bestaudio/best"
                else:
                    height = int(res.replace("p", ""))
                    ydl_opts["format"] = f"bestvideo[height<={height}]+bestaudio/best"
                ydl_opts["merge_output_format"] = "mp4"
            else:  # both
                ydl_opts["format"] = "bestvideo+bestaudio/best"
                ydl_opts["merge_output_format"] = "mp4"

            try:
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                self.log_download("✅ Téléchargement terminé.")
            except Exception as e:
                self.log_download(f"❌ Erreur: {e}")

        self.set_progress_download(0)

    def ydl_hook(self, d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            if total and total > 0:
                progress = downloaded / total
                self.set_progress_download(progress)
                self.log_download(f"Téléchargement : {int(progress*100)}%")
        elif d['status'] == 'finished':
            self.set_progress_download(1)
            self.log_download("Téléchargement terminé.")

    # -------------- Onglet Compression --------------
    def create_compression_tab(self):
        frame = self.notebook.tab("Compression")

        ctk.CTkLabel(frame, text="Sélectionnez la vidéo à compresser :").pack(pady=5)
        self.comp_file_entry = ctk.CTkEntry(frame)
        self.comp_file_entry.pack(fill="x", padx=20)

        btn_browse_file = ctk.CTkButton(frame, text="Choisir fichier", command=self.browse_comp_file)
        btn_browse_file.pack(pady=5)

        ctk.CTkLabel(frame, text="Taille cible :").pack(pady=5)
        self.comp_size_var = ctk.StringVar(value="Compression max (0 Mo)")
        self.comp_size_menu = ctk.CTkOptionMenu(frame, 
            values=["Compression max (0 Mo)", "10 Mo", "25 Mo", "50 Mo", "100 Mo"],
            variable=self.comp_size_var
        )
        self.comp_size_menu.pack(pady=5)

        ctk.CTkLabel(frame, text="Dossier de destination :").pack(pady=5)
        self.comp_dest_entry = ctk.CTkEntry(frame)
        self.comp_dest_entry.pack(fill="x", padx=20)

        last_dest = self.config_data.get("compression_dest", "")
        if last_dest and os.path.isdir(last_dest):
            self.comp_dest_entry.insert(0, last_dest)

        btn_browse_dest = ctk.CTkButton(frame, text="Choisir dossier destination", command=self.browse_comp_dest)
        btn_browse_dest.pack(pady=5)

        self.comp_btn = ctk.CTkButton(frame, text="Compresser", command=self.start_compress_thread)
        self.comp_btn.pack(pady=10)

        self.comp_progress = ctk.CTkProgressBar(frame)
        self.comp_progress.pack(fill="x", padx=20)

        self.comp_log = ctk.CTkTextbox(frame, height=8)
        self.comp_log.pack(fill="both", padx=10, pady=10, expand=True)

    def browse_comp_file(self):
        file = filedialog.askopenfilename(title="Sélectionnez une vidéo")
        if file:
            self.comp_file_entry.delete(0, "end")
            self.comp_file_entry.insert(0, file)

    def browse_comp_dest(self):
        folder = filedialog.askdirectory(title="Choisir dossier destination compression")
        if folder:
            self.comp_dest_entry.delete(0, "end")
            self.comp_dest_entry.insert(0, folder)
            self.config_data["compression_dest"] = folder
            save_config(self.config_data)

    def log_comp(self, msg):
        self.comp_log.configure(state="normal")
        self.comp_log.insert("end", msg + "\n")
        self.comp_log.see("end")
        self.comp_log.configure(state="disabled")

    def set_progress_comp(self, progress):
        self.comp_progress.set(progress)

    def start_compress_thread(self):
        threading.Thread(target=self.compress_video, daemon=True).start()

    def compress_video(self):
        self.comp_log.configure(state="normal")
        self.comp_log.delete("1.0", "end")
        self.comp_log.configure(state="disabled")
        self.set_progress_comp(0)

        input_file = self.comp_file_entry.get().strip()
        if not os.path.isfile(input_file):
            self.log_comp("⚠️ Fichier vidéo invalide.")
            return

        dest_folder = self.comp_dest_entry.get().strip()
        if not os.path.isdir(dest_folder):
            self.log_comp("⚠️ Dossier destination invalide.")
            return

        self.config_data["compression_dest"] = dest_folder
        save_config(self.config_data)

        size_str = self.comp_size_var.get()
        if size_str == "Compression max (0 Mo)":
            size_mb = 0
        else:
            size_mb = int(size_str.split()[0]) 

        size_bytes = size_mb * 1024 * 1024

        base = os.path.basename(input_file)
        name, ext = os.path.splitext(base)
        output_file = os.path.join(dest_folder, f"{name}_compressed.mp4")

        if not self.ffmpeg_path or not os.path.isfile(self.ffmpeg_path):
            self.log_comp("⚠️ ffmpeg.exe non configuré ou introuvable.")
            return

        duration = self.get_video_duration(input_file)
        if duration is None or duration == 0:
            self.log_comp("⚠️ Impossible d'obtenir la durée vidéo.")
            return

        if size_mb == 0:
            bitrate = "500k" 
        else:
            target_bits = size_bytes * 8
            bitrate_val = int(target_bits / duration) 
            bitrate_k = int(bitrate_val / 1000)       
            bitrate = f"{bitrate_k}k"


        self.log_comp(f"Durée vidéo: {duration:.2f}s")
        self.log_comp(f"Débit cible: {bitrate}")

        cmd = [
            self.ffmpeg_path,
            "-i", input_file,
            "-b:v", bitrate,
            "-bufsize", bitrate,
            "-maxrate", bitrate,
            "-y",
            output_file
        ]

        self.log_comp("Lancement compression...")
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

            while True:
                line = proc.stderr.readline()
                if not line:
                    break
                self.log_comp(line.strip())

            proc.wait()
            if proc.returncode == 0:
                self.log_comp(f"✅ Compression terminée : {output_file}")
                self.set_progress_comp(1)
            else:
                self.log_comp(f"❌ Erreur lors de la compression, code {proc.returncode}")
                self.set_progress_comp(0)
        except Exception as e:
            self.log_comp(f"Erreur compression : {e}")
            self.set_progress_comp(0)


    def get_video_duration(self, file):
        if not self.ffmpeg_path or not os.path.isfile(self.ffmpeg_path):
            return None
        cmd = [self.ffmpeg_path.replace("ffmpeg.exe", "ffprobe.exe"), "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file]
        try:
            output = subprocess.check_output(cmd, universal_newlines=True).strip()
            return float(output)
        except Exception:
            return None


    # -------------- Onglet Conversion --------------
    def create_conversion_tab(self):
        frame = self.notebook.tab("Conversion")
        self.mode = tk.StringVar(value="file")

        switch = ctk.CTkFrame(frame)
        switch.pack(fill="x", padx=10, pady=(10,0))
        ctk.CTkButton(switch, text="🎞️ Fichier", command=lambda: self.show_mode("file")).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(switch, text="📁 Dossier", command=lambda: self.show_mode("folder")).pack(side="left", expand=True, padx=5)

        panels = ctk.CTkFrame(frame)
        panels.pack(fill="both", expand=True, padx=10, pady=10)

        self.file_frame = ctk.CTkFrame(panels)
        self.file_frame.pack(side="left", fill="both", expand=True, padx=(0,5))

        ctk.CTkLabel(self.file_frame, text="🎞️ Fichier à convertir :", anchor="w").pack(fill="x", padx=10, pady=(10,0))
        self.conv_file_entry = ctk.CTkEntry(self.file_frame)
        self.conv_file_entry.pack(fill="x", padx=10)
        ctk.CTkButton(self.file_frame, text="Choisir fichier", command=self.browse_conv_file).pack(padx=10, pady=5)

        ctk.CTkLabel(self.file_frame, text="Format de sortie :", anchor="w").pack(fill="x", padx=10, pady=(5,0))
        self.file_format_var = tk.StringVar()
        self.file_format_menu = ctk.CTkOptionMenu(self.file_frame, variable=self.file_format_var, values=[])
        self.file_format_menu.pack(fill="x", padx=10, pady=(0,10))

        self.folder_frame = ctk.CTkFrame(panels)
        self.folder_frame.pack(side="left", fill="both", expand=True, padx=(5,0))

        ctk.CTkLabel(self.folder_frame, text="📁 Dossier à convertir :", anchor="w").pack(fill="x", padx=10, pady=(10,0))
        self.folder_path_entry = ctk.CTkEntry(self.folder_frame)
        self.folder_path_entry.pack(fill="x", padx=10)
        ctk.CTkButton(self.folder_frame, text="Choisir dossier", command=self.browse_folder_path).pack(padx=10, pady=5)

        ctk.CTkLabel(self.folder_frame, text="Format de sortie :", anchor="w").pack(fill="x", padx=10, pady=(5,0))
        self.folder_format_var = tk.StringVar()
        self.folder_format_menu = ctk.CTkOptionMenu(self.folder_frame, variable=self.folder_format_var, values=[])
        self.folder_format_menu.pack(fill="x", padx=10, pady=(0,10))

        ctk.CTkLabel(frame, text="📥 Dossier de destination :", anchor="w").pack(fill="x", padx=20, pady=(10,0))
        self.conv_dest_entry = ctk.CTkEntry(frame)
        self.conv_dest_entry.pack(fill="x", padx=20)
        last = self.config_data.get("conversion_dest", "")
        if last and os.path.isdir(last):
            self.conv_dest_entry.insert(0, last)
        ctk.CTkButton(frame, text="Choisir dossier de sortie", command=self.browse_conv_dest).pack(pady=5)

        self.conv_btn = ctk.CTkButton(frame, text="🚀 Convertir", font=("Arial",14,"bold"), command=self.start_convert_thread)
        self.conv_btn.pack(pady=(10,5))

        self.conv_progress = ctk.CTkProgressBar(frame)
        self.conv_progress.pack(fill="x", padx=20, pady=(5,0))
        self.conv_log = ctk.CTkTextbox(frame, height=8)
        self.conv_log.pack(fill="both", padx=10, pady=10, expand=True)

        self.show_mode(self.mode.get())

    def show_mode(self, mode):
        self.mode.set(mode)
        self.file_frame.pack_forget()
        self.folder_frame.pack_forget()
        if mode == "file":
            self.file_frame.pack(side="left", fill="both", expand=True, padx=(0,5))
        else:
            self.folder_frame.pack(side="left", fill="both", expand=True, padx=(5,0))

    def browse_conv_file(self):
        path = filedialog.askopenfilename(title="Sélectionnez un fichier")
        if not path: 
            return
        self.conv_file_entry.delete(0,"end")
        self.conv_file_entry.insert(0,path)
        ext = os.path.splitext(path)[1].lower()
        opts = self.detect_types([ext])
        self.file_format_menu.configure(values=opts)
        self.file_format_var.set(opts[0])

    def browse_folder_path(self):
        folder = filedialog.askdirectory(title="Choisir un dossier")
        if not folder: 
            return
        self.folder_path_entry.delete(0,"end")
        self.folder_path_entry.insert(0,folder)
        exts = {os.path.splitext(f)[1].lower() for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))}
        opts = self.detect_types(list(exts))
        self.folder_format_menu.configure(values=opts)
        self.folder_format_var.set(opts[0])

    def browse_conv_dest(self):
        folder = filedialog.askdirectory(title="Choisir dossier de destination")
        if not folder: 
            return
        self.conv_dest_entry.delete(0,"end")
        self.conv_dest_entry.insert(0,folder)
        self.config_data["conversion_dest"] = folder

    def detect_types(self, exts):
        types = set()
        for e in exts:
            if e in ['.mp4','.mkv','.avi','.mov','.webm','.flv']:
                types |= set(self.format_map['video'])
            elif e in ['.mp3','.wav','.flac','.ogg','.aac','.m4a']:
                types |= set(self.format_map['audio'])
            elif e in ['.jpg','.jpeg','.png','.gif','.bmp','.webp']:
                types |= set(self.format_map['image'])
            elif e in ['.pdf','.docx','.txt','.xlsx','.pptx']:
                types |= set(self.format_map['doc'])
            elif e in ['.zip','.tar','.gz','.rar','.7z']:
                types |= set(self.format_map['archive'])
        return sorted(types) if types else ['mp4','mp3','png','pdf']

    def start_convert_thread(self):
        mode = self.mode.get()
        if mode=="file":
            threading.Thread(target=self.convert_file, daemon=True).start()
        else:
            threading.Thread(target=self.convert_folder, daemon=True).start()

    def convert_file(self):
        self.log_conv("")  
        self.set_progress_conv(0)
        inp = self.conv_file_entry.get().strip()
        out_fmt = self.file_format_var.get().strip()
        dst = self.conv_dest_entry.get().strip()

        if not os.path.isfile(inp):
            return self.log_conv("⚠️ Fichier invalide.")
        if not out_fmt:
            return self.log_conv("⚠️ Choisissez un format.")
        if not os.path.isdir(dst):
            return self.log_conv("⚠️ Dossier de destination invalide.")
        if not self.ffmpeg_path or not os.path.isfile(self.ffmpeg_path):
            return self.log_conv("⚠️ ffmpeg non configuré.")

        name,_ = os.path.splitext(os.path.basename(inp))
        out = os.path.join(dst, f"{name}_converted.{out_fmt}")
        cmd = [self.ffmpeg_path, "-y", "-i", inp, out]
        self.log_conv(f"🔄 1/1 : {os.path.basename(inp)} → {out_fmt}")
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)
        for line in proc.stderr:
            self.log_conv(line.strip())
        proc.wait()
        if proc.returncode==0:
            self.log_conv(f"✅ Terminé : {out}")
            self.set_progress_conv(1)
        else:
            self.log_conv(f"❌ Erreur {proc.returncode}")

    def convert_folder(self):
        self.log_conv("")  
        self.set_progress_conv(0)
        folder = self.folder_path_entry.get().strip()
        out_fmt = self.folder_format_var.get().strip()
        dst = self.conv_dest_entry.get().strip()

        if not os.path.isdir(folder):
            return self.log_conv("⚠️ Dossier invalide.")
        if not out_fmt:
            return self.log_conv("⚠️ Choisissez un format.")
        if not os.path.isdir(dst):
            return self.log_conv("⚠️ Dossier de destination invalide.")
        if not self.ffmpeg_path or not os.path.isfile(self.ffmpeg_path):
            return self.log_conv("⚠️ ffmpeg non configuré.")

        exts = tuple(['.'+ext for ext in self.format_map['video']+self.format_map['audio']+
                    self.format_map['image']+self.format_map['doc']])
        files = [os.path.join(folder,f) for f in os.listdir(folder) if f.lower().endswith(exts)]
        if not files:
            return self.log_conv("⚠️ Aucun fichier compatible trouvé.")

        total = len(files)
        self.log_conv(f"🔁 {total} fichiers à convertir...")
        for i,f in enumerate(files, start=1):
            name,_ = os.path.splitext(os.path.basename(f))
            out = os.path.join(dst, f"{name}_converted.{out_fmt}")
            cmd = [self.ffmpeg_path, "-y", "-i", f, out]
            self.log_conv(f"🔄 {i}/{total} : {os.path.basename(f)} → {out_fmt}")
            proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)
            for line in proc.stderr:
                self.log_conv(line.strip())
            proc.wait()
            if proc.returncode==0:
                self.log_conv(f"✅ {os.path.basename(out)}")
            else:
                self.log_conv(f"❌ Erreur {proc.returncode}")
            self.set_progress_conv(i/total)
        self.log_conv("🎉 Tout est terminé !")

    def log_conv(self, text):
        # Ajoute le texte au widget log
        self.conv_log.configure(state="normal")
        if text == "":
            self.conv_log.delete("0.0", "end")
        else:
            self.conv_log.insert("end", text + "\n")
            self.conv_log.see("end")
        self.conv_log.configure(state="disabled")

    def set_progress_conv(self, value):
        self.conv_progress.set(value)
        self.update_idletasks()

    # -------------- Onglet Configuration --------------
    def create_config_tab(self):
        frame = self.notebook.tab("Configuration")

        ctk.CTkLabel(frame, text="Sélectionnez le chemin vers ffmpeg.exe :").pack(pady=5)

        self.ffmpeg_entry = ctk.CTkEntry(frame)
        self.ffmpeg_entry.pack(fill="x", padx=20)
        self.ffmpeg_entry.insert(0, self.ffmpeg_path)

        btn_browse_ffmpeg = ctk.CTkButton(frame, text="Parcourir", command=self.browse_ffmpeg)
        btn_browse_ffmpeg.pack(pady=5)

        btn_save_ffmpeg = ctk.CTkButton(frame, text="Sauvegarder", command=self.save_ffmpeg_path)
        btn_save_ffmpeg.pack(pady=10)

        ctk.CTkLabel(frame, text="Fichier cookie YouTube (cookieyt.txt) sera utilisé si présent dans le même dossier que ce script.").pack(pady=20)

    def browse_ffmpeg(self):
        file = filedialog.askopenfilename(title="Choisir ffmpeg.exe", filetypes=[("Executable", "ffmpeg.exe")])
        if file:
            self.ffmpeg_entry.delete(0, "end")
            self.ffmpeg_entry.insert(0, file)

    def save_ffmpeg_path(self):
        path = self.ffmpeg_entry.get().strip()
        if os.path.isfile(path) and path.lower().endswith("ffmpeg.exe"):
            self.ffmpeg_path = path
            self.config_data["ffmpeg_path"] = path
            save_config(self.config_data)
            messagebox.showinfo("Succès", "Chemin ffmpeg.exe sauvegardé.")
        else:
            messagebox.showerror("Erreur", "Chemin invalide ou fichier non ffmpeg.exe")

if __name__ == "__main__":
    ctk.set_appearance_mode("System")  
    ctk.set_default_color_theme("blue")
    app = VideoToolApp()
    app.mainloop()
