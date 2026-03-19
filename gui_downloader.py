#!/usr/bin/env python3
"""
YouTube Content Downloader with GUI using yt-dlp and tkinter
"""

import yt_dlp
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
from pathlib import Path
import queue

class YouTubeDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Content Downloader")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Variables
        self.url_var = tk.StringVar()
        self.quality_var = tk.StringVar(value="best")
        self.output_dir_var = tk.StringVar(value="downloads")
        self.download_type_var = tk.StringVar(value="video")
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Готов к работе")
        
        # Queue for thread communication
        self.queue = queue.Queue()
        
        # Create GUI
        self.create_widgets()
        
        # Start queue checker
        self.root.after(100, self.check_queue)
    
    def create_widgets(self):
        """Create all GUI widgets"""
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # URL Input
        ttk.Label(main_frame, text="URL видео:").grid(row=0, column=0, sticky=tk.W, pady=5)
        url_entry = ttk.Entry(main_frame, textvariable=self.url_var, width=60)
        url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # Download Type
        ttk.Label(main_frame, text="Тип загрузки:").grid(row=1, column=0, sticky=tk.W, pady=5)
        type_frame = ttk.Frame(main_frame)
        type_frame.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        ttk.Radiobutton(type_frame, text="Видео", variable=self.download_type_var, 
                       value="video").pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(type_frame, text="Аудио (MP3)", variable=self.download_type_var, 
                       value="audio").pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(type_frame, text="Плейлист видео", variable=self.download_type_var, 
                       value="playlist").pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(type_frame, text="Плейлист аудио", variable=self.download_type_var, 
                       value="playlist_audio").pack(side=tk.LEFT)
        
        # Quality Selection
        ttk.Label(main_frame, text="Качество:").grid(row=2, column=0, sticky=tk.W, pady=5)
        quality_combo = ttk.Combobox(main_frame, textvariable=self.quality_var, 
                                     values=["best", "worst", "1080p", "720p", "480p", "360p"],
                                     state="readonly", width=20)
        quality_combo.grid(row=2, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Output Directory
        ttk.Label(main_frame, text="Папка сохранения:").grid(row=3, column=0, sticky=tk.W, pady=5)
        dir_frame = ttk.Frame(main_frame)
        dir_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        dir_frame.columnconfigure(0, weight=1)
        
        dir_entry = ttk.Entry(dir_frame, textvariable=self.output_dir_var, width=50)
        dir_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(dir_frame, text="Обзор...", command=self.browse_directory).grid(row=0, column=1, padx=(5, 0))
        
        # Progress Bar
        ttk.Label(main_frame, text="Прогресс:").grid(row=4, column=0, sticky=tk.W, pady=5)
        progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, 
                                      maximum=100, length=400)
        progress_bar.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # Status Label
        status_label = ttk.Label(main_frame, textvariable=self.status_var, 
                                 font=('Arial', 10, 'bold'))
        status_label.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=20)
        
        self.download_button = ttk.Button(button_frame, text="Скачать", 
                                         command=self.start_download, style="Accent.TButton")
        self.download_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="Отмена", command=self.cancel_download).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Очистить лог", command=self.clear_log).pack(side=tk.LEFT)
        
        # Log Text Area
        ttk.Label(main_frame, text="Лог загрузки:").grid(row=7, column=0, columnspan=2, 
                                                          sticky=tk.W, pady=(10, 5))
        
        self.log_text = scrolledtext.ScrolledText(main_frame, height=15, width=80, 
                                                  wrap=tk.WORD, font=('Consolas', 9))
        self.log_text.grid(row=8, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Configure grid weights for log area
        main_frame.rowconfigure(8, weight=1)
    
    def browse_directory(self):
        """Browse for output directory"""
        directory = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if directory:
            self.output_dir_var.set(directory)
    
    def log_message(self, message):
        """Add message to log text area"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def clear_log(self):
        """Clear log text area"""
        self.log_text.delete(1.0, tk.END)
    
    def start_download(self):
        """Start download in separate thread"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Ошибка", "Пожалуйста, введите URL видео")
            return
        
        # Disable download button during download
        self.download_button.config(state='disabled')
        self.progress_var.set(0)
        self.status_var.set("Загрузка...")
        self.log_message(f"Начало загрузки: {url}")
        
        # Start download in separate thread
        thread = threading.Thread(target=self.download_worker, args=(url,))
        thread.daemon = True
        thread.start()
    
    def download_worker(self, url):
        """Worker thread for download process"""
        try:
            download_type = self.download_type_var.get()
            quality = self.quality_var.get()
            output_dir = self.output_dir_var.get()
            
            # Create output directory
            Path(output_dir).mkdir(exist_ok=True)
            
            # Configure yt-dlp options
            ydl_opts = {
                'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
                'format': quality,
                'noplaylist': download_type not in ['playlist', 'playlist_audio'],
                'progress_hooks': [self.progress_hook],
            }
            
            # Configure for playlist
            if download_type in ['playlist', 'playlist_audio']:
                ydl_opts['outtmpl'] = os.path.join(output_dir, '%(playlist_title)s/%(playlist_index)s - %(title)s.%(ext)s')
            
            # Configure for audio only
            if download_type in ['audio', 'playlist_audio']:
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
                ydl_opts['keepvideo'] = False
            else:
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }]
            
            # Download
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.queue.put(("status", "Скачивание..."))
                ydl.download([url])
                self.queue.put(("status", "Загрузка завершена!"))
                self.queue.put(("progress", 100))
                self.queue.put(("log", "Загрузка успешно завершена!"))
        
        except Exception as e:
            self.queue.put(("error", f"Ошибка загрузки: {str(e)}"))
        
        finally:
            self.queue.put(("finished", None))
    
    def progress_hook(self, d):
        """Progress hook for yt-dlp"""
        if d['status'] == 'downloading':
            percent_str = d.get('_percent_str', '0.0%')
            try:
                percent = float(percent_str.strip('%'))
                self.queue.put(("progress", percent))
                self.queue.put(("status", f"Скачивание... {percent_str}"))
                self.queue.put(("log", f"Скачивание: {d.get('filename', 'Unknown')} - {percent_str}"))
            except ValueError:
                pass
        elif d['status'] == 'finished':
            self.queue.put(("log", f"Завершено: {d.get('filename', 'Unknown')}"))
    
    def check_queue(self):
        """Check queue for messages from worker thread"""
        try:
            while True:
                msg_type, msg = self.queue.get_nowait()
                
                if msg_type == "progress":
                    self.progress_var.set(msg)
                elif msg_type == "status":
                    self.status_var.set(msg)
                elif msg_type == "log":
                    self.log_message(msg)
                elif msg_type == "error":
                    self.log_message(f"ОШИБКА: {msg}")
                    messagebox.showerror("Ошибка", msg)
                elif msg_type == "finished":
                    self.download_button.config(state='normal')
        
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.check_queue)
    
    def cancel_download(self):
        """Cancel download (placeholder)"""
        self.status_var.set("Отмена загрузки...")
        self.log_message("Отмена загрузки...")
        # Note: yt-dlp doesn't have a simple cancel mechanism
        # This would require more complex implementation
        self.download_button.config(state='normal')

def main():
    """Main function to run GUI"""
    root = tk.Tk()
    
    # Configure style
    style = ttk.Style()
    style.configure("Accent.TButton", font=('Arial', 10, 'bold'))
    
    app = YouTubeDownloaderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
