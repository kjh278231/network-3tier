from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_litellm import ChatLiteLLM

load_dotenv(Path(__file__).parent / ".env")
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from data_loader import FailedRunData
from prompt import SYSTEM_PROMPT
from tools import make_tools


def run_diagnosis(run_data: FailedRunData) -> str:
    tools = make_tools(run_data)
    model_name = os.getenv("LLM_MODEL", "claude-sonnet-4-6")
    model = ChatLiteLLM(model=model_name, max_tokens=8096)

    app = create_react_agent(
        model=model,
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )

    nd = run_data.network_data
    sim = nd.simulation
    user_prompt = (
        f"다음 런 디렉터리의 MILP 최적화 실패 원인을 진단하세요: {run_data.run_dir}\n\n"
        f"**런 정보**:\n"
        f"- 시뮬레이션 이름: {sim.simulation_name}\n"
        f"- 필요 창고 수 (warehouse_qty): {sim.warehouse_qty}\n"
        f"- 공장 수: {len(nd.plants)}\n"
        f"- 창고 후보 수: {len(nd.warehouses)}\n"
        f"- 고객 수: {len(nd.customers)}\n"
        f"- 솔버 오류: {run_data.error_message}\n\n"
        f"모든 도구를 순서대로 호출하여 불가능성 원인을 진단한 후 한국어 마크다운 보고서를 작성하세요."
    )

    result = app.invoke(
        {"messages": [HumanMessage(content=user_prompt)]},
        {"recursion_limit": 60},
    )

    messages = result.get("messages", [])
    for msg in reversed(messages):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            return msg.content
        if hasattr(msg, "content") and isinstance(msg.content, list):
            text_parts = [b["text"] for b in msg.content if isinstance(b, dict) and b.get("type") == "text"]
            if text_parts:
                return "\n".join(text_parts)

    return "# 불가능성 진단 보고서\n\n보고서를 생성하지 못했습니다."
