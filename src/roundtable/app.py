"""Streamlit Web UI for Roundtable."""

from __future__ import annotations

import streamlit as st

from roundtable.engine import create_client, run_quick, run_deep
from roundtable.loader import list_personas, load_personas, build_prompt


def init_session() -> None:
    """Initialize session state."""
    if "history" not in st.session_state:
        st.session_state.history = []  # list of {"role", "content"}
    if "result" not in st.session_state:
        st.session_state.result = ""


@st.cache_resource
def get_client():
    """Create OpenAI client (cached)."""
    return create_client()


def main() -> None:
    st.set_page_config(
        page_title="Roundtable",
        page_icon="🔵",
        layout="wide",
    )

    init_session()

    # Sidebar: settings
    with st.sidebar:
        st.header("⚙️ 设置")

        # API Key
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            help="或设置环境变量 OPENAI_API_KEY",
        )
        if api_key:
            import os
            os.environ["OPENAI_API_KEY"] = api_key

        base_url = st.text_input(
            "API Base URL（可选）",
            placeholder="https://api.openai.com/v1",
            help="留空使用默认 OpenAI",
        )
        if base_url:
            import os
            os.environ["OPENAI_BASE_URL"] = base_url

        model = st.text_input(
            "Model",
            value="gpt-4o",
            help="默认 gpt-4o，可改为其他模型",
        )

        mode = st.radio("讨论模式", ["快速共识 (~30s)", "深度圆桌 (~2.5min)"])
        mode_value = "quick" if mode.startswith("快速") else "deep"

        st.divider()

        # Persona selection
        available = list_personas()
        persona_names = list(available.keys())

        selected = st.multiselect(
            "选择参与者",
            options=persona_names,
            default=["kahneman", "munger", "deng-xiaoping"],
            format_func=lambda x: {
                "kahneman": "卡尼曼 — 认知偏差审计",
                "munger": "芒格 — 逆向排除",
                "deng-xiaoping": "邓小平 — 务实渐进",
                "hayek": "哈耶克 — 知识论批判",
                "dalio": "达利欧 — 原则驱动诊断",
            }.get(x, x),
        )

        st.divider()
        st.caption(f"内置 {len(available)} 个人格配方")

    # Main area
    st.title("🔵 Roundtable")
    st.markdown("多角色结构化讨论 —— 让不同思维视角交叉质疑，形成共识")

    # Topic input
    topic = st.text_area(
        "输入你的议题",
        height=100,
        placeholder="例如：我应该先做回测验证还是先找种子用户试跑？",
    )

    col_run, col_clear = st.columns([1, 4])
    with col_run:
        run_clicked = st.button("🚀 开始讨论", type="primary", use_container_width=True)
    with col_clear:
        clear_clicked = st.button("清除结果", use_container_width=True)

    if clear_clicked:
        st.session_state.result = ""
        st.session_state.history = []
        st.rerun()

    if run_clicked:
        if not topic.strip():
            st.warning("请输入议题")
        elif not selected:
            st.warning("请至少选择一位参与者")
        elif not api_key and not __import__("os").environ.get("OPENAI_API_KEY"):
            st.error("请输入 OpenAI API Key")
        else:
            personas = load_personas(selected)

            with st.spinner("讨论中..."):
                try:
                    client = get_client()
                    result = (
                        run_quick(topic, personas, model=model, client=client)
                        if mode_value == "quick"
                        else run_deep(topic, personas, model=model, client=client)
                    )
                    st.session_state.result = result
                    st.session_state.history.append({
                        "role": "system",
                        "content": f"议题：{topic} | 参与者：{', '.join(p.name for p in personas)} | 模式：{mode}",
                    })
                    st.session_state.history.append({"role": "assistant", "content": result})
                except Exception as e:
                    st.error(f"错误：{e}")

    # Result display
    if st.session_state.result:
        st.divider()
        st.subheader("📋 讨论结果")

        # Tabs: Full / Conclusion only
        tab_full, tab_conclusion = st.tabs(["完整记录", "结论优先"])

        with tab_full:
            st.markdown(st.session_state.result)

        with tab_conclusion:
            # Extract conclusion section from markdown
            result_text = st.session_state.result
            lines = result_text.split("\n")
            conclusion_lines = []
            capturing = False
            in_table = False
            for line in lines:
                if line.startswith("## 结论"):
                    capturing = True
                    continue
                if capturing:
                    if line.startswith("## ") and not line.startswith("## 结论"):
                        break
                    if line.startswith("|") or line.startswith("---"):
                        continue  # skip tables for now
                    conclusion_lines.append(line)
            if conclusion_lines:
                st.markdown("\n".join(conclusion_lines))
            else:
                st.info("未检测到结论段落，请查看完整记录")

        # Follow-up input (P-9)
        st.divider()
        st.subheader("💬 追问与展开")
        followup = st.text_input(
            "追问（例如：'卡尼曼，你说的认知陷阱能具体说说吗？' 或 '我不同意芒格的观点...'）",
            placeholder="输入追问...",
        )
        if followup and st.button("发送追问", key="followup_btn"):
            with st.spinner("追问中..."):
                try:
                    client = get_client()
                    from roundtable.engine import _call_llm
                    followup_prompt = f"""# 圆桌会议追问

## 原始议题
{topic}

## 上一次讨论结论摘要
{st.session_state.result[:2000]}...

## 用户追问
{followup}

## 要求
请相关人格回应这个追问。如果追问指向特定人格，该人格回应；如果是反驳或新观点，所有相关人格可以参与。保持结构化输出格式。
"""
                    followup_result = _call_llm(client, model, followup_prompt)
                    st.session_state.result += f"\n\n---\n\n## 💬 追问：{followup}\n\n{followup_result}"
                    st.session_state.history.append({"role": "user", "content": followup})
                    st.session_state.history.append({"role": "assistant", "content": followup_result})
                    st.rerun()
                except Exception as e:
                    st.error(f"追问错误：{e}")


if __name__ == "__main__":
    main()
