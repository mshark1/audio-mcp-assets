"""Review a pack through MCP: set-level consistency (audio_batch_survey) and one-line event descriptions per file."""

import asyncio
import json
import sys
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main(pack: Path):
    server = StdioServerParameters(command=sys.executable, args=["-m", "audio_mcp"])
    async with stdio_client(server) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        async def call(tool, args):
            res = await session.call_tool(tool, args)
            return json.loads(next(c.text for c in res.content if c.type == "text"))

        survey = await call("audio_batch_survey", {"target": str(pack), "pattern": "*.wav"})
        print("SURVEY:", json.dumps(survey["stats"]))
        for f in survey["findings"]:
            print("  -", f)
        for fix in survey["suggested_fixes"]:
            print("  suggested:", fix)
        print()
        for row in sorted(survey["files"], key=lambda r: r["name"]):
            ev = await call("audio_events", {"path": row["file"], "split_on_onsets": True})
            rms = row["rms_dbfs"]
            print(f"{row['name']:26s} {row['duration_s']:5.2f}s rms {rms:6.1f}  | " + " || ".join(ev["as_text"][:4]))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(main(Path(sys.argv[1]).resolve()))
