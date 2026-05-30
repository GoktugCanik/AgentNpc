# AgentNpc Usage Guide

## What This Project Is

AgentNpc is a Ren'Py project that combines:

- a reusable NPC state system
- multiple AI backends
- selection-based dialogue
- generative dialogue
- trust, mood, and memory updates
- developer logging and debug UI

The current core flow is:

1. The player selects an NPC.
2. The player talks in either `selection` or `generative` mode.
3. The AI layer returns a structured response.
4. The NPC updates mood, trust, and short-term memory.
5. The result is shown on screen and written to `ai_testing_logs.txt`.

## Main Files

### Engine and Runtime

- `script.rpy`
  - Main conversation flow.
  - Chooses between selection mode and generative mode.
  - Calls `ask_local_ai(...)`.

- `ai_engine/ai_handler.rpy`
  - Main AI routing layer.
  - Selects backend and mode.
  - Loads NPC config, world lore, and dialogue pools.
  - Parses AI output into structured data.

- `ai_engine/npc_engine.rpy`
  - Defines the `NPCEngine` class.
  - Stores trust, mood, short-term memory, long-term events, and debug fields.

- `npc_screens.rpy`
  - NPC selector UI.
  - Stats panel.
  - Debug panel.
  - Thinking screen.

- `test_logger.rpy`
  - Writes interaction logs to `ai_testing_logs.txt`.

### NPC Content and Data

- `ai_engine/personalities.json`
  - Per-NPC personality, backstory, trust triggers, and trust values.

- `ai_engine/npc_texts.json`
  - Per-NPC dialogue pools for selection mode.

- `ai_engine/world_lore.json`
  - Shared lore injected into AI context.

- `ai_engine/sprites.json`
  - Maps NPC names and moods to displayable sprite names.

- `ai_engine/scene_policies.json`
  - Scene-level behavior data such as allowed categories and mode defaults.

### Prompts

- `ai_engine/prompts/system_selection.txt`
  - Prompt used in selection mode.

- `ai_engine/prompts/system_generative.txt`
  - Prompt used in generative mode.

### AI Backends

- `ai_engine/backend_llama_server.rpy`
- `ai_engine/backend_llama_cli.rpy`
- `ai_engine/backend_ollama.rpy`

These backends are selected through `ai_handler.rpy`.

## What You Need To Run It

### Minimum Project Requirements

- Ren'Py project structure
- `requests` available inside the project package set
- at least one working backend
- one usable model

### Current Local Backend Assets

The current project already includes local llama.cpp files in `ai_engine/`, including:

- `llama-server.exe`
- `llama-cli.exe`
- `models/qwen2.5-3b.gguf`

### Current Backend Defaults

The current defaults live in `ai_engine/ai_handler.rpy`:

- `ai_backend = "llama_server"`
- `ai_engine_mode = "selection"`

If you want a different default backend or mode, change those values there.

## How The System Works

### Selection Mode

Selection mode pulls replies from `ai_engine/npc_texts.json`.

The runtime flow is:

1. `script.rpy` calls `ask_local_ai(...)` with mode `selection`.
2. `ai_handler.rpy` loads the selected NPC's dialogue map.
3. The backend chooses either:
   - a category and reply index
   - or only a reply index if the category is already known
4. The selected text is returned as `reply`.

Selection mode is best for:

- fast scene dialogue
- controlled writing
- low hallucination risk

### Generative Mode

Generative mode uses the NPC personality, world lore, trust, mood, and memory to generate a structured JSON response.

The response is expected to include fields like:

- `reply`
- `analysis`
- `sentiment_category`
- `reasoning`
- `mood`
- `summary`

Generative mode is best for:

- open-ended player input
- roleplay
- emergent dialogue

## How To Add A New NPC

Adding an NPC currently requires updating multiple places. The project is partly generic, but the selector and defaults are still content-driven by explicit entries.

### 1. Add Personality Data

Edit `ai_engine/personalities.json`.

Add a new top-level key for the NPC name. Example:

```json
{
  "Mira": {
    "hometown": "Bravil",
    "voice": "Sharp-tongued herbalist, speaks in calm but cutting phrases.",
    "backstory": "Mira runs a small apothecary and distrusts soldiers and nobles.",
    "social_rules": [
      "Be patient with sincere questions.",
      "Dislike arrogance and empty politeness."
    ],
    "triggers": {
      "love": "Protecting her shop or helping her community.",
      "like": "Respecting her craft or asking thoughtful questions.",
      "neutral": "Basic greetings and small talk.",
      "dislike": "Being rude, dismissive, or wasteful.",
      "hate": "Threatening her or mocking her work."
    },
    "trust_logic": {
      "love": 20,
      "like": 10,
      "neutral": 0,
      "dislike": -10,
      "hate": -25
    }
  }
}
```

Important:

- The key must match the NPC name used in the runtime object.
- `trust_logic` should include the same sentiment categories your AI returns.

### 2. Add Selection Dialogue

Edit `ai_engine/npc_texts.json`.

Add dialogue categories for the same NPC name. Example:

```json
{
  "Mira": {
    "greeting": [
      "State your need. I do not chat for sport.",
      "If you're ill, speak clearly. If not, be brief."
    ],
    "appreciation": [
      "Hm. At least someone notices good work.",
      "Praise is cheaper than herbs, but I will take it."
    ],
    "critique": [
      "If you came to insult my craft, leave.",
      "Ignorance is common. I do not stock a cure for it."
    ]
  }
}
```

Important:

- The NPC name must match `personalities.json`.
- Selection mode can only choose from categories and lines that exist here.

### 3. Add Sprite Mapping

Edit `ai_engine/sprites.json`.

Add a new entry for the NPC. Example:

```json
{
  "Mira": {
    "image_tag": "mira",
    "moods": {
      "neutral": "mira neutral",
      "happy": "mira happy",
      "angry": "mira angry"
    }
  }
}
```

Important:

- The mood names should match the moods your game actually displays.
- The final image names must correspond to Ren'Py image declarations or valid image assets.

### 4. Add Image Assets

Put the NPC art in the `images/` folder and make sure the image names match the sprite mappings you intend to use.

Current project examples include:

- `images/elder_man.png`
- `images/elder_man_happy.png`
- `images/boy_idle.png`

If you are using direct image names like `mira neutral`, make sure those image tags are declared somewhere in your project.

### 5. Add A Runtime NPC Object

Edit `ai_engine/npc_engine.rpy`.

Create a new Ren'Py default object:

```python
default mira = NPCEngine("Mira", "mira")
```

Important:

- The first argument must match the keys in:
  - `personalities.json`
  - `npc_texts.json`
  - `sprites.json`
- The second argument is the `image_tag`.

### 6. Add The NPC To The Selector UI

Edit `npc_screens.rpy`.

Inside `screen npc_selector()`, add a button:

```renpy
textbutton "Talk to Mira":
    action [SetVariable("active_npc", mira), Jump("setup_conversation")]
    text_size 18
```

Without this, the NPC exists in code but cannot be selected from the current UI.

## How To Change AI Behavior

### Change Default Backend

Edit `ai_engine/ai_handler.rpy`.

Current choices are:

- `llama_server`
- `llama_cli`
- `ollama`

The default is controlled by:

```python
default ai_backend = "llama_server"
```

### Change Default Mode

Edit `ai_engine/ai_handler.rpy`.

Current modes are:

- `selection`
- `generative`

The default is controlled by:

```python
default ai_engine_mode = "selection"
```

### Change Selection Prompt

Edit `ai_engine/prompts/system_selection.txt`.

Use this when you want to change:

- category choice rules
- reply index rules
- answer length
- scene-specific selection behavior

### Change Generative Prompt

Edit `ai_engine/prompts/system_generative.txt`.

Use this when you want to change:

- character roleplay style
- JSON response rules
- lore/memory guidance

## How Scene Control Works

`script.rpy` currently passes:

- `mode=ai_mode`
- `category="auto"` in selection mode
- `scene_id="forge_demo"` in selection mode

This means the current demo scene is still partly specialized.

Scene-level policies are stored in:

- `ai_engine/scene_policies.json`

Current example:

- `forge_demo`

If you want more scene-aware behavior, add new scene entries there and make sure the handler actually uses them where needed.

## Where To Change Things

### To Add A New NPC

Change these files:

- `ai_engine/personalities.json`
- `ai_engine/npc_texts.json`
- `ai_engine/sprites.json`
- `ai_engine/npc_engine.rpy`
- `npc_screens.rpy`
- optionally `images/`

### To Change Selection Choices

Change these files:

- `ai_engine/npc_texts.json`
- `ai_engine/prompts/system_selection.txt`
- optionally `script.rpy`

### To Change Generative Personality Output

Change these files:

- `ai_engine/personalities.json`
- `ai_engine/prompts/system_generative.txt`
- `ai_engine/world_lore.json`

### To Change UI

Change:

- `npc_screens.rpy`

### To Change Logging

Change:

- `test_logger.rpy`

## Current Limitations

- The NPC selector is still hardcoded in `npc_screens.rpy`.
- The sample selection menu in `script.rpy` is still demo-specific.
- `npc_engine.rpy` currently hardcodes sprite suffix logic in `get_sprite()`, even though `sprites.json` exists.
- Some scene logic still references `forge_demo`.

So while the project is moving toward a generic module, it is not fully generic yet.

## Recommended Workflow For Adding An NPC

1. Add the NPC to `personalities.json`.
2. Add selection categories to `npc_texts.json`.
3. Add sprite mappings to `sprites.json`.
4. Add images or image declarations.
5. Add `default new_npc = NPCEngine(...)` to `npc_engine.rpy`.
6. Add a selector button in `npc_screens.rpy`.
7. Test both:
   - selection mode
   - generative mode
8. Check `ai_testing_logs.txt` and the debug UI.

## Quick Example Checklist

- Add name in `personalities.json`
- Add dialogue pools in `npc_texts.json`
- Add image tag and moods in `sprites.json`
- Add art assets
- Add `default` NPC object in `npc_engine.rpy`
- Add selector button in `npc_screens.rpy`
- Test in game

## Suggested Future Refactor

If you want this project to become a truly generic module, the next improvements should be:

- generate the selector UI from JSON or a registry instead of hardcoded buttons
- load NPC definitions from one unified source of truth
- make `get_sprite()` use `sprites.json` directly
- remove demo-specific scene assumptions from `script.rpy`
- separate engine code from sample game content
