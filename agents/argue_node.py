import json

from core.debate_guidance import build_targeted_context
from core.fallback import get_llm_with_fallback
from core.prompt_cache import cached_invoke
from core.topic_utils import topic_name
from rag.evidence_organizer import format_structured_evidence, organize_evidence
from rag.retrieval_pipeline import format_retrieved_context, retrieve_bundle_for_node


MAX_RAG_CHARS = 1000
MAX_SUMMARIES = 2


def _topic_info_list(topic_info: dict, key: str, limit: int = 2) -> list[str]:
    values = topic_info.get(key, [])
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()][:limit]


def _clean_line(text: str) -> str:
    return " ".join(str(text).split()).strip()


def _summary_lines(summaries: list[str]) -> list[str]:
    lines: list[str] = []
    for summary in summaries:
        for raw in str(summary).splitlines():
            clean = _clean_line(raw).strip('- ')
            if clean and clean.upper() != 'SUMMARY:':
                lines.append(clean)
    return lines


def _argument_seed_points(topic: str, summaries: list[str], topic_info: dict, drafted_motion: dict) -> dict:
    summary_points = _summary_lines(summaries)
    frameworks = _topic_info_list(topic_info, 'essential_theoretical_frameworks', 2)
    mechanisms = _topic_info_list(topic_info, 'the_mechanisms_to_understand', 2)
    missed_angles = _topic_info_list(topic_info, 'argument_angles_most_debaters_miss', 2)
    live_cases = _topic_info_list(topic_info, 'live_case_studies_with_analytical_value', 1)
    clash_axes = drafted_motion.get('likely_clash_axis', []) if isinstance(drafted_motion, dict) else []

    default_for = [
        summary_points[0] if summary_points else f'{topic.title()} requires an argument about who is excluded from power and how institutions reproduce that exclusion.',
        frameworks[0] if frameworks else f'Build a proposition case around structural reform rather than abstract moral approval of {topic}.',
        missed_angles[0] if missed_angles else 'Show why delaying reform preserves the current distribution of harm instead of staying neutral.',
    ]
    default_against = [
        summary_points[1] if len(summary_points) > 1 else f'Challenge whether the chosen mechanism in {topic} solves the real problem rather than only producing symbolic change.',
        mechanisms[0] if mechanisms else 'Interrogate which incentives actually change, which actors resist, and who bears the cost when implementation is blunt.',
        missed_angles[1] if len(missed_angles) > 1 else 'Press second-order effects like backlash, legitimacy loss, or policy capture if the reform is badly designed.',
    ]
    middle = (
        f"Use the live case '{live_cases[0]}' to accept the goal but dispute whether this exact tool is fair, feasible, and durable."
        if live_cases else
        f"A strong middle ground on {topic} accepts the goal but disputes whether this mechanism solves the right problem."
    )
    if clash_axes:
        middle = f"The middle ground accepts the value but asks whether '{clash_axes[0]}' should be resolved through this tool or through a less distortive mechanism."

    return {
        'for': [_clean_line(item) for item in default_for[:3]],
        'against': [_clean_line(item) for item in default_against[:3]],
        'middle': _clean_line(middle),
    }


def _looks_like_motion_echo(text: str, motion_text: str) -> bool:
    clean = _clean_line(text).lower()
    motion = _clean_line(motion_text).lower()
    if not clean:
        return True
    if motion and (clean == motion or clean in motion or motion[:80] in clean):
        return True
    bad_starts = (
        'under the motion',
        'challenge the motion',
        'prove that governments',
        'show where the mechanism breaks',
        'if you are proposition',
        'if you are opposition',
    )
    return clean.startswith(bad_starts)


def _normalize_arg_list(value, fallback: list[str], motion_text: str) -> list[str]:
    if not isinstance(value, list):
        return fallback[:3]
    cleaned: list[str] = []
    for item in value:
        line = _clean_line(item)
        if not line or _looks_like_motion_echo(line, motion_text):
            continue
        if line not in cleaned:
            cleaned.append(line)
        if len(cleaned) >= 3:
            break
    for filler in fallback:
        if filler not in cleaned:
            cleaned.append(filler)
        if len(cleaned) >= 3:
            break
    return cleaned[:3]


def _extract_json_object(content: str) -> dict | None:
    text = str(content or '').strip()
    if not text:
        return None
    if text.startswith('```'):
        text = text.split('```', 2)[1]
        if text.startswith('json'):
            text = text[4:]
        text = text.strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass

    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        snippet = text[start:end + 1]
        try:
            parsed = json.loads(snippet)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
    return None


def _invoke_argument_json(state: dict, prompt: str) -> dict | None:
    llm = get_llm_with_fallback(state)
    response = cached_invoke(llm, prompt, scope='argue')
    parsed = _extract_json_object(str(getattr(response, 'content', response)))
    if parsed is not None:
        return parsed

    repair_prompt = (
        'Repair this into valid JSON only with keys for, against, middle. '
        'Both for and against must be arrays of exactly 3 short argument strings. '
        'middle must be one short string.\n\nRAW OUTPUT:\n'
        f"{str(getattr(response, 'content', response))}"
    )
    repair = cached_invoke(llm, repair_prompt, scope='argue_repair')
    return _extract_json_object(str(getattr(repair, 'content', repair)))


def argue_node(state: dict) -> dict:
    state['task_type'] = 'argue'
    topic = topic_name(state.get('topic'))
    summaries = state.get('summaries', [])[:MAX_SUMMARIES]
    topic_info = state.get('topic_info', {}) or {}
    drafted_motion = state.get('drafted_motion', {}) or {}
    lead_title = str((state.get('lead_case') or {}).get('title', '')).strip()
    motion_text = str(drafted_motion.get('drafted_motion', '')).strip()
    query = f"{topic} {lead_title} {motion_text}".strip()
    bundle = retrieve_bundle_for_node('argue_node', query, state=state)
    rag_chunks = bundle['chunks']
    rag_context = format_retrieved_context(rag_chunks)
    structured_evidence = organize_evidence(rag_chunks)
    structured_context = format_structured_evidence(structured_evidence, per_section=2)
    state.setdefault('retrieval_plans', {})['argue_node'] = bundle['plan'] or {}
    state.setdefault('retrieval_traces', {})['argue_node'] = bundle['trace']
    state['argument_evidence'] = structured_evidence

    default_arguments = _argument_seed_points(topic, summaries, topic_info, drafted_motion)

    if not summaries and not rag_context:
        state['arguments'] = default_arguments
        return state

    guidance = build_targeted_context(
        'argue_node',
        sections=[
            ('concepts', 'argumentation'),
            ('concepts', 'burdens'),
            ('concepts', 'mechanism'),
            ('contract', 'nodes.argue_node'),
            ('contract', 'cross_node_guardrails'),
        ],
        max_chars=2600,
    )

    prompt = (
        'You are generating debate arguments for a student who needs substance, not buzzwords.\n'
        'Return JSON only with keys: for, against, middle.\n'
        "'for' and 'against' must each be arrays of exactly 3 arguments.\n"
        "'middle' must be one nuanced bridging position.\n"
        'Do not restate the motion as an argument.\n'
        'Each argument should be a real claim about institutions, incentives, harms, or comparative outcomes.\n\n'
        f'Topic: {topic}\n'
        f'Lead case: {lead_title}\n'
        f'Generated motion: {motion_text}\n'
        f'Summaries: {json.dumps(summaries, ensure_ascii=False)}\n'
        f'Structured evidence:\n{structured_context[:MAX_RAG_CHARS]}\n\n'
        f'Fallback RAG context: {rag_context[:MAX_RAG_CHARS]}'
    )

    try:
        parsed = _invoke_argument_json(state, prompt)
        if not isinstance(parsed, dict):
            raise ValueError('argue LLM returned no valid JSON object after repair')

        state['arguments'] = {
            'for': _normalize_arg_list(parsed.get('for'), default_arguments['for'], motion_text),
            'against': _normalize_arg_list(parsed.get('against'), default_arguments['against'], motion_text),
            'middle': _clean_line(parsed.get('middle') or default_arguments['middle']),
        }
    except Exception as exc:
        print(f'[Argue] LLM parse failed: {exc}')
        state['arguments'] = default_arguments

    return state
