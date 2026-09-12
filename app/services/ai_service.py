import asyncio
import json
import os


async def generate_chat_response(user_text: str, user_id: str) -> str:
    prompt = user_text.strip()
    if not prompt:
        return "[Bot]: Please send a message."

    try:
        reply = await _run_opencode(prompt)
        if reply.strip():
            return reply.strip()
    except Exception as e:
        print(f"[opencode error]: {e}")

    return "[Bot]: Sorry, I couldn't generate a response right now."


async def _run_opencode(prompt: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        *OPENCODE_CMD,
        prompt,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=OPENCODE_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise TimeoutError("opencode run timed out")

    if proc.returncode != 0:
        raise RuntimeError(
            f"opencode exited with code {proc.returncode}: "
            f"{stderr.decode(errors='replace')}"
        )

    parts = []
    for line in stdout.decode(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        part = event.get("part", {})
        if event.get("type") == "text" and part.get("type") == "text":
            text = part.get("text", "").strip()
            if text:
                parts.append(text)
    return "\n".join(parts)


OPENCODE_CMD = os.getenv("OPENCODE_CMD", "opencode").split()
if "--format" not in " ".join(OPENCODE_CMD):
    OPENCODE_CMD.extend(["--format", "json"])
OPENCODE_TIMEOUT_SECONDS = int(os.getenv("OPENCODE_TIMEOUT_SECONDS", "120"))