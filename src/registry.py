"""Versioned prompt registry: load YAML prompts, diff versions."""

from pathlib import Path
import yaml
from pydantic import BaseModel

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class PromptVersion(BaseModel):
    name: str
    version: str
    model: str = "gpt-4o-mini"
    temperature: float = 0
    system: str
    changelog: str = ""

    def render(self, user_input: str) -> list[dict]:
        return [
            {"role": "system", "content": self.system},
            {"role": "user", "content": user_input},
        ]


def load_prompt(name: str, version: str) -> PromptVersion:
    path = PROMPTS_DIR / f"{name}.{version}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"No such prompt: {path}")
    with open(path) as f:
        data = yaml.safe_load(f)
    return PromptVersion(**data)


def list_versions(name: str) -> list[str]:
    return sorted(
        p.stem.split(".", 1)[1]
        for p in PROMPTS_DIR.glob(f"{name}.*.yaml")
    )


def diff_versions(name: str, v1: str, v2: str) -> str:
    """Human-readable diff of two prompt versions."""
    a, b = load_prompt(name, v1), load_prompt(name, v2)
    lines = [f"--- {name}.{v1}  →  {name}.{v2}"]
    for field in ("model", "temperature", "system"):
        va, vb = getattr(a, field), getattr(b, field)
        if va != vb:
            lines.append(f"\n[{field}]")
            lines.append(f"- {str(va)[:200]}")
            lines.append(f"+ {str(vb)[:200]}")
    if b.changelog:
        lines.append(f"\nChangelog ({v2}): {b.changelog}")
    return "\n".join(lines)
