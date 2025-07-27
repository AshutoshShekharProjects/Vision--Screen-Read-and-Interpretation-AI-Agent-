# For GUI
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import json
import os
import queue
import sys

# For AIScreenReaderAgent
import win32gui
import win32ui
import win32con
import pyautogui
from PIL import Image
import pyttsx3
import time
import google.generativeai as genai
from murf import Murf
import io
import requests
import re
import pygame


if sys.prefix != sys.base_prefix:
    # Hardcoding the Tcl/Tk library paths as working in virtual environments causes issues with Tkinter.
    # This uses the specific Python path.
    try:
        # Path to your main Python 3.13 installation directory
        python_base_dir = r"C:\Users\ashut\AppData\Local\Programs\Python\Python313"

        # We construct the expected paths to the tcl and tk libraries
        tcl_library_path = os.path.join(python_base_dir, "tcl", "tcl8.6")
        tk_library_path = os.path.join(python_base_dir, "tcl", "tk8.6")

        # If these paths exist, we set the environment variables to point to them
        if os.path.isdir(tcl_library_path) and os.path.isdir(tk_library_path):
            os.environ["TCL_LIBRARY"] = tcl_library_path
            os.environ["TK_LIBRARY"] = tk_library_path

        else:
            # If the paths are not found, we print an error.
            print(
                f"--- Diagnostic ERROR: Could not find Tcl/Tk libraries in the hardcoded path: {python_base_dir}\\tcl ---"
            )
            print(
                "--- Please double-check that this path is correct and contains a 'tcl' folder. ---"
            )

    except Exception as e:
        print(
            f"--- Diagnostic ERROR: An error occurred while setting Tcl/Tk paths: {e} ---"
        )
    # --- END OF DIAGNOSTIC CODE ---


class AIScreenReaderAgent:
    def __init__(self, status_callback=None, response_callback=None):
        """Initialize the agent with callbacks to update the GUI."""
        self.status_callback = status_callback
        self.response_callback = response_callback
        self.google_api_key = None
        self.murf_api_key = None
        self.tts_provider = "pyttsx3"

        self.gemini_model = None
        self.tts_engine = None
        self.murf_client = None

        self.is_reading = False
        self.reading_thread = None
        self.conversation_history = []

        self.system_prompt = """You are an intelligent screen reading assistant. Your job is to:
1. Analyze screen content and provide intelligent summaries
2. Answer questions about what's on screen
3. Identify key information, actionable items, and important elements
4. Be conversational, helpful, and concise. Focus on what's most important or relevant."""

        self.user_preferences = {
            "murf_voice_id": "en-US-natalie",
            "murf_style": "conversational",
        }

        # Initialize pygame mixer for audio playback
        try:
            pygame.mixer.init()
        except pygame.error as e:
            self.log_status(
                f"Error initializing pygame mixer: {e}. Murf TTS may not work."
            )

    def log_status(self, message):
        """Send status updates to the GUI."""
        if self.status_callback:
            self.status_callback(message)
        else:
            print(message)

    def log_response(self, role, content):
        """Send conversation responses to the GUI."""
        if self.response_callback:
            self.response_callback(role, content)
        else:
            print(f"{role.capitalize()}: {content}")

    def configure(
        self,
        google_api_key,
        murf_api_key=None,
        tts_provider="pyttsx3",
        murf_voice_id="en-US-natalie",
    ):
        """Configure API keys and settings from the GUI."""
        self.google_api_key = google_api_key
        self.murf_api_key = murf_api_key
        self.tts_provider = tts_provider
        self.user_preferences["murf_voice_id"] = murf_voice_id

        try:
            genai.configure(api_key=self.google_api_key)
            self.gemini_model = genai.GenerativeModel("gemini-1.5-flash")
            self.log_status("Gemini AI configured successfully.")
        except Exception as e:
            self.log_status(f"Error configuring Gemini: {e}")
            return False

        if self.tts_provider == "murf" and self.murf_api_key:
            try:
                self.murf_client = Murf(api_key=self.murf_api_key)
                self.log_status("Murf AI TTS configured successfully.")
            except Exception as e:
                self.log_status(
                    f"Error configuring Murf AI: {e}. Falling back to pyttsx3."
                )
                self.tts_provider = "pyttsx3"
                self.setup_pyttsx3()
        else:
            self.setup_pyttsx3()
        return True

    def setup_pyttsx3(self):
        """Configure pyttsx3 text-to-speech."""
        try:
            self.tts_engine = pyttsx3.init()
            voices = self.tts_engine.getProperty("voices")
            if voices:
                self.tts_engine.setProperty("voice", voices[0].id)
            self.tts_engine.setProperty("rate", 160)
            self.tts_engine.setProperty("volume", 0.9)
            self.log_status("pyttsx3 TTS configured successfully.")
        except Exception as e:
            self.log_status(f"Error configuring pyttsx3: {e}")

    # Splitting long texts into smaller chunks for Murf ie. less than 300 characters
    def chunk_text_for_murf(self, text: str, max_chars: int = 2800) -> list:
        if len(text) <= max_chars:
            return [text]
        chunks, sentences = [], text.split(". ")
        current_chunk = ""
        for sentence in sentences:
            sentence_with_period = sentence + (
                ". " if not sentence.endswith(".") else " "
            )
            if len(current_chunk + sentence_with_period) <= max_chars:
                current_chunk += sentence_with_period
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence_with_period
        if current_chunk:
            chunks.append(current_chunk.strip())
        return chunks

    def generate_murf_speech(self, text: str):
        try:
            text_chunks = self.chunk_text_for_murf(text)
            audio_chunks = []
            self.log_status(
                f"Generating {len(text_chunks)} audio chunk(s) from Murf..."
            )
            for i, chunk in enumerate(text_chunks):
                self.log_status(f"Processing chunk {i + 1}/{len(text_chunks)}...")
                response = self.murf_client.text_to_speech.generate(
                    text=chunk, voice_id=self.user_preferences["murf_voice_id"]
                )
                if hasattr(response, "audio_file"):
                    audio_response = requests.get(response.audio_file)
                    audio_chunks.append(audio_response.content)
                if i < len(text_chunks) - 1:
                    time.sleep(0.5)
            return audio_chunks
        except Exception as e:
            self.log_status(f"MURF TTS Error: {e}")
            raise e

    def play_audio_from_bytes(self, audio_data_list):
        try:
            for i, audio_data in enumerate(audio_data_list):
                if not self.is_reading:
                    break
                self.log_status(
                    f"Playing audio chunk {i + 1}/{len(audio_data_list)}..."
                )
                audio_buffer = io.BytesIO(audio_data)
                pygame.mixer.music.load(audio_buffer)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy() and self.is_reading:
                    time.sleep(0.1)
        except Exception as e:
            self.log_status(f"Audio playback error: {e}")

    def capture_active_window(self) -> Image.Image:
        try:
            hwnd = win32gui.GetForegroundWindow()
            x, y, right, bottom = win32gui.GetWindowRect(hwnd)
            width, height = right - x, bottom - y
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)
            bmpstr = saveBitMap.GetBitmapBits(True)
            im = Image.frombuffer("RGB", (width, height), bmpstr, "raw", "BGRX", 0, 1)
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
            return im
        except Exception as e:
            self.log_status(f"Error capturing active window: {e}")
            return pyautogui.screenshot()

    def analyze_screen_with_vision_llm(
        self, image: Image.Image, user_query: str = None
    ) -> str:
        if not self.gemini_model:
            self.log_status("Error: Gemini model not configured.")
            return "AI model is not configured. Please check your API key in settings."
        try:
            self.log_status("Analyzing screen with Gemini Vision...")
            prompt_text = f"{self.system_prompt}\n\n"
            if user_query:
                prompt_text += f'Analyze this screen image and answer the user\'s question: "{user_query}"'
            else:
                prompt_text += "Analyze this screen image and provide an intelligent summary of its content and interactive elements."

            contents = [prompt_text, image]
            response = self.gemini_model.generate_content(contents)
            analysis = response.text
            self.log_status("AI analysis complete.")
            return analysis
        except Exception as e:
            self.log_status(f"Gemini Vision Error: {e}")
            return f"An error occurred during AI analysis: {e}"

    def speak_text(self, text: str):
        if not text or self.is_reading:
            return
        self.is_reading = True
        try:
            speech_text = re.sub(r"[\*#]+", "", text)
            if self.tts_provider == "murf" and self.murf_client:
                self.log_status("Generating speech with Murf AI...")
                audio_data = self.generate_murf_speech(speech_text)
                self.play_audio_from_bytes(audio_data)
            elif self.tts_engine:
                self.log_status("Generating speech with pyttsx3...")
                self.tts_engine.say(speech_text)
                self.tts_engine.runAndWait()
            else:
                self.log_status("No TTS provider is configured.")
        except Exception as e:
            self.log_status(f"TTS Error: {e}")
        finally:
            self.is_reading = False
            self.log_status("Ready.")

    def stop_speaking(self):
        if not self.is_reading:
            return
        self.log_status("Stopping speech...")
        self.is_reading = False
        if self.tts_provider == "murf":
            pygame.mixer.music.stop()
        if self.tts_engine and self.tts_engine._inLoop:
            self.tts_engine.stop()
        if self.reading_thread and self.reading_thread.is_alive():
            # This is a bit abrupt, but necessary to stop pyttsx3's loop
            # A more graceful solution would involve setting a flag that the thread checks
            pass
        self.log_status("Speech stopped.")

    def smart_read_screen(self, capture_mode="screen", query=None):
        if self.is_reading:
            self.log_status("Already reading. Please wait or stop the current speech.")
            return

        self.log_status(f"Capturing {capture_mode}...")
        image = (
            self.capture_active_window()
            if capture_mode == "window"
            else pyautogui.screenshot()
        )

        if query:
            self.log_response("user", query)

        analysis = self.analyze_screen_with_vision_llm(image, query)

        if analysis:
            self.log_response("assistant", analysis)
            self.reading_thread = threading.Thread(
                target=self.speak_text, args=(analysis,)
            )
            self.reading_thread.daemon = True
            self.reading_thread.start()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI Screen Reader Agent")
        self.geometry("800x600")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.settings_file = "app_settings.json"
        self.gui_queue = queue.Queue()

        # Initialize the agent with callbacks
        self.agent = AIScreenReaderAgent(
            status_callback=self.queue_status_update,
            response_callback=self.queue_response_update,
        )

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Top Frame for Controls ---
        self.top_frame = ctk.CTkFrame(self, height=50)
        self.top_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.top_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.read_screen_button = ctk.CTkButton(
            self.top_frame, text="Read Full Screen", command=self.on_read_screen
        )
        self.read_screen_button.grid(row=0, column=0, padx=5, pady=5)

        self.read_window_button = ctk.CTkButton(
            self.top_frame, text="Read Active Window", command=self.on_read_window
        )
        self.read_window_button.grid(row=0, column=1, padx=5, pady=5)

        self.stop_button = ctk.CTkButton(
            self.top_frame,
            text="Stop Speaking",
            command=self.agent.stop_speaking,
            fg_color="#D32F2F",
            hover_color="#B71C1C",
        )
        self.stop_button.grid(row=0, column=2, padx=5, pady=5)

        self.settings_button = ctk.CTkButton(
            self.top_frame, text="Settings", command=self.open_settings_window
        )
        self.settings_button.grid(row=0, column=3, padx=5, pady=5)

        # --- Main Frame for Chat/Response ---
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=1, column=0, padx=10, pady=0, sticky="nsew")
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.response_textbox = ctk.CTkTextbox(
            self.main_frame, state="disabled", wrap="word", font=("Arial", 14)
        )
        self.response_textbox.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # --- Bottom Frame for User Input ---
        self.bottom_frame = ctk.CTkFrame(self, height=50)
        self.bottom_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        self.bottom_frame.grid_columnconfigure(0, weight=1)

        self.question_entry = ctk.CTkEntry(
            self.bottom_frame, placeholder_text="Ask a question about the screen..."
        )
        self.question_entry.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.question_entry.bind("<Return>", self.on_ask_question)

        self.ask_button = ctk.CTkButton(
            self.bottom_frame, text="Ask", command=self.on_ask_question
        )
        self.ask_button.grid(row=0, column=1, padx=10, pady=10)

        # --- Status Bar ---
        self.status_bar = ctk.CTkLabel(
            self, text="Ready. Load API keys in Settings to begin.", anchor="w"
        )
        self.status_bar.grid(row=3, column=0, padx=10, pady=5, sticky="ew")

        # Load settings and configure agent
        self.settings = self.load_settings()
        self.configure_agent_from_settings()

        # Start processing the queue
        self.process_gui_queue()

        # Handle window closing
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        """Handle application exit."""
        self.agent.stop_speaking()
        pygame.mixer.quit()
        self.destroy()

    def process_gui_queue(self):
        """Process updates from the agent thread safely."""
        try:
            while not self.gui_queue.empty():
                msg_type, data = self.gui_queue.get_nowait()
                if msg_type == "status":
                    self.status_bar.configure(text=data)
                elif msg_type == "response":
                    role, content = data
                    self.update_response_box(role, content)
        finally:
            self.after(100, self.process_gui_queue)

    def queue_status_update(self, message):
        """Queue a status update from another thread."""
        self.gui_queue.put(("status", message))

    def queue_response_update(self, role, content):
        """Queue a response update from another thread."""
        self.gui_queue.put(("response", (role, content)))

    def update_response_box(self, role, content):
        """Updates the response text box with new content."""
        self.response_textbox.configure(state="normal")
        self.response_textbox.insert(
            tk.END, f"{role.upper()}:\n", (role.lower(), "bold")
        )
        self.response_textbox.insert(tk.END, f"{content}\n\n")
        self.response_textbox.configure(state="disabled")
        self.response_textbox.see(tk.END)

        # Configure tags for styling
        self.response_textbox.tag_config(
            "user", foreground="#76A9EA", font=("Arial", 14, "bold")
        )
        self.response_textbox.tag_config(
            "assistant", foreground="#A3BE8C", font=("Arial", 14, "bold")
        )

    def run_agent_task(self, target, *args):
        """Runs an agent method in a separate thread to avoid freezing the GUI."""
        if not self.agent.google_api_key:
            messagebox.showerror(
                "API Key Missing",
                "Please set your Google Gemini API Key in the Settings.",
            )
            return

        thread = threading.Thread(target=target, args=args)
        thread.daemon = True
        thread.start()

    def on_read_screen(self):
        self.run_agent_task(self.agent.smart_read_screen, "screen")

    def on_read_window(self):
        self.run_agent_task(self.agent.smart_read_screen, "window")

    def on_ask_question(self, event=None):
        question = self.question_entry.get()
        if question:
            self.run_agent_task(self.agent.smart_read_screen, "screen", question)
            self.question_entry.delete(0, tk.END)

    def load_settings(self):
        """Loads settings from a JSON file."""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def save_settings(self, settings_to_save):
        """Saves settings to a JSON file."""
        try:
            with open(self.settings_file, "w") as f:
                json.dump(settings_to_save, f, indent=4)
            self.settings = settings_to_save
            self.configure_agent_from_settings()
            messagebox.showinfo(
                "Settings Saved", "Your settings have been saved successfully."
            )
        except IOError:
            messagebox.showerror("Error", "Could not save settings to file.")

    def configure_agent_from_settings(self):
        """Configures the agent using loaded settings."""
        google_key = self.settings.get("google_api_key", "")
        murf_key = self.settings.get("murf_api_key", "")
        tts_provider = self.settings.get("tts_provider", "pyttsx3")
        murf_voice = self.settings.get("murf_voice_id", "en-US-natalie")

        if google_key:
            self.agent.configure(google_key, murf_key, tts_provider, murf_voice)
        else:
            self.status_bar.configure(
                text="Welcome! Please configure your Google API key in Settings."
            )

    def open_settings_window(self):
        """Opens the settings dialog window."""
        settings_win = SettingsWindow(self, self.settings, self.save_settings)
        settings_win.grab_set()  # Make window modal


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, current_settings, save_callback):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("500x350")
        self.transient(parent)  # Keep on top of the main window

        self.save_callback = save_callback

        self.grid_columnconfigure(1, weight=1)

        # Google API Key
        ctk.CTkLabel(self, text="Google Gemini API Key:").grid(
            row=0, column=0, padx=10, pady=10, sticky="w"
        )
        self.google_key_entry = ctk.CTkEntry(self, width=300, show="*")
        self.google_key_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.google_key_entry.insert(0, current_settings.get("google_api_key", ""))

        # Murf API Key
        ctk.CTkLabel(self, text="Murf AI API Key:").grid(
            row=1, column=0, padx=10, pady=10, sticky="w"
        )
        self.murf_key_entry = ctk.CTkEntry(self, width=300, show="*")
        self.murf_key_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        self.murf_key_entry.insert(0, current_settings.get("murf_api_key", ""))

        # TTS Provider
        ctk.CTkLabel(self, text="TTS Provider:").grid(
            row=2, column=0, padx=10, pady=10, sticky="w"
        )
        self.tts_provider_var = tk.StringVar(
            value=current_settings.get("tts_provider", "pyttsx3")
        )
        self.tts_provider_menu = ctk.CTkOptionMenu(
            self, variable=self.tts_provider_var, values=["pyttsx3", "murf"]
        )
        self.tts_provider_menu.grid(row=2, column=1, padx=10, pady=10, sticky="w")

        # Murf Voice ID
        ctk.CTkLabel(self, text="Murf Voice ID:").grid(
            row=3, column=0, padx=10, pady=10, sticky="w"
        )
        self.murf_voice_entry = ctk.CTkEntry(self, width=200)
        self.murf_voice_entry.grid(row=3, column=1, padx=10, pady=10, sticky="w")
        self.murf_voice_entry.insert(
            0, current_settings.get("murf_voice_id", "en-US-natalie")
        )

        # Save Button
        self.save_button = ctk.CTkButton(
            self, text="Save and Apply", command=self.save_and_close
        )
        self.save_button.grid(row=4, column=0, columnspan=2, padx=10, pady=20)

    def save_and_close(self):
        new_settings = {
            "google_api_key": self.google_key_entry.get().strip(),
            "murf_api_key": self.murf_key_entry.get().strip(),
            "tts_provider": self.tts_provider_var.get(),
            "murf_voice_id": self.murf_voice_entry.get().strip(),
        }
        self.save_callback(new_settings)
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
