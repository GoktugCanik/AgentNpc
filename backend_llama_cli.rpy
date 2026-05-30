init python:
    import json
    import os
    import subprocess

    LLAMA_CLI_MODEL_DIR = os.path.join(renpy.config.gamedir, "ai_engine")
    LLAMA_CLI_EXE_PATH = os.path.join(
        LLAMA_CLI_MODEL_DIR,
        "llama-cli.exe" if os.name == "nt" else "llama-cli"
    )
    LLAMA_CLI_MODEL_PATH = os.path.join(LLAMA_CLI_MODEL_DIR, "models", "qwen2.5-3b.gguf")

    def llama_cli_backend_available():
        return os.path.exists(LLAMA_CLI_EXE_PATH) and os.path.exists(LLAMA_CLI_MODEL_PATH)

    def _llama_cli_cleanup_temp_files(*file_paths):
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)

    def _llama_cli_run_command(cmd, timeout=45):
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo,
            cwd=LLAMA_CLI_MODEL_DIR
        )
        stdout, stderr = process.communicate(timeout=timeout)
        return (
            stdout.decode("utf-8", errors="ignore").strip(),
            stderr.decode("utf-8", errors="ignore").strip()
        )

    def llama_cli_selection_request(system_msg, player_text, known_category_mode):
        if not llama_cli_backend_available():
            return ""

        temp_prompt_path = os.path.join(LLAMA_CLI_MODEL_DIR, "temp_selection_prompt.txt")
        full_prompt = (
            f"<|im_start|>system\n{system_msg}<|im_end|>\n"
            f"<|im_start|>user\n{player_text}<|im_end|>\n"
            "<|im_start|>assistant\n"
        )

        try:
            with open(temp_prompt_path, "w", encoding="utf-8") as f:
                f.write(full_prompt)

            if known_category_mode:
                cmd = [
                    LLAMA_CLI_EXE_PATH,
                    "-m", LLAMA_CLI_MODEL_PATH,
                    "-f", temp_prompt_path,
                    "-n", "16",
                    "--temp", "0.0",
                    "--ignore-eos"
                ]
                raw_content, _ = _llama_cli_run_command(cmd, timeout=30)
                return raw_content

            temp_schema_path = os.path.join(LLAMA_CLI_MODEL_DIR, "temp_selection_schema.json")
            schema_dict = {
                "type": "object",
                "properties": {
                    "selected_category": {"type": "string"},
                    "selected_index": {"type": "integer"}
                },
                "required": ["selected_category", "selected_index"]
            }

            with open(temp_schema_path, "w", encoding="utf-8") as f:
                json.dump(schema_dict, f)
            with open(temp_schema_path, "r", encoding="utf-8") as f:
                loaded_schema_string = f.read()

            cmd = [
                LLAMA_CLI_EXE_PATH,
                "-m", LLAMA_CLI_MODEL_PATH,
                "-f", temp_prompt_path,
                "--json-schema", loaded_schema_string,
                "-n", "32",
                "--temp", "0.0"
            ]
            raw_content, _ = _llama_cli_run_command(cmd, timeout=30)
            return raw_content
        except Exception:
            return ""
        finally:
            _llama_cli_cleanup_temp_files(
                temp_prompt_path,
                os.path.join(LLAMA_CLI_MODEL_DIR, "temp_selection_schema.json") if not known_category_mode else None
            )

    def llama_cli_generative_request(system_msg, player_text):
        if not llama_cli_backend_available():
            return ""

        temp_prompt_path = os.path.join(LLAMA_CLI_MODEL_DIR, "temp_prompt.txt")
        temp_schema_path = os.path.join(LLAMA_CLI_MODEL_DIR, "temp_schema.json")
        full_prompt = (
            f"<|im_start|>system\n{system_msg}<|im_end|>\n"
            f"<|im_start|>user\n{player_text}<|im_end|>\n"
            "<|im_start|>assistant\n"
        )
        schema_dict = {
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

        try:
            with open(temp_prompt_path, "w", encoding="utf-8") as f:
                f.write(full_prompt)
            with open(temp_schema_path, "w", encoding="utf-8") as f:
                json.dump(schema_dict, f)
            with open(temp_schema_path, "r", encoding="utf-8") as f:
                loaded_schema_string = f.read()

            cmd = [
                LLAMA_CLI_EXE_PATH,
                "-m", LLAMA_CLI_MODEL_PATH,
                "-f", temp_prompt_path,
                "--json-schema", loaded_schema_string,
                "-n", "256",
                "--temp", "0.3"
            ]
            raw_content, _ = _llama_cli_run_command(cmd, timeout=45)
            return raw_content
        except Exception:
            return ""
        finally:
            _llama_cli_cleanup_temp_files(temp_prompt_path, temp_schema_path)
