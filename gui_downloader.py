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
import json
import subprocess
import re
import traceback
import logging
from datetime import datetime

class YouTubeDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Content Downloader")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Settings file
        self.settings_file = "settings.json"
        self.log_file = "youtube_downloader.log"
        
        # Setup logging
        self.setup_logging()
        
        # Load settings
        self.settings = self.load_settings()
        
        # Variables
        self.url_var = tk.StringVar()
        self.quality_var = tk.StringVar(value=self.settings.get('quality', 'best'))
        self.output_dir_var = tk.StringVar(value=self.settings.get('output_dir', 'downloads'))
        self.download_type_var = tk.StringVar(value=self.settings.get('download_type', 'video'))
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Готов к работе")
        
        # Queue for thread communication
        self.queue = queue.Queue()
        
        # Create GUI
        self.create_widgets()
        
        # Start queue checker
        self.root.after(100, self.check_queue)
        
        # Save settings on exit
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_logging(self):
        """Setup logging to file"""
        try:
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(self.log_file, encoding='utf-8'),
                    logging.StreamHandler()
                ]
            )
            self.logger = logging.getLogger(__name__)
            self.logger.info("=== YouTube Downlogger Started ===")
        except Exception as e:
            print(f"Failed to setup logging: {e}")
            self.logger = logging.getLogger(__name__)
    
    def log_error(self, error_msg, exception=None):
        """Log error with traceback"""
        self.logger.error(error_msg)
        if exception:
            self.logger.error(f"Exception: {str(exception)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Also send to GUI
        self.queue.put(("log", f"ERROR: {error_msg}"))
        if exception:
            self.queue.put(("log", f"Exception: {str(exception)}"))
    
    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def save_settings(self):
        """Save current settings to file"""
        try:
            settings = {
                'quality': self.quality_var.get(),
                'output_dir': self.output_dir_var.get(),
                'download_type': self.download_type_var.get(),
                'audio_quality': self.audio_quality_var.get()
            }
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def on_closing(self):
        """Handle window closing"""
        self.save_settings()
        self.root.destroy()
    
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
        url_entry = ttk.Entry(main_frame, textvariable=self.url_var, width=60, font=('Arial', 10))
        url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # Set focus to URL entry
        url_entry.focus_set()
        
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
        ttk.Label(main_frame, text="Качество видео:").grid(row=2, column=0, sticky=tk.W, pady=5)
        quality_combo = ttk.Combobox(main_frame, textvariable=self.quality_var, 
                                     values=["best", "worst", "1080p", "720p", "480p", "360p"],
                                     state="readonly", width=20)
        quality_combo.grid(row=2, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Audio Quality Selection
        ttk.Label(main_frame, text="Качество аудио:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.audio_quality_var = tk.StringVar(value=self.settings.get('audio_quality', 'высокое'))
        audio_quality_combo = ttk.Combobox(main_frame, textvariable=self.audio_quality_var,
                                           values=["высокое", "среднее", "низкое"],
                                           state="readonly", width=20)
        audio_quality_combo.grid(row=3, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Output Directory
        ttk.Label(main_frame, text="Папка сохранения:").grid(row=4, column=0, sticky=tk.W, pady=5)
        dir_frame = ttk.Frame(main_frame)
        dir_frame.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        dir_frame.columnconfigure(0, weight=1)
        
        dir_entry = ttk.Entry(dir_frame, textvariable=self.output_dir_var, width=50)
        dir_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(dir_frame, text="Обзор...", command=self.browse_directory).grid(row=0, column=1, padx=(5, 0))
        
        # Progress Bar
        ttk.Label(main_frame, text="Прогресс:").grid(row=5, column=0, sticky=tk.W, pady=5)
        progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, 
                                      maximum=100, length=400)
        progress_bar.grid(row=5, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # Status Label
        status_label = ttk.Label(main_frame, textvariable=self.status_var, 
                                 font=('Arial', 10, 'bold'))
        status_label.grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=20)
        
        self.download_button = ttk.Button(button_frame, text="Скачать", 
                                         command=self.start_download, style="Accent.TButton")
        self.download_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="Отмена", command=self.cancel_download).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Очистить лог", command=self.clear_log).pack(side=tk.LEFT)
        
        # Log Text Area
        ttk.Label(main_frame, text="Лог загрузки:").grid(row=8, column=0, columnspan=2, 
                                                          sticky=tk.W, pady=(10, 5))
        
        self.log_text = scrolledtext.ScrolledText(main_frame, height=15, width=80, 
                                                  wrap=tk.WORD, font=('Consolas', 9))
        self.log_text.grid(row=9, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Configure grid weights for log area
        main_frame.rowconfigure(9, weight=1)
    
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
            self.logger.info(f"Starting download for URL: {url}")
            
            download_type = self.download_type_var.get()
            quality = self.quality_var.get()
            audio_quality = self.audio_quality_var.get()
            output_dir = self.output_dir_var.get()
            
            self.logger.info(f"Download type: {download_type}, quality: {quality}, audio_quality: {audio_quality}")
            
            # Create output directory
            Path(output_dir).mkdir(exist_ok=True)
            self.logger.info(f"Output directory: {output_dir}")
            
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
                self.logger.info("Playlist mode enabled")
            
            # Configure for audio only
            if download_type in ['audio', 'playlist_audio']:
                # For audio only, download best audio stream based on quality
                if audio_quality == 'высокое':
                    ydl_opts['format'] = 'bestaudio[abr<=320]/bestaudio'
                elif audio_quality == 'среднее':
                    ydl_opts['format'] = 'bestaudio[abr<=192]/bestaudio'
                else:  # низкое
                    ydl_opts['format'] = 'bestaudio[abr<=128]/bestaudio'
                
                self.logger.info(f"Audio quality mode: {audio_quality}, format: {ydl_opts['format']}")
                
                # Completely disable postprocessors
                ydl_opts['postprocessors'] = []
                ydl_opts['writethumbnail'] = False
                ydl_opts['writedescription'] = False
                ydl_opts['writeinfojson'] = False
                ydl_opts['writesubtitles'] = False
                ydl_opts['allsubtitles'] = False
                ydl_opts['keepvideo'] = False  # We'll handle file deletion ourselves
                
                # Add custom progress hook for audio extraction
                original_hook = self.progress_hook
                def audio_progress_hook(d):
                    try:
                        self.logger.debug(f"Progress hook status: {d.get('status')}")
                        if d['status'] == 'finished':
                            # Start real audio extraction progress
                            self.queue.put(("status", "Начало конвертации аудио..."))
                            self.queue.put(("log", "Начало конвертации в MP3..."))
                            
                            # Get the downloaded file path
                            filepath = d.get('filename', '')
                            self.logger.info(f"Downloaded file: {filepath}")
                            
                            if filepath and os.path.exists(filepath):
                                output_file = os.path.splitext(filepath)[0] + '.mp3'
                                self.logger.info(f"Target MP3 file: {output_file}")
                                self.extract_audio_with_progress(filepath, output_file, audio_quality)
                            else:
                                self.log_error(f"Downloaded file not found: {filepath}")
                    except Exception as e:
                        self.log_error("Error in audio progress hook", e)
                    
                    original_hook(d)
                
                ydl_opts['progress_hooks'] = [audio_progress_hook]
            else:
                # For video, use fallback format selection
                if quality == '360p':
                    ydl_opts['format'] = 'best[height<=360]/best[height<=480]/best[height<=720]/best'
                elif quality == '480p':
                    ydl_opts['format'] = 'best[height<=480]/best[height<=720]/best'
                elif quality == '720p':
                    ydl_opts['format'] = 'best[height<=720]/best'
                elif quality == '1080p':
                    ydl_opts['format'] = 'best[height<=1080]/best'
                elif quality == 'worst':
                    ydl_opts['format'] = 'worst'
                else:  # best or any other
                    ydl_opts['format'] = 'best'
                
                self.logger.info(f"Video quality mode: {quality}, format: {ydl_opts['format']}")
                
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }]
            
            self.logger.info("Starting yt-dlp download...")
            # Download
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.queue.put(("status", "Скачивание..."))
                ydl.download([url])
                self.queue.put(("status", "Загрузка завершена!"))
                self.queue.put(("progress", 100))
                self.queue.put(("log", "Загрузка успешно завершена!"))
                self.logger.info("Download completed successfully")
        
        except Exception as e:
            self.log_error("Error in download worker", e)
            self.queue.put(("error", f"Ошибка загрузки: {str(e)}"))
        
        finally:
            self.queue.put(("finished", None))
    
    def extract_audio_with_progress(self, input_file, output_file, audio_quality):
        """Extract audio with real progress tracking using FFmpeg"""
        try:
            self.logger.info(f"Starting audio extraction: {input_file} -> {output_file}")
            
            # Set audio bitrate based on quality
            if audio_quality == 'высокое':
                bitrate = '320k'
            elif audio_quality == 'среднее':
                bitrate = '192k'
            else:  # низкое
                bitrate = '128k'
            
            # FFmpeg command for audio extraction
            cmd = [
                'ffmpeg', '-i', input_file,
                '-vn', '-acodec', 'mp3', '-ab', bitrate,
                '-y', output_file
            ]
            
            self.logger.info(f"FFmpeg command: {' '.join(cmd)}")
            self.queue.put(("log", f"Качество аудио: {audio_quality} ({bitrate})"))
            
            # Start FFmpeg process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=False,  # Don't use text mode
                bufsize=1
            )
            
            total_duration = None
            line_count = 0
            
            # Read FFmpeg output line by line with proper encoding handling
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                
                line_count += 1
                try:
                    # Try to decode with UTF-8 first, then fallback to cp1251
                    try:
                        line = line.decode('utf-8').strip()
                    except UnicodeDecodeError:
                        line = line.decode('cp1251', errors='replace').strip()
                    
                    self.logger.debug(f"FFmpeg output {line_count}: {line}")
                    
                    # Parse duration from FFmpeg output
                    duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})', line)
                    if duration_match and total_duration is None:
                        hours, minutes, seconds = duration_match.groups()
                        total_duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                        self.logger.info(f"Total duration: {total_duration} seconds")
                        continue
                    
                    # Parse current time from FFmpeg output
                    time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2}\.\d{2})', line)
                    if time_match and total_duration:
                        hours, minutes, seconds = time_match.groups()
                        current_time = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                        
                        # Calculate progress percentage
                        progress = (current_time / total_duration) * 100
                        self.logger.debug(f"Progress: {progress:.1f}% (time: {current_time}/{total_duration})")
                        self.queue.put(("progress", progress))
                        self.queue.put(("status", f"Конвертация в MP3... {progress:.1f}%"))
                        self.queue.put(("log", f"Конвертация аудио: {progress:.1f}%"))
                        
                except Exception as e:
                    self.logger.warning(f"Failed to process FFmpeg output line {line_count}: {e}")
                    continue
            
            # Wait for process to complete
            return_code = process.wait()
            self.logger.info(f"FFmpeg process finished with return code: {return_code}")
            
            if return_code == 0:
                self.queue.put(("progress", 100))
                self.queue.put(("log", f"Конвертация завершена: {os.path.basename(output_file)}"))
                # Remove original file
                try:
                    os.remove(input_file)
                    self.logger.info(f"Removed original file: {input_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to remove original file: {e}")
            else:
                error_msg = f"FFmpeg failed with return code {return_code}"
                self.log_error(error_msg)
                self.queue.put(("error", "Ошибка конвертации аудио"))
                
        except Exception as e:
            self.log_error("Error in audio extraction", e)
            self.queue.put(("error", f"Ошибка конвертации: {str(e)}"))
    
    def progress_hook(self, d):
        """Progress hook for yt-dlp"""
        if d['status'] == 'downloading':
            # Get download progress
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded_bytes = d.get('downloaded_bytes', 0)
            
            if total_bytes > 0:
                percent = (downloaded_bytes / total_bytes) * 100
                self.queue.put(("progress", percent))
                self.queue.put(("status", f"Скачивание... {percent:.1f}%"))
                self.queue.put(("log", f"Скачивание: {d.get('filename', 'Unknown')} - {percent:.1f}%"))
            else:
                # Fallback to percentage string if available
                percent_str = d.get('_percent_str', '0.0%')
                try:
                    percent = float(percent_str.strip('%'))
                    self.queue.put(("progress", percent))
                    self.queue.put(("status", f"Скачивание... {percent_str}"))
                    self.queue.put(("log", f"Скачивание: {d.get('filename', 'Unknown')} - {percent_str}"))
                except ValueError:
                    self.queue.put(("status", "Скачивание..."))
                    self.queue.put(("log", f"Скачивание: {d.get('filename', 'Unknown')}"))
                    
        elif d['status'] == 'finished':
            self.queue.put(("log", f"Завершено: {d.get('filename', 'Unknown')}"))
            
        elif d['status'] == 'error':
            self.queue.put(("error", f"Ошибка скачивания: {d.get('filename', 'Unknown')}"))
    
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
