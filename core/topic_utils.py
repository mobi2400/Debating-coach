from __future__ import annotations


def topic_name(topic: object) -> str:
    if isinstance(topic, str):
        return topic.strip()

    if isinstance(topic, dict):
        value = topic.get("topic")
        if isinstance(value, str):
            return value.strip()

    if topic is None:
        return ""

    return str(topic).strip()

