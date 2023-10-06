from datetime import datetime
from typing import Optional, Type

import requests
import tushare as ts
import yfinance as yf
from bs4 import BeautifulSoup
from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import json

from robot import logging,config

logger = logging.getLogger(__name__)
class ToolInputSchema(BaseModel):
    cmd: str = Field(description="Command that can be given to the Xiaoai speaker, for example: 主卧开灯.")

DEFAULT_SYMBOLS = ['000001.SS', '^HSI', '^DJI', '0700.HK', 'BIDU']
class DeviceControl(BaseTool):
    name = "DeviceControl"
    description = "Control smart device."
    args_schema: Type[ToolInputSchema] = ToolInputSchema

    def _run(
        self, cmd: str = None, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        return self.control_device(command=cmd)
    
    def control_device(self, command: str) -> str:
        logger.info("control_device command=" + command)
        output = ""
        try:
            # 通过小爱音箱调用Home Assistant控制设备，这样不需要一个配置设备
            # Home Assistant的URL，例如：http://localhost:8123
            # Home Assistant rest api介绍：https://developers.home-assistant.io/docs/api/rest/
            base_url = config.get("/gpt_tool/hass/url", "")
            token = config.get("/gpt_tool/hass/key", "")

            '''
            控制小爱音箱执行指令。
            curl \
            -H "Authorization: Bearer xx" \
            -H "Content-Type: application/json" \
            -d '{"entity_id": "text.xiaomi_lx06_fb9b_execute_text_directive","value": "关灯"}' \
            http://192.168.3.22:8123/api/services/text/set_value

            '''
            # 要控制的实体ID
            entity_id = 'text.xiaomi_lx06_fb9b_execute_text_directive'

            headers = {
                'Authorization': '{}'.format(token),
                'content-type': 'application/json',
            }

            # 要发送的数据，例如：打开灯
            data = {
                "entity_id": f"{entity_id}",
                "value": command
            }

            # 发送请求
            response = requests.post('{}/api/services/text/set_value'.format(base_url),
                                    headers=headers,
                                    data=json.dumps(data))
            
            logger.info("control_device response=" + response.text)
            output = "命令执行成功。"
        except Exception as e:
            output = f"命令执行失败:{e}\n"
            logger.error(output)

        logger.info("命令执行成功。：" + command + ",result=" + output)
        return output