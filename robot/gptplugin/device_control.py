import os
from typing import Optional, Type

import requests
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
    args_schema: Type[BaseModel] = ToolInputSchema

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
    

class GetStatusToolInputSchema(BaseModel):
    pass
class DeviceStatus(BaseTool):
    name = "DeviceStatus"
    description = "Get device status."
    args_schema: Type[BaseModel] = GetStatusToolInputSchema

    def _run(
        self, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        return self.get_status()

    def getCPUtemperature(self):
        result = 0.0
        try:
            tempFile = open("/sys/class/thermal/thermal_zone0/temp")
            res = tempFile.read()
            result = float(res) / 1000
        except Exception as e:
            logger.error(f"getCPUtemperature error:{e}")
        return result

    def getRAMinfo(self):
        p = os.popen('free')
        i = 0
        while 1:
            i = i + 1
            line = p.readline()
            if i == 2:
                return (line.split()[1:4])

    def getDiskSpace(self):
        p = os.popen("df -h /")
        i = 0
        while 1:
            i = i +1
            line = p.readline()
            if i == 2:
                return (line.split()[1:5])

    def getPiStatus(self):
        result = {'cpu_tmp': 0.0,
                  'ram_total': 0, 'ram_used': 0, 'ram_percentage': 0,
                  'disk_total': '0.0', 'disk_used': '0.0','disk_percentage': 0}

        result['cpu_tmp'] = self.getCPUtemperature()
        ram_stats = self.getRAMinfo()
        result['ram_total'] = int(ram_stats[0]) / 1024
        result['ram_used'] = int(ram_stats[1]) / 1024
        result['ram_percentage'] = int(result['ram_used'] * 100 / result['ram_total'])
        disk_stats = self.getDiskSpace()
        result['disk_total'] = disk_stats[0]
        result['disk_used'] = disk_stats[1]
        result['disk_percentage'] = disk_stats[3].split('%')[0]
        return result

    def get_status(self):
        try:
            status = self.getPiStatus()
            result = '处理器温度' + str(status['cpu_tmp']) + '度,内存使用百分之' + str(status['ram_percentage']) + ',存储使用百分之' + str(status['disk_percentage'])
            return result
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"get_status error:{e}")
            return "获取设备状态失败.{}".format(e)