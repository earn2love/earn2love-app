"""Central Game Registry — the single source of truth for all Play Together games.

Each game maps to ONE reusable mechanic (gameType) + a content pool + config.
Adding game #51 = add one entry here (or create it via the admin), not new code.
"""

ALL_TIERS = ["casual", "friendship", "love"]

# (num, slug, name, mechanic, contentKey, category, icon, short, config, tiers, ai, uvu, difficulty, minutes)
_G = [
    # A — Conversation & Connection
    (1, "would_you_rather", "Would You Rather", "choice", "would_you_rather", "Conversation & Connection", "Split", "Choose between two options and compare.", {"rounds": 6}, ALL_TIERS, True, True, "easy", 5),
    (2, "this_or_that", "This or That", "choice", "this_or_that", "Conversation & Connection", "ToggleLeft", "Fast preference face-offs.", {"rounds": 8}, ALL_TIERS, True, True, "easy", 4),
    (3, "quick_questions", "Quick Questions", "prompt", "quick_questions", "Conversation & Connection", "Zap", "Rapid short-answer rounds.", {"rounds": 6}, ALL_TIERS, True, True, "easy", 5),
    (4, "conversation_cards", "Conversation Cards", "prompt", "conversation_cards", "Conversation & Connection", "MessageSquareText", "Meaningful conversation prompts.", {"rounds": 6}, ALL_TIERS, True, True, "easy", 8),
    (5, "get_to_know_me", "Get to Know Me", "prompt", "get_to_know_me", "Conversation & Connection", "UserSearch", "Learn about each other.", {"rounds": 6}, ALL_TIERS, True, True, "easy", 8),
    (6, "first_impressions", "First Impressions", "prompt", "first_impressions", "Conversation & Connection", "Eye", "Light first-impression questions.", {"rounds": 5}, ALL_TIERS, True, True, "easy", 5),
    (7, "guess_my_answer", "Guess My Answer", "guess", "guess_my_answer", "Conversation & Connection", "HelpCircle", "Predict what the other will choose.", {"rounds": 6}, ALL_TIERS, True, True, "medium", 6),
    (8, "how_well_do_you_know_me", "How Well Do You Know Me?", "guess", "how_well", "Conversation & Connection", "Brain", "Answer questions about each other.", {"rounds": 6}, ALL_TIERS, True, True, "medium", 6),
    (9, "finish_my_sentence", "Finish My Sentence", "prompt", "finish_sentence", "Conversation & Connection", "PenLine", "One starts, the other finishes.", {"rounds": 6}, ALL_TIERS, True, True, "easy", 6),
    (10, "tell_me_more", "Tell Me More", "prompt", "tell_me_more", "Conversation & Connection", "MessagesSquare", "Progressively deeper prompts.", {"rounds": 5}, ALL_TIERS, True, True, "easy", 8),
    # B — Fun & Personality
    (11, "two_truths_and_a_lie", "Two Truths and a Lie", "guess", "two_truths", "Fun & Personality", "Drama", "Spot the false statement.", {"rounds": 5}, ALL_TIERS, True, True, "medium", 7),
    (12, "never_have_i_ever", "Never Have I Ever", "prompt", "never_have_i_ever", "Fun & Personality", "Hand", "Safe social prompts.", {"rounds": 6}, ALL_TIERS, True, True, "easy", 6),
    (13, "most_likely_to", "Most Likely To", "choice", "most_likely_statements", "Fun & Personality", "Users", "Who best matches the statement.", {"rounds": 8, "scoreOnMatch": True}, ALL_TIERS, True, True, "easy", 5),
    (14, "personality_match", "Personality Match", "choice", "personality", "Fun & Personality", "Sparkles", "Compare personality answers.", {"rounds": 8, "scoreOnMatch": True}, ALL_TIERS, True, True, "easy", 6),
    (15, "emoji_personality", "Emoji Personality", "choice", "emoji_personality", "Fun & Personality", "Smile", "Answer with emojis.", {"rounds": 8}, ALL_TIERS, True, True, "easy", 5),
    (16, "mood_match", "Mood Match", "choice", "mood", "Fun & Personality", "Activity", "Compare current moods.", {"rounds": 8, "scoreOnMatch": True}, ALL_TIERS, True, True, "easy", 4),
    (17, "choose_my_adventure", "Choose My Adventure", "coop", "choose_adventure", "Fun & Personality", "Map", "Branch through a story together.", {"rounds": 8}, ALL_TIERS, True, True, "medium", 8),
    (18, "what_would_you_do", "What Would You Do?", "choice", "what_would_you_do", "Fun & Personality", "Lightbulb", "Interesting hypotheticals.", {"rounds": 6}, ALL_TIERS, True, True, "easy", 6),
    (19, "desert_island", "Desert Island", "choice", "desert_island", "Fun & Personality", "Palmtree", "Choose limited items for scenarios.", {"rounds": 8}, ALL_TIERS, True, True, "easy", 6),
    (20, "superpower_choice", "Superpower Choice", "choice", "superpower", "Fun & Personality", "Flame", "Choose and discuss abilities.", {"rounds": 8}, ALL_TIERS, True, True, "easy", 5),
    # C — Knowledge & Thinking
    (21, "general_trivia", "General Trivia", "trivia", "general", "Knowledge & Thinking", "GraduationCap", "Configurable multiple-choice trivia.", {"rounds": 8}, ALL_TIERS, True, True, "medium", 7),
    (22, "movie_trivia", "Movie Trivia", "trivia", "movie", "Knowledge & Thinking", "Clapperboard", "Movie questions.", {"rounds": 8}, ALL_TIERS, True, True, "medium", 7),
    (23, "music_trivia", "Music Trivia", "trivia", "music", "Knowledge & Thinking", "Music", "Music questions.", {"rounds": 8}, ALL_TIERS, True, True, "medium", 7),
    (24, "geography_challenge", "Geography Challenge", "trivia", "geography", "Knowledge & Thinking", "Globe", "Countries, capitals & landmarks.", {"rounds": 8}, ALL_TIERS, True, True, "medium", 7),
    (25, "food_around_the_world", "Food Around the World", "trivia", "food", "Knowledge & Thinking", "UtensilsCrossed", "Food & cuisine knowledge.", {"rounds": 8}, ALL_TIERS, True, True, "medium", 7),
    (26, "science_quick_quiz", "Science Quick Quiz", "trivia", "science", "Knowledge & Thinking", "FlaskConical", "Accessible science questions.", {"rounds": 8}, ALL_TIERS, True, True, "medium", 7),
    (27, "technology_quiz", "Technology Quiz", "trivia", "technology", "Knowledge & Thinking", "Cpu", "General technology questions.", {"rounds": 8}, ALL_TIERS, True, True, "medium", 7),
    (28, "history_challenge", "History Challenge", "trivia", "history", "Knowledge & Thinking", "Landmark", "General history questions.", {"rounds": 8}, ALL_TIERS, True, True, "medium", 7),
    (29, "guess_the_fact", "Guess the Fact", "trivia", "guess_fact", "Knowledge & Thinking", "BadgeCheck", "Find the correct statement.", {"rounds": 8}, ALL_TIERS, True, True, "medium", 7),
    (30, "true_or_false", "True or False", "trivia", "true_false", "Knowledge & Thinking", "CheckCheck", "Reusable true/false engine.", {"rounds": 8}, ALL_TIERS, True, True, "easy", 5),
    # D — Word & Language
    (31, "word_association", "Word Association", "prompt", "word_association", "Word & Language", "Link", "Respond with associated words.", {"rounds": 8}, ALL_TIERS, True, True, "easy", 5),
    (32, "category_rush", "Category Rush", "prompt", "category_rush", "Word & Language", "ListChecks", "Name items in a category.", {"rounds": 8}, ALL_TIERS, True, True, "easy", 5),
    (33, "guess_the_word", "Guess the Word", "trivia", "guess_word", "Word & Language", "Search", "Clue-based word guessing.", {"rounds": 8}, ALL_TIERS, True, True, "medium", 6),
    (34, "forbidden_word", "Forbidden Word", "prompt", "forbidden_word", "Word & Language", "Ban", "Explain without banned words.", {"rounds": 6}, ALL_TIERS, True, True, "medium", 7),
    (35, "word_scramble", "Word Scramble", "trivia", "word_scramble", "Word & Language", "Shuffle", "Unscramble the word.", {"rounds": 8}, ALL_TIERS, True, True, "medium", 6),
    (36, "missing_letters", "Missing Letters", "trivia", "missing_letters", "Word & Language", "SpellCheck", "Complete the missing letters.", {"rounds": 8}, ALL_TIERS, True, True, "medium", 6),
    (37, "riddle_me_this", "Riddle Me This", "trivia", "riddle", "Word & Language", "Puzzle", "Solve the riddle.", {"rounds": 6}, ALL_TIERS, True, True, "hard", 7),
    (38, "synonym_challenge", "Synonym Challenge", "trivia", "synonym", "Word & Language", "Equal", "Choose the right synonym.", {"rounds": 8}, ALL_TIERS, True, True, "medium", 6),
    (39, "opposites", "Opposites", "trivia", "opposites", "Word & Language", "ArrowLeftRight", "Identify the antonym.", {"rounds": 8}, ALL_TIERS, True, True, "easy", 5),
    (40, "language_match", "Language Match", "trivia", "language_match", "Word & Language", "Languages", "Match words & meanings across languages.", {"rounds": 8}, ALL_TIERS, True, True, "medium", 6),
    # E — Cooperative & Relationship Play
    (41, "compatibility_quiz", "Compatibility Quiz", "choice", "compatibility", "Cooperative & Relationship", "HeartHandshake", "Compare preferences together.", {"rounds": 8, "scoreOnMatch": True}, ALL_TIERS, True, True, "easy", 7),
    (42, "dream_trip", "Dream Trip", "coop", "dream_trip", "Cooperative & Relationship", "Plane", "Build an imaginary trip together.", {"rounds": 8}, ALL_TIERS, True, True, "easy", 7),
    (43, "perfect_weekend", "Perfect Weekend", "coop", "perfect_weekend", "Cooperative & Relationship", "CalendarHeart", "Plan a weekend together.", {"rounds": 8}, ALL_TIERS, True, True, "easy", 7),
    (44, "build_a_story", "Build a Story", "coop", "build_story", "Cooperative & Relationship", "BookOpen", "Take turns adding to a story.", {"rounds": 8}, ALL_TIERS, True, True, "medium", 8),
    (45, "memory_lane", "Memory Lane", "prompt", "memory_lane", "Cooperative & Relationship", "Camera", "Prompts about shared/real experiences.", {"rounds": 6}, ALL_TIERS, True, True, "easy", 8),
    (46, "team_decisions", "Team Decisions", "coop", "team_decisions", "Cooperative & Relationship", "Handshake", "Solve everyday decisions together.", {"rounds": 8}, ALL_TIERS, True, True, "easy", 6),
    (47, "common_ground", "Common Ground", "choice", "common_ground", "Cooperative & Relationship", "CircleDot", "Discover shared preferences.", {"rounds": 8, "scoreOnMatch": True}, ALL_TIERS, True, True, "easy", 6),
    (48, "bucket_list_builder", "Bucket List Builder", "coop", "bucket_list", "Cooperative & Relationship", "ClipboardList", "Create a shared wishlist.", {"rounds": 8}, ALL_TIERS, True, True, "easy", 7),
    (49, "friendship_challenge", "Friendship Challenge", "guess", "friendship_challenge", "Cooperative & Relationship", "UsersRound", "Friendly knowledge challenge.", {"rounds": 6}, ALL_TIERS, True, True, "medium", 6),
    (50, "couple_challenge", "Couple Challenge", "prompt", "couple_challenge", "Cooperative & Relationship", "Heart", "Relationship prompts for eligible users.", {"rounds": 6}, ["love"], True, True, "easy", 8),
]

INSTRUCTIONS = {
    "choice": "Each round shows a prompt with options. Every player picks one, then answers are revealed and compared.",
    "trivia": "Each round asks a multiple-choice question. Pick your answer — correct answers score a point. The right answer is revealed after everyone answers.",
    "prompt": "Each round shows a conversation prompt. Share your answer (some rounds are turn-based). There are no winners — it's about connecting.",
    "guess": "One player secretly sets an answer, the other predicts it. Correct guesses score a point. The setter alternates each round.",
    "coop": "Take turns adding to something you build together. There's no competition — enjoy creating it as a team.",
}


def build_game(entry, sort_index):
    (num, slug, name, mech, ckey, cat, icon, short, cfg, tiers, ai, uvu, diff, mins) = entry
    config = {"rounds": cfg.get("rounds", 6), "timerSeconds": cfg.get("timerSeconds", 45),
              "scoreOnMatch": cfg.get("scoreOnMatch", False), "contentKey": ckey}
    return {
        "gameId": slug,
        "slug": slug,
        "name": name,
        "shortDescription": short,
        "fullDescription": f"{name}: {short} A reusable '{mech}' experience — play with another user or, soon, an Earn2Love AI character.",
        "category": cat,
        "gameType": mech,
        "icon": icon,
        "coverImage": "",
        "enabled": True,
        "featured": num in (1, 11, 21, 41),
        "sortOrder": sort_index,
        "minPlayers": 2,
        "maxPlayers": 6,
        "estimatedMinutes": mins,
        "difficulty": diff,
        "tierAccess": tiers,
        "supportsAI": ai,
        "supportsUserVsUser": uvu,
        "instructions": INSTRUCTIONS[mech],
        "rules": INSTRUCTIONS[mech],
        "version": 1,
        "contentVersion": 1,
        "ageRating": "18+",
        "configuration": config,
        "archived": False,
    }


def default_games():
    return [build_game(e, i) for i, e in enumerate(_G)]


GAME_INDEX = {e[1]: build_game(e, i) for i, e in enumerate(_G)}
MECHANIC_OF = {e[1]: e[3] for e in _G}
CONTENT_KEY_OF = {e[1]: e[4] for e in _G}
