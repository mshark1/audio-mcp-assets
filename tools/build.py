"""Build an asset pack by calling the audio-mcp server over MCP (stdio), exactly as an AI agent would.

Usage: python tools/build.py <pack_dir>
  Reads <pack_dir>/recipes.json, runs each recipe's tool calls, then runs its checks and writes
  <pack_dir>/manifest.json with expected vs measured values. Exits non-zero if any check fails.

Recipe format (see recipes.json):
  {"file": "name.wav", "description": "...", "steps": [{"tool": "audio_synthesize", "args": {...}}, ...],
   "checks": [{"tool": "audio_analyze", "field": "levels.peak_dbfs", "expect": -20, "tol": 0.01}, ...]}
  Strings may use {out} (the asset's final path) and {tmp} (a scratch directory).
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def fill(value, out, tmp):
    if isinstance(value, str):
        return value.replace("{out}", out).replace("{tmp}", tmp)
    if isinstance(value, list):
        return [fill(v, out, tmp) for v in value]
    if isinstance(value, dict):
        return {k: fill(v, out, tmp) for k, v in value.items()}
    return value


def dig(data, dotted):
    for key in dotted.split("."):
        if isinstance(data, list):
            data = data[int(key)]
        elif isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return None
    return data


class Agent:
    """Thin wrapper: call a tool, get parsed JSON back, raise on tool errors."""

    def __init__(self, session):
        self.session = session
        self.calls = 0

    async def call(self, tool, args):
        self.calls += 1
        result = await self.session.call_tool(tool, args)
        text = next((c.text for c in result.content if c.type == "text"), "")
        if result.is_error:
            raise RuntimeError(f"{tool} failed: {text}")
        return json.loads(text) if text.strip().startswith(("{", "[")) else text


def evaluate(check, measured):
    if "expect" in check:
        exp, tol = check["expect"], check.get("tol", 0)
        if isinstance(exp, (int, float)) and not isinstance(exp, bool):
            return isinstance(measured, (int, float)) and abs(measured - exp) <= tol
        return measured == exp
    if "contains" in check:
        return check["contains"] in json.dumps(measured, ensure_ascii=False)
    if "min" in check or "max" in check:
        return isinstance(measured, (int, float)) and check.get("min", -1e18) <= measured <= check.get("max", 1e18)
    raise ValueError(f"check needs expect/contains/min/max: {check}")


async def build(pack: Path):
    recipes = json.loads((pack / "recipes.json").read_text(encoding="utf-8"))
    tmp = tempfile.mkdtemp(prefix="audio-mcp-assets-")
    server = StdioServerParameters(command=sys.executable, args=["-m", "audio_mcp"])
    manifest, failures = [], []
    async with stdio_client(server) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        agent = Agent(session)
        for recipe in recipes["assets"]:
            out = str((pack / recipe["file"]).resolve())
            for step in recipe["steps"]:
                await agent.call(step["tool"], fill(step["args"], out, tmp))
            info = await agent.call("audio_info", {"path": out})
            results = []
            for check in recipe["checks"]:
                args = {"path": out, **check.get("args", {})}
                data = await agent.call(check["tool"], args)
                measured = dig(data, check["field"])
                if "pluck" in check and isinstance(measured, list):  # e.g. notes -> list of note names
                    measured = [item[check["pluck"]] for item in measured]
                ok = evaluate(check, measured)
                expected = {k: check[k] for k in ("expect", "tol", "contains", "min", "max") if k in check}
                results.append({"measure": f"{check['tool']}:{check['field']}", **expected, "measured": measured, "pass": ok})
                if not ok:
                    failures.append(f"{recipe['file']}: {check['field']} = {measured!r}, wanted {expected}")
            manifest.append(
                {
                    "file": recipe["file"],
                    "description": recipe["description"],
                    "format": {k: info[k] for k in ("format", "subtype", "sample_rate", "channels", "duration_s")},
                    "ground_truth": recipe.get("ground_truth", {}),
                    "verification": results,
                    "recipe": recipe["steps"],
                }
            )
            print(f"{'ok  ' if all(r['pass'] for r in results) else 'FAIL'} {recipe['file']}")
        print(f"\n{len(manifest)} assets, {agent.calls} MCP tool calls")
    (pack / "manifest.json").write_text(
        json.dumps({"pack": recipes["pack"], "license": "CC0-1.0", "assets": manifest}, indent=1, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    if failures:
        sys.exit("\nCHECKS FAILED:\n  " + "\n  ".join(failures))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(build(Path(sys.argv[1]).resolve()))
