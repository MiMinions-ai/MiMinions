# @title Imports
import os
import asyncio
import html
import json, random, time, threading
import openai
from openai import OpenAI
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass
from typing import List, Optional, Dict, Literal
from jsonschema import validate as js_validate, ValidationError
from fastmcp import FastMCP
from contextlib import AsyncExitStack
from pydantic import BaseModel, Field, ValidationError
from agents import (
    Agent,
    Runner,
    WebSearchTool,
    function_tool,
    SQLiteSession,
    ModelSettings,
    FunctionTool
)
from agents.agent_output import AgentOutputSchemaBase
from agents.mcp import MCPServerStreamableHttp
from agents.exceptions import ModelBehaviorError

from IPython.display import HTML, Markdown
import warnings
warnings.filterwarnings('ignore')

import logging
logging.getLogger("openai.agents").setLevel(logging.ERROR)

api_key = os.environ["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

model = "gpt-4o-mini"

user_prompt = """
You are a helpful assistant that can answer questions and help with tasks.
"""

# @title Define BaseLLM
class BaseLLM:
    """Demonstrates basic LLM functionality - single call, direct response"""

    def __init__(self, model="gpt-4o"):
        self.model = model

    def generate(self, user_prompt: str,max_tokens=1000):
        """Single forward pass through LLM"""
        print("🧠 BaseLLM: Making single API call...")
        start_time = time.time()
        response = client.chat.completions.create(
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


# @title Define ReasoningLLM
class ReasoningLLM:
    """Demonstrates reasoning framework - multiple orchestrated calls"""

    def __init__(self, base_llm: BaseLLM):
        self.base_llm = base_llm
        self.conversation_history = []

    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Step 1: Analyze the type of query and create reasoning plan"""
        analysis_prompt = f"""
        Analyze this query and determine the best approach to answer it comprehensively:
        Query: "{query}"

        Respond with:
        1. Query type (factual, process, comparison, etc.)
        2. Key components to address
        3. Suggested breakdown steps

        Keep response concise and structured.
        """

        print("🔧 ReasoningLLM: Step 1 - Analyzing query...")
        response = self.base_llm.generate(analysis_prompt)
        return {"analysis": response["content"], "tokens": response["tokens_used"]}

    def decompose_problem(self, query: str, analysis: str) -> List[str]:
        """Step 2: Break down into specific sub-questions"""
        decomposition_prompt = f"""
        Based on this analysis: {analysis}

        Break down the query "{query}" into 3-4 specific sub-questions that, when answered together,
        will provide a comprehensive response. List only the questions, one per line.
        """

        print("🔧 ReasoningLLM: Step 2 - Decomposing problem...")
        response = self.base_llm.generate(decomposition_prompt)

        # Extract questions from response
        questions = [q.strip() for q in response['content'].split('\n') if q.strip() and '?' in q]
        return questions[:4]  # Limit to 4 questions

    def answer_sub_question(self, question: str) -> str:
        """Step 3: Answer each sub-question specifically"""
        focused_prompt = f"""
        Answer this specific question about cheese making with precise, technical details:
        {question}

        Provide a clear, factual answer focusing only on this aspect.
        """

        print(f"🔧 ReasoningLLM: Step 3 - Answering: {question[:50]}...")
        response = self.base_llm.generate(focused_prompt)
        return response["content"]

    def verify_response(self, question: str, answer: str) -> Dict[str, Any]:
        """Step 4: Verify accuracy and completeness"""
        verification_prompt = f"""
        Question: {question}
        Answer: {answer}

        Evaluate this answer on a scale of 1-10 for:
        1. Accuracy
        2. Completeness
        3. Clarity

        Respond with just three numbers and any critical missing information.
        """
 
        print("🔧 ReasoningLLM: Step 4 - Verifying response...")
        response = self.base_llm.generate(verification_prompt)
        return {"verification": response["content"]}

    def synthesize_final_response(self, query: str, qa_pairs: List[tuple]) -> str:
        """Step 5: Combine all verified answers into structured response"""
        synthesis_prompt = f"""
        Original question: {query}

        Sub-questions and answers with verifications:
        {chr(10).join([
            f"Q: {qa['question']}\nA: {qa['answer']}\nVerification: {qa['verification']}\n"
            for qa in qa_pairs
        ])}

        Synthesize these into a well-structured, comprehensive answer to the original question.
        Use clear steps/sections and ensure logical flow.
        """

        print("🔧 ReasoningLLM: Step 5 - Synthesizing final response...")
        response = self.base_llm.generate(synthesis_prompt)
        return response["content"]

    def reason(self, query: str) -> Dict[str, Any]:
        """Main reasoning orchestration method"""
        print(f"\n🔧 ReasoningLLM: Processing '{query}'")
        start_time = time.time()

        # Step 1: Analyze query
        analysis = self.analyze_query(query)

        # Step 2: Decompose into sub-questions
        sub_questions = self.decompose_problem(query, analysis['analysis'])

        # Step 3 & 4: Answer and verify each sub-question
        qa_pairs = []
        total_tokens = analysis['tokens']

        for question in sub_questions:
            answer = self.answer_sub_question(question)
            verification = self.verify_response(question, answer)
            qa_pairs.append({
                "question": question,
                "answer": answer,
                "verification": verification["verification"]
            })
            total_tokens += 100  # Approximate token usage

        # Step 5: Synthesize final response
        final_response = self.synthesize_final_response(query, qa_pairs)

        end_time = time.time()

        return {
            "response": final_response,
            "reasoning_steps": {
                "analysis": analysis['analysis'],
                "sub_questions": sub_questions,
                "qa_pairs": qa_pairs
            },
            "total_tokens": total_tokens,
            "processing_time": end_time - start_time
        }


# @title Define SimpleAgent
class SimpleAgent:
    """Demonstrates agent functionality - LLM, instructions, tool usage (research-oriented)"""

    def __init__(
        self,
        model: str = "gpt-4o",
        user_location: Dict[str, Any] | None = None,
        search_context_size: str = "medium",          # "low" | "medium" | "high"
        instructions: str | None = None,
    ):
        # Configure the web search tool
        web_tool = WebSearchTool(
            user_location=user_location,
            search_context_size=search_context_size
        )

        # Instructions similar to Reasoning LLM
        if instructions is None:
            instructions = (
                "You are a meticulous research agent. "
                "Before answering, outline a brief plan with 3–4 sub-questions. "
                "Use the web_search tool for up-to-date or factual details. "
                "Perform at least TWO web_search calls across DIFFERENT reputable domains. "
                "Cross-check key facts (dates, figures, definitions). "
                "Then write a clear, structured answer with sections and practical recommendations. "
                "Finish with a 'Sources' list (title + URL) covering the items you used."
            )

        self.agent = Agent(
            name="SimpleAgent",
            instructions=instructions,
            model=model,
            tools=[web_tool],
        )

    def _research_prompt(self, query: str) -> str:
        return f"""
Task: Answer the user's question comprehensively.

User question: {query}

Workflow you must follow:
1) **Plan**: List 3–4 concise sub-questions you will answer.
2) **Research**: Use `web_search` at least twice across different domains to gather facts.
3) **Synthesize**: Combine findings into a cohesive answer that is better than a generic LLM response.
4) **Verify**: Re-check critical claims and resolve conflicts if sources disagree.
5) **Present**: Write the final answer with these sections:
   - Summary (2–4 sentences)
   - Key Criteria / How to Choose
   - Top Recommendations (with brief justifications)
   - Smart Variations or Blends (if applicable)
   - Practical Tips (actionable steps)
   - Sources (bullet list: Title — URL)

Output format: Markdown.
If uncertainty remains, say what is uncertain and why.
"""

    async def generate(self, query: str) -> Dict[str, Any]:
        print(f"\n🤖 SimpleAgent: Running with web_search for '{query}'")
        start = time.time()

        # 🔧 pass the guided research prompt
        result = await Runner.run(self.agent, input=self._research_prompt(query))

        end = time.time()
        return {
            "response": result.final_output,
            "processing_time": end - start,
            "tools": self.agent.tools  # available tools (actual usage will show in logs/tracing if enabled)
        }


# Long memory
# Information from past conversations (assume stored in a database)
USER_MEMORY = {
    "user_id": "user_123",
    "preferences": {
        "previous_cheese_choice": "mild cheddar (mac and cheese, 2 weeks ago)",
        "dietary_restrictions": "lactose sensitivity",
        "shopping_location": "Kroger",
        "budget_preference": "under $6",
        "household": "cooking for kids"
    }
}

# Load user memory
memory_context = f"""User Profile:
- Previously enjoyed: {USER_MEMORY['preferences']['previous_cheese_choice']}
- Dietary note: {USER_MEMORY['preferences']['dietary_restrictions']}
- Shops at: {USER_MEMORY['preferences']['shopping_location']}
- Budget: {USER_MEMORY['preferences']['budget_preference']}
- Household: {USER_MEMORY['preferences']['household']}"""

# System prompt
system_prompt = f"""You are a culinary expert specializing in cheese and comfort foods.
When recommending cheeses, consider:
- Melting properties and optimal temperatures
- Flavor profiles (mild to sharp)
- Availability in typical grocery stores
- Practical cooking techniques

Be specific, practical, and explain your reasoning.

{memory_context}

Use this information to personalize your recommendations."""

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "I'm cooking for my kids who prefer mild flavors"},
    {"role": "assistant", "content": "Great! I'll keep that in mind. Kids often prefer milder, creamier cheeses. What would you like to make?"},
    {"role": "user", "content": user_prompt}
]

response = client.chat.completions.create(
    model=model,
    messages=messages,
    temperature=0.2,
)


# @title Step 6: Tool Call Outputs
# Simulated tool functions: Results from function calls (APIs, databases, calculations)
check_grocery_inventory = {
    "Kraft American Singles": {"price": 4.99, "in_stock": True},
    "Kroger Mild Cheddar": {"price": 3.49, "in_stock": True},
    "Tillamook Medium Cheddar": {"price": 5.99, "in_stock": True},
    "Boar's Head Vermont Cheddar": {"price": 8.99, "in_stock": True}
}
check_lactose_content = {
    "american": {"lactose_per_slice": "0.1g", "note": "processed, lactose removed"},
    "mild_cheddar": {"lactose_per_slice": "0.2g", "note": "naturally low"},
    "aged_cheddar": {"lactose_per_slice": "0.1g", "note": "aging reduces lactose"}
}
simulate_melting = {
    "american": "Smooth melt, no separation, kid-friendly texture",
    "mild_cheddar": "Good melt, slight oil separation at high heat, richer flavor"
}

# Format tool outputs for context
tool_outputs = f"""Tool Call Results:

Grocery Inventory at Kroger:
{str(check_grocery_inventory)}

Lactose Content Analysis:
{str(check_lactose_content)}

Melting Simulation Results:
{str(simulate_melting)}"""

# System prompt
system_prompt = f"""You are a culinary expert specializing in cheese and comfort foods.
When recommending cheeses, consider:
- Melting properties and optimal temperatures
- Flavor profiles (mild to sharp)
- Availability in typical grocery stores
- Practical cooking techniques

Be specific, practical, and explain your reasoning.

{memory_context}

Use this information to personalize your recommendations."""

# Inject tool outputs into the prompt
enhanced_user_prompt = f"""{str(tool_outputs)}
Use this real-time data to make your recommendation.
User question: {user_prompt}"""

response = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": enhanced_user_prompt}
    ],
    temperature=0.2,
)



Runner.run(Agent(model=model, instructions=user_prompt, tools=[FunctionTool(function=check_grocery_inventory)]), input=user_prompt)