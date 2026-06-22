"""Engine: execute roundtable discussion via LLM API calls."""

from __future__ import annotations

import os
from typing import Any

from openai import OpenAI

from .loader import Persona, build_prompt, load_personas


def create_client() -> OpenAI:
    """Create OpenAI client from environment variables."""
    api_key = os.environ.get("OPENAI_API_KEY", "sk-abcdef1234567890abcdef1234567890abcdef12")
    base_url = os.environ.get("OPENAI_BASE_URL", None)

    if not api_key:
        raise SystemExit(
            "Error: OPENAI_API_KEY not set.\n"
            "  export OPENAI_API_KEY=sk-...\n"
            "  # Optional: export OPENAI_BASE_URL=https://..."
        )

    kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def run_quick(
    topic: str,
    personas: list[Persona],
    model: str | None = None,
    client: OpenAI | None = None,
) -> str:
    """Run quick-consensus mode: single LLM call, all 5 steps in one prompt."""
    if client is None:
        client = create_client()

    if model is None:
        model = os.environ.get("ROUNDTABLE_MODEL", "gpt-4o")

    prompt = build_prompt(topic, personas, mode="quick")

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=4000,
    )

    return response.choices[0].message.content or ""


def run_deep(
    topic: str,
    personas: list[Persona],
    model: str | None = None,
    client: OpenAI | None = None,
) -> str:
    """Run deep-roundtable mode: 5 sequential LLM calls.

    Returns the final structured output (Step 5).
    """
    if client is None:
        client = create_client()

    if model is None:
        model = os.environ.get("ROUNDTABLE_MODEL", "gpt-4o")

    # Step 1: 各抒己见
    step1_prompt = build_prompt(topic, personas, mode="deep")
    step1_result = _call_llm(client, model, step1_prompt)

    # Step 2: 交叉反驳
    step2_prompt = f"""# 圆桌会议 Step 2：交叉反驳

## 议题

{topic}

## Step 1 产出

{step1_result}

## 要求

每位参与者至少反驳一位其他参与者的核心论点。反驳时必须显式称呼对方："我不同意{{对方名}}的观点，因为……"。反驳必须针对论点本身，不能以人格名作为论据。"""
    step2_result = _call_llm(client, model, step2_prompt)

    # Step 3: 推理综合
    step3_prompt = f"""# 圆桌会议 Step 3：推理综合

## 议题

{topic}

## Step 1 产出

{step1_result}

## Step 2 产出

{step2_result}

## 要求

基于各方观点和反驳，综合出共识与分歧：
- 列出各方一致同意的结论
- 列出各方仍然分歧的观点及分歧原因"""
    step3_result = _call_llm(client, model, step3_prompt)

    # Step 4: 共识裁决
    step4_prompt = f"""# 圆桌会议 Step 4：共识裁决

## 议题

{topic}

## Step 3 产出

{step3_result}

## 要求

输出最终结论。共识优先，裁决次之。分歧点标记为"待定"而非强行统一。"""
    step4_result = _call_llm(client, model, step4_prompt)

    # Step 5: 结构化产出
    step5_prompt = f"""# 圆桌会议 Step 5：结构化产出

## 议题

{topic}

## 前序产出摘要

Step 1 各抒己见:
{step1_result[:500]}...

Step 2 交叉反驳:
{step2_result[:500]}...

Step 3 推理综合:
{step3_result[:500]}...

Step 4 共识裁决:
{step4_result[:500]}...

## 要求

按以下格式输出最终结果：

## 结论
[一段话总结最终结论]

## 可操作信号
| # | 行动 | 预期效果 | 负责视角 |
|---|------|---------|---------|

## 共识矩阵
| 议题点 | 共识度 | 共识方向 | 分歧原因 |
|--------|--------|---------|---------|

## 盲点
1. [本次讨论未覆盖的重要视角]
2. [...]

## 置信度
[高/中/低] — [理由]"""
    step5_result = _call_llm(client, model, step5_prompt)

    # Return full transcript
    return f"""# 圆桌会议完整记录

## 议题：{topic}

---

## Step 1：各抒己见

{step1_result}

---

## Step 2：交叉反驳

{step2_result}

---

## Step 3：推理综合

{step3_result}

---

## Step 4：共识裁决

{step4_result}

---

## Step 5：结构化产出

{step5_result}
"""


def _call_llm(client: OpenAI, model: str, prompt: str) -> str:
    """Single LLM call helper."""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=4000,
    )
    return response.choices[0].message.content or ""
