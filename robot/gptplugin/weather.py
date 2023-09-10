# Import things that are needed genericallyI
from langchain.tools import BaseTool, StructuredTool, Tool, tool
from typing import Optional, Type
from robot import config, logging
import requests
import json

from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)

logger = logging.getLogger(__name__)

class Weather(BaseTool):
    name = "Weather"
    description = "useful for when you want to know weather.input must only be city."

    def get_weather(self,city):
        logger.info("get_weather:" + city)
        key = config.get("/gpt_tool/weather/key")
        WEATHER_API = 'https://api.seniverse.com/v3/weather/daily.json'
        # SUGGESTION_API = 'https://api.seniverse.com/v3/life/suggestion.json'
        try:

            body = {
            'key': key,
            'location': city
            }
            result = requests.get(WEATHER_API, params=body, timeout=3)
            logger.info("fetch_weather result:" + result.text)
            
            return f"天气查询，result:{result.text}"
        except Exception as e:
            logger.error(e)

        return "天气查询失败。"


    def _run(
        self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool."""
        return self.get_weather(query)

    async def _arun(
        self, query: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("custom_search does not support async")
            
    