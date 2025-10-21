import json, random, time, threading
from typing import Dict, Any
from typing import List, Optional, Dict, Literal
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

from IPython.display import HTML, Markdown
import warnings
warnings.filterwarnings('ignore')

import logging
logging.getLogger("openai.agents").setLevel(logging.ERROR)
from pydantic import BaseModel, Field
from agents import (
    Agent as OpenAIAgent,
    Runner,
    ModelSettings
)
from agents.agent_output import AgentOutputSchemaBase
from agents.exceptions import ModelBehaviorError


class AgentConfig(BaseModel):
    name: str = Field(description="The name of the agent")
    instructions: str = Field(description="The instructions for the agent")
    model: str = Field(default="gpt-4o", description="The model to use for the agent")
    tools: List[str] = Field(description="The tools to use for the agent")
    
class MetaAgentResponse(BaseModel):
    agent_config: AgentConfig = Field(description="The agentic configuration for the new agent")
    response_content: str = Field(description="The response content from the meta agent to communicate with the user")
    
class Agent(OpenAIAgent):
    def __init__(self,**kwargs) -> None:
        super().__init__(**kwargs)
        
        
# @title Define MetaAgent
class MetaAgent:
    """Demonstrates agent functionality - LLM, instructions, tool usage (research-oriented)"""

    def __init__(
        self,
        model: str = "gpt-4o",
        user_location: Dict[str, Any] | None = None,
        search_context_size: str = "medium",          # "low" | "medium" | "high"
        **kwargs,
    ):
        # Configure the web search tool
        web_tool = WebSearchTool(
            user_location=user_location,
            search_context_size=search_context_size
        )

        # Instructions similar to Reasoning LLM
        instructions = (
            "You are a Meta AI agent who reads user query and create an ai agent to better answer the user query. "
            "Before create the agent configuration, identify what the user goal is and what the agent shall be best suited for it"
            "Then outline a brief plan with 3–4 sub-questions. "
            "Use the web_search tool for up-to-date or factual details. "
            "Perform at least TWO web_search calls across DIFFERENT reputable domains. "
            "Cross-check key facts (dates, figures, definitions). "
            "Finish with a agentic configuration for the new agent."
        )

        self.agent = Agent(
            name="MetaAgent",
            instructions=instructions,
            model=model,
            tools=[web_tool],
            output_type=MetaAgentResponse,
        )

    def _research_prompt(self, query: str) -> str:
        return f"""
Task: Create an agentic configuration for the new agent based on the user query.

User question: {query}

Workflow you must follow:
1) **Plan**: List 3–4 concise sub-domain you will need to know.
2) **Research**: Use `web_search` at least twice across different domains to gather facts to generate the agentic configuration.
3) **Synthesize**: Combine findings into an agentic configuration which is best suited for the user query.
4) **Verify**: Check against the tools currently available. If not, request for the tools to be added.
    {"".join([f"- {tool}\n" for tool in mock_tools.keys()])}
5) **Generate**: Create the agentic configuration:
    - name: <name of the agent>
    - instructions: <instructions for the agent>
        This shall include what the agent needs to do step by step from planning, research, synthesis, verification, and generation of the response.
    - model: <model to use for the agent>
    - tools: <list of tools to use for the agent>

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
            "response": result.raw_responses,
            "processing_time": end - start,
            "tools": self.agent.tools  # available tools (actual usage will show in logs/tracing if enabled)
        }

