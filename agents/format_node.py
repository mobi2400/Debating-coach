from __future__ import annotations

from agents.rank_node import _is_explainer_article, _is_news_article, _is_reference_article
from core.debate_guidance import get_node_guidance
from core.topic_utils import topic_name
from memory.weekly_store import save_daily_digest
from rag.retrieval_memory import compact_retrieval_snapshot


FINAL_DOC_CHAR_LIMIT = 15000


def _remove_ellipses(text: str) -> str:
    value = str(text).replace('?', '.').replace('...', '.')
    while '..' in value:
        value = value.replace('..', '.')
    return value


def _format_rules() -> dict:
    guidance = get_node_guidance("format_node")
    contract = guidance.get("contract", {}) or {}
    node_rules = contract.get("nodes.format_node", {}) or {}
    guardrails = contract.get("cross_node_guardrails", {}) or {}
    return {
        "must_do": [str(item).strip() for item in node_rules.get("must_do", []) if str(item).strip()],
        "must_not_do": [str(item).strip() for item in node_rules.get("must_not_do", []) if str(item).strip()],
        "required_end_state": [str(item).strip() for item in guardrails.get("required_end_state", []) if str(item).strip()],
    }


def _join_lines(lines: list[str]) -> str:
    return "\n".join(line.rstrip() for line in lines if line is not None)


def _clean_text(text: str) -> str:
    value = _remove_ellipses(str(text))
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

    floor = max(int(char_limit * 0.6), 40)
    window = compact[:char_limit]
    for marker in (". ", "! ", "? ", "; ", ": "):
        idx = window.rfind(marker)
        if idx >= floor:
            clipped = window[: idx + 1].rstrip()
            return clipped if clipped.endswith((".", "!", "?")) else clipped + "."

    split_at = window.rfind(" ")
    if split_at >= floor:
        clipped = window[:split_at].rstrip()
        return clipped if clipped.endswith((".", "!", "?")) else clipped + "."

    return compact[:char_limit].rstrip()


def _trim_document(text: str, char_limit: int) -> str:
    compact = str(text).strip()
    if len(compact) <= char_limit:
        return compact
    return _remove_ellipses(compact[:char_limit].rstrip())


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

    topic_foundation = state.get("topic_foundation", {}) or {}
    specialist_notes = topic_foundation.get("notes") if isinstance(topic_foundation, dict) else []
    if not specialist_notes:
        specialist_notes = state.get("preknowledge_notes", []) or []
    if specialist_notes:
        for note in specialist_notes[:3]:
            points.append(_trim_block(note, 220))

    frameworks = topic_foundation.get("frameworks", []) if isinstance(topic_foundation, dict) else []
    for item in frameworks[:2]:
        clean = _clean_text(item)
        if clean:
            points.append(f"Framework: {clean}")

    key_concepts = topic_foundation.get("key_concepts", []) if isinstance(topic_foundation, dict) else []
    for item in key_concepts[:2]:
        clean = _clean_text(item)
        if clean:
            points.append(f"Key concept: {clean}")

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
    article_context = state.get("article_context", {}) or {}
    article_notes = article_context.get("notes", []) if isinstance(article_context, dict) else []
    if article_notes:
        article_points.extend(str(item).strip() for item in article_notes[:2] if str(item).strip())

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


def _coach_note_lines(state: dict) -> list[str]:
    teaching = state.get("debate_teaching", {}) or {}
    coach_note = teaching.get("coach_note", {}) or {}
    if isinstance(coach_note, dict) and coach_note:
        lines = ["Coach note:"]
        if coach_note.get("how_to_open"):
            lines.append(f"Start with this: {_clean_text(coach_note['how_to_open'])}")
        if coach_note.get("hidden_lens"):
            lines.append(f"Hidden lens: {_clean_text(coach_note['hidden_lens'])}")
        if coach_note.get("what_most_debaters_miss"):
            lines.append(f"What most debaters miss: {_clean_text(coach_note['what_most_debaters_miss'])}")
        if coach_note.get("what_wins_the_judge"):
            lines.append(f"What wins the judge: {_clean_text(coach_note['what_wins_the_judge'])}")
        return lines[:5]

    sections = _extract_coach_sections(state)
    if sections.get("unique_angle"):
        lines = ["Coach note:"]
        if sections.get("open_with_this"):
            lines.append(f"Start with this: {_clean_text(sections['open_with_this'])}")
        lines.append(f"Hidden lens: {_clean_text(sections['unique_angle'])}")
        return lines[:3]

    misses = _topic_info_list(state, "argument_angles_most_debaters_miss", 1)
    if misses:
        return ["Coach note:", f"Hidden lens: {_clean_text(misses[0])}"]
    return ["Coach note:", "Hidden lens: Do not stop at moral language. Prove the mechanism and the comparative impact."]


def _rebuttal_drills(state: dict) -> list[dict[str, str]]:
    arguments = state.get("arguments", {}) or {}
    coach_sections = _extract_coach_sections(state)
    article_title, article_examples = _article_example_context(state)
    article_tag = f"in today's case about {article_title}" if article_title else "in today's case"
    drills: list[dict[str, str]] = []

    against_args = arguments.get("against", [])[:3]
    for_args = arguments.get("for", [])[:3]

    if against_args:
        example = _trim_block(article_examples[0], 150) if article_examples else "one concrete case detail"
        drills.append({
            "prompt": f"If they say this against you: {_trim_block(against_args[0], 170)}",
            "answer": (
                "Answer: Ask them to identify the exact point where their feasibility objection starts to bite. "
                f"Then bring the round back to outcomes {article_tag} by showing how {example} proves the harm is not abstract and cannot be postponed."
            ),
        })
    if len(against_args) > 1:
        drills.append({
            "prompt": f"If they push this second opposition line: {_trim_block(against_args[1], 170)}",
            "answer": (
                "Answer: Force them to explain what incentive changes would actually make actors behave differently. "
                "If they cannot show that alternative mechanism, say they are describing frustration with the world as it is, not a better comparative world."
            ),
        })
    if for_args:
        example = _trim_block(article_examples[1], 150) if len(article_examples) > 1 else (_trim_block(article_examples[0], 150) if article_examples else "the article's strongest factual detail")
        drills.append({
            "prompt": f"If they say this for you and you are opposing: {_trim_block(for_args[0], 170)}",
            "answer": (
                "Answer: Attack the mechanism first. Ask who pays the cost immediately, who implements the policy in the real world, "
                f"and why {example} shows their precedent is weaker than they claim."
            ),
        })
    if coach_sections.get("top_rebuttal") and len(drills) < 4:
        drills.append({
            "prompt": "Detailed rebuttal script:",
            "answer": f"Answer: {_clean_text(coach_sections['top_rebuttal'])}",
        })
    return drills[:4]


def _rebuttal_drill_lines(state: dict) -> list[str]:
    lines: list[str] = []
    for drill in _rebuttal_drills(state):
        prompt = _clean_text(drill.get("prompt", ""))
        answer = _clean_text(drill.get("answer", ""))
        if prompt:
            lines.append(prompt)
        if answer:
            lines.append(answer)
        if prompt or answer:
            lines.append("")
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def _weight_language_lines() -> list[str]:
    return [
        "Use weighing words like: more likely, deeper harm, broader impact, less reversible, structurally entrenched.",
        "Use framing words like: the real question, the decisive distinction, the stronger comparison, on balance.",
        "Use judge language like: this matters more because, even if they win that point, we still win the round because.",
    ]


def _vocab_session(state: dict, english: dict) -> list[str]:
    lines: list[str] = []
    vocabulary_output = state.get("vocabulary_output", {}) or {}
    selected_words = vocabulary_output.get("selected_words", []) if isinstance(vocabulary_output, dict) else []
    context_notes = [str(note).strip() for note in (state.get("vocab_context_notes", []) or []) if str(note).strip()]

    for item in selected_words[:2]:
        word = _trim_block(item.get("word", ""), 36)
        meaning = _trim_block(item.get("meaning", ""), 170)
        why = _trim_block(item.get("why_it_helps", ""), 210)
        example = _trim_block(item.get("example", ""), 220)
        if word and meaning:
            lines.append(f"{word}: {meaning}")
        if why:
            lines.append(f"Why use it: {why}")
        if example:
            lines.append(f"Example: {example}")

    if not lines and english.get("meaning") and english.get("word"):
        lines.append(f"Use this precisely: {_trim_block(english['word'], 40)} means {_trim_block(english['meaning'], 150)}")
    if context_notes:
        lines.append(f"Why this word fits today: {_trim_block(context_notes[0], 220)}")
    if english.get("bonus"):
        lines.append(f"Second useful word: {_trim_block(english['bonus'], 180)}")
    return lines[:6] or ["Power move: Replace a vague adjective with a precise mechanism word."]


def _motion_section(state: dict) -> list[str]:
    drafted_motion = state.get("drafted_motion", {}) or {}
    motion_text = str(drafted_motion.get("drafted_motion", "")).strip()
    if not motion_text:
        return []

    lines = [motion_text]
    clash_axes = drafted_motion.get("likely_clash_axis", []) or []
    prop_burden = drafted_motion.get("prop_burden", []) or []
    opp_burden = drafted_motion.get("opp_burden", []) or []
    motion_type = str(drafted_motion.get("motion_type", "")).strip()
    motion_type_explanation = drafted_motion.get("motion_type_explanation", {}) or {}
    why_balanced = str(drafted_motion.get("why_this_motion_is_balanced", "")).strip()
    if motion_type:
        lines.append(f"Motion type: {motion_type}")
    if motion_type_explanation.get("what_it_means"):
        lines.append(f"What this motion type means: {_trim_block(motion_type_explanation.get('what_it_means', ''), 260)}")
    if motion_type_explanation.get("how_to_debate_it"):
        lines.append(f"How to build arguments in this motion: {_trim_block(motion_type_explanation.get('how_to_debate_it', ''), 260)}")
    if clash_axes:
        lines.append(f"Main clash axis: {clash_axes[0]}")
    if prop_burden:
        lines.append(f"Proposition must prove: {_trim_block(prop_burden[0], 210)}")
    if opp_burden:
        lines.append(f"Opposition must prove: {_trim_block(opp_burden[0], 210)}")
    if why_balanced:
        lines.append(f"Why this is balanced: {_trim_block(why_balanced, 220)}")
    return lines[:5]


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


def _compact_argument_block(label: str, block: dict) -> list[str]:
    claim = _clean_text(block.get("claim", ""))
    framing = _clean_text(block.get("explanation", ""))
    framing_example = _clean_text(block.get("framing_example", ""))
    mechanism = _clean_text(block.get("mechanism", ""))
    mechanism_example = _clean_text(block.get("mechanism_example", ""))
    lines = [f"{label}: {claim}"]
    if framing:
        lines.append(f"Framing: {framing}")
    if framing_example:
        lines.append(f"Framing example: {framing_example}")
    if mechanism:
        lines.append(f"Mechanism: {mechanism}")
    if mechanism_example:
        lines.append(f"Mechanism example: {mechanism_example}")
    return lines


def _explain_debate_lines(state: dict) -> list[str]:
    teaching = state.get("debate_teaching", {}) or {}
    coach_sections = _extract_coach_sections(state)
    drafted_motion = state.get("drafted_motion", {}) or {}
    motion_text = str(drafted_motion.get("drafted_motion", "")).strip()
    motion_type = str(drafted_motion.get("motion_type", "")).strip()
    motion_type_explanation = drafted_motion.get("motion_type_explanation", {}) or {}
    lines: list[str] = []

    if motion_text:
        lines.append(f"Motion we are debating: {_trim_block(motion_text, 240)}")
    if motion_type:
        lines.append(f"Motion type: {_trim_block(motion_type, 60)}")
    if motion_type_explanation.get("what_it_means"):
        lines.append(f"What this motion type means: {_trim_block(motion_type_explanation.get('what_it_means', ''), 280)}")
    if motion_type_explanation.get("how_to_debate_it"):
        lines.append(f"How to handle the burden in this motion: {_trim_block(motion_type_explanation.get('how_to_debate_it', ''), 280)}")

    motion_explanation = str(teaching.get("motion_explanation", "")).strip()
    if motion_explanation:
        lines.append(f"What this round is really asking: {_trim_block(motion_explanation, 340)}")

    prop_burdens = teaching.get("prop_burden", []) or []
    if prop_burdens:
        lines.append(f"If you are proposition, prove this: {_trim_block(prop_burdens[0], 250)}")
    opp_burdens = teaching.get("opp_burden", []) or []
    if opp_burdens:
        lines.append(f"If you are opposition, prove this: {_trim_block(opp_burdens[0], 250)}")

    for index, block in enumerate((teaching.get("for_arguments", []) or [])[:2], 1):
        lines.extend(_compact_argument_block(f"For argument {index}", block))

    for index, block in enumerate((teaching.get("against_arguments", []) or [])[:2], 1):
        lines.extend(_compact_argument_block(f"Against argument {index}", block))

    core_clash = teaching.get("core_clash", {}) or {}
    if core_clash.get("main_clash"):
        lines.append(f"Main clash: {_trim_block(core_clash.get('main_clash', ''), 250)}")
    if core_clash.get("what_prop_says"):
        lines.append(f"What proposition says matters most: {_trim_block(core_clash.get('what_prop_says', ''), 260)}")
    if core_clash.get("what_opp_says"):
        lines.append(f"What opposition says matters most: {_trim_block(core_clash.get('what_opp_says', ''), 260)}")
    if core_clash.get("judge_comparison"):
        lines.append(f"How the judge should decide: {_trim_block(core_clash.get('judge_comparison', ''), 320)}")

    mechanism = teaching.get("mechanism", {}) or {}
    mechanism_steps = mechanism.get("step_by_step_logic", []) if isinstance(mechanism, dict) else []
    if mechanism_steps:
        joined = " -> ".join(_trim_block(step, 120) for step in mechanism_steps[:2] if str(step).strip())
        if joined:
            lines.append(f"Mechanism chain to explain in your speech: {joined}")

    framing = teaching.get("framing", {}) or {}
    if framing.get("prop_frame"):
        lines.append(f"Best proposition framing: {_trim_block(framing.get('prop_frame', ''), 340)}")
    if framing.get("opp_frame"):
        lines.append(f"Best opposition framing: {_trim_block(framing.get('opp_frame', ''), 340)}")
    if framing.get("strategic_note"):
        lines.append(f"What the judge should care about most: {_trim_block(framing.get('strategic_note', ''), 340)}")

    if coach_sections.get("claim_warrant_impact"):
        lines.append(f"Coach lens: {_trim_block(coach_sections['claim_warrant_impact'], 420)}")

    return lines

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
    rules = _format_rules()
    english = _parse_english_lesson(state)
    pre_knowledge = _pre_knowledge_points(state)
    article_lines, _article = _article_section(state)
    motion_lines = _motion_section(state)
    debate_lines = _explain_debate_lines(state)
    rebuttal_drill_lines = _rebuttal_drill_lines(state)
    weight_lines = _weight_language_lines()
    vocab_lines = _vocab_session(state, english)
    coach_note_lines = _coach_note_lines(state)
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
        "",
        *coach_note_lines,
        "",
        "🛡️ REBUTTAL DRILLS",
        *_bullets(rebuttal_drill_lines, 320),
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
    rules = _format_rules()
    pre_knowledge = _pre_knowledge_points(state)
    article_lines, _article = _article_section(state)
    motion_lines = _motion_section(state)
    debate_lines = _explain_debate_lines(state)
    state["final_sections"] = {
        "pre_knowledge": pre_knowledge,
        "article": article_lines,
        "motion": motion_lines,
        "debate": debate_lines,
        "vocab": _vocab_session(state, _parse_english_lesson(state)),
        "format_rules": rules,
    }
    state["final_doc"] = _heuristic_format(state)

    save_daily_digest(
        topic,
        {
            "selector_reason": state.get("selector_reason", ""),
            "pre_knowledge": pre_knowledge,
            "ranked_articles": state.get("ranked_articles", []),
            "summaries": state.get("summaries", []),
            "arguments": state.get("arguments", {}),
            "drafted_motion": state.get("drafted_motion", {}),
            "motion_intelligence": state.get("motion_intelligence", {}),
            "key_facts": state.get("key_facts", []),
            "concepts": state.get("concepts", []),
            "debate_angle": state.get("debate_angle", ""),
            "english_lesson": state.get("english_lesson", ""),
            "vocab_words": state.get("vocab_words", []),
            "vocabulary_output": state.get("vocabulary_output", {}),
            "word_roots": state.get("word_roots", []),
            "retrieval_memory": compact_retrieval_snapshot(state),
        },
    )

    return state
