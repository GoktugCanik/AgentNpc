init -1 python:
    class NPCEngine(object):
        def __init__(self, name, image_tag, trust=50, mood="neutral"):
            self.name = name
            self.image_tag = image_tag
            self.trust = trust
            self.mood = mood
            self.short_term = []
            self.long_term = []
            self.last_category = "None"
            self.last_reasoning = "None"

        def update_state(self, ai_response):
            self.mood = ai_response.get("mood", "neutral")
            self.last_category = ai_response.get("sentiment_category", "neutral")
            self.last_reasoning = ai_response.get("reasoning", "N/A")
            self.change_trust(ai_response.get("trust_change", 0))

            summary = ai_response.get("summary", "")
            if summary and summary != "...":
                self.short_term.append(summary)
                if len(self.short_term) > 5:
                    self.short_term.pop(0)

        def change_trust(self, amount):
            self.trust = max(0, min(100, self.trust + amount))

        def add_event(self, description, trust_impact=0):
            self.long_term.append(description)
            self.change_trust(trust_impact)

            if trust_impact <= -20:
                self.mood = "angry"
            elif trust_impact >= 20:
                self.mood = "happy"

        def get_sprite(self):
            suffixes = {
                "elder": {"neutral": "man", "happy": "happy", "angry": "angry"},
                "boy": {"neutral": "idle", "happy": "happy", "angry": "angry"},
            }
            char_map = suffixes.get(self.image_tag, {})
            mood_name = char_map.get(self.mood, char_map.get("neutral", "idle"))
            return "{} {}".format(self.image_tag, mood_name)

# CRITICAL FOR PLUGIN STANDALONE EXPORTS: Declaring engines with default 
# registers them with Ren'Py's native rollback and save/load state architecture.
default kaldar = NPCEngine("Kaldar", "elder")
default boy = NPCEngine("Boy", "boy")
default active_npc = None