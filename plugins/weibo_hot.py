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
# 配置 OpenAI 认证密钥

class Plugin(AbstractPlugin):

    SLUG = "weibo_hot"

    def createNews(self):
        # 请求URL
        url = 'https://s.weibo.com/top/summary?cate=realtimehot'
        header = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
            'Host': 's.weibo.com',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            # 定期更换Cookie
            'Cookie': 'SINAGLOBAL=6080892482943.147.1545718325197; SUB=_2AkMUDjCSf8NxqwJRmPkczWjhaYx1wg7EieKiUsFJJRMxHRl-yj9jqlUDtRB6P44efXkomSWFmpqzHf8Z-tnOy3fmSqo_; SUBP=0033WrSXqPxfM72-Ws9jqgMF55529P9D9W5K1O86ZKSjSJUI7OIc1IQh; UOR=,,www.baidu.com; _s_tentry=-; Apache=3049488574867.7246.1681370428616; ULV=1681370428635:2:1:1:3049488574867.7246.1681370428616:1666367398579'
        }

        # 发送 GET 请求获取HTML内容
        response = requests.get(url,headers=header)

        # 解析HTML内容，获取热搜榜单

        # logger.info("createNews start response=%s", response.content)
        soup = BeautifulSoup(response.content, "html.parser")
        items = soup.select(".td-02 a")
        logger.info(f"createNews item:{len(items)}")
        summary = ""
        for i in range(3):
            item = items[i]
            try:
                logger.info(f"createNews parse item：{item.text}")
                title = item.text.strip()
                href = item["href"]
                link = f"https://s.weibo.com{href}"
                
                logger.info(f"createNews parse item,title={title},url={link}")

                # # 发送 GET 请求获取文章内容
                # response = requests.get(link,headers=header)
                # logger.info(f"createNews parse item,title={title},url={link},response={response.content}")

                # # 解析HTML内容，获取文章正文
                # soup = BeautifulSoup(response.content, "html.parser")
                # article_content = soup.find("div", {"class": "WB_editor_iframe_new"}).text.strip()

                # logger.info(f"createNews parse item,url={link},article_content={response.article_content}")

                # # 对文章内容长度进行限制
                # if len(article_content) > 2048:
                #     article_content = article_content[:2045] + "..."

                # # 使用 GPT 模型生成文章摘要
                # prompt = article_content[:1000]
                # summary = ""

                # for i in range(6):
                #     res = openai.Completion.create(engine="davinci", prompt=prompt + summary, max_tokens=20, n=1, stream=False)
                #     summary += res.choices[0].text
                #     logger.info(f"createNews title:{title},article_content:{article_content},prompt:{prompt},summary:{summary}")

                summary = summary + title + "。\n"
            except Exception as e:
                logger.error(f"Error occurred while processing article: {item}")
                logger.error(e)
                return "createNews 解析失败"
            
        return f"微博热搜前三名是：{summary}"


    def handle(self, text, parsed):
        self.say("正在为你抓取微博热榜：", cache=True)
        news = self.createNews()
        self.say(news)

    def isValid(self, text, parsed):
        return any(word in text for word in ["微博热榜", "微博热点", "微博热搜"]) 
