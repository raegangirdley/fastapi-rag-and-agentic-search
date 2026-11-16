from pathlib import Path
import json
import ollama
import re

from tools.grep import grep
from tools.list_files import list_files
from tools.read_file import read_file

tools_path = Path(__file__).resolve().parent / "tools" / "tools.json"
with tools_path.open(encoding="utf-8") as file:
    tool_schemas = json.load(file)

available_tools = {
    "grep": grep,
    "list_files": list_files,
    "read_file": read_file,
}

LANGUAGE_MODEL = "llama3.1:8b"

SYSTEM_PROMPT = """Answer only using information returned by tools from the corpus.
Do not use prior knowledge or invent facts, examples, APIs, or libraries.
Do not generate code; explain in layman's terms.
Cite every corpus-supported claim as [corpus/<file.md>:<line>].
Use only file paths and line numbers present in tool results; don't fabricate sources.
If a claim is not supported by the corpus, say so clearly.
If evidence is insufficient, search and read relevant corpus files before answering.
Keep the answer concise. Never copy file contents or line-numbered text 
into your answer."""

MAX_STEPS = 20
MAX_RETRIES = 2
MAX_DUPLICATES = 2 
TOLERANCE = 1
MIN_OVERLAP = 0.3

CITATION = re.compile(r"\[(corpus/[^\]:]+\.md):(\d+)(?:-(\d+))?\]")
GREP_LINE = re.compile(r"^(corpus/\S+?\.md):(\d+): ")
NUM_LINE = re.compile(r"^(\d+): ")

STOP = set("that this with from have your when then they them what which will also "
           "into only more than just like each other these those about there their "
           "would could should while where using used".split())

def dispatcher(func: str, arguments: dict) -> str:
    result = available_tools[func](**arguments)
    if func == "read_file":
        result = f"File: {arguments['path']}\n{result}"
    if isinstance(result, list):
        return "\n".join(result)
    return result

def run_tool(tool_call) -> str:
    name = tool_call.function.name
    try:
        if name not in available_tools:
            return f"Unknown tool: {name}, Available: {', '.join(available_tools)}"
        return dispatcher(name, tool_call.function.arguments)
    except Exception as exc:
        return f"Tool error ({type(exc).__name__}): {exc}"

def call_model(messages, use_tools=True):
    return ollama.chat(
        model=LANGUAGE_MODEL,
        messages=messages,
        tools=tool_schemas if use_tools else None,
        options={"temperature": 0},
    )

def content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in STOP}

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def retrieved_lines(tool_texts: list[str]) -> dict[tuple[str, int], str]:
    seen = {}
    for text in tool_texts:
        current = None
        for line in text.splitlines():
            if line.startswith("File: "):
                current = line[6:].strip()
                continue
            m = GREP_LINE.match(line)
            if m:
                seen[(m.group(1), int(m.group(2)))] = line[m.end():]
                continue
            m = NUM_LINE.match(line)
            if m and current:
                seen[(current, int(m.group(1)))] = line[m.end():]
    return seen

# returns list of problems w/ answer; empty means grounded
def check_answer(answer, tool_texts, tools_used) -> list[str]:
    problems = []
    if "read_file" not in tools_used:
        problems.append("you never opened a file with read_file")

    # answer won't paste file contents
    dumped = sum(1 for l in answer.splitlines() if NUM_LINE.match(l))
    if dumped > 2 or "File: corpus" in answer:
        problems.append("the answer copies tool output; summarize instead")

    # citations point at real non-blank lines
    seen = retrieved_lines(tool_texts)
    prev_end = 0
    cites = list(CITATION.finditer(answer))
    if not cites:
        problems.append("no citations")
    for m in cites:
        claim = answer[prev_end:m.start()]
        prev_end = m.end()
        path, start = m.group(1), int(m.group(2))
        end = int(m.group(3) or start)
        window = range(start - TOLERANCE, end + TOLERANCE + 1)
        source = " ".join(seen.get((path, n), "") for n in window)
        words = content_words(claim)
        if not source.strip():
            problems.append(f"{path}:{start} is blank or was never retrieved")
        elif words and len(words & content_words(source)) / len(words) < MIN_OVERLAP:
            problems.append(f"claim does not match cited lines {path}:{start}-{end}")

    # code in answer must appear
    joined = norm("\n".join(NUM_LINE.sub("", l) for t in tool_texts
                            for l in t.splitlines()))
    for block in re.findall(r"```(?:\w+)?\n(.*?)```", answer, re.S):
        for line in block.splitlines():
            line = norm(NUM_LINE.sub("", line))
            if line and line not in joined:
                problems.append(f"code not found in sources: {line[:60]}")
                break

    # every substantial sentence needs citation
    for sent in re.split(r"(?<=[.!?])\s+", answer.strip()):
        if len(sent.split()) > 6 and not CITATION.search(sent):
            problems.append(f"sentence has no citation: {sent[:50]}")
            
    return problems

def answer_question(question: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    tool_texts: list[str] = []
    tools_used: set[str] = set()
    seen_calls: set[str] = set()
    duplicates = 0
    retries = 0
    force_final = False

    for step in range(MAX_STEPS):
        message = call_model(messages, use_tools=not force_final)["message"]

        if message.tool_calls and not force_final:
            messages.append(message)
            for tool_call in message.tool_calls:
                name = tool_call.function.name
                args = tool_call.function.arguments
                key = f"{name}:{json.dumps(args, sort_keys=True)}"
                if key in seen_calls:
                    duplicates += 1
                    result = "You already ran this exact call. Use the earlier result."
                else:
                    seen_calls.add(key)
                    result = run_tool(tool_call)
                    tool_texts.append(result)
                    tools_used.add(name)
                print(f"[step {step + 1}] TOOL: {name} {args}")
                messages.append({"role": "tool", "name": name, "content": result})

            if duplicates >= MAX_DUPLICATES and "read_file" in tools_used:
                force_final = True
                messages.append({"role": "user", "content": (
                    "Stop searching. Write the final answer now, using only text "
                    "you have already read.")})
            continue

        answer = message.content or ""
        problems = check_answer(answer, tool_texts, tools_used)
        if not problems:
            return answer

        if retries < MAX_RETRIES:
            retries += 1
            if "read_file" in tools_used:
                force_final = True
                step_hint = "Do not call any tools; use the text you already read."
            else:
                step_hint = "Open the most relevant file with read_file first."
            messages.append(message)
            messages.append({"role": "user", "content": (
                "Your answer failed verification: " + "; ".join(problems) + ". "
                + step_hint + " Write 3 to 6 sentences. Do not copy file text. "
                "Cite each claim as [corpus/<file>.md:<line>] using the exact "
                "line number where the claim appears.")})
            continue

        return answer + "\n\n[UNVERIFIED: " + "; ".join(problems) + "]"

    return "Stopped: step limit reached without a final answer."