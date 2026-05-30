init python:
    import requests

    OLLAMA_API_URL = "http://localhost:11434/api/chat"
    OLLAMA_MODEL_NAME = "qwen2.5:3b"

    def ollama_selection_request(system_msg, player_text, known_category_mode):
        try:
            request_payload = {
                "model": OLLAMA_MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": player_text},
                ],
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "num_predict": 16 if known_category_mode else 32
                }
            }
            if not known_category_mode:
                request_payload["format"] = "json"

            r = requests.post(
                OLLAMA_API_URL,
                json=request_payload,
                timeout=30,
            )
            return r.json()["message"]["content"].strip()
        except Exception:
            return ""

    def ollama_generative_request(system_msg, player_text):
        try:
            r = requests.post(
                OLLAMA_API_URL,
                json={
                    "model": OLLAMA_MODEL_NAME,
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": player_text},
                    ],
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 256
                    }
                },
                timeout=60,
            )
            return r.json()["message"]["content"].strip()
        except Exception:
            return ""
