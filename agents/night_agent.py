import json
import re
from datetime import date

from core.fallback import get_llm_with_fallback
from delivery.telegram import send_message, wait_for_reply
from memory.weekly_store import get_today_log, mark_as_studied


YES_TOKENS = {"yes", "y", "yep", "yeah", "studied", "done"}
NO_TOKENS = {"no", "n", "nope", "nah", "timeout"}
ENGLISH_TOKENS = {"english", "vocab", "vocabulary", "word power", "wpm"}


def _normalize_reply(reply: str) -> str:
    return (reply or "").strip().lower()


def _looks_like_yes(reply: str) -> bool:
    value = _normalize_reply(reply)
    return any(token in value for token in YES_TOKENS)


def _looks_like_english(reply: str) -> bool:
    value = _normalize_reply(reply)
    return any(token in value for token in ENGLISH_TOKENS)


def _fallback_mcq_from_memory(today_log: list[dict]) -> list[dict]:
    """Deterministic 5-question MCQ when the LLM is unavailable."""
    topic = today_log[0]["topic"] if today_log else "today's topic"
    facts = (today_log[0].get("key_facts") if today_log else []) or [
        "No fact recorded today.",
        "Recall the most cited stat.",
        "Recall the strongest case study.",
    ]
    concepts = (today_log[0].get("concepts") if today_log else []) or [
        "Framing",
        "Mechanism vs impact",
        "Comparative weighing",
    ]
    arguments = (today_log[0].get("arguments") if today_log else {}) or {}
    for_args = arguments.get("for") or ["Expands autonomy", "Improves access", "Reframes incentives"]
    against_args = arguments.get("against") or ["Triggers backlash", "Implementation cost", "Unintended effects"]

    def pad(options, fallbacks):
        """Ensure 4 distinct options."""
        seen, result = set(), []
        for option in options + fallbacks:
            key = option.strip().lower()
            if option and key not in seen:
                seen.add(key)
                result.append(option)
            if len(result) == 4:
                break
        while len(result) < 4:
            result.append(f"None of the above ({len(result)})")
        return result

    fact_opts = pad([facts[0]], ["Generic news headline", "Off-topic celebrity quote", "Unrelated statistic"])
    concept_opts = pad([concepts[0]], ["Random news term", "Unrelated trivia", "Off-topic jargon"])
    for_opts = pad([for_args[0]], against_args[:3])
    against_opts = pad([against_args[0]], for_args[:3])
    return [
        {
            "q": f"Which of these was a key fact from today's digest on {topic}?",
            "a": fact_opts[0], "b": fact_opts[1], "c": fact_opts[2], "d": fact_opts[3],
            "answer": "a",
        },
        {
            "q": "Which named concept did today's digest emphasise?",
            "a": concept_opts[0], "b": concept_opts[1], "c": concept_opts[2], "d": concept_opts[3],
            "answer": "a",
        },
        {
            "q": "Which is a sound FOR-side argument from the digest?",
            "a": for_opts[0], "b": for_opts[1], "c": for_opts[2], "d": for_opts[3],
            "answer": "a",
        },
        {
            "q": "Which is a sound AGAINST-side argument from the digest?",
            "a": against_opts[0], "b": against_opts[1], "c": against_opts[2], "d": against_opts[3],
            "answer": "a",
        },
        {
            "q": "Pick the strongest move when the opposition presses you on impact.",
            "a": "Show mechanism, magnitude, and reversibility.",
            "b": "Repeat the claim louder.",
            "c": "Pivot to an unrelated topic.",
            "d": "Concede and move on.",
            "answer": "a",
        },
    ]


def _generate_quiz_with_llm(state: dict, today_log: list[dict], fallback_quiz: list[dict]) -> list[dict]:
    prompt = (
        "Generate a 5-question multiple-choice debate revision quiz.\n"
        "Mix: 2 factual, 2 argument-based, 1 application question.\n"
        "Return ONLY valid JSON in this exact shape:\n"
        '{"questions": [{"q": "...", "a": "...", "b": "...", "c": "...", "d": "...", "answer": "a"}]}\n'
        "answer must be one of a, b, c, d. Keep options short and distinct.\n\n"
        f"Today's memory: {json.dumps(today_log, ensure_ascii=False)}"
    )

    try:
        llm = get_llm_with_fallback(state)
        response = llm.invoke(prompt)
        content = getattr(response, "content", response)
        text = str(content).strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text).rsplit("```", 1)[0].strip()
        parsed = json.loads(text)
        questions = parsed.get("questions") if isinstance(parsed, dict) else parsed
        if isinstance(questions, list) and len(questions) >= 5:
            cleaned = []
            for q in questions[:5]:
                if all(k in q for k in ("q", "a", "b", "c", "d", "answer")):
                    cleaned.append(q)
            if len(cleaned) == 5:
                return cleaned
    except Exception as exc:
        print(f"[Night quiz] LLM generation failed: {exc}")

    return fallback_quiz


def _render_quiz(questions: list[dict]) -> str:
    lines = ["QUICK REVISION QUIZ", "-" * 20, ""]
    for index, q in enumerate(questions, start=1):
        lines.append(f"Q{index}: {q['q']}")
        lines.append(f"A) {q['a']}")
        lines.append(f"B) {q['b']}")
        lines.append(f"C) {q['c']}")
        lines.append(f"D) {q['d']}")
        lines.append("")
    lines.append("Reply like: 1a 2b 3c 4d 5a")
    return "\n".join(lines)


def _parse_mcq_answers(reply: str, count: int) -> list[str]:
    normalized = (reply or "").strip().lower().replace(",", " ")
    answers = [""] * count
    pattern = re.compile(r"(\d)\s*([abcd])")
    for match in pattern.finditer(normalized):
        idx = int(match.group(1)) - 1
        if 0 <= idx < count:
            answers[idx] = match.group(2)
    return answers


def _score_quiz_response(reply: str, questions: list[dict]) -> tuple[int, list[str]]:
    answers = _parse_mcq_answers(reply, len(questions))
    correct = 0
    feedback = []
    for i, (user, q) in enumerate(zip(answers, questions), start=1):
        truth = str(q.get("answer", "")).strip().lower()
        if user and user == truth:
            correct += 1
            feedback.append(f"Q{i}: Correct")
        else:
            feedback.append(f"Q{i}: Wrong (answer was {truth.upper() or '?'})")
    score = int((correct / max(len(questions), 1)) * 100)
    return score, feedback


def quiz_mode(state: dict) -> dict:
    state["task_type"] = "quiz"
    today_log = get_today_log()
    fallback_quiz = _fallback_mcq_from_memory(today_log)
    questions = _generate_quiz_with_llm(state, today_log, fallback_quiz)
    send_message(_render_quiz(questions))
    answer_reply = wait_for_reply(10)
    score, feedback = _score_quiz_response(answer_reply, questions)
    tail = (
        "Excellent! You are debate-ready."
        if score >= 80
        else "Review the weak areas tomorrow morning."
    )
    send_message(
        "QUIZ RESULT\n" + "-" * 10 + f"\nScore: {score}%\n\n"
        + "\n".join(feedback) + f"\n\n{tail}"
    )
    mark_as_studied(str(date.today()), True, score)
    state["studied_today"] = True
    state["quiz_score"] = score
    state["quiz_questions"] = questions
    return state


def _heuristic_bedtime(today_log: list[dict]) -> str:
    if today_log:
        entry = today_log[0]
        fact = (entry.get("key_facts") or ["Remember one core fact from the digest."])[0]
        argument_for = (entry.get("arguments", {}).get("for") or ["Have one clean affirmative line ready."])[0]
        argument_against = (entry.get("arguments", {}).get("against") or ["Have one clean negative line ready."])[0]
        vocab = (entry.get("vocab_words") or ["lucid"])[0]
        phrase = (entry.get("debate_angle") or "Keep your framing tight and comparative.")[:140]
    else:
        fact = "No daily digest was stored today."
        argument_for = "Support the side with the clearest mechanism."
        argument_against = "Challenge the side with the weakest tradeoff analysis."
        vocab = "lucid"
        phrase = "Sleep on the framing, not just the headlines."

    return (
        "BEDTIME RECAP\n\n"
        f"Fact: {fact}\n"
        f"For: {argument_for}\n"
        f"Against: {argument_against}\n"
        f"English: Use '{vocab}' once in a debate sentence tomorrow.\n"
        f"Line: {phrase}"
    )


def _llm_bedtime_compression(state: dict, today_log: list[dict]) -> str | None:
    if not today_log:
        return None

    combined = "\n\n".join(
        f"Topic: {entry.get('topic', '')}\n"
        f"Summaries: {entry.get('summaries', '')}\n"
        f"Facts: {entry.get('key_facts', [])}\n"
        f"For: {entry.get('arguments', {}).get('for', [])}\n"
        f"Against: {entry.get('arguments', {}).get('against', [])}\n"
        f"Angle: {entry.get('debate_angle', '')}"
        for entry in today_log
    )

    prompt = (
        "The debate student did NOT read today's digest. They are in bed.\n"
        "Compress it into a max 100-word recap. Casual, friendly tone, like a friend texting.\n\n"
        f"Content:\n{combined}\n\n"
        "Include ONLY:\n"
        "1. The single most important fact (one sentence)\n"
        "2. One argument FOR (one sentence)\n"
        "3. One argument AGAINST (one sentence)\n"
        "4. One killer debate line they can use tomorrow (one sentence)\n\n"
        "Max 100 words total. No bullet symbols. No markdown. Plain text."
    )

    try:
        llm = get_llm_with_fallback(state)
        response = llm.invoke(prompt)
        text = str(getattr(response, "content", response)).strip()
        return text or None
    except Exception as exc:
        print(f"[Bedtime] LLM compression failed: {exc}")
        return None


def bedtime_mode(state: dict) -> dict:
    state["task_type"] = "bedtime"
    today_log = get_today_log()

    llm_text = _llm_bedtime_compression(state, today_log)
    if llm_text:
        message = "No worries — here's the 2-min version:\n\n" + llm_text + "\n\nSleep well."
    else:
        message = _heuristic_bedtime(today_log)

    send_message(message)
    mark_as_studied(str(date.today()), False)
    state["studied_today"] = False
    state["quiz_score"] = None
    return state


def _run_compulsory_english_quiz(state: dict) -> dict:
    from agents.english_quiz_node import english_quiz_node

    send_message(
        "English vocab is compulsory tonight too. After the debate part, do this short vocabulary test."
    )
    return english_quiz_node(state)


def night_agent_node(state: dict) -> dict:
    send_message(
        "Did you read today's debate digest? Reply yes for a debate quiz, "
        "english for a vocabulary quiz, or no for a bedtime recap."
    )
    reply = wait_for_reply(30)

    if _looks_like_english(reply):
        from agents.english_quiz_node import english_quiz_node

        return english_quiz_node(state)

    if _looks_like_yes(reply):
        state = quiz_mode(state)
        return _run_compulsory_english_quiz(state)

    state = bedtime_mode(state)
    return _run_compulsory_english_quiz(state)
