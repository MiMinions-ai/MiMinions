"""Quick interactive chat test — run directly with: python chat_test.py"""

import asyncio
import os
import sys

sys.path.insert(0, "src")

# Load .env
with open(".env") as f:
    for line in f:
        line = line.strip()
        if line and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k] = v.strip('"')

from miminions.agent import create_minion
from miminions.memory.distiller import llm_filter


async def chat():
    minion = create_minion(
        name="MiMinions",
        description=llm_filter()["history_summary"],
    )
    history = []
    print("MiMinions ready. Type 'exit' to quit.\n")

    while True:
        try:
            msg = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not msg or msg.lower() == "exit":
            break

        reply = await minion.run(msg, message_history=history)
        history = minion._last_messages
        print(f"\n{reply}\n")


asyncio.run(chat())
