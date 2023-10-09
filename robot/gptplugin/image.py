from typing import Optional, Type

from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from robot import logging

logger = logging.getLogger(__name__)
class ToolInputSchema(BaseModel):
    prompt: str = Field(description="For image descriptions, use multiple phrases to summarize the entity")

class DrawImage(BaseTool):
    name = "DrawImage"
    description = "Generate image by text description."
    args_schema: Type[BaseModel] = ToolInputSchema

    def _run(
        self, prompt: str = None, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        result = [
            {"url": f"https://image.pollinations.ai/prompt/{prompt}"},
            # {"url": f"https://images.unsplash.com/{prompt}"},
            ]
        return result