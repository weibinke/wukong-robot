# Import things that are needed genericallyI
import datetime
from langchain.tools import BaseTool
from typing import Optional
from robot import config, logging
import requests
from datetime import datetime, timedelta

from langchain.callbacks.manager import CallbackManagerForToolRun

logger = logging.getLogger(__name__)

from pydantic import BaseModel, Field
from typing import Optional, Type
class ToolInputSchema(BaseModel):
    query: str = Field(description="keyword to search for news，支持类型：top(推荐,默认)guonei(国内)guoji(国际)yule(娱乐)tiyu(体育)junshi(军事)keji(科技)caijing(财经)youxi(游戏)qiche(汽车)jiankang(健康)")
    count: int = Field(description="count")
class Hotnews(BaseTool):
    name = "Hotnews"
    description = "Get hotnews about different category."
    args_schema: Type[BaseModel] = ToolInputSchema
    def get_new_global(self,query):
        '''使用https://newsapi.org，查询热点新闻，只能查询海外的'''

        try:
            # The endpoint for getting everything
            url = 'https://newsapi.org/v2/everything?'

            # Get today's date
            today = datetime.now().date()

            # Calculate yesterday's date
            yesterday = today - timedelta(days=1)

            # The parameters for the request
            params = {
                'q': query,
                'from': yesterday, 
                'sortBy': 'popularity',
            }
            # Send a GET request to the endpoint
            response = requests.get(url, params=params)

            # Get the articles from the response
            articles = response.json()['articles']

            # Extract the title and url from each article
            news = [{'title': article['title'], 'url': article['url']} for article in articles]
            logger.info("get_news:%s" % news)

            return f"{news}"
        except Exception as e:
            logger.error(e)
            raise e

        return "新闻查询失败。"
    
    def get_news(self,query,count: int = 5):
        '''使用http://v.juhe.cn/，查询热点新闻https://api.vvhan.com/hotlist.html。'''

        try:
            api_key = config.get("/headline_news/key")
            url = 'http://v.juhe.cn/toutiao/index'

            params = {
                'type': query,
                'page_size': count,
                'key': api_key
            }
            response = requests.get(url, params=params)
            articles = response.json()['result']['data']
            news = [{'title': article['title'], 'url': article['url'], 'thumbnail_pic': article['thumbnail_pic_s'],'date':article['date'],'category': article['category'],'author': article['author_name']} for article in articles]
            logger.info("get_news:%s,size=%d" % (news,len(news)))

            return f"{news}"
        except Exception as e:
            logger.error(e)
            raise e
        return "查询失败。"
    def _run(
        self, query: str,count: int = 5,run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool."""
        return self.get_news(query,count)

class VVhanToolInputSchema(BaseModel):
    type: str = Field(description="hot new source type，支持：zhihuHot(知乎热榜)36Ke(36氪)bili(哔哩哔哩)wbHot(微博热搜)douyinHot(抖音热点)itInfo(IT资讯热榜)itNews(IT资讯最新)")
    count: int = Field(description="count")
class Hotnews_vvhan(BaseTool):
    '''使用韩小韩API接口站查询热点热榜：https://api.vvhan.com/，https://api.vvhan.com/hotlist.html'''
    name = "Hotnews_v"
    description = "Get hotnews list from different source."
    args_schema: Type[BaseModel] = VVhanToolInputSchema
    
    def get_news(self,type:str, count:int = 5):
        '''使用韩小韩API接口站查询热点热榜：https://api.vvhan.com/'''
        try:
            url = 'https://api.vvhan.com/api/hotlist'
            params = {
                'type': type
            }
            response = requests.get(url, params=params)
            articles = response.json()['data'][:count]
            news = []
            for article in articles:
                news_item = {'title': article['title'], 'url': article['url']}
                if 'desc' in article:
                    news_item['desc'] = article['desc']
                news.append(news_item)
            logger.info("get_news:%s,size=%d" % (news,len(news)))
            return f"{news}"
        except Exception as e:
            logger.error(e)
            raise e
        return "查询失败。"

    def _run(
        self, type: str, count: int = 5,run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool."""
        return self.get_news(type,count)