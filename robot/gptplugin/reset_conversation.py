# Import things that are needed genericallyI
from typing import Optional, Type

import requests
from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from langchain.memory import ConversationBufferMemory

from robot import config, logging

logger = logging.getLogger(__name__)
class ToolInputSchema(BaseModel):
    pass

class ResetConversation(BaseTool):
    name = "ResetConversation"
    description = "useful when user want to reset conversation or clear chat history."
    args_schema: Type[BaseModel] = ToolInputSchema
    memory: ConversationBufferMemory = None

    def __init__(self, memory: ConversationBufferMemory):
        super().__init__()
        self.memory = memory
        
    def _run(
        self, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        logger.info("reset_conversation")
        self.memory.clear()

        return "执行成功。"