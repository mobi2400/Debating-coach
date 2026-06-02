import os

from dotenv import load_dotenv

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    ChatGoogleGenerativeAI = None

try:
    from langchain_groq import ChatGroq
except ImportError:  # pragma: no cover - exercised in bootstrap environments
    ChatGroq = None

load_dotenv()


class MissingDependencyLLM:
    def __init__(self, provider: str, package_name: str):
        self.provider = provider
        self.package_name = package_name

    def invoke(self, _: str):
        raise RuntimeError(
            f"{self.provider} provider is unavailable. Install '{self.package_name}' "
            "from requirements.txt before invoking this model."
        )


def _groq_model(model: str, temperature: float, max_tokens: int):
    if ChatGroq is None:
        return MissingDependencyLLM("Groq", "langchain-groq")
    return ChatGroq(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        groq_api_key=os.getenv("GROQ_API_KEY"),
    )


def _gemini_model(model: str, temperature: float, max_output_tokens: int):
    if ChatGoogleGenerativeAI is None:
        return MissingDependencyLLM("Google Gemini", "langchain-google-genai")
    return ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )


LLM_POOL = {
    "fast": _groq_model(
        model="llama-3.1-8b-instant",
        temperature=0.1,
        max_tokens=2048,
    ),
    "balanced": _groq_model(
        model="llama-3.3-70b-versatile",
        temperature=0.3,
        max_tokens=4096,
    ),
    "structured": _groq_model(
        model="mixtral-8x7b-32768",
        temperature=0.1,
        max_tokens=4096,
    ),
    "reasoning": _groq_model(
        model="deepseek-r1-distill-llama-70b",
        temperature=0.4,
        max_tokens=4096,
    ),
    "long_ctx": _gemini_model(
        model="gemini-1.5-flash",
        temperature=0.2,
        max_output_tokens=4096,
    ),
    "best": _gemini_model(
        model="gemini-1.5-pro",
        temperature=0.5,
        max_output_tokens=4096,
    ),
}
