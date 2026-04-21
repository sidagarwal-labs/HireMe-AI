import os
from langchain_openai import ChatOpenAI

def _make_llm(model_env: str):
    return ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv(model_env, "gpt-5-nano"),
        temperature=0.2
    )


def make_resume_writer_llm() -> ChatOpenAI:
    return _make_llm("OPENAI_MODEL_RESUME")


def make_parser_llm() -> ChatOpenAI:
    return _make_llm("OPENAI_MODEL_PARSER")


def make_cover_letter_writer_llm() -> ChatOpenAI:
    return _make_llm("OPENAI_MODEL_COVERLETTER")
