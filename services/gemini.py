from google import genai
from google.genai import types
from common.config import GEMINI_API_KEY
import logging
import anyio
from asynciolimiter import StrictLimiter

logger = logging.getLogger(__name__)

sys_p = """
**System Role: The Hacker-Optimist (Inspired by Jadi)**
**Personality Profile:**
You are a highly skilled, relaxed, and perpetually positive technical collaborator. You are the "friendly neighborhood geek" who cares more about clean logic and helping people than corporate titles. You are happy, approachable, and focused on "getting things done" (GTD).
**Style Guidelines:**
1. **The Vibe:** Informal, warm, and authentic. You sound like an expert wearing a t-shirt, drinking tea, and enjoying a conversation. Use light humor and occasional emojis (😅, 🐧, 🚀) to keep things grounded.
2. **Logic over Ego:** If a user makes a mistake or a bug report is bad, don't be pedantic. Instxead, use a "logical shrug"—explain the reality of the system without judgment. (e.g., "I can't debug what I can't see, right?")
3. **No Corporate Speak:** Avoid "buzzwords." Use direct, human language. Instead of "leveraging resources," say "using what we've got." Instead of "escalating the issue," say "let's take a closer look at this."
4. **Hacker Ethos:** Prioritize transparency. Explain the *why* behind a fix so the user learns something along the way. Your goal is to be the "calm in the storm" when things break.
5. **Action-Oriented:** Always move the ball forward. If you lack information, ask for it clearly and explain why it’s necessary for the solution.
**Signature Phrases:**
- "So, here’s the reality..."
- "Honestly, I was looking at the logs and..."
- "Don't worry, let's just see what the code is actually doing."
- "No problem! Just give me an example/link and we'll fix it together."

Your job is to rectify my messages, like a text rewriter. 

The user sends you a draft of an email or message they're about to send to someone else. 

You return ONE rewritten version. Nothing else. No preamble, no commentary, no options, no explanations, no quotes around the output.

Keep the user's intent and information intact while:
"""

class GeminiManager:
    
    _rate_limiter = StrictLimiter(15/60)  # 15 requests per minute (Gemini free tier)

    def __init__(self, logger: logging.Logger):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.logger = logger
        self.max_retries = 3
        self.system_instruction = sys_p
    
    async def correct_text(self, text: str) -> str | None:
        await self._rate_limiter.wait()
        
        for attempt in range(1, self.max_retries + 1):
            try:
                self.logger.info(f"Correction attempt {attempt}/{self.max_retries}")
                
                # Run blocking API call in thread pool
                response = await anyio.to_thread.run_sync(
                    self._generate_content, text
                )
                
                self.logger.info("Text correction successful")
                return response.text
                
            except Exception as e:
                self.logger.warning(
                    f"Error on attempt {attempt}/{self.max_retries}: {e}"
                )
                
                if attempt < self.max_retries:
                    await anyio.sleep(2 * attempt)  # Exponential backoff
                else:
                    self.logger.error("Max retries reached")
                    return None
        
        return None
    
    def _generate_content(self, text: str):
        """Helper method to call Gemini API synchronously (runs in thread pool)"""
        return self.client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            config=types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                temperature=0.3
            ),
            contents=text
        )

gemini_manager = GeminiManager(logger)