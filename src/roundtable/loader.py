"""Load personas and templates from YAML/MD files."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


# Project root: where personas/, templates/ live
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # roundtable/

PERSONAS_DIR = PROJECT_ROOT / "personas"
TEMPLATES_DIR = PROJECT_ROOT / "templates"


@dataclass
class Persona:
    """A roundtable persona with 4 core elements."""

    id: str
    name: str
    speaking_style: str
    stance_anchors: list[str] = field(default_factory=list)
    honesty_rules: str = ""
    anti_pattern: str = ""

    @classmethod
    def from_yaml(cls, path: Path) -> "Persona":
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        p = data.get("persona", {})
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            speaking_style=p.get("speaking_style", ""),
            stance_anchors=p.get("stance_anchors", []),
            honesty_rules=p.get("honesty_rules", ""),
            anti_pattern=p.get("anti_pattern", ""),
        )

    def render_for_prompt(self) -> str:
        """Render persona as prompt section."""
        anchors = "\n".join(f"  {i+1}. {a}" for i, a in enumerate(self.stance_anchors))
        return (
            f"### {self.name}\n\n"
            f"- **说话风格**：{self.speaking_style}\n"
            f"- **追问方向**：\n{anchors}\n"
            f"- **诚实规则**：{self.honesty_rules}\n"
            f"- **反套路**：{self.anti_pattern}\n"
        )


def list_personas() -> dict[str, Path]:
    """Return {name: path} for all available personas."""
    result = {}
    if not PERSONAS_DIR.exists():
        return result
    for p in sorted(PERSONAS_DIR.glob("*.yaml")):
        name = p.stem
        result[name] = p
    return result


def load_persona(name: str) -> Persona:
    """Load a persona by name (e.g. 'kahneman')."""
    # Try exact match first
    candidates = list_personas()
    if name in candidates:
        return Persona.from_yaml(candidates[name])

    # Try partial match
    for key, path in candidates.items():
        if name in key:
            return Persona.from_yaml(path)

    raise ValueError(
        f"Persona '{name}' not found. Available: {', '.join(candidates.keys())}"
    )


def load_personas(names: list[str]) -> list[Persona]:
    """Load multiple personas by name."""
    return [load_persona(n) for n in names]


def load_template(mode: str = "quick") -> str:
    """Load a prompt template by mode name."""
    template_map = {
        "quick": "quick-consensus.md",
        "deep": "deep-roundtable.md",
        "full": "full-prompt-template.md",
    }
    filename = template_map.get(mode, f"{mode}.md")
    path = TEMPLATES_DIR / filename
    if not path.exists():
        raise ValueError(f"Template '{mode}' not found at {path}")
    return path.read_text(encoding="utf-8")


def build_prompt(topic: str, personas: list[Persona], mode: str = "quick") -> str:
    """Build the full prompt from topic + personas using the quick-consensus template.

    For the quick mode, we construct the prompt directly rather than doing
    string replacement on the template file, because the template is designed
    for copy-paste usage. The programmatic path builds the same structure.
    """
    if mode == "quick":
        return _build_quick_prompt(topic, personas)
    elif mode == "deep":
        return _build_deep_step1_prompt(topic, personas)
    else:
        # Fallback: use template with replacement
        template = load_template(mode)
        return template.replace("{议题}", topic)


def _build_quick_prompt(topic: str, personas: list[Persona]) -> str:
    """Build the quick-consensus prompt — optimized for 30s single-call output."""
    personas_section = "\n".join(p.render_for_prompt() for p in personas)

    return f"""# 圆桌会议（快速共识模式）

## 议题

{topic}

## 参与者

{personas_section}

## 要求

请一次性完成以下5步，输出结构化结论。每步尽量精简，重点在Step 5的结构化产出。

**Step 1：各抒己见** — 每位参与者100字左右回应议题，以[身份：人格名]开头。

**Step 2：交叉反驳** — 每位参与者用1-2句话反驳一位其他参与者的核心论点，显式称呼对方。

**Step 3：推理综合** — 列出共识点和分歧点。

**Step 4：共识裁决** — 一句话结论。分歧标记"待定"。

**Step 5：结构化产出** — 按以下格式输出：

## 结论
[一段话]

## 可操作信号
| # | 行动 | 预期效果 | 负责视角 |
|---|------|---------|---------|

## 共识矩阵
| 议题点 | 共识度 | 共识方向 | 分歧原因 |
|--------|--------|---------|---------|

## 盲点
1. ...
2. ...

## 置信度
[高/中/低] — [理由]
"""


def _build_deep_step1_prompt(topic: str, personas: list[Persona]) -> str:
    """Build Step 1 prompt for deep mode."""
    personas_section = "\n".join(p.render_for_prompt() for p in personas)

    return f"""# 圆桌会议 Step 1：各抒己见

## 议题

{topic}

## 参与者

{personas_section}

## 要求

每位参与者从自己的视角回应议题，200字左右。每条发言必须以 [身份：人格名] 开头。
"""
