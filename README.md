# ai_engine

`ai_engine` is a reusable Ren'Py NPC dialogue module built for local AI-assisted interactive narrative games.

It combines:

- persistent NPC state
- selection-based dialogue
- generative dialogue
- multiple local AI backends
- trust, mood, and memory updates
- prompt-based response control

This repository version is intended to contain the engine source files, prompt files, and JSON data used by the system.

## Features

- Supports two dialogue modes:
  - `selection`
  - `generative`
- Supports multiple backend routes:
  - `llama_server`
  - `llama_cli`
  - `ollama`
- Tracks per-NPC state:
  - trust
  - mood
  - short-term memory
  - long-term events
- Loads NPC personality and lore from JSON files
- Parses structured AI output into gameplay updates
- Designed to plug into a Ren'Py project

## Quick Setup

If someone downloads this repository and wants to run it, they need to prepare a backend first.

### Option 1: Use `llama_server` or `llama_cli`

If you want to use `llama_server` or `llama_cli`, you should:

1. place the backend executable files inside the `ai_engine` folder
2. create a folder named `models` inside `ai_engine`
3. put your `.gguf` model file inside `ai_engine/models/`

The current code expects paths like these:

- `ai_engine/llama-server.exe`
- `ai_engine/llama-cli.exe`
- `ai_engine/models/qwen2.5-3b.gguf`

So if you use the current defaults, your local structure should look like:

```text
ai_engine/
  ai_handler.rpy
  backend_llama_server.rpy
  backend_llama_cli.rpy
  backend_ollama.rpy
  npc_engine.rpy
  prompts/
  models/
    qwen2.5-3b.gguf
  llama-server.exe
  llama-cli.exe
```

If you use a different model filename or location, update the paths in:

- `backend_llama_server.rpy`
- `backend_llama_cli.rpy`

### Option 2: Use `ollama`

If you want to use `ollama`, you do not need local `.gguf` placement inside this repository.

Instead, you should:

1. install Ollama on your machine
2. download or pull a model into Ollama
3. make sure the Ollama local API is running
4. update the model name in `backend_ollama.rpy` if needed

The current default Ollama model name is:

```python
OLLAMA_MODEL_NAME = "qwen2.5:3b"
```

### Backend Choice

The default backend and mode are set in `ai_handler.rpy`:

```python
default ai_backend = "llama_server"
default ai_engine_mode = "selection"
```

If you want to use Ollama by default, change `ai_backend` to:

```python
"ollama"
```

## Repository Contents

Expected source files in this repository:

- `ai_handler.rpy`
- `npc_engine.rpy`
- `backend_llama_server.rpy`
- `backend_llama_cli.rpy`
- `backend_ollama.rpy`
- `prompts/system_selection.txt`
- `prompts/system_generative.txt`
- `personalities.json`
- `personalities.schema.json`
- `npc_texts.json`
- `sprites.json`
- `world_lore.json`

## What Each File Does

### Core Runtime

- `ai_handler.rpy`

  - Main AI routing layer.
  - Chooses backend and mode.
  - Loads lore, personality, and dialogue data.
  - Builds prompt context.
  - Parses backend responses into a structured payload.
- `npc_engine.rpy`

  - Defines the `NPCEngine` class.
  - Stores trust, mood, short-term memory, long-term events, last category, and last reasoning.
  - Applies state updates from AI responses.

### Backend Adapters

- `backend_llama_server.rpy`

  - Uses a local `llama-server` style HTTP backend.
  - Starts and checks the local server process.
  - Sends selection and generative requests through the chat-completions API.
- `backend_llama_cli.rpy`

  - Uses a local `llama-cli` style command-line backend.
  - Writes temporary prompt/schema files.
  - Executes the model process and captures structured output.
- `backend_ollama.rpy`

  - Uses the local Ollama chat API.
  - Supports both selection and generative requests.

### Prompt Files

- `prompts/system_selection.txt`

  - Prompt template used for selection mode.
- `prompts/system_generative.txt`

  - Prompt template used for generative mode.

### Data Files

- `personalities.json`

  - NPC personality definitions.
  - Includes backstory, voice, social rules, triggers, and trust logic.
- `personalities.schema.json`

  - Schema reference for personality data.
- `npc_texts.json`

  - Selection-mode dialogue pools.
  - Organized by NPC and dialogue category.
- `sprites.json`

  - Sprite and mood mapping data.
- `world_lore.json`

  - Shared world knowledge injected into AI context.

## How It Works

The general runtime flow is:

1. The player selects an NPC.
2. The player talks in either `selection` or `generative` mode.
3. `ai_handler.rpy` loads the current NPC configuration and world lore.
4. The engine builds a context map using trust, mood, memory, and lore.
5. The active backend is called.
6. The response is parsed into a structured result.
7. `npc_engine.rpy` updates trust, mood, and memory.
8. The game displays the reply.

## Dialogue Modes

### Selection Mode

Selection mode uses authored dialogue from `npc_texts.json`.

The backend chooses:

- a category and reply index, or
- only a reply index if the category is already known

This mode is useful when you want:

- stronger control over wording
- lower hallucination risk
- consistent character voice
- fast scene interaction

### Generative Mode

Generative mode uses prompt templates plus structured NPC context to produce a JSON-like response.

The expected output includes fields such as:

- `reply`
- `analysis`
- `sentiment_category`
- `reasoning`
- `mood`
- `summary`

This mode is useful when you want:

- open-ended player input
- more flexible interaction
- emergent responses inside a stateful system

## NPC State Model

Each NPC is represented by `NPCEngine`.

Important state fields include:

- `trust`
- `mood`
- `short_term`
- `long_term`
- `last_category`
- `last_reasoning`

The engine applies:

- trust changes from sentiment mapping
- mood changes from AI output
- short-term summaries from recent interactions
- long-term event updates from gameplay actions

## Backend Defaults

Current defaults are defined in `ai_handler.rpy`:

```python
default ai_backend = "llama_server"
default ai_engine_mode = "selection"
```

If you want a different default backend or mode, edit those values.

## Requirements

To use this module inside a Ren'Py project, you should have:

- a Ren'Py project
- Python `requests` available in the project environment
- at least one working local backend setup
- one usable local model for the backend you choose

## Integration Notes

This module is designed to be copied into a Ren'Py project and connected to:

- a conversation loop in `script.rpy`
- one or more UI screens for NPC selection and stats
- image declarations or sprite assets that match your NPC configuration

The engine itself does not force one exact UI structure, but it expects:

- an active NPC object
- player input
- a call to `ask_local_ai(...)`
- application of the returned structured response

## Example Integration Flow

Typical Ren'Py-side usage looks like this:

```python
$ ai_data = ask_local_ai(player_input, active_npc, mode="selection")
$ active_npc.update_state(ai_data)
$ reply = ai_data.get("reply", "...")
```

Or in generative mode:

```python
$ ai_data = ask_local_ai(player_input, active_npc, mode="generative")
$ active_npc.update_state(ai_data)
$ reply = ai_data.get("reply", "...")
```

## How To Add A New NPC

To add a new NPC, update the following:

1. `personalities.json`
2. `npc_texts.json`
3. `sprites.json`
4. `npc_engine.rpy` with a new `default` NPC object
5. your Ren'Py UI and image declarations

The NPC name should stay consistent across all files.

## Notes For Developers

- `ai_handler.rpy` includes normalization and fallback parsing to make local model output more reliable.
- Selection mode and generative mode are intentionally separate because they solve different design problems.
- The engine is easier to scale when dialogue content, personality data, and UI logic remain separated.
