import argparse
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


def _safe_path(path: str) -> Path:
    target = (WORKSPACE_ROOT / path).resolve()
    if WORKSPACE_ROOT not in target.parents and target != WORKSPACE_ROOT:
        raise ValueError("Path must stay inside the project workspace.")
    return target


@tool
def list_files(path: str = ".") -> str:
    """List files and directories in a relative project path."""
    target = _safe_path(path)
    if not target.exists():
        return f"{path} does not exist."
    entries = sorted(p.name for p in target.iterdir())
    return "\n".join(entries) if entries else "(empty)"


@tool
def read_text(path: str) -> str:
    """Read UTF-8 text from a file in this workspace."""
    target = _safe_path(path)
    if not target.exists():
        return f"{path} does not exist."
    if target.is_dir():
        return f"{path} is a directory."
    return target.read_text(encoding="utf-8")


@tool
def write_text(path: str, content: str) -> str:
    """Write UTF-8 text to a file in this workspace, creating folders if needed."""
    target = _safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} chars to {path}"


@tool
def finish(answer: str) -> str:
    """Call this when the objective is complete and provide the final answer."""
    return answer


TOOLS = [list_files, read_text, write_text, finish]
TOOL_REGISTRY: Dict[str, object] = {tool_.name: tool_ for tool_ in TOOLS}


def run_autonomous_agent(objective: str, max_steps: int = 12, model: str = "gpt-4o-mini") -> str:
    load_dotenv()
    llm = ChatOpenAI(model=model, temperature=0).bind_tools(TOOLS)

    system_prompt = (
        "You are an autonomous project agent.\n"
        "Goal: complete the user objective by planning and using tools.\n"
        "Rules:\n"
        "1) Think step-by-step and use tools when needed.\n"
        "2) Keep work inside the project workspace.\n"
        "3) Prefer small, verifiable actions.\n"
        "4) When done, call the finish tool with a concise final answer.\n"
    )

    messages: List[object] = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Objective: {objective}"),
    ]

    for step in range(1, max_steps + 1):
        ai_msg = llm.invoke(messages)
        messages.append(ai_msg)

        if not ai_msg.tool_calls:
            content = ai_msg.content if isinstance(ai_msg.content, str) else str(ai_msg.content)
            return f"Stopped at step {step} without finish tool.\n\n{content}"

        for call in ai_msg.tool_calls:
            tool_name = call["name"]
            tool_ = TOOL_REGISTRY.get(tool_name)
            if tool_ is None:
                output = f"Tool '{tool_name}' is not available."
            else:
                try:
                    output = tool_.invoke(call.get("args", {}))
                except Exception as exc:
                    output = f"Tool '{tool_name}' failed: {exc}"

            messages.append(ToolMessage(content=str(output), tool_call_id=call["id"]))

            if tool_name == "finish":
                return str(output)

    return f"Stopped after max_steps={max_steps} without a finish call."


def main() -> None:
    parser = argparse.ArgumentParser(description="LangChain autonomous agent example")
    parser.add_argument("objective", help="Goal for the agent to complete")
    parser.add_argument("--max-steps", type=int, default=12, help="Maximum tool/action loop steps")
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI chat model name")
    args = parser.parse_args()

    result = run_autonomous_agent(args.objective, max_steps=args.max_steps, model=args.model)
    print("\n=== Final Result ===")
    print(result)


if __name__ == "__main__":
    main()
