from datetime import datetime
import json
from typing import Optional, Type

from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from robot import logging

logger = logging.getLogger(__name__)
class ToolInputSchema(BaseModel):
    pass

class Information(BaseTool):
    name = "information"
    description = "ask my information(my name/my city/current datetime)."
    args_schema: Type[BaseModel] = ToolInputSchema

    def _run(
        self, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        now = datetime.now()
        city = "深圳"
        name = "小彬"
        data = {
            "datetime": str(now),
            "user city": city,
            "user name": name
        }
        result = json.dumps(data, ensure_ascii=False)

        return f"{result}"