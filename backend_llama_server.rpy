init python:
    import atexit
    import os
    import subprocess
    import time
    import requests

    LLAMA_SERVER_MODEL_DIR = os.path.join(renpy.config.gamedir, "ai_engine")
    LLAMA_SERVER_EXE_PATH = os.path.join(
        LLAMA_SERVER_MODEL_DIR,
        "llama-server.exe" if os.name == "nt" else "llama-server"
    )
    LLAMA_SERVER_MODEL_PATH = os.path.join(LLAMA_SERVER_MODEL_DIR, "models", "qwen2.5-3b.gguf")
    LLAMA_SERVER_HOST = "127.0.0.1"
    LLAMA_SERVER_PORT = 8081
    LLAMA_SERVER_BASE_URL = "http://{}:{}".format(LLAMA_SERVER_HOST, LLAMA_SERVER_PORT)
    LLAMA_SERVER_CHAT_URL = LLAMA_SERVER_BASE_URL + "/v1/chat/completions"
    LLAMA_SERVER_HEALTH_URL = LLAMA_SERVER_BASE_URL + "/v1/models"
    LLAMA_SERVER_PROCESS = None

    def llama_server_backend_available():
        return os.path.exists(LLAMA_SERVER_EXE_PATH) and os.path.exists(LLAMA_SERVER_MODEL_PATH)

    def _llama_server_is_healthy():
        try:
            response = requests.get(LLAMA_SERVER_HEALTH_URL, timeout=1.5)
            return response.status_code == 200
        except Exception:
            return False

    def _llama_server_start_process():
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        return subprocess.Popen(
            [
                LLAMA_SERVER_EXE_PATH,
                "-m", LLAMA_SERVER_MODEL_PATH,
                "--host", LLAMA_SERVER_HOST,
                "--port", str(LLAMA_SERVER_PORT),
                "-c", "4096"
            ],
            cwd=LLAMA_SERVER_MODEL_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo
        )

    def llama_server_shutdown():
        global LLAMA_SERVER_PROCESS

        process = LLAMA_SERVER_PROCESS
        LLAMA_SERVER_PROCESS = None

        if process is None:
            return

        try:
            if process.poll() is not None:
                return
        except Exception:
            return

        try:
            process.terminate()
            process.wait(timeout=5)
        except Exception:
            try:
                process.kill()
                process.wait(timeout=2)
            except Exception:
                pass

    def llama_server_ensure_running(wait_timeout=20.0):
        global LLAMA_SERVER_PROCESS

        if not llama_server_backend_available():
            return False

        if _llama_server_is_healthy():
            return True

        if LLAMA_SERVER_PROCESS is None or LLAMA_SERVER_PROCESS.poll() is not None:
            try:
                LLAMA_SERVER_PROCESS = _llama_server_start_process()
            except Exception:
                LLAMA_SERVER_PROCESS = None
                return False

        deadline = time.time() + wait_timeout
        while time.time() < deadline:
            if _llama_server_is_healthy():
                return True

            if LLAMA_SERVER_PROCESS is not None and LLAMA_SERVER_PROCESS.poll() is not None:
                LLAMA_SERVER_PROCESS = None
                return False

            time.sleep(0.5)

        return False

    def _llama_server_request(messages, max_tokens, temperature, response_format=None, timeout=30):
        if not llama_server_ensure_running():
            return ""

        request_payload = {
            "model": "local",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        if response_format is not None:
            request_payload["response_format"] = response_format

        try:
            response = requests.post(
                LLAMA_SERVER_CHAT_URL,
                json=request_payload,
                timeout=timeout
            )
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                return ""

            message = choices[0].get("message", {})
            return (message.get("content") or "").strip()
        except Exception:
            return ""

    def llama_server_selection_request(system_msg, player_text, known_category_mode):
        return _llama_server_request(
            [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": player_text},
            ],
            max_tokens=8 if known_category_mode else 20,
            temperature=0.0,
            response_format=None,
            timeout=15
        )

    def llama_server_generative_request(system_msg, player_text):
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "generative_payload",
                "schema": {
                    "type": "object",
                    "properties": {
                        "analysis": {"type": "string"},
                        "reply": {"type": "string"},
                        "sentiment_category": {"type": "string"},
                        "reasoning": {"type": "string"},
                        "mood": {"type": "string"},
                        "summary": {"type": "string"}
                    },
                    "required": ["analysis", "reply", "sentiment_category", "reasoning", "mood", "summary"]
                }
            }
        }

        raw_content = _llama_server_request(
            [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": player_text},
            ],
            max_tokens=256,
            temperature=0.3,
            response_format=response_format,
            timeout=45
        )

        # Some llama-server builds return empty content for structured output requests.
        # Retry once without response_format and let the prompt enforce JSON-only output.
        if raw_content:
            return raw_content

        return _llama_server_request(
            [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": player_text},
            ],
            max_tokens=256,
            temperature=0.3,
            response_format=None,
            timeout=45
        )

    atexit.register(llama_server_shutdown)
