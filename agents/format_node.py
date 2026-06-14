from __future__ import annotations

from agents.rank_node import _is_explainer_article, _is_news_article, _is_reference_article
from core.topic_utils import topic_name
from memory.weekly_store import save_daily_digest
from rag.retrieval_memory import compact_retrieval_snapshot


FINAL_DOC_CHAR_LIMIT = 12000


def _join_lines(lines: list[str]) -> str:
    return "\n".join(line.rstrip() for line in lines if line is not None)


def _clean_text(text: str) -> str:
    value = str(text)
    for token in ("**", "__", "*", "`"):
        value = value.replace(token, "")
    return " ".join(value.split()).strip()


def _trim_block(text: str, char_limit: int, line_limit: int | None = None) -> str:
    lines = [line.strip() for line in str(text).splitlines() if line.strip()]
    if line_limit is not None:
        lines = lines[:line_limit]
    compact = _clean_text(" ".join(lines))
    if len(compact) <= char_limit:
        return compact
    return compact[: char_limit - 3].rstrip() + "..."


def _trim_document(text: str, char_limit: int) -> str:
    compact = str(text).strip()
    if len(compact) <= char_limit:
        return compact
    return compact[: char_limit - 3].rstrip() + "..."


def _sentences(text: str, limit: int = 2) -> list[str]:
    parts: list[str] = []
    for raw in str(text).replace("\n", " ").split(". "):
        sentence = _clean_text(raw).strip(" -")
        if sentence:
            parts.append(sentence.rstrip(".") + ".")
        if len(parts) >= limit:
            break
    return parts


def _bullets(lines: list[str], char_limit: int = 180, prefix: str = "•") -> list[str]:
    return [f"{prefix} {_trim_block(line, char_limit)}" for line in lines if str(line).strip()]


def _topic_info_list(state: dict, key: str, limit: int = 2) -> list[str]:
    topic_info = state.get("topic_info", {}) or {}
    values = topic_info.get(key, [])
    if not isinstance(values, list):
        return []
    return [_clean_text(item) for item in values if _clean_text(item)][:limit]


def _topic_info_text(state: dict, key: str, char_limit: int = 180) -> str:
    topic_info = state.get("topic_info", {}) or {}
    value = topic_info.get(key, "")
    return _trim_block(value, char_limit) if value else ""


def _pre_knowledge_points(state: dict) -> list[str]:
    points: list[str] = []

    specialist_notes = state.get("preknowledge_notes", []) or []
    if specialist_notes:
        for note in specialist_notes[:3]:
            points.append(_trim_block(note, 220))

    why = _topic_info_text(state, "why_this_matters_for_debate", 280)
    if why:
        points.append(f"Why this matters: {why}")

    for item in _topic_info_list(state, "essential_theoretical_frameworks", 2):
        points.append(f"Framework: {item}")

    for item in _topic_info_list(state, "key_concepts_own_these_precisely", 2):
        points.append(f"Key concept: {item}")

    if points:
        return points[:5]

    reference_background = str(state.get("reference_background", "")).strip()
    if reference_background:
        return _sentences(reference_background, limit=3)

    concepts = state.get("concepts", [])[:3]
    if concepts:
        return [f"Own this idea precisely: {_trim_block(concept, 140)}." for concept in concepts]
    return ["Know the core definition before you argue implementation."]


def _parse_english_lesson(state: dict) -> dict:
    lesson = str(state.get("english_lesson", "")).strip()
    parsed = {
        "word": "",
        "meaning": "",
        "upgrade": "",
        "debate_line": "",
        "bonus": "",
        "root": "",
    }
    for line in lesson.splitlines():
        clean = line.strip()
        lower = clean.lower()
        if lower.startswith("word:"):
            parsed["word"] = clean.split(":", 1)[1].strip()
        elif lower.startswith("meaning:"):
            parsed["meaning"] = clean.split(":", 1)[1].strip()
        elif lower.startswith("upgrade:"):
            parsed["upgrade"] = clean.split(":", 1)[1].strip()
        elif lower.startswith("debate line:"):
            parsed["debate_line"] = clean.split(":", 1)[1].strip()
        elif lower.startswith("bonus word:"):
            parsed["bonus"] = clean.split(":", 1)[1].strip()
        elif lower.startswith("root:"):
            parsed["root"] = clean.split(":", 1)[1].strip()

    vocab_words = state.get("vocab_words", []) or []
    if not parsed["word"] and vocab_words:
        parsed["word"] = _clean_text(vocab_words[0])
    if not parsed["bonus"] and len(vocab_words) > 1:
        parsed["bonus"] = f"{_clean_text(vocab_words[1])} = another sharp debate word to use this week."
    word_roots = state.get("word_roots", []) or []
    if not parsed["root"] and word_roots:
        parsed["root"] = f"{_clean_text(word_roots[0])} -> notice it in stronger English words."
    return parsed


def _extract_coach_sections(state: dict) -> dict:
    debate_angle = str(state.get("debate_angle", "")).strip()
    sections = {
        "unique_angle": "",
        "value_clash": "",
        "burden_of_proof": "",
        "mechanism": "",
        "open_with_this": "",
        "claim_warrant_impact": "",
        "top_rebuttal": "",
        "judge_language": "",
        "power_phrases": "",
    }
    if not debate_angle:
        return sections

    current_key = None
    label_map = {
        "UNIQUE ANGLE": "unique_angle",
        "VALUE CLASH": "value_clash",
        "BURDEN OF PROOF": "burden_of_proof",
        "MECHANISM": "mechanism",
        "OPEN WITH THIS": "open_with_this",
        "CLAIM-WARRANT-IMPACT": "claim_warrant_impact",
        "TOP REBUTTAL": "top_rebuttal",
        "TOP REBUTTALS": "top_rebuttal",
        "JUDGE LANGUAGE": "judge_language",
        "POWER PHRASES": "power_phrases",
    }

    for raw_line in debate_angle.splitlines():
        line = _clean_text(raw_line)
        if not line:
            continue
        matched = False
        for label, key in label_map.items():
            prefix = f"{label}:"
            if line.upper().startswith(prefix):
                sections[key] = line[len(prefix):].strip()
                current_key = key
                matched = True
                break
        if matched:
            continue
        if current_key:
            sections[current_key] = f"{sections[current_key]} {line}".strip()

    return sections


def _pick_lede(ranked_articles: list[dict]) -> dict | None:
    if not ranked_articles:
        return None

    def is_placeholder(article: dict) -> bool:
        title = str(article.get("title", "")).lower()
        return title.startswith("duckduckgo results for:")

    for article in ranked_articles:
        if _is_news_article(article) and not is_placeholder(article):
            return article
    for article in ranked_articles:
        if not is_placeholder(article) and not _is_reference_article(article) and not _is_explainer_article(article):
            return article
    for article in ranked_articles:
        if not is_placeholder(article) and not _is_reference_article(article):
            return article
    return ranked_articles[0]


def _summary_points_for_article(state: dict, article_index: int) -> list[str]:
    points: list[str] = []
    summaries = state.get("summaries", []) or []
    if 0 <= article_index < len(summaries):
        for line in str(summaries[article_index]).splitlines():
            clean = _clean_text(line).strip(" -")
            if clean and clean.upper() != "SUMMARY:":
                points.append(clean)
            if len(points) >= 4:
                return points
    return points


def _topical_case_lens(state: dict) -> str:
    live_cases = _topic_info_list(state, "live_case_studies_with_analytical_value", 1)
    return live_cases[0] if live_cases else ""


def _article_section(state: dict) -> tuple[list[str], dict | None]:
    ranked_articles = state.get("ranked_articles", [])
    article = state.get("lead_case") or _pick_lede(ranked_articles)
    if article is None:
        live_case = _topical_case_lens(state)
        if live_case:
            return [f"No sharp article landed today, so use this live case instead: {live_case}"], None
        return ["No strong live article landed today, so revise the framework and debate angles below."], None

    lines = [f"Article: {_trim_block(article.get('title', 'Untitled article'), 140)}"]
    weak_case = _is_reference_article(article) or _is_explainer_article(article) or str(article.get("title", "")).lower().startswith("duckduckgo results")
    try:
        article_index = ranked_articles.index(article)
    except ValueError:
        article_index = 0

    article_points = _summary_points_for_article(state, article_index)
    if not article_points:
        article_points = _sentences(article.get("content", ""), limit=3)
    deep_dive = state.get("case_deep_dive", []) or []
    if deep_dive:
        article_points.extend(str(item).strip() for item in deep_dive[:2] if str(item).strip())

    if weak_case:
        live_case = _topical_case_lens(state)
        if live_case:
            lines[0] = f"Use this live case lens: {_trim_block(live_case, 140)}"

    lines.extend(article_points[:4])

    key_facts = state.get("key_facts", []) or []
    if 0 <= article_index < len(key_facts):
        lines.append(f"Use this detail: {_trim_block(key_facts[article_index], 190)}")
    elif key_facts:
        lines.append(f"Use this detail: {_trim_block(key_facts[0], 190)}")

    live_case = _topical_case_lens(state)
    if live_case:
        lines.append(f"Why this matters in debate: {_trim_block(live_case, 210)}")

    return lines[:8], article


def _debate_section(state: dict) -> list[str]:
    arguments = state.get("arguments", {}) or {}
    coach_sections = _extract_coach_sections(state)
    lines: list[str] = []

    for index, item in enumerate(arguments.get("for", [])[:3], 1):
        lines.append(f"For argument {index}: {_trim_block(item, 250)}")
    for index, item in enumerate(arguments.get("against", [])[:3], 1):
        lines.append(f"Against argument {index}: {_trim_block(item, 250)}")

    middle = arguments.get("middle")
    if middle:
        lines.append(f"Main clash: {_trim_block(middle, 280)}")
    if coach_sections.get("value_clash"):
        lines.append(f"Underlying value clash: {_trim_block(coach_sections['value_clash'], 290)}")
    if coach_sections.get("burden_of_proof"):
        lines.append(f"Burden of proof: {_trim_block(coach_sections['burden_of_proof'], 290)}")
    if coach_sections.get("mechanism"):
        lines.append(f"Mechanism to explain: {_trim_block(coach_sections['mechanism'], 290)}")
    if coach_sections.get("claim_warrant_impact"):
        lines.append(f"Why this wins: {_trim_block(coach_sections['claim_warrant_impact'], 320)}")
    if coach_sections.get("top_rebuttal"):
        lines.append(f"Best rebuttal move: {_trim_block(coach_sections['top_rebuttal'], 290)}")
    if coach_sections.get("judge_language"):
        lines.append(f"Judge framing: {_trim_block(coach_sections['judge_language'], 260)}")
    if coach_sections.get("power_phrases"):
        lines.append(f"Power phrase to steal: {_trim_block(coach_sections['power_phrases'], 260)}")

    if not lines:
        lines.append("Compare the mechanism, who gets harmed first, and which side controls long-term incentives.")

    return lines[:10]


def _coach_note(state: dict) -> str:
    sections = _extract_coach_sections(state)
    if sections.get("unique_angle"):
        extra = ""
        if sections.get("open_with_this"):
            extra = f" Open with something like: {sections['open_with_this']}"
        return _trim_block(sections["unique_angle"] + extra, 560)

    misses = _topic_info_list(state, "argument_angles_most_debaters_miss", 1)
    if misses:
        return _trim_block(misses[0], 280)
    return "Do not stop at moral language. Prove the mechanism and the comparative impact."


def _rebuttal_drills(state: dict) -> list[str]:
    arguments = state.get("arguments", {}) or {}
    coach_sections = _extract_coach_sections(state)
    article_title, article_examples = _article_example_context(state)
    article_tag = f"in today's case about {article_title}" if article_title else "in today's case"
    drills: list[str] = []

    against_args = arguments.get("against", [])[:3]
    for_args = arguments.get("for", [])[:3]

    if against_args:
        example = _trim_block(article_examples[0], 150) if article_examples else "one concrete case detail"
        drills.append(
            f"If they say this against you: {_trim_block(against_args[0], 130)} | Reply by asking exactly where their feasibility objection kicks in, then anchor the answer {article_tag} with {example}."
        )
    if len(against_args) > 1:
        drills.append(
            f"If they push this second opposition line: {_trim_block(against_args[1], 130)} | Force them to explain what incentive changes would actually make actors behave differently, instead of just asserting collapse."
        )
    if for_args:
        example = _trim_block(article_examples[1], 150) if len(article_examples) > 1 else (_trim_block(article_examples[0], 150) if article_examples else "the article's strongest factual detail")
        drills.append(
            f"If they say this for you and you are opposing: {_trim_block(for_args[0], 130)} | Reply by attacking the mechanism, asking who pays the cost first, and showing why {example} weakens their precedent claim."
        )
    if coach_sections.get("top_rebuttal") and len(drills) < 4:
        drills.append(f"Detailed rebuttal script: {_trim_block(coach_sections['top_rebuttal'], 260)}")
    return drills[:4]


def _weight_language_lines() -> list[str]:
    return [
        "Use weighing words like: more likely, deeper harm, broader impact, less reversible, structurally entrenched.",
        "Use framing words like: the real question, the decisive distinction, the stronger comparison, on balance.",
        "Use judge language like: this matters more because, even if they win that point, we still win the round because.",
    ]


def _vocab_session(state: dict, english: dict) -> list[str]:
    lines: list[str] = []
    candidates = [str(word).strip() for word in (state.get("vocab_candidates", []) or []) if str(word).strip()]
    context_notes = [str(note).strip() for note in (state.get("vocab_context_notes", []) or []) if str(note).strip()]
    if english.get("meaning") and english.get("word"):
        lines.append(f"Use this precisely: {_trim_block(english['word'], 40)} means {_trim_block(english['meaning'], 150)}")
    if candidates:
        fresh = [word for word in candidates if word.lower() != str(english.get("word", "")).lower()]
        if fresh:
            lines.append(f"Fresh article word: {_trim_block(fresh[0], 36)} -> pull this into one rebuttal tomorrow.")
    if context_notes:
        lines.append(f"Why this word fits today: {_trim_block(context_notes[0], 220)}")
    if english.get("bonus"):
        lines.append(f"Bonus word: {_trim_block(english['bonus'], 180)}")
    if english.get("root"):
        lines.append(f"Root to notice: {_trim_block(english['root'], 160)}")
    if english.get("debate_line"):
        lines.append(f"Say it like this: {_trim_block(english['debate_line'], 220)}")
    if english.get("upgrade"):
        lines.append(f"Upgrade habit: {_trim_block(english['upgrade'], 180)}")
    return lines[:5] or ["Power move: Replace a vague adjective with a precise mechanism word."]


def _article_takeaway(state: dict, article_lines: list[str]) -> str:
    if len(article_lines) >= 3:
        return _trim_block(article_lines[2], 200)
    key_facts = state.get("key_facts", []) or []
    if key_facts:
        return _trim_block(key_facts[0], 200)
    return "Turn the case into a mechanism, not just an event summary."


def _article_example_context(state: dict) -> tuple[str, list[str]]:
    article_lines, article = _article_section(state)
    title = ""
    if article is not None:
        title = _trim_block(article.get("title", ""), 90)
    if not title and article_lines:
        title = _trim_block(article_lines[0], 90)

    examples: list[str] = []
    key_facts = state.get("key_facts", []) or []
    for fact in key_facts[:3]:
        clean = _trim_block(fact, 180)
        if clean and clean not in examples:
            examples.append(clean)

    for line in article_lines[1:5]:
        clean = _trim_block(line, 180)
        if clean and clean not in examples:
            examples.append(clean)
        if len(examples) >= 4:
            break

    deep_dive = state.get("case_deep_dive", []) or []
    for item in deep_dive[:2]:
        clean = _trim_block(item, 180)
        if clean and clean not in examples:
            examples.append(clean)
        if len(examples) >= 5:
            break
    return title, examples[:5]


def _argument_explanation(side: str, index: int) -> str:
    if side == "for":
        explanations = [
            "Why this matters: Lead with the principle or institutional good you are protecting. Show why the rule itself creates legitimacy, predictability, or durable cooperation.",
            "Why this matters: This is your mechanism argument. Explain the chain clearly: what actors want, what incentives they face, and why that produces the outcome you are claiming.",
            "Why this matters: This is your comparative-world argument. Show why your world allocates costs, risks, or opportunities better than the alternative world.",
        ]
    else:
        explanations = [
            "Why this matters: Attack the feasibility of their story. Ask where the model breaks once real actors face cost, fear, domestic pressure, or power asymmetry.",
            "Why this matters: This is your incentive critique. Show why even well-worded principles fail when states or institutions have reasons to defect or selectively comply.",
            "Why this matters: This is your second-order-effects argument. Prove that even if their first-order benefit exists, it triggers longer-term harms, backlash, or bad precedent.",
        ]
    return explanations[min(index, len(explanations) - 1)]


def _argument_case_example(argument: str, article_tag: str, examples: list[str], index: int) -> str:
    if not examples:
        return ""

    chosen = examples[min(index, len(examples) - 1)]
    lower = argument.lower()

    if any(token in lower for token in ("legitim", "norm", "fair", "rights", "order")):
        lens = "Use this to show how legitimacy or norm enforcement plays out in practice"
    elif any(token in lower for token in ("mechan", "incent", "deterren", "security", "power", "coerc")):
        lens = "Use this to walk the judge through the incentive chain step by step"
    elif any(token in lower for token in ("middle power", "compar", "world", "tradeoff", "cost", "precedent")):
        lens = "Use this as a comparative example to show who benefits, who pays, and what precedent follows"
    else:
        lens = "Use this concrete case detail to anchor the abstract claim"

    return f"Example: {lens} {article_tag}: {_trim_block(chosen, 200)}"


def _explain_debate_lines(state: dict) -> list[str]:
    arguments = state.get("arguments", {}) or {}
    coach_sections = _extract_coach_sections(state)
    article_title, article_examples = _article_example_context(state)
    article_tag = f"in today's case about {article_title}" if article_title else "in today's case"

    lines: list[str] = []

    for index, item in enumerate(arguments.get("for", [])[:3], 1):
        lines.append(f"For argument {index}: {_trim_block(item, 230)}")
        lines.append(_argument_explanation("for", index - 1))
        example = _argument_case_example(item, article_tag, article_examples, index - 1)
        if example:
            lines.append(example)

    for index, item in enumerate(arguments.get("against", [])[:3], 1):
        lines.append(f"Against argument {index}: {_trim_block(item, 230)}")
        lines.append(_argument_explanation("against", index - 1))
        example = _argument_case_example(item, article_tag, article_examples, index + 1)
        if example:
            lines.append(example)

    middle = arguments.get("middle")
    if middle:
        lines.append(f"Main clash: {_trim_block(middle, 260)}")
        lines.append(
            "Clash explanation: This is the hinge of the round. It tells you which comparison the judge must care about once both teams finish giving examples."
        )
    if coach_sections.get("value_clash"):
        lines.append(f"Underlying value clash: {_trim_block(coach_sections['value_clash'], 280)}")
        lines.append(
            "Value clash explained: This tells you what moral or political priorities are actually colliding underneath the surface story."
        )
    if coach_sections.get("burden_of_proof"):
        lines.append(f"Burden of proof: {_trim_block(coach_sections['burden_of_proof'], 280)}")
    if coach_sections.get("mechanism"):
        lines.append(f"Mechanism to explain: {_trim_block(coach_sections['mechanism'], 280)}")
        if article_examples:
            lines.append(
                f"Mechanism example: Use {article_tag} to show the step-by-step chain, not just the outcome. Start from actor incentives, then show how that produced {_trim_block(article_examples[0], 170)}"
            )
    if coach_sections.get("claim_warrant_impact"):
        lines.append(f"Why this wins: {_trim_block(coach_sections['claim_warrant_impact'], 320)}")
    if coach_sections.get("judge_language"):
        lines.append(f"Judge framing: {_trim_block(coach_sections['judge_language'], 250)}")

    return lines[:22]


def _things_to_take_care(state: dict) -> list[str]:
    lines: list[str] = []
    concepts = state.get("concepts") or []
    if concepts:
        lines.append(f"Do not misuse the term {_trim_block(concepts[0], 95)} without defining it.")
    if len(concepts) > 1:
        lines.append(f"Keep this distinction ready: {_trim_block(concepts[1], 150)}")
    key_facts = state.get("key_facts", []) or []
    if key_facts:
        lines.append(f"Do not quote this loosely: {_trim_block(key_facts[0], 180)}")
    lines.append(f"Main article takeaway: {_trim_block(_article_takeaway(state, _article_section(state)[0]), 210)}")
    lines.append(f"Use this recall trigger: {_trim_block(_recall_prompt(state), 200)}")
    return lines[:5]


def _recall_prompt(state: dict) -> str:
    topic = topic_name(state.get("topic"))
    concept = _clean_text((state.get("concepts") or ["the main concept"])[0])
    return f"Explain in one line why {concept} changes how we debate {topic}."


def _heuristic_format(state: dict) -> str:
    topic = topic_name(state.get("topic"))
    english = _parse_english_lesson(state)
    pre_knowledge = _pre_knowledge_points(state)
    article_lines, _article = _article_section(state)
    debate_lines = _explain_debate_lines(state)
    rebuttal_drills = _rebuttal_drills(state)
    weight_lines = _weight_language_lines()
    vocab_lines = _vocab_session(state, english)
    care_lines = _things_to_take_care(state)

    lines = [
        "🎯 TOPIC FOR TODAY",
        topic.upper(),
        f"_{_trim_block(state.get('selector_reason', 'Priority topic rotation.'), 140)}_",
        "",
        "🧠 PRE-KNOWLEDGE",
        *_bullets(pre_knowledge, 235),
        "",
        "📖 WORD BEFORE YOU READ",
        f"• {_trim_block(english.get('word') or 'lucid', 32)} = {_trim_block(english.get('meaning') or 'clear and easy to follow', 170)}",
        f"• {_trim_block(english.get('upgrade') or 'Use a sharper word than good when you explain a claim.', 210)}",
        f"• Why it helps today: Use this word when you contrast {_trim_block(topic, 40)} arguments with more precision.",
        "",
        "📰 TODAY'S ARTICLE / CASE",
        *_bullets(article_lines, 255),
        "",
        "⚔️ YOUR DEBATING BUILD",
        *_bullets(debate_lines, 255),
        f"• Coach note: {_trim_block(_coach_note(state), 560)}",
        "",
        "🛡️ REBUTTAL DRILLS",
        *_bullets(rebuttal_drills, 255),
        "",
        "🎙️ WEIGHING LANGUAGE TO USE",
        *_bullets(weight_lines, 240),
        "",
        "🗣️ VOCAB SESSION",
        *_bullets(vocab_lines, 225),
        "",
        "✅ THINGS TO TAKE CARE",
        *_bullets(care_lines, 235),
    ]

    output = _join_lines(lines).strip()
    return _trim_document(output, FINAL_DOC_CHAR_LIMIT)


def format_node(state: dict) -> dict:
    state["task_type"] = "format"
    topic = topic_name(state.get("topic"))
    pre_knowledge = _pre_knowledge_points(state)
    state["final_doc"] = _heuristic_format(state)

    save_daily_digest(
        topic,
        {
            "selector_reason": state.get("selector_reason", ""),
            "pre_knowledge": pre_knowledge,
            "ranked_articles": state.get("ranked_articles", []),
            "summaries": state.get("summaries", []),
            "arguments": state.get("arguments", {}),
            "key_facts": state.get("key_facts", []),
            "concepts": state.get("concepts", []),
            "debate_angle": state.get("debate_angle", ""),
            "english_lesson": state.get("english_lesson", ""),
            "vocab_words": state.get("vocab_words", []),
            "word_roots": state.get("word_roots", []),
            "retrieval_memory": compact_retrieval_snapshot(state),
        },
    )

    return state
