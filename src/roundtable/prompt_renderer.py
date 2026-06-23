"""Render D7p persona recipe + lens + method into a standalone LLM prompt.

消费者：外部 LLM 单独对话场景（脱离 pangu 体系）。
权威源：D7p persona recipe（recipes/persona-*.md）+ lens（lenses/*/lens.md）+ method（methodologies/*/skill.md）。
定位：呈现层视图，非蒸馏产出。不进仓颉，不版本治理。D7p 升级 → 渲染器自动产出新 Prompt。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

# pangu 根目录：roundtable/src/roundtable/prompt_renderer.py → 上溯 4 层到 FQuant，再进 .trae/pangu
PANGU_ROOT = Path(__file__).resolve().parent.parent.parent.parent / ".trae" / "pangu"
RECIPES_DIR = PANGU_ROOT / "recipes"
LENSES_DIR = PANGU_ROOT / "lenses"
METHODS_DIR = PANGU_ROOT / "methodologies"


@dataclass
class ParsedDoc:
    """带 YAML frontmatter 的 markdown 文档解析结果。"""
    frontmatter: dict
    body: str


def parse_md(path: Path) -> ParsedDoc:
    """解析带 YAML frontmatter 的 markdown 文件。"""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not m:
        return ParsedDoc(frontmatter={}, body=text)
    return ParsedDoc(frontmatter=yaml.safe_load(m.group(1)) or {}, body=m.group(2))


def extract_section(body: str, header_regex: str, level: int = 2) -> str:
    """从 markdown body 提取 `{#}* {header}` 到同级或更高级 header 或文末的内容。

    header_regex 是正则片段，匹配 header 后的标题文本。
    level 控制 ## (2) 还是 ### (3)。
    """
    hashes = "#" * level
    # 第一步：匹配 header 行（不跨行，^ 锚定行首）
    header_pattern = rf"^{hashes} {header_regex}[^\n]*\n"
    m = re.search(header_pattern, body, re.MULTILINE)
    if not m:
        return ""
    start = m.end()
    # 第二步：从 header 后找下一个同级或更高级 header
    if level > 1:
        next_pattern = rf"\n{hashes} |\n{'#' * (level - 1)} "
    else:
        next_pattern = rf"\n{hashes} "
    rest = body[start:]
    m2 = re.search(next_pattern, rest)
    if m2:
        return rest[:m2.start()].strip()
    return rest.strip()


def extract_subsection(body: str, header_regex: str) -> str:
    """提取 `### {header}` 到下一个 `### ` 或 `## ` 或文末的内容。"""
    return extract_section(body, header_regex, level=3)


def load_recipe(persona_id: str) -> ParsedDoc:
    path = RECIPES_DIR / f"persona-{persona_id}.md"
    if not path.exists():
        raise FileNotFoundError(f"D7p persona recipe not found: {path}")
    return parse_md(path)


def load_lens(lens_id: str) -> ParsedDoc:
    path = LENSES_DIR / lens_id / "lens.md"
    if not path.exists():
        raise FileNotFoundError(f"lens not found: {path}")
    return parse_md(path)


def load_method(method_id: str) -> ParsedDoc | None:
    path = METHODS_DIR / method_id / "skill.md"
    if not path.exists():
        import warnings
        warnings.warn(f"method not found: {path}, skipping", stacklevel=2)
        return None
    return parse_md(path)


def _strip_md_list(items_text: str) -> list[str]:
    """把 markdown 列表文本拆成纯文本条目列表。"""
    lines = [ln.strip() for ln in items_text.splitlines() if ln.strip()]
    out = []
    for ln in lines:
        # 去掉 - / 数字. 前缀
        ln = re.sub(r"^[-*]\s+", "", ln)
        ln = re.sub(r"^\d+\.\s+", "", ln)
        if ln:
            out.append(ln)
    return out


def _extract_method_attribution(body: str) -> str:
    """提取方法论溯源引用块（> 开头）。"""
    m = re.search(r"> \*\*方法论溯源\*\*\s*\n>(.*?)(?=\n## |\Z)", body, re.DOTALL)
    if not m:
        return ""
    raw = m.group(1)
    # 合并 > 引用行
    lines = [ln.lstrip("> ").rstrip() for ln in raw.splitlines()]
    return " ".join(ln for ln in lines if ln).strip()


def _extract_step0_table(body: str) -> str:
    """提取方法论步骤0中的六阶段表格（步骤0 是 ### 级别）。"""
    section = extract_section(body, r"步骤0[:：].*", level=3)
    # 表格行：以 | 开头，以 | 结尾，中间非换行
    rows = re.findall(r"^\|[^\n]*\|$", section, re.MULTILINE)
    if len(rows) < 2:
        return ""
    return "\n".join(rows)


def _extract_observation_indicators(method_body: str, lens_body: str) -> list[str]:
    """从 method 步骤0 的方法清单 + lens 应用步骤提炼观察指标。"""
    section = extract_section(method_body, r"步骤0[:：].*")
    # 提取 **方法**：下的编号清单
    method_lines = _strip_md_list(section)
    # lens 应用步骤也提取
    lens_steps = _strip_md_list(extract_section(lens_body, r"应用方式"))
    # 合并去重，保留语义
    indicators = []
    seen = set()
    for ln in method_lines + lens_steps:
        # 简化：取前 40 字作为指标摘要
        key = ln[:40]
        if key not in seen and ("检查" in ln or "计算" in ln or "观察" in ln or "对照" in ln):
            seen.add(key)
            indicators.append(ln)
    return indicators


def _clean_internal_marks(text: str) -> str:
    """去掉 D7p 内部追溯标记（# CM1=...）和 ** ** 标记。"""
    text = re.sub(r"\s*#.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    return text


def _strip_value_floor(text: str) -> str:
    """去掉 forbidden 行中的（价值底线：...）括号内容。"""
    return re.sub(r"（价值底线：[^）]+）", "", text)


def render_persona_prompt(persona_id: str) -> str:
    """渲染完整的人格 prompt（_cmd_.txt 风格）。

    结构忠实于 D7p 字段，不强行套 _cmd_.txt 节名——缺口会自然暴露。
    """
    recipe = load_recipe(persona_id)
    recipe_fm = recipe.frontmatter

    # 从 D7p body 能力层解析引用（frontmatter 可能没有这些字段）
    capability_section = extract_section(recipe.body, r"能力层")

    # 解析方法论 ID：支持 -method / -methodology / 其他后缀
    method_id = recipe_fm.get("methodology")
    if not method_id:
        # 从 "- **方法论**：xxx" 行解析
        m = re.search(r"\*\*方法论\*\*：\s*(.+)", capability_section)
        if m:
            raw = m.group(1).strip()
            # "无专属方法论" → None
            if raw and raw != "无专属方法论":
                method_id = raw

    # 解析透镜 ID 列表
    lens_ids: list[str] = []
    if isinstance(recipe_fm.get("lenses"), list):
        lens_ids = recipe_fm["lenses"]
    if not lens_ids:
        # 从 "- xxx" 行解析（透镜列表）
        lens_ids = re.findall(r"^\s+-\s+([\w-]+)", capability_section, re.MULTILINE)

    # 加载第一个透镜（渲染器只用主透镜）
    lens_id = lens_ids[0] if lens_ids else None
    lens = load_lens(lens_id) if lens_id else None
    method = load_method(method_id) if method_id else None

    name = recipe_fm.get("name", persona_id)

    # === 提取各章节 ===
    identity_narrative = extract_subsection(recipe.body, r"身份叙述")
    speaking_style = extract_subsection(recipe.body, r"说话风格")
    stance_anchors_raw = extract_subsection(recipe.body, r"立场锚点")
    honesty_rules_raw = extract_subsection(recipe.body, r"诚实规则")
    anti_pattern = extract_subsection(recipe.body, r"反套路")
    interaction_raw = extract_subsection(recipe.body, r"对话行为层")
    signature_quotes_raw = extract_subsection(recipe.body, r"辨识度金句")

    lens_overview = extract_section(lens.body, r"透镜概述") if lens else ""
    if not lens_overview and lens:
        # 兼容旧格式：从 body 中 > 引用块提取概述（跳过标题行）
        m = re.search(r"(?:^|\n)(>.*(?:\n>.*)*)", lens.body)
        if m:
            lines = [ln.lstrip("> ").rstrip() for ln in m.group(1).splitlines()]
            lens_overview = " ".join(ln for ln in lines if ln).strip()
    forbidden_raw = extract_section(lens.body, r"禁忌行为") if lens else ""

    step0_table = _extract_step0_table(method.body) if method else ""
    method_constraints_raw = extract_section(method.body, r"约束") if method else ""

    # === 渲染 ===
    parts: list[str] = []

    # 1. 角色身份
    parts.append(f"# {name} · 人格 prompt")
    parts.append("## 角色身份")
    # 去掉 HTML 注释
    identity_clean = re.sub(r"<!--.*?-->", "", identity_narrative, flags=re.DOTALL).strip()
    if identity_clean:
        parts.append(f"你是 {name}（{identity_clean}）")
    elif lens_overview:
        parts.append(f"你是 {name}。{lens_overview}")
    else:
        parts.append(f"你是 {name}。")
    parts.append("")

    # 2. 核心思维模式（lens 概述作为哲学陈述）
    parts.append("## 核心思维模式")
    parts.append(lens_overview if lens_overview else "（lens 概述缺失）")
    parts.append("")

    # 3. 立场锚点（追问方向）
    anchors = _strip_md_list(stance_anchors_raw)
    anchors = [_clean_internal_marks(a) for a in anchors]
    anchors = [a for a in anchors if a]
    if anchors:
        parts.append("## 立场锚点（追问方向）")
        for i, a in enumerate(anchors, 1):
            parts.append(f"{i}. {a}")
        parts.append("")

    # 4. 方法论框架（仅当 method 有步骤0表格时渲染，节名从表格内容推断）
    if step0_table:
        # 从表格第一列推断节名（如"阶段"→"情绪周期六阶段框架"）
        header_line = step0_table.split("\n")[0] if step0_table else ""
        if "阶段" in header_line:
            section_title = "情绪周期六阶段框架"
        else:
            # 通用标题
            section_title = "方法论框架"
        parts.append(f"## {section_title}")
        parts.append(step0_table)
        parts.append("")

    # 5. 关键观察指标（仅当有内容时渲染）
    indicators = _extract_observation_indicators(method.body if method else "", lens.body if lens else "")
    indicators = [_clean_internal_marks(ind) for ind in indicators]
    indicators = [ind for ind in indicators if ind]
    if indicators:
        parts.append("## 关键观察指标（多维交叉验证）")
        for ind in indicators:
            parts.append(f"- {ind}")
        parts.append("")

    # 6. 沟通风格
    parts.append("## 沟通风格")
    parts.append(f"- {_clean_internal_marks(speaking_style)}")
    parts.append("")

    # 7. 互动规则（保留 interaction_protocol 结构，不拍平）
    parts.append("## 互动规则")
    interaction_text = _clean_internal_marks(interaction_raw)
    parts.append(interaction_text if interaction_text else "（interaction_protocol 缺失）")
    parts.append("")

    # 8. 经典语录库
    quotes = _strip_md_list(signature_quotes_raw)
    quotes = [_clean_internal_marks(q) for q in quotes]
    quotes = [q for q in quotes if q]
    if quotes:
        parts.append("## 经典语录库（随机穿插）")
        for q in quotes:
            parts.append(f"- {q}")
        parts.append("")

    # 9. 禁忌行为
    forbidden = _strip_md_list(forbidden_raw)
    forbidden = [_clean_internal_marks(f) for f in forbidden]
    forbidden = [_strip_value_floor(f) for f in forbidden]
    forbidden = [f for f in forbidden if f]
    if forbidden:
        parts.append("## 禁忌行为")
        for f in forbidden:
            parts.append(f"- {f}")
        parts.append("")

    # 10. 诚实规则
    honesty = _strip_md_list(honesty_rules_raw)
    honesty = [_clean_internal_marks(h) for h in honesty]
    honesty = [h for h in honesty if h]
    if honesty:
        parts.append("## 诚实规则")
        for h in honesty:
            parts.append(f"- {h}")
        parts.append("")

    # 11. 反套路
    if anti_pattern:
        parts.append("## 反套路")
        parts.append(_clean_internal_marks(anti_pattern))
        parts.append("")

    # 12. 时效性警示（从 lens 产出注入）
    if lens:
        confidence = extract_section(lens.body, r"产出注入")
        if confidence:
            m = re.search(r"confidence_note:\s*\|\s*\n((?:\s+.*\n)+)", confidence)
            if m:
                note_lines = [ln.strip() for ln in m.group(1).splitlines() if ln.strip()]
                parts.append("## 时效性警示")
                for ln in note_lines:
                    parts.append(ln)
                parts.append("")

    return "\n".join(parts)


def main():
    import sys
    persona_id = sys.argv[1] if len(sys.argv) > 1 else "chao-gu-yang-jia"
    prompt = render_persona_prompt(persona_id)
    print(prompt)


if __name__ == "__main__":
    main()
