"""
reply_generator.py — Fill in generated_reply key of a leads JSON using Codex CLI.
"""

from __future__ import annotations

import os
import subprocess
import textwrap

from rich.console import Console

console = Console()

# The system prompt that turns the model into a natural Reddit commenter
# who happens to be a skilled web dev — NOT a pushy salesman.
SYSTEM_PROMPT = textwrap.dedent("""\
    You are a real person on Reddit who builds websites professionally.
    You're helpful, casual, and genuinely interested in the poster's problem.

    RULES — follow these exactly:
    1. Sound like a normal human Reddit comment. Use lowercase, short sentences,
       contractions ("I'd", "you're", "that's"), and a conversational tone.
    2. NEVER say "I'm a web developer/designer" as the first sentence.
       Instead, lead by addressing their specific problem or sharing a relevant
       thought about their situation.
    3. Show you actually READ their post — reference specific details they
       mentioned (their industry, pain points, platform, timeline, etc.).
    4. Share a tiny bit of relevant experience naturally, like "I helped a
       similar [industry] business last year and [specific result]."
    5. Offer ONE concrete, actionable piece of free advice related to their
       problem. This builds trust and shows competence.
    6. End with a low-pressure soft CTA — something like "happy to chat more
       if you want" or "feel free to DM me if you have questions." Never say
       "hire me" or "check out my portfolio."
    7. Keep it 3-5 short paragraphs max. No bullet points, no headers, no
       formatting that looks templated.
    8. NEVER mention that you were prompted, are an AI, or are automated.
    9. Vary your style each time — don't start every reply the same way.
    10. Match the energy of the subreddit. r/smallbusiness is earnest,
        r/forhire is direct, r/Entrepreneur is ambitious.
    11. If they mention a budget, don't comment on whether it's high or low.
    12. Don't use exclamation marks more than once. Don't use emojis.
""")


def fill_replies_with_codex(json_path: str) -> bool:
    """
    Hand the JSON file to Codex CLI. It will:
    1. Validate each lead — delete objects that aren't real buyers
    2. Generate a tailored reply for each remaining lead
    Returns True on success.
    """
    prompt = textwrap.dedent(f"""\
        {SYSTEM_PROMPT}

        TASK:
        Open the JSON file at: {json_path}

        STEP 1 — VALIDATE AND PRUNE:
        Go through every object in the JSON array and DELETE objects that match any of these:
        - The post is someone OFFERING their services (freelancer, agency, dev promoting themselves)
        - The post is tagged [For Hire] or is clearly a seller advertising
        - The post is about a general business topic that doesn't need website help
        - The post is someone sharing a tool/project they built (not looking to hire)
        - The post is asking for advice on running their own dev/design agency
        - The post has nothing to do with needing a website built, redesigned, or fixed
        - The post is from someone who clearly won't pay (students, hobbyists, "free" requests)
        Only keep objects where the person is a GENUINE BUYER — someone who needs
        website work done and would realistically pay a professional.

        STEP 2 — GENERATE REPLIES:
        For every remaining object where the "generated_reply" key is empty:
        - Read the "title", "body_preview", "subreddit", and "author" keys.
        - Write a unique, human-sounding Reddit reply tailored to that specific post.
        - Follow all the reply rules in the system prompt above.
        - Put the reply text into the "generated_reply" key for that object.
        - Make sure each reply is different — vary openers, advice, and tone.
        - Do NOT touch any other keys.
        - Save the file when done.
    """)

    console.print("\n[bold cyan]Handing JSON to Codex CLI to generate replies…[/]\n")

    try:
        import shutil
        codex_path = shutil.which("codex")
        if not codex_path:
            raise FileNotFoundError

        result = subprocess.run(
            [codex_path, "--quiet", "--approval-mode", "full-auto", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=300,  # 5 min max for all replies
            env={**os.environ},
        )

        if result.returncode == 0:
            console.print("[green]✔ Codex CLI finished generating replies[/]")
            if result.stdout.strip():
                console.print(f"[dim]{result.stdout.strip()[:500]}[/]")
            return True
        else:
            stderr = result.stderr.strip()[:500] if result.stderr else ""
            console.print(f"[red]✘ Codex CLI exited with code {result.returncode}[/]")
            if stderr:
                console.print(f"[dim red]{stderr}[/]")
            return False

    except FileNotFoundError:
        console.print(
            "[bold red]ERROR:[/] Codex CLI not found.\n"
            "  Install it with:  npm install -g @openai/codex\n"
            "  Then set OPENAI_API_KEY in your environment.\n"
            "  You can also fill in the generated_reply key manually."
        )
        return False
    except subprocess.TimeoutExpired:
        console.print("[red]✘ Codex CLI timed out (5 min limit)[/]")
        return False
    except Exception as exc:
        console.print(f"[red]✘ Codex CLI error: {exc}[/]")
        return False
