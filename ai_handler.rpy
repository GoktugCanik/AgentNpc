default ai_backend = "llama_server"
default ai_engine_mode = "selection"

init python:
    import json
    import re

    AI_BACKEND_NAMES = ("llama_server", "llama_cli", "ollama")
    AI_BACKENDS = {
        "llama_server": {
            "selection": "llama_server_selection_request",
            "generative": "llama_server_generative_request"
        },
        "llama_cli": {
            "selection": "llama_cli_selection_request",
            "generative": "llama_cli_generative_request"
        },
        "ollama": {
            "selection": "ollama_selection_request",
            "generative": "ollama_generative_request"
        }
    }

    def normalize_ai_backend_name(backend_name):
        if backend_name is None:
            return "llama_server"

        normalized = str(backend_name).strip().lower()
        if normalized in AI_BACKEND_NAMES:
            return normalized
        return "llama_server"

    def set_ai_backend_mode(backend_name):
        store.ai_backend = normalize_ai_backend_name(backend_name)
        return store.ai_backend

    def get_ai_backend_mode():
        return normalize_ai_backend_name(getattr(store, "ai_backend", "llama_server"))

    def get_backend():
        backend_def = AI_BACKENDS.get(get_ai_backend_mode())
        if not backend_def:
            return None

        selection_name = backend_def.get("selection")
        generative_name = backend_def.get("generative")

        selection_fn = globals().get(selection_name)
        generative_fn = globals().get(generative_name)

        if not selection_fn or not generative_fn:
            return None

        return {
            "selection": selection_fn,
            "generative": generative_fn
        }

    AI_MODES = ("selection", "generative")

    def normalize_ai_mode(mode_name):
        if mode_name is None:
            return "selection"

        normalized = str(mode_name).strip().lower()
        if normalized in AI_MODES:
            return normalized
        return "selection"

    def set_ai_mode(mode_name):
        store.ai_engine_mode = normalize_ai_mode(mode_name)
        return store.ai_engine_mode

    def get_ai_mode():
        return normalize_ai_mode(getattr(store, "ai_engine_mode", "selection"))

    def get_world_lore():
        try:
            with renpy.file("ai_engine/world_lore.json") as f:
                return json.load(f)
        except Exception:
            return {}

    def get_relevant_lore(player_text, lore_data, npc_home=None):
        relevant = [f"Kingdom: {lore_data.get('kingdom', '')}"]

        for t in lore_data.get("towns", []):
            if t["name"].lower() in player_text.lower() or t["name"] == npc_home:
                relevant.append(f"Location {t['name']}: {t['current_state']}")

        for threat in lore_data.get("threats", []):
            if any(word.lower() in player_text.lower() for word in threat.split() if len(word) > 3):
                relevant.append(f"Threat: {threat}")

        return "\n".join(relevant)

    def get_npc_config(name):
        try:
            with renpy.file("ai_engine/personalities.json") as f:
                data = json.load(f)
            return data.get(name, {})
        except Exception:
            return {}

    def get_npc_dialogue_map(npc_name):
        try:
            with renpy.file("ai_engine/npc_texts.json") as f:
                data = json.load(f)
            return data.get(npc_name, {})
        except Exception:
            return {}

    def get_npc_dialogue_pool(npc_name, category):
        return get_npc_dialogue_map(npc_name).get(category, [])

    def _build_context_map(player_text, npc_obj, config, lore_data):
        current_lore = get_relevant_lore(player_text, lore_data, config.get("hometown", ""))
        return {
            "name": npc_obj.name,
            "backstory": config.get("backstory", "No known past."),
            "voice": config.get("voice", "Stay in character."),
            "current_lore": current_lore,
            "short_context": " | ".join(npc_obj.short_term) or "Just started talking.",
            "event_context": " | ".join(npc_obj.long_term) or "No recent interactions.",
            "trust": npc_obj.trust,
            "mood": npc_obj.mood
        }

    def _load_prompt(prompt_file_path, context_map):
        with renpy.file(prompt_file_path) as f:
            raw_template = f.read().decode("utf-8")
        return raw_template.format(**context_map)

    def _extract_first_json_object(raw_content):
        start_idx = raw_content.find("{")
        if start_idx == -1:
            raise ValueError("Structural JSON markers missing.")

        brace_depth = 0
        in_string = False
        escape_next = False

        for idx in range(start_idx, len(raw_content)):
            char = raw_content[idx]

            if in_string:
                if escape_next:
                    escape_next = False
                elif char == "\\":
                    escape_next = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
            elif char == "{":
                brace_depth += 1
            elif char == "}":
                brace_depth -= 1
                if brace_depth == 0:
                    return raw_content[start_idx:idx + 1]

        raise ValueError("Complete JSON object not found.")

    def _parse_json_response(raw_content):
        clean_content = (raw_content or "").strip()
        if clean_content.startswith("```"):
            clean_content = clean_content.strip("`").replace("json", "", 1).strip()

        return json.loads(_extract_first_json_object(clean_content))

    def _normalize_selected_category(selected_category, dialogue_map, fallback_category):
        if selected_category in dialogue_map:
            return selected_category

        selected_key = (selected_category or "").strip().lower()
        for category_name in dialogue_map.keys():
            if category_name.lower() == selected_key:
                return category_name

        return fallback_category

    def _extract_first_index(raw_content, fallback_idx=0):
        matches = re.findall(r"-?\d+", raw_content or "")
        if not matches:
            return fallback_idx

        try:
            return int(matches[0])
        except Exception:
            return fallback_idx

    def _extract_selection_payload(raw_content, dialogue_map, fallback_category):
        chosen_category = fallback_category
        chosen_idx = 0

        try:
            data = _parse_json_response(raw_content)
            chosen_category = _normalize_selected_category(
                data.get("selected_category", fallback_category),
                dialogue_map,
                fallback_category
            )
            chosen_idx = int(data.get("selected_index", 0))
            return chosen_category, chosen_idx
        except Exception:
            pass

        category_match = re.search(r'"selected_category"\s*:\s*"([^"]+)"', raw_content or "", re.I)
        index_match = re.search(r'"selected_index"\s*:\s*(-?\d+)', raw_content or "", re.I)

        if category_match:
            chosen_category = _normalize_selected_category(
                category_match.group(1),
                dialogue_map,
                fallback_category
            )
        if index_match:
            chosen_idx = int(index_match.group(1))

        return chosen_category, chosen_idx

    def _build_default_response(reply, analysis, reasoning, summary, config, mood="neutral", category="neutral"):
        return {
            "reply": reply,
            "analysis": analysis,
            "reasoning": reasoning,
            "summary": summary,
            "sentiment_category": category,
            "mood": mood,
            "trust_change": int(config.get("trust_logic", {}).get(category, 0))
        }

    def _request_selection_raw(system_msg, player_text, known_category_mode):
        backend = get_backend()

        if not backend:
            return ""
        try:
            return backend["selection"](system_msg, player_text, known_category_mode)
        except Exception:
            return ""

    def _request_generative_raw(system_msg, player_text):
        backend = get_backend()

        if not backend:
            return ""
        try:
            return backend["generative"](system_msg, player_text)
        except Exception:
            return ""

    def _execute_selection_mode(player_text, npc_obj, config, dialogue_map, context_map, requested_category=None):
        known_category_mode = requested_category and requested_category not in ("auto", "any")

        if known_category_mode:
            filtered_options = dialogue_map.get(requested_category, [])
            dialogue_map = {requested_category: filtered_options} if filtered_options else {}

        if not dialogue_map:
            fallback = _build_default_response(
                "...",
                "No dialogue options found for requested category.",
                "Dialogue pool missing",
                "Selection defaulted to fallback reply.",
                config
            )
            fallback["selected_index"] = 0
            return fallback

        context_map = dict(context_map)
        context_map["player_text"] = player_text

        if known_category_mode:
            selected_options = next(iter(dialogue_map.values()))
            context_map["selection_scope"] = "The scene already selected the dialogue category: {}.".format(requested_category)
            context_map["category_options"] = "\n".join(
                ["[{}] {}".format(i, opt) for i, opt in enumerate(selected_options)]
            )
            context_map["output_rule"] = "Return ONLY the best matching reply index as a single integer. Example: 0"
        else:
            context_map["selection_scope"] = (
                "Choose the best matching dialogue category from these available categories:\n{}\n"
                "Then choose the best reply index inside that category."
            ).format(", ".join(dialogue_map.keys()))
            context_map["category_options"] = "\n\n".join(
                "{}:\n{}".format(
                    category_name,
                    "\n".join(["[{}] {}".format(i, opt) for i, opt in enumerate(options)])
                )
                for category_name, options in dialogue_map.items() if options
            )
            context_map["output_rule"] = (
                "Return ONLY JSON with this shape:\n"
                "{{\n"
                '  "selected_category": "greeting",\n'
                '  "selected_index": 0\n'
                "}}"
            )

        try:
            system_msg = _load_prompt("ai_engine/prompts/system_selection.txt", context_map)
        except Exception as e:
            return _build_default_response(
                "Prompt File Missing at ai_engine/prompts/system_selection.txt. Error: {}".format(str(e)),
                "Selection prompt load failed.",
                "Prompt file error",
                "Selection could not start.",
                config
            )

        raw_content = _request_selection_raw(system_msg, player_text, known_category_mode)

        fallback_category = "greeting" if "greeting" in dialogue_map else next(iter(dialogue_map.keys()))
        fallback_options = dialogue_map[fallback_category]
        chosen_category = fallback_category
        chosen_idx = 0

        if known_category_mode:
            chosen_idx = _extract_first_index(raw_content, fallback_idx=0)
            reasoning = "Selection via fixed category index."
        else:
            chosen_category, chosen_idx = _extract_selection_payload(
                raw_content,
                dialogue_map,
                fallback_category
            )
            reasoning = "Selection via AI category and index."

        selected_options = dialogue_map.get(chosen_category, fallback_options)
        if not (0 <= chosen_idx < len(selected_options)):
            chosen_idx = 0

        result = _build_default_response(
            selected_options[chosen_idx],
            raw_content or "Selection backend returned no text.",
            reasoning,
            "Selection via fast category lookup." if known_category_mode else "Selection via AI category and index.",
            config,
            category="neutral"
        )
        result["selected_category"] = chosen_category
        result["selected_index"] = chosen_idx
        return result

    def _execute_generative_mode(player_text, npc_obj, config, context_map):
        try:
            system_msg = _load_prompt("ai_engine/prompts/system_generative.txt", context_map)
        except Exception as e:
            return _build_default_response(
                "Prompt File Missing at ai_engine/prompts/system_generative.txt. Error: {}".format(str(e)),
                "Generative prompt load failed.",
                "Prompt file error",
                "Generative mode could not start.",
                config
            )

        raw_content = _request_generative_raw(system_msg, player_text)
        if not raw_content:
            return _build_default_response(
                "All AI backends failed to return content.",
                "No backend response received.",
                "Backend failure",
                "Generative mode returned no structured content.",
                config,
                mood="Mute"
            )

        try:
            res = _parse_json_response(raw_content)
        except Exception as e:
            return _build_default_response(
                "Structured response parse failed: {}".format(str(e)),
                raw_content,
                "JSON parse failure",
                "Generative output was not valid structured JSON.",
                config,
                mood="Broken"
            )

        cat = res.get("sentiment_category", "neutral").lower().strip()
        res["trust_change"] = int(config.get("trust_logic", {}).get(cat, 0))
        return res

    def ask_local_ai(player_text, npc_obj, category=None, mode=None, scene_id=None):
        config = get_npc_config(npc_obj.name)
        lore_data = get_world_lore()

        if not config:
            return {"reply": "NPC Configuration missing.", "trust_change": 0}
        if not lore_data:
            return {"reply": "World Lore missing.", "trust_change": 0}

        context_map = _build_context_map(player_text, npc_obj, config, lore_data)
        if scene_id is not None:
            context_map["scene_id"] = scene_id
        active_mode = normalize_ai_mode(mode if mode is not None else get_ai_mode())

        if active_mode == "selection":
            dialogue_map = get_npc_dialogue_map(npc_obj.name)
            return _execute_selection_mode(
                player_text,
                npc_obj,
                config,
                dialogue_map,
                context_map,
                requested_category=category or "auto"
            )

        return _execute_generative_mode(player_text, npc_obj, config, context_map)
