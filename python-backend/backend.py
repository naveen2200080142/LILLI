from flask import Flask, request, jsonify
import speech_recognition as sr
import pyttsx3
import google.generativeai as genai
import os
import json
from threading import Thread

app = Flask(__name__)

# Gemini AI Setup
genai.configure(api_key=os.environ.get("API_KEY", "your-api-key-here"))
recognizer = sr.Recognizer()
tts_engine = pyttsx3.init()
tts_engine.setProperty('voice', r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_EN-US_DAVID_11.0')

# JSON file for chat history
HISTORY_FILE = "chat_history.json"

# Initial RAG Context (will grow with user interactions)
RAG_CONTEXT = """
JARVIS is an AI assistant designed to help users with tasks, inspired by Tony Stark's companion.
It uses advanced AI models and can respond via text and voice.
"""

def load_history():
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"Error loading history: {str(e)}")
        return []

def save_to_history(user_input, response):
    history = load_history()
    history.append({"user_input": user_input, "assistant_response": response})
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)
    print(f"Saved to JSON: {user_input} -> {response}")

def get_rag_context():
    global RAG_CONTEXT
    history = load_history()
    # Append recent interactions to RAG context (limit to last 10 for efficiency)
    recent_history = history[-10:] if len(history) > 10 else history
    context = RAG_CONTEXT + "\n\nRecent Interactions:\n"
    for entry in recent_history:
        context += f"User: {entry['user_input']}\nJARVIS: {entry['assistant_response']}\n"
    return context

def update_rag_context(new_text):
    global RAG_CONTEXT
    RAG_CONTEXT += f"\n\nUser-Provided Context: {new_text}"
    print(f"Updated RAG context with: {new_text}")

def get_ai_response(user_input):
    print(f"Generating AI response for: {user_input}")
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config={"temperature": 0.9, "top_p": 0.95, "max_output_tokens": 200}
    )
    prompt = f"{get_rag_context()}\nUser: {user_input}\nRespond as JARVIS in 20-30 words."
    try:
        response = model.generate_content(prompt).text
        print(f"AI Response: {response}")
        return response if response else "JARVIS: Error generating response."
    except Exception as e:
        error_msg = f"JARVIS: Apologies, sir. An error occurred: {str(e)}"
        print(f"AI Error: {error_msg}")
        return error_msg

def speak_response(response):
    def tts_task():
        try:
            tts_engine.say(response)
            tts_engine.runAndWait()
            print(f"Spoke response: {response}")
        except Exception as e:
            print(f"TTS Error: {str(e)}")
    Thread(target=tts_task).start()

@app.route('/api/message', methods=['POST'])
def handle_message():
    data = request.json
    print(f"Received request: {data}")
    user_input = data.get('message', '')
    is_voice = data.get('isVoice', False)
    file_content = data.get('file_content', '')  # For TXT file uploads

    if not user_input and not file_content:
        response = 'JARVIS: Please provide input or a file, sir.'
        print(f"Sending response: {response}")
        return jsonify({'response': response}), 400

    if file_content:
        update_rag_context(file_content)
        response = "JARVIS: File processed, sir. How may I assist further?"
        save_to_history("File Upload", response)
        speak_response(response)
        return jsonify({'response': response})

    if is_voice and user_input == "Listen":
        return handle_voice()

    response = get_ai_response(user_input)
    save_to_history(user_input, response)
    speak_response(response)
    print(f"Sending response: {response}")
    return jsonify({'response': response})

@app.route('/api/voice', methods=['POST'])
def handle_voice():
    print("Listening for voice input...")
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        audio = recognizer.listen(source, timeout=5)
    try:
        user_input = recognizer.recognize_google(audio)
        print(f"Recognized voice input: {user_input}")
        response = get_ai_response(user_input)
        save_to_history(user_input, response)
        speak_response(response)
        return jsonify({'response': response})
    except sr.UnknownValueError:
        response = "JARVIS: Apologies, sir. I couldn’t understand your command."
        speak_response(response)
        return jsonify({'response': response}), 400
    except sr.RequestError as e:
        response = f"JARVIS: Speech service error: {str(e)}"
        return jsonify({'response': response}), 500

if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=5000, debug=True)