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
    query: str = Field(description="keyword to search for news，支持类型：top(推荐,默认)guonei(国内)guoji(国际)yule(娱乐)tiyu(体育)junshi(军事)keji(科技)caijing(财经)youxi(游戏)qiche(汽车)jiankang(健康).")
class Hotnews(BaseTool):
    name = "Hotnews"
    description = "Useful for search news information."
    args_schema: Type[BaseModel] = ToolInputSchema
    def get_new_global(self,query):
        '''使用https://newsapi.org，查询热点新闻，只能查询海外的'''

        try:
             # Your API key
            api_key = ''

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
                'apiKey': api_key
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
    
    def get_new_china(self,query):
        '''使用http://v.juhe.cn/，查询热点新闻。'''

        try:
             # Your API key
            api_key = config.get("/headline_news/key")

            # The endpoint for getting everything
            url = 'http://v.juhe.cn/toutiao/index'

            params = {
                'type': query,
                'page_size': 5,
                'key': api_key
            }
            # Send a GET request to the endpoint
            response = requests.get(url, params=params)

            # Get the articles from the response
            articles = response.json()['result']['data']

            # Extract the title and url from each article
            news = [{'title': article['title'], 'url': article['url'],'date':article['date'],'category': article['category'],'author': article['author_name']} for article in articles]
            logger.info("get_news:%s,size=%d" % (news,len(news)))

            return f"{news}"
        except Exception as e:
            logger.error(e)
            raise e

        return "新闻查询失败。"


    def _run(
        self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool."""
        return self.get_new_china(query)