import os
from langchain_openai import ChatOpenAI

def _make_llm(model_env: str, temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv(model_env, "gpt-4.1-nano"),
        temperature=temperature,
    )


def make_resume_writer_llm(temperature: float = 0.3) -> ChatOpenAI:
    return _make_llm("OPENAI_MODEL_RESUME", temperature=temperature)


def make_parser_llm() -> ChatOpenAI:
    return _make_llm("OPENAI_MODEL_PARSER", temperature=0.0)


def make_cover_letter_writer_llm(temperature: float = 0.3) -> ChatOpenAI:
    return _make_llm("OPENAI_MODEL_COVERLETTER", temperature=temperature)
