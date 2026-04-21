from __future__ import annotations
import json

import re 
from collections import Counter
from typing import Any 

from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage

# Starter file for LLM tools. Define your tool schemas and @tool functions here.

class StripLocationInput(BaseModel):
    text: str = Field(..., description="Text that may include location info.")

class ExtractKeywordsInput(BaseModel):
    job_description: str = Field(..., description="Full job description text.")
    top_k: int = Field(15, ge=5, le=40)


@tool("strip_location", args_schema=StripLocationInput)
def strip_location(text: str) -> str:
    """Remove comon location markers like '(Remote)' or ', CA'."""
    text = re.sub(r"\((remote|hybrid|onsite)\)", "", text, flags=re.I)
    text = re.sub(r",\s*[A-Z]{2}\b", "", text)  # ", CA"
    return re.sub(r"\s{2,}", " ", text).strip(" ,-|" )

@tool("extract_job_keywords", args_schema=ExtractKeywordsInput)
def extract_job_keywords(job_description: str, top_k: int = 15) -> dict[str, Any]:
    """Return frequent keywords from a JD."""
    stop = {"the", "and", "for", "with", "you", "your", "are", "will", "job", "role"}
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]+", job_description.lower())
    freq = Counter(t for t in tokens if t not in stop and len(t) > 2)
    return {"keywords": [w for w, _ in freq.most_common(top_k)]}

TOOLS = [strip_location, extract_job_keywords]
TOOL_MAP = {t.name: t for t in TOOLS}


def invoke_with_tools(llm, prompt: str, max_rounds: int = 4) -> str:
    """LLM decides when to call tools; function executes tool calls and continues."""
    llm_with_tools = llm.bind_tools(TOOLS)
    messages = [HumanMessage(content=prompt)]

    for _ in range(max_rounds):
        ai = llm_with_tools.invoke(messages)
        messages.append(ai)

        if not ai.tool_calls:
            return str(ai.content)

        for call in ai.tool_calls:
            tool = TOOL_MAP[call["name"]]
            result = tool.invoke(call.get("args", {}))
            messages.append(
                ToolMessage(
                    json.dumps(result),
                    tool_call_id=call["id"],
                )
            )

    return str(llm_with_tools.invoke(messages).content)