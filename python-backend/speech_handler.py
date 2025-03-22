import speech_recognition as sr
import pyttsx3
from queue import Queue
from threading import Thread, Lock

recognizer = sr.Recognizer()
tts_engine = pyttsx3.init()
tts_engine.setProperty('voice', r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_EN-US_DAVID_11.0')

# Queue for TTS requests
tts_queue = Queue()
tts_lock = Lock()  # Prevent concurrent runAndWait calls
tts_thread = None

def process_voice_input():
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        try:
            audio = recognizer.listen(source, timeout=5)
            return recognizer.recognize_google(audio)
        except (sr.UnknownValueError, sr.RequestError) as e:
            print(f"Voice error: {str(e)}")
            return None

def tts_worker():
    while True:
        response = tts_queue.get()
        if response is None:  # Sentinel to stop the thread
            break
        with tts_lock:  # Ensure exclusive access
            tts_engine.say(response)
            tts_engine.runAndWait()
        tts_queue.task_done()

def speak_response(response):
    global tts_thread
    if tts_thread is None or not tts_thread.is_alive():
        tts_thread = Thread(target=tts_worker, daemon=True)
        tts_thread.start()
    tts_queue.put(response)
    print(f"Queued TTS: {response}")

def stop_tts():
    tts_queue.put(None)  # Stop the worker thread gracefully