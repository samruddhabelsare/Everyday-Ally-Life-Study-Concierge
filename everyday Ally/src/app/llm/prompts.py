
from typing import List

STUDY_PROMPT_TEMPLATE = (
    "You are an expert study planner. The user has {hours} hours today and needs to study these topics: {topics}.\n\n"
    "Create {blocks} focused study blocks. For each block provide:\n"
    " - title (string)\n"
    " - duration_min (integer minutes)\n"
    " - goal (one-line string)\n\n"
    "Return EXACTLY a single JSON object with a top-level key \"study_blocks\" whose value is an array of objects, "
    "for example:\n"
    "{{\n  \"study_blocks\": [\n    {{\"title\":\"Block 1\",\"duration_min\":60,\"goal\":\"...\"}},\n    {{\"title\":\"Block 2\",\"duration_min\":30,\"goal\":\"...\"}}\n  ]\n}}\n"
    "Do not include any explanatory text, comments, or markdown—only JSON."
)

def study_prompt(hours: int = 3, topics: List[str] = None, blocks: int = 2) -> str:
    topics = topics or ["general"]
    topics_text = ", ".join(topics)
    return STUDY_PROMPT_TEMPLATE.format(hours=hours, topics=topics_text, blocks=blocks)


NUTRITION_PROMPT_TEMPLATE = (
    "You are a helpful nutrition assistant. The user's diet preference is: '{diet}'.\n\n"
    "Provide 2 meal suggestions for today. Each meal object should include:\n"
    " - meal (string)\n"
    " - desc (one-line description)\n"
    " - cal (integer estimated calories)\n\n"
    "Return EXACTLY a single JSON object with a top-level key \"meals\" whose value is an array, for example:\n"
    "{{\n  \"meals\": [\n    {{\"meal\":\"Name\",\"desc\":\"...\",\"cal\":350}},\n    {{\"meal\":\"Name 2\",\"desc\":\"...\",\"cal\":420}}\n  ]\n}}\n"
    "Do not include any extra commentary—only JSON."
)

def nutrition_prompt(diet: str = "omnivore", num: int = 2) -> str:
    # num is kept for clarity but template requests 2 by default; model can still follow it.
    return NUTRITION_PROMPT_TEMPLATE


FITNESS_PROMPT = (
    "You are a friendly fitness coach. Suggest ONE short, practical workout suitable for most users.\n\n"
    "Return EXACTLY a single JSON object with a top-level key \"workout\" whose value is an object with a "
    "single key 'workout' describing the routine, for example:\n"
    "{{\"workout\": {{\"workout\": \"20-min brisk walk + 10-min stretching\"}}}}\n"
    "Do not include any extra text—only JSON."
)
