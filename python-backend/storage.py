import json
import os

HISTORY_FILE = "chat_history.json"

def load_history():
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"Error loading history: {str(e)}")
        return []

def save_to_history(user_input, response):
    history = load_history()
    history.append({"user_input": user_input, "assistant_response": response})
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)
    print(f"Saved: {user_input} -> {response}")