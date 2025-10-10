from agents import (
    Agent as OpenAIAgent,
    Runner,
    ModelSettings
)
from agents.agent_output import AgentOutputSchemaBase
from agents.exceptions import ModelBehaviorError

class Agent(OpenAIAgent):
    def __init__(self,**kwargs) -> None:
        super().__init__(**kwargs)