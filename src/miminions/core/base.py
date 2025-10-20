# @title Define BaseLLM
import os
from time import time
from openai import OpenAI

CLIENT = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class BaseLLM:
    """Demonstrates basic LLM functionality - single call, direct response"""

    def __init__(self, model="gpt-4o"):
        self.model = model

    def generate(self, user_prompt: str,max_tokens=1000):
        """Single forward pass through LLM"""
        print("🧠 BaseLLM: Making single API call...")
        start_time = time.time()
        response = CLIENT.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=max_tokens
        )
        end_time = time.time()

        return {
            "content": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens,
            "response_time": end_time - start_time
        }