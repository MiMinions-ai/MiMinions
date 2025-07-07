from typing import Dict, Optional, Any

from pydantic import BaseModel, Field

class Agent(BaseModel):
    client: Optional[Any] = Field()
    memory: Optional[Any] = Field()
    attention: Optional[Any] = Field()
    reward: Optional[Any] = Field()
    
    def set_goal(goal:str):
        pass
    
    def run():
        pass