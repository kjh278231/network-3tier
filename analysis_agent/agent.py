from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_litellm import ChatLiteLLM

load_dotenv(Path(__file__).parent / ".env")
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from data_loader import RunData
from prompt import SYSTEM_PROMPT
from tools import make_tools


def run_analysis(run_data: RunData) -> str:
    tools = make_tools(run_data)
    model_name = os.getenv("LLM_MODEL", "claude-sonnet-4-6")
    model = ChatLiteLLM(model=model_name, max_tokens=8096)

    app = create_react_agent(
        model=model,
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )

    sim = run_data.simulation
    meta = run_data.run_meta
    user_prompt = (
        f"Analyze the network optimization results from run directory: {run_data.run_dir}\n\n"
        f"**Run Info**:\n"
        f"- Format: {run_data.format}\n"
        f"- Simulation: {sim.get('simulationName', 'N/A')}\n"
        f"- Required Warehouses: {sim.get('warehouseQty', 'N/A')}\n"
        f"- Total Cases: {len(run_data.cases)}\n"
        f"- Best Case: {run_data.best_case().case_name}\n"
        f"- Solver: {meta.get('solver', meta.get('best_case', 'SCIP'))}\n\n"
        f"Please use all available tools to gather complete data, then write the full markdown analysis report."
    )

    result = app.invoke(
        {"messages": [HumanMessage(content=user_prompt)]},
        {"recursion_limit": 50},
    )

    # Extract final text from the last AIMessage
    messages = result.get("messages", [])
    for msg in reversed(messages):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            return msg.content
        if hasattr(msg, "content") and isinstance(msg.content, list):
            text_parts = [b["text"] for b in msg.content if isinstance(b, dict) and b.get("type") == "text"]
            if text_parts:
                return "\n".join(text_parts)

    return "# Analysis Report\n\nNo report was generated."
