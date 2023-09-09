# prompt template + STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION Agent + memory
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain import OpenAI, LLMChain
from langchain.agents import ZeroShotAgent, Tool, AgentExecutor
from langchain.agents import load_tools
from langchain.agents import initialize_agent
from langchain.agents import AgentType
from langchain.tools import BaseTool, StructuredTool, Tool, tool
import os
from robot import config
from robot import logging
from langchain.callbacks import ArgillaCallbackHandler, StdOutCallbackHandler
import langchain
from duckduckgo_search import DDGS
from itertools import islice
from datetime import datetime

langchain.debug = True

OPENAI_API_KEY = config.get("/openai/openai_api_key")
if(OPENAI_API_KEY):
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

SERPAPI_API_KEY = config.get("/gpt_tool/SERPAPI_API_KEY")
if(SERPAPI_API_KEY):
    os.environ["SERPAPI_API_KEY"] = SERPAPI_API_KEY
    SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")


logger = logging.getLogger(__name__)

from langchain.prompts.chat import (
    PromptTemplate,
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.memory import ConversationBufferMemory
from langchain.prompts import MessagesPlaceholder
import requests
import json
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
        
        
    def init_agent(self,prefix=""):

        # tools = load_tools(["serpapi", "llm-math"], llm=self.llm)
        tools = load_tools(["ddg-search", "llm-math"], llm=self.llm)

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

        prefix = f"""{prefix}\nOnce you have provided the final answer, the conversation should end immediately.Do not include any URLs in your responses. You have access to the following tools:"""
        suffix = """Begin!"

        ChatHistory:{chat_history}
        Question: {input}
        {agent_scratchpad}"""

        prompt = ZeroShotAgent.create_prompt(
            tools,
            prefix=prefix,
            suffix=suffix,
            input_variables=["input", "chat_history", "agent_scratchpad"],
        )
        self.memory = ConversationBufferMemory(memory_key="chat_history")

        llm_chain = LLMChain(llm=self.llm,prompt=prompt)
        self.agent = ZeroShotAgent(llm_chain=llm_chain, tools=tools, verbose=True)
        self.agent_chain = AgentExecutor.from_agent_and_tools(
            agent=self.agent, tools=tools, verbose=True, memory=self.memory
        )

        # langchain有bug，得用这个才能开启完整的llm调试日志
        self.agent_chain.agent.llm_chain.verbose=True        


    def chat(self, texts, parsed):
        """
        使用OpenAI机器人聊天

        Arguments:
        texts -- user input, typically speech, to be parsed by a module
        """
        
        try:
            respond = self.agent_chain.run(input=texts)
            logger.info("gpt chat result:" + respond)
            return respond
        # except self.openai.error.InvalidRequestError:
        #     logger.warning("token超出长度限制，丢弃历史会话")
        #     self.memory.clear()
        #     return self.chat(texts, parsed)
        
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
        