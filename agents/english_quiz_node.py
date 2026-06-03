"""English quiz built from the structured Word Power Made Easy index.

Pulls etymology + definition chunks from english_db, drafts five
mixed-style questions (definition / usage / root identification),
sends them over WhatsApp, scores the reply, and writes the score to
the weekly log under `english_quiz_score`.
"""

from __future__ import annotations

import json
import re
from datetime import date

from core.fallback import get_llm_with_fallback
from core.topic_utils import topic_name
from delivery.whatsapp import send_message, wait_for_reply
from memory.weekly_store import mark_english_quiz
from rag.retrieval_pipeline import _load_vector_store


QUESTION_TYPES = ["definition", "usage", "root"]


def _gather_english_chunks(query: str, k: int = 12) -> list:
    store = _load_vector_store("english_db")
    if store is None:
        return []
    try:
        return store.similarity_search(query, k=k)
    except Exception as exc:
        print(f"[english_quiz] retrieval failed: {exc}")
        return []


def _chunk_to_dict(chunk) -> dict:
    if hasattr(chunk, "page_content"):
        return {
            "content": chunk.page_content,
            "metadata": getattr(chunk, "metadata", {}) or {},
        }
    return {"content": chunk.get("page_content", ""), "metadata": chunk.get("metadata", {})}


def _filter_by_section(chunks: list, section_types: list[str], limit: int) -> list[dict]:
    selected = []
    for chunk in chunks:
        rec = _chunk_to_dict(chunk)
        if rec["metadata"].get("section_type") in section_types:
            selected.append(rec)
        if len(selected) >= limit:
            break
    return selected


def _heuristic_questions(chunks: list) -> list[dict]:
    """Build a usable quiz when the LLM is unavailable.

    Pulls candidate words (uppercase or pronunciation-tagged tokens)
    and root-style fragments straight out of the etymology chunks.
    """
    pool = " ".join(c["content"] for c in chunks)
    words = []
    for m in re.findall(r"\b([a-z]{6,14})\b", pool):
        lower = m.lower()
        if lower not in words and lower not in {"english", "meaning", "prefix", "suffix"}:
            words.append(lower)
        if len(words) >= 5:
            break

    roots = []
    for m in re.findall(r"\b([a-z]{3,6})-(?:[a-z]|,)", pool):
        if m not in roots:
            roots.append(m)
        if len(roots) >= 3:
            break

    fallback_words = words or ["lucid", "cogent", "salient", "nuance", "incisive"]
    fallback_roots = roots or ["dict", "cred", "bene"]

    return [
        {
            "type": "definition",
            "question": f"What does '{fallback_words[0]}' mean? Give a one-line definition.",
            "answer_hint": "Aim for a clear, precise one-sentence definition.",
        },
        {
            "type": "usage",
            "question": f"Use '{fallback_words[1]}' in a debate sentence about today's topic.",
            "answer_hint": "One sentence; show the word strengthens your argument.",
        },
        {
            "type": "root",
            "question": f"What does the root '{fallback_roots[0]}-' mean, and name one word built on it?",
            "answer_hint": "Explain the root, then give one word that uses it.",
        },
        {
            "type": "definition",
            "question": f"Define '{fallback_words[2]}' and contrast it with a near-synonym.",
            "answer_hint": "Definition first, then the distinction.",
        },
        {
            "type": "usage",
            "question": f"Write a one-line rebuttal that uses '{fallback_words[3]}'.",
            "answer_hint": "Make the word load the rebuttal, not decorate it.",
        },
    ]


def _generate_questions(state: dict, chunks: list) -> list[dict]:
    fallback = _heuristic_questions(chunks)
    if not chunks:
        return fallback

    context_lines = []
    for rec in chunks[:8]:
        section = rec["metadata"].get("section_type", "prose")
        session = rec["metadata"].get("session")
        context_lines.append(
            f"[session {session} · {section}] {rec['content'][:600]}"
        )

    prompt = (
        "You are quizzing a debater on vocabulary and roots from "
        "Word Power Made Easy.\n"
        "Return JSON only: an array of exactly 5 objects with keys "
        "question, answer_hint, type.\n"
        "Include 2 'definition', 2 'usage', and 1 'root' question. "
        "Pull words/roots directly from the provided context.\n\n"
        f"Topic: {state.get('topic', 'general debate')}\n"
        f"Context:\n" + "\n\n".join(context_lines)
    )

    try:
        state["task_type"] = "structured"
        llm = get_llm_with_fallback(state)
        response = llm.invoke(prompt)
        content = getattr(response, "content", response)
        text = str(content).strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text).rsplit("```", 1)[0].strip()
        parsed = json.loads(text)
        if isinstance(parsed, list) and parsed:
            return parsed[:5]
    except Exception as exc:
        print(f"[english_quiz] LLM generation failed: {exc}")

    return fallback


def _render_quiz(questions: list[dict]) -> str:
    lines = ["ENGLISH QUIZ", "Word Power Made Easy", ""]
    for index, item in enumerate(questions, start=1):
        lines.append(f"{index}. ({item.get('type', '?')}) {item['question']}")
        hint = item.get("answer_hint")
        if hint:
            lines.append(f"   Hint: {hint}")
    lines.append("")
    lines.append("Reply with all 5 answers numbered 1-5.")
    return "\n".join(lines)


def _score_quiz_response(reply: str, questions: list[dict]) -> int:
    normalized = (reply or "").strip().lower()
    if not normalized:
        return 0
    answer_lines = [line.strip() for line in re.split(r"[\n;]+", normalized) if line.strip()]
    coverage = min(len(answer_lines), len(questions))
    length_bonus = 1 if len(normalized.split()) >= 25 else 0
    score = min(100, int((coverage / max(len(questions), 1)) * 80) + (length_bonus * 10))
    return max(score, 20)


def english_quiz_node(state: dict) -> dict:
    state["task_type"] = "quiz"
    query = topic_name(state.get("topic")) or "vocabulary roots etymology"

    raw_chunks = _gather_english_chunks(query)
    if raw_chunks:
        primary = _filter_by_section(raw_chunks, ["etymology", "definitions"], limit=8)
        if not primary:
            primary = [_chunk_to_dict(c) for c in raw_chunks[:8]]
    else:
        primary = []

    questions = _generate_questions(state, primary)
    send_message(_render_quiz(questions))
    reply = wait_for_reply(10)
    score = _score_quiz_response(reply, questions)
    send_message(
        f"ENGLISH QUIZ RESULT\n\nScore: {score}%\n"
        "Loop back to the words you missed and use one of them in tomorrow's speech."
    )

    mark_english_quiz(str(date.today()), score)
    state["english_quiz_score"] = score
    state["english_quiz_questions"] = questions
    return state
