from flask import Flask, request, jsonify
import os
from rag_handler import get_response_from_rag_with_history, update_rag_context
from storage import load_history, save_to_history
from speech_handler import process_voice_input, speak_response

app = Flask(__name__)

@app.route('/api/message', methods=['POST'])
def handle_message():
    data = request.json
    user_input = data.get('message', '')
    is_voice = data.get('isVoice', False)
    file_content = data.get('file_content', '')

    if not user_input and not file_content:
        response = "JARVIS: Please provide input or a file, sir."
        return jsonify({'response': response}), 400

    if file_content:
        update_rag_context(file_content)
        response = "JARVIS: File processed, sir. How may I assist further?"
        save_to_history("File Upload", response)
        speak_response(response)
        return jsonify({'response': response})

    if is_voice and user_input == "Listen":
        return handle_voice()

    session_id = "default_session"  # Placeholder; use user-specific ID later
    response = get_response_from_rag_with_history("default_user", session_id, user_input)
    save_to_history(user_input, response)
    speak_response(response)
    return jsonify({'response': response})

@app.route('/api/voice', methods=['POST'])
def handle_voice():
    user_input = process_voice_input()
    if not user_input:
        response = "JARVIS: Sorry, sir, I couldn’t hear you."
        speak_response(response)
        return jsonify({'response': response}), 400

    session_id = "default_session"
    response = get_response_from_rag_with_history("default_user", session_id, user_input)
    save_to_history(user_input, response)
    speak_response(response)
    return jsonify({'response': response})

@app.route('/api/history', methods=['GET'])
def get_history():
    history = load_history()
    last_10 = history[-10:] if len(history) > 10 else history
    return jsonify({'history': last_10})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)