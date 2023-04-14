# -*- coding: utf-8 -*-
import os
import subprocess
import time
from robot import config, constants, logging
from robot.sdk.AbstractPlugin import AbstractPlugin
import requests
from bs4 import BeautifulSoup
import re
import requests
import openai
import time

logger = logging.getLogger(__name__)

class Plugin(AbstractPlugin):

    SLUG = "lighters"

    def handle(self, text, parsed):
        if any(word in text for word in ["开灯"]) :
            self.say("开了")
        elif any(word in text for word in ["关灯"]):
            self.say("关了")
        elif any(word in text for word in ["扫地"]):
            self.say("扫地僧出动了")

    def isValid(self, text, parsed):
        return any(word in text for word in ["开灯", "关灯", "扫地"]) 
