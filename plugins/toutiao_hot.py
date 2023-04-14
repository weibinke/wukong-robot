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

    SLUG = "toutiao_hot"

    def createNews(self):
       # 获取今日头条热榜页面的链接
        url = "https://www.toutiao.com/api/pc/feed/?category=news_hot"
        params = {
            "utm_source": "toutiao",
            "widen": 1,
            "max_behot_time": 0,
            "max_behot_time_tmp": 0,
            "tadrequire": "true",
            "as": "A1B5F9E10C8886C",
            "cp": "618D7BE23EF7EE1"
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 Edge/B08C3901",
            "Referer": "https://www.toutiao.com/ch/news_hot/"
        }
        response = requests.get(url, params=params, headers=headers)
        json_data = response.json()

        # logger.info(f"createNews response={response},content={json_data}")

        # 解析JSON内容，找到包含文章信息的JSON元素并提取数据
        hot_list = json_data["data"]
        summary = ""
        for i in range(3):
            item = hot_list[i]
            title = item["title"]  # 文章标题
            gid = item["group_id"]
            source = item["source"]  # 文章来源
            url = f"https://www.toutiao.com/article/{gid}"  # 文章链接
            # url = f"https://www.toutiao.com/article/7221453343355699716"  # 文章链接
            behot_time = item["behot_time"]  # 文章时间戳
            # article_resp = requests.get(url,headers=headers)
            # article_soup = BeautifulSoup(article_resp.content, "html.parser")
            # article_content = article_soup.select_one(".article-content")  # 文章内容
            # logger.info(f"createNews article, url={url},article_resp={article_resp.content},content={article_content}")
            # if article_content:  # 处理广告等非文章内容
            #     article_content = article_content.text.strip()
            # else:
            #     continue
            # logger.info(f"createNews item,标题：{title}\n来源：{source}\n链接：{url}\n时间戳：{behot_time}\n内容：{article_content}\n")
            logger.info(f"createNews item,标题：{title}\n来源：{source}\n链接：{url}\n时间戳：{behot_time}\n")
            
            summary = summary + title + "。"

        return f"头条热搜前三名是：{summary}"
            


    def handle(self, text, parsed):
        self.say("正在为你抓取头条热榜：", cache=True)
        news = self.createNews()
        self.say(news)

    def isValid(self, text, parsed):
        return any(word in text for word in ["头条热榜", "头条热点", "头条热搜"]) 
