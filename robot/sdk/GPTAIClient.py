# prompt template + STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION Agent + memory
import os
from datetime import datetime, timedelta
from itertools import islice
import langchain
from duckduckgo_search import DDGS
from langchain.chat_models import ChatOpenAI
import openai
from langchain.agents import (AgentType, Tool, initialize_agent, load_tools)
from langchain.memory import ConversationBufferMemory
from langchain.tools import Tool, tool
from langchain.utilities import SerpAPIWrapper

from robot import config, logging
from robot.gptplugin.volume import VolumeControl
from robot.gptplugin.weather import Weather
import json
import requests

langchain.debug = True

OPENAI_API_KEY = config.get("/openai/openai_api_key")
if(OPENAI_API_KEY):
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

SERPAPI_API_KEY = config.get("/gpt_tool/SERPAPI_API_KEY")
if(SERPAPI_API_KEY):
    os.environ["SERPAPI_API_KEY"] = SERPAPI_API_KEY
    SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

BING_SUBSCRIPTION_KEY = config.get("/gpt_tool/BING_SUBSCRIPTION_KEY")
if(BING_SUBSCRIPTION_KEY):
    os.environ["BING_SUBSCRIPTION_KEY"] = BING_SUBSCRIPTION_KEY

BING_SEARCH_URL = config.get("/gpt_tool/BING_SEARCH_URL")
if(BING_SEARCH_URL):
    os.environ["BING_SEARCH_URL"] = BING_SEARCH_URL


logger = logging.getLogger(__name__)

context_expiration = config.get("/gpt_tool/context_expiration",600)
class GPTAgent():

    def __init__(
        self,
        model,
        temperature,
        max_tokens,
        top_p,
        frequency_penalty,
        presence_penalty,
        prefix="",
        api_base="",
    ):
        """
        OpenAI机器人
        """

        self.llm=ChatOpenAI(model=model,temperature=temperature,openai_api_base=api_base,verbose=True)
        self.prefix = prefix
        self.init_agent(prefix = self.prefix)
        self.last_chat_time = None
        
    # use chat_conversation_agent
    # https://python.langchain.com/docs/modules/agents/agent_types/chat_conversation_agent
    def init_agent(self,prefix=""):

        # tools = load_tools(["serpapi", "llm-math"], llm=self.llm)
        # tools = load_tools(["ddg-search", "llm-math"], llm=self.llm)
        tools = load_tools(["bing-search", "llm-math"], llm=self.llm)
        tools.append(VolumeControl())
        tools.append(Weather())

        tools.append(
            Tool.from_function(
                func=self.get_information,
                name="get_information",
                description="useful when you need information about current datetime/user name/user city."
            )
        )

        tools.append(
            Tool.from_function(
                func=self.reset_conversation,
                name="reset_conversation",
                description="useful when user want to reset conversation or clear chat history."
            )
        )

        if (config.get("/gpt_tool/hass/enable")):
            tools.append(
                Tool.from_function(
                    func=self.control_device,
                    name="control_device",
                    description="useful when you need to control smart device. The input is a command that can be given to the Xiaoai speaker, for example: 主卧开灯."
                )
            )

        PREFIX = f"""{prefix}Assistant is a large language model trained by OpenAI.

Assistant is designed to be able to assist with a wide range of tasks, from answering simple questions to providing in-depth explanations and discussions on a wide range of topics. As a language model, Assistant is able to generate human-like text based on the input it receives, allowing it to engage in natural-sounding conversations and provide responses that are coherent and relevant to the topic at hand.

Assistant is constantly learning and improving, and its capabilities are constantly evolving. It is able to process and understand large amounts of text, and can use this knowledge to provide accurate and informative responses to a wide range of questions. Additionally, Assistant is able to generate its own text based on the input it receives, allowing it to engage in discussions and provide explanations and descriptions on a wide range of topics.

Overall, Assistant is a powerful system that can help with a wide range of tasks and provide valuable insights and information on a wide range of topics. Whether you need help with a specific question or just want to have a conversation about a particular topic, Assistant is here to assist."""

        self.memory = ConversationBufferMemory(memory_key="chat_history",return_messages=True)
        # self.agent_chain = initialize_agent(tools, self.llm, agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION, verbose=True, memory=self.memory)
        self.agent_chain = initialize_agent(tools, self.llm, agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION, verbose=True, memory=self.memory,
                                            agent_kwargs={'prefix':PREFIX}
                                            )

        # langchain有bug，得用这个才能开启完整的llm调试日志
        self.agent_chain.agent.llm_chain.verbose=True      

    def chat(self, texts):

        # 如果上一次聊天超过一段时间了，则清空张上下文，减少token消耗
        current_time = datetime.now()
        if (self.last_chat_time is not None):
            time_difference = current_time - self.last_chat_time
            if time_difference > timedelta(seconds=context_expiration):
                self.reset_conversation()

        self.last_chat_time = current_time
        
        try:
            respond = self.agent_chain.run(input=texts)
            logger.info("gpt chat result:" + respond)
            return respond
        except openai.error.InvalidRequestError as e:
            import traceback
            traceback.print_exc()
            logger.critical("openai robot failed to response for %r", texts, exc_info=True)
            logger.warning("token超出长度限制，丢弃历史会话")
            # self.memory.clear()
            # return self.chat(texts, parsed)
            return "抱歉，Token长度超了。"
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.critical(
                "openai robot failed to response for %r", texts, exc_info=True
            )
            return "抱歉，OpenAI 回答失败"
        
    def google_search_simple(self, query):
        results = []
        with DDGS() as ddgs:
            ddgs_gen = ddgs.text(query, backend="lite")
            for r in islice(ddgs_gen, 10):
                results.append({
                    "title": r["title"],
                    "link": r["href"],
                    "snippet": r["body"]
                })
        return str(results)
    
    def get_information(self, query):
        """get information about current datetime/user name/user city."""
        now = datetime.now()
        city = "深圳"
        name = "小彬"
        data = {
            "datetime": str(now),
            "user city": city,
            "user name": name
        }
        result = json.dumps(data)

        return f"这是我的个人信息。{result}。"

        results = []
        with DDGS() as ddgs:
            ddgs_gen = ddgs.text(query, backend="lite")
            for r in islice(ddgs_gen, 10):
                results.append({
                    "title": r["title"],
                    "link": r["href"],
                    "snippet": r["body"]
                })
        return str(results)
    
    def control_device(self, command: str) -> str:
        """useful when you need to control smart device. The input is a command that can be given to the Xiaoai speaker, for example: 主卧开灯."""
        logger.info("control_device command=" + command)
        # 通过小爱音箱调用Home Assistant控制设备，这样不需要一个配置设备
        # Home Assistant的URL，例如：http://localhost:8123
        # Home Assistant rest api介绍：https://developers.home-assistant.io/docs/api/rest/
        base_url = config.get("/gpt_tool/hass/url","")
        token = config.get("/gpt_tool/hass/key","")

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
        
        logger.info("命令执行成功。：" + command + ",result=" + response.text)
        
        return "执行成功."

    def reset_conversation(self,input="") -> str:
        '''
        useful when user want to reset conversation or clear chat history.
        '''
        logger.info("reset_conversation")
        self.init_agent(self.prefix)
        return "执行成功。"
        