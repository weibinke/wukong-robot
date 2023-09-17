# Import things that are needed genericallyI
from langchain.tools import BaseTool, StructuredTool, Tool, tool
from typing import Optional, Type

from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)

import subprocess
import platform

from robot import logging

logger = logging.getLogger(__name__)

class VolumeControl(BaseTool):
    name = "VolumeControl"
    description = "useful for when you want to get or set device volume. query should be on of get/up/down, or number between 0-100."

    def volume(self,query):
        """
        set or get volume
        """
        current_volume = 0
        try:
            num = int(query)
            current_volume = self.set_volume(num)
        except ValueError:
            if query  == "up":
                current_volume = self.turnUp()
            elif query == "down":
                current_volume = self.turnDown()
            else:
                current_volume = self.get_volume()

        return f"执行成功，当前音量：{current_volume}."
            
        
    # end def

    def _run(
        self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool."""
        return self.volume(query)

    def get_volume(self):
        system = platform.system()
        volume = 0
        if system == "Darwin":
            res = subprocess.run(
                ["osascript", "-e", "output volume of (get volume settings)"],
                shell=False,
                capture_output=True,
                universal_newlines=True,
            )
            volume = int(res.stdout.strip())
            
        elif system == "Linux":
            res = subprocess.run(
                ["amixer get Master|grep -o -m 1 '[0-9]\+%'"],
                shell=True,
                capture_output=True,
                universal_newlines=True,
            )
            if res.stdout != "" and res.stdout.strip().endswith("%"):
                volume = int(res.stdout.strip().replace("%", ""))
        else:
            logger.error("当前系统不支持调节音量")

        return volume
    
    def set_volume(self,num):
        system = platform.system()
        if system == "Darwin":
            subprocess.run(["osascript", "-e", f"set volume output volume {num}"])
        elif system == "Linux":
            subprocess.run(["amixer", "set", "Master", f"{num}%"])
        else:
            logger.error("当前系统不支持调节音量")
        return num
        

    def turnUp(self):
        volume = self.get_volume()
        volume += 20
        if volume >= 100:
            volume = 100
        return self.set_volume(volume)
        

    def turnDown(self):
        volume = self.get_volume()
        volume -= 20
        if volume < 0:
            volume = 0
        return self.set_volume(volume)