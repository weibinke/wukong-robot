# Import things that are needed genericallyI
from typing import Optional, Type

import requests
from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from robot import config, logging

logger = logging.getLogger(__name__)
class ToolInputSchema(BaseModel):
    city: str = Field(description="should be city name.")
class Weather(BaseTool):
    name = "Weather"
    description = "useful for when you want to know weather."
    args_schema: Type[BaseModel] = ToolInputSchema

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
            
            return f"{result.text}"
        except Exception as e:
            logger.error(e)

        return "天气查询失败。"


    def _run(
        self, city: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool."""
        return self.get_weather(city)