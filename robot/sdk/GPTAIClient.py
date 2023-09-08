# prompt template + STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION Agent + memory
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain import OpenAI, LLMChain
from langchain.agents import ZeroShotAgent, Tool, AgentExecutor
from langchain.agents import load_tools
from langchain.agents import initialize_agent
from langchain.agents import AgentType
from langchain.agents import tool
import os
from robot import config
from robot import logging

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

@tool
def control_devie(command: str) -> int:
    """useful when you need to control smart device. The input is a command that can be given to the Xiaoai speaker, for example: 主卧开灯."""
    logger.info("control_devie command=" + command)
    # 通过小爱音箱调用Home Assistant控制设备，这样不需要一个配置设备
    # Home Assistant的URL，例如：http://localhost:8123
    # Home Assistant rest api介绍：https://developers.home-assistant.io/docs/api/rest/
    base_url = config.get("/gpt_tool/hass/url","")
    token = config.get("/gpt_tool/hass/key","")

    '''
    curl \
    -H "Authorization: Bearer xx" \
    -H "Content-Type: application/json" \
    -d '{"entity_id": "light.yeelink_lamp4_1ba3_light"}' \
    http://192.168.3.22:8123/api/services/light/turn_on


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
    
    return "已经执行命令：" + command + ",result=" + response.text

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

        self.llm=ChatOpenAI(model=model,temperature=temperature,api_base=api_base,verbose=True)

        self.tools = load_tools(["serpapi", "llm-math"], llm=self.llm)
        if (config.get("/gpt_tool/hass/enable")):
            self.tools.append(control_devie)

        self.chat_history = MessagesPlaceholder(variable_name="chat_history")
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

        self.agent_chain = initialize_agent(
            self.tools, 
            self.llm, 
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION, 
            verbose=True, 
            memory=self.memory, 
            agent_kwargs = {
                "memory_prompts": [self.chat_history],
                "input_variables": ["input", "agent_scratchpad", "chat_history"]
            }
        )

        # self.agent_chain.run(input="Hi I'm Erica.")
        # self.agent_chain.run(input="whats my name?")

        # response = await agent_chain.arun(input="Hi I'm Erica.")
        # print(response)
        # response = await agent_chain.arun(input="whats my name?")
        # print(response)


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
