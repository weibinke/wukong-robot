# Import things that are needed genericallyI
import os
from langchain.tools import BaseTool
from typing import Optional
import requests

from robot import config, logging
from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.document_loaders import WebBaseLoader
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.document_loaders import PyPDFLoader
from langchain.chains.summarize import load_summarize_chain
from langchain.document_loaders import SeleniumURLLoader
from langchain.document_loaders import PlaywrightURLLoader
from pydantic import BaseModel, Field
from typing import Optional, Type
from langchain.utilities import BingSearchAPIWrapper
from langchain.utilities import DuckDuckGoSearchAPIWrapper
from langchain.utilities import GoogleSerperAPIWrapper

logger = logging.getLogger(__name__)

# import ssl

# ssl_context = ssl.create_default_context()
# ssl_context.check_hostname = False
# ssl_context.verify_mode = ssl.CERT_NONE

class SearchToolInputSchema(BaseModel):
    query: str = Field(description="search query")
class BingSearchTool(BaseTool):
    name = "Search"
    description = "A Bing Search Engine. Useful when you need to search information you don't know."
    args_schema: Type[BaseModel] = SearchToolInputSchema

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        SERPER_API_KEY = config.get("/gpt_tool/SERPER_API_KEY")
        if (SERPER_API_KEY):
            os.environ["SERPER_API_KEY"] = SERPER_API_KEY

        BING_SUBSCRIPTION_KEY = config.get("/gpt_tool/BING_SUBSCRIPTION_KEY")
        if (BING_SUBSCRIPTION_KEY):
            os.environ["BING_SUBSCRIPTION_KEY"] = BING_SUBSCRIPTION_KEY

        BING_SEARCH_URL = config.get("/gpt_tool/BING_SEARCH_URL")
        if (BING_SEARCH_URL):
            os.environ["BING_SEARCH_URL"] = BING_SEARCH_URL

    def _run(
        self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        try:
            result = self.custom_search(query)
            return result
        except Exception as e:
            logger.error("custom_search faild: %s", e)
            
        try:
            result = self.ddg_search(query)
            return result
        except Exception as e:
            logger.error("DuckDuckGo search faild: %s", e)

        try:
            result = self.google_serper(query)
            return result
        except Exception as e:
            logger.error("google_serper faild: %s", e)

        try:
            result = self.bing_search(query)
            return result
        except Exception as e:
            logger.error("Bing search faild: %s", e)

        return "搜索失败。"
    
    def bing_search(self,query:str):
        search = BingSearchAPIWrapper()
        result = search.results(query, 5)
        return result

    def google_serper(self,query:str):
        search = GoogleSerperAPIWrapper()
        return search.results(query)
    
    def ddg_search(self,query:str):
        search = DuckDuckGoSearchAPIWrapper()
        return search.results(query,num_results=5)

    def custom_search(self,query:str):        
        try:
            CUSTOM_SEARCH_PROXY_BASE = config.get("/gpt_tool/CUSTOM_SEARCH_PROXY_BASE")
            if (not CUSTOM_SEARCH_PROXY_BASE):
                raise ValueError("CUSTOM_SEARCH_PROXY_BASE not specified")
            
            CUSTOM_SEARCH_PROXY_KEY = config.get("/gpt_tool/CUSTOM_SEARCH_PROXY_KEY")
            if (not CUSTOM_SEARCH_PROXY_KEY):
                raise ValueError("CUSTOM_SEARCH_PROXY_KEY not specified")

            response = requests.get(
                CUSTOM_SEARCH_PROXY_BASE,
                params={'q': query,'key': CUSTOM_SEARCH_PROXY_KEY},
                headers={}
            )

            logger.debug("custom_search result: %s", response)
            return response.json()
        except Exception as e:
            logger.error("custom search proxy failed: %s", e)
            raise e
        
class ToolInputSchema(BaseModel):
    url: str = Field(description="URL.")

class SummaryWebpage(BaseTool):
    name = "SummaryWebpage"
    description = "Summary content of a webpage."
    args_schema: Type[BaseModel] = ToolInputSchema

    async def my_async_function(self,query):
        loader = PlaywrightURLLoader(urls=[query])
        docs = await loader.aload()
        return docs

    def _run(
        self, url: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool."""
        # nltk.download('punkt')
        output=""
        try:
            if (url.endswith(".pdf")):
                loader = PyPDFLoader(url)
                docs = loader.load_and_split()
            else:
                # # 只能加载html，不能渲染js
                # loader = WebBaseLoader(query)
                # docs = loader.load()
                
                # 可以渲染js，会带html标签
                # loader = AsyncChromiumLoader([query])
                # docs = loader.load()
                
                # 可以渲染js，并会去掉html标签
                # docs = asyncio.run(self.my_async_function(query))

                # 可以渲染js，并会去掉html标签
                loader = SeleniumURLLoader([url])
                docs = loader.load()
                if (len(docs[0].page_content) == 0):
                    logger.error("SummaryWebpage load url with SeleniumURLLoader failed, retry with WebBaseLoader")
                    loader = WebBaseLoader(url)
                    docs = loader.load()

            # prompt_template = """Write a concise summary of the following:
            # {text}
            # CONCISE SUMMARY:"""
            prompt_template = """根据以下内容写一段总结:
            {text}
            总结:"""
            prompt = PromptTemplate.from_template(prompt_template)

            refine_template = (
                "Your job is to produce a final summary with Chinese.\n"
                "We have provided an existing summary up to a certain point: {existing_answer}\n"
                "We have the opportunity to refine the existing summary"
                "(only if needed) with some more context below.\n"
                "------------\n"
                "{text}\n"
                "------------\n"
                "Given the new context, refine the original summary in Italian"
                "If the context isn't useful, return the original summary."
            )
            refine_prompt = PromptTemplate.from_template(refine_template)
            api_key = config.get("/gpt_tool/sumary_openai_api_key")
            api_base = config.get('/gpt_tool/sumary_openai_api_base')
            llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo-16k", openai_api_key=api_key, openai_api_base=api_base)
            chain = load_summarize_chain(
                llm=llm,
                chain_type="refine",
                question_prompt=prompt,
                refine_prompt=refine_prompt,
                return_intermediate_steps=True,
                input_key="input_documents",
                output_key="output_text",
            )
            result = chain({"input_documents": docs}, return_only_outputs=True)
            output = result["output_text"]
        except Exception as e:
            output = ("SummaryWebpage failed to response for %s, %s", url, e)
            logger.error(output)

        return output

class Browser(BaseTool):
    name = "Browser"
    description = "useful when you need to load a web page, this tool returns the content of webpage."
    args_schema: Type[BaseModel] = ToolInputSchema

    def _run(
        self, url: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool."""
        # nltk.download('punkt')
        output=""
        try:
            if (url.endswith(".pdf")):
                loader = PyPDFLoader(url)
                docs = loader.load_and_split()
            else:
                # # 只能加载html，不能渲染js
                # loader = WebBaseLoader(query)
                # docs = loader.load()
                
                # 可以渲染js，会带html标签
                # loader = AsyncChromiumLoader([query])
                # docs = loader.load()
                
                # 可以渲染js，并会去掉html标签
                # docs = asyncio.run(self.my_async_function(query))

                # 可以渲染js，并会去掉html标签
                loader = SeleniumURLLoader([url])
                docs = loader.load()
                if (len(docs[0].page_content) == 0):
                    logger.error("SummaryWebpage load url with SeleniumURLLoader failed, retry with WebBaseLoader")
                    loader = WebBaseLoader(url)
                    docs = loader.load()

            return docs[0]
        except Exception as e:
            output = ("Browser failed to response for %s, %s", url, e)
            logger.error(output)

        return output
