import asyncio
import os
import edge_tts

OUT = "/Users/jack/WorkBuddy/2026-10-09-13-44-47/remotion-videos/public/vo"
VOICE = "en-US-AvaNeural"
RATE = "+8%"

LINES = [
    ("vo-1.mp3", "Your sofa looks tired?"),
    ("vo-2.mp3", "Meet the Subrtex seven-piece stretch sofa cover set."),
    ("vo-3.mp3", "One sofa cover, three cushion covers, three backrest covers. One perfect fit."),
    ("vo-4.mp3", "Built for real life. Pets, kids, spills. It stays locked in place."),
    ("vo-5.mp3", "Soft, stretchy, and totally machine washable."),
    ("vo-6.mp3", "Small change, big difference. Search Subrtex on Amazon today."),
]

async def gen(name: str, text: str):
    path = os.path.join(OUT, name)
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
    await communicate.save(path)
    print(f"OK {name} {os.path.getsize(path)} bytes")

async def main():
    for name, text in LINES:
        await gen(name, text)

asyncio.run(main())
