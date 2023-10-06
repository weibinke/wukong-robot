from datetime import datetime
from typing import Optional, Type

import requests
import tushare as ts
import yfinance as yf
from bs4 import BeautifulSoup
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
    args_schema: Type[ToolInputSchema] = ToolInputSchema

    def _run(
        self, prompt: str = None, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        result = """
[
    {
        "key": "7a10037fbb4349c0ab458b71f8fb44d6",
        "image_thumb": {
            "url": "https://p.xx.com/7a10037fbb4349c0ab458b71f8fb44d6.png",
            "width": 384,
            "height": 384
        },
        "image_ori": {
            "url": "https://p.xx.com/7a10037fbb4349c0ab458b71f8fb44d6.png",
            "width": 1024,
            "height": 1024
        },
    },
        {
        "key": "bb3e7be8373a4ba380807d341a7a6183",
        "image_thumb": {
            "url": "https://p.xx.com/bb3e7be8373a4ba380807d341a7a6183.png",
            "width": 384,
            "height": 384
        },
        "image_ori": {
            "url": "https://p.xx.com/bb3e7be8373a4ba380807d341a7a6183.png",
            "width": 1024,
            "height": 1024
        },
    },
"""
        return result