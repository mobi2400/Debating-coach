import json
import re
from datetime import date

from core.fallback import get_llm_with_fallback
from delivery.whatsapp import send_message, wait_for_reply
from memory.weekly_store import get_today_log, mark_as_studied


YES_TOKENS = {"yes", "y", "yep", "yeah", "studied", "done"}
NO_TOKENS = {"no", "n", "nope", "nah", "timeout"}


def _normalize_reply(reply: str) -> str:
    return (reply or "").strip().lower()


def _looks_like_yes(reply: str) -> bool:
    value = _normalize_reply(reply)
    return any(token in value for token in YES_TOKENS)


def _build_quiz_from_memory(today_log: list[dict]) -> list[dict]:
    topic = today_log[0]["topic"] if today_log else "today's debate topic"
    facts = today_log[0].get("key_facts", []) if today_log else []
    concepts = today_log[0].get("concepts", []) if today_log else []

    return [
        {"question": f"What was the main topic studied today?", "answer_hint": topic, "type": "factual"},
        {
            "question": "Name one key fact from today.",
            "answer_hint": facts[0] if facts else "Use the strongest fact you remember.",
            "type": "factual",
        },
        {
            "question": "Name one concept worth remembering.",
            "answer_hint": concepts[0] if concepts else "Recall the core concept from the digest.",
            "type": "concept",
        },
        {"question": "Give one argument in favor of the topic.", "answer_hint": "Use a clear warrant.", "type": "argument"},
        {"question": "Give one argument against the topic.", "answer_hint": "Challenge impact or mechanism.", "type": "argument"},
    ]


def _generate_quiz_with_llm(state: dict, today_log: list[dict], fallback_quiz: list[dict]) -> list[dict]:
    prompt = (
        "Generate a 5-question debate revision quiz.\n"
        "Return JSON only as an array of objects with keys: question, answer_hint, type.\n"
        "Include 2 factual, 2 argument, and 1 concept/application style question.\n\n"
        f"Today's memory: {json.dumps(today_log, ensure_ascii=False)}"
    )

    try:
        llm = get_llm_with_fallback(state)
        response = llm.invoke(prompt)
        content = getattr(response, "content", response)
        parsed = json.loads(str(content))
        if isinstance(parsed, list) and parsed:
            return parsed[:5]
    except Exception:
        pass

    return fallback_quiz


def _render_quiz(questions: list[dict]) -> str:
    lines = ["QUIZ MODE", ""]
    for index, item in enumerate(questions, start=1):
        lines.append(f"{index}. {item['question']}")
        lines.append(f"   Hint: {item['answer_hint']}")
    return "\n".join(lines)


def _score_quiz_response(reply: str, questions: list[dict]) -> int:
    normalized = _normalize_reply(reply)
    if not normalized:
        return 0

    answer_lines = [line.strip() for line in re.split(r"[\n;]+", normalized) if line.strip()]
    coverage = min(len(answer_lines), len(questions))
    length_bonus = 1 if len(normalized.split()) >= 15 else 0
    score = min(100, int((coverage / max(len(questions), 1)) * 80) + (length_bonus * 10))
    return max(score, 20)


def quiz_mode(state: dict) -> dict:
    state["task_type"] = "quiz"
    today_log = get_today_log()
    fallback_quiz = _build_quiz_from_memory(today_log)
    questions = _generate_quiz_with_llm(state, today_log, fallback_quiz)
    send_message(_render_quiz(questions))
    answer_reply = wait_for_reply(10)
    score = _score_quiz_response(answer_reply, questions)
    send_message(
        f"QUIZ RESULT\n\nScore: {score}%\n"
        "Review both sides of the motion, tighten your warranting, and answer with clearer structure next time."
    )
    mark_as_studied(str(date.today()), True, score)
    state["studied_today"] = True
    state["quiz_score"] = score
    return state


def bedtime_mode(state: dict) -> dict:
    state["task_type"] = "bedtime"
    today_log = get_today_log()

    if today_log:
        entry = today_log[0]
        fact_list = entry.get("key_facts") or ["Remember one core fact from the digest."]
        for_list = entry.get("arguments", {}).get("for") or ["Have one clean affirmative line ready."]
        against_list = entry.get("arguments", {}).get("against") or ["Have one clean negative line ready."]
        fact = fact_list[0]
        argument_for = for_list[0]
        argument_against = against_list[0]
        phrase = entry.get("debate_angle", "Keep your framing tight and comparative.")[:140]
    else:
        fact = "No daily digest was stored today."
        argument_for = "Support the side with the clearest mechanism."
        argument_against = "Challenge the side with the weakest tradeoff analysis."
        phrase = "Sleep on the framing, not just the headlines."

    message = (
        "BEDTIME RECAP\n\n"
        f"Fact: {fact}\n"
        f"For: {argument_for}\n"
        f"Against: {argument_against}\n"
        f"Line: {phrase}"
    )
    send_message(message)
    mark_as_studied(str(date.today()), False)
    state["studied_today"] = False
    state["quiz_score"] = None
    return state


def night_agent_node(state: dict) -> dict:
    send_message("Did you read today's debate digest? Reply yes or no.")
    reply = wait_for_reply(30)

    if _looks_like_yes(reply):
        return quiz_mode(state)

    return bedtime_mode(state)
