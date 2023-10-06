import json
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from io import StringIO
from itertools import islice
from traceback import print_stack
from typing import Any, Dict, List, Optional
from uuid import UUID

import langchain
import openai
import requests
from duckduckgo_search import DDGS
from langchain.agents import AgentExecutor, Tool, load_tools
from langchain.agents.format_scratchpad import format_log_to_str
from langchain.agents.output_parsers import JSONAgentOutputParser
from langchain.callbacks.base import BaseCallbackHandler
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import AgentFinish, LLMResult
from langchain.tools import Tool
from langchain.tools.render import render_text_description_and_args

from robot import config, logging
from robot.gptplugin import prompt as agent_prompt
from robot.gptplugin.news import Hotnews
from robot.gptplugin.search import SummaryWebpage
from robot.gptplugin.stock import Stock
from robot.gptplugin.volume import VolumeControl
from robot.gptplugin.weather import Weather
from robot.gptplugin.device_control import DeviceControl
from robot.gptplugin.image import DrawImage


# langchain.debug = True

SERPAPI_API_KEY = config.get("/gpt_tool/SERPAPI_API_KEY")
if (SERPAPI_API_KEY):
    os.environ["SERPAPI_API_KEY"] = SERPAPI_API_KEY

BING_SUBSCRIPTION_KEY = config.get("/gpt_tool/BING_SUBSCRIPTION_KEY")
if (BING_SUBSCRIPTION_KEY):
    os.environ["BING_SUBSCRIPTION_KEY"] = BING_SUBSCRIPTION_KEY

BING_SEARCH_URL = config.get("/gpt_tool/BING_SEARCH_URL")
if (BING_SEARCH_URL):
    os.environ["BING_SEARCH_URL"] = BING_SEARCH_URL


logger = logging.getLogger(__name__)

context_expiration = config.get("/gpt_tool/context_expiration", 600)


class GPTAgent():

    def __init__(
        self,
        model,
        temperature,
        max_tokens,
        top_p,
        frequency_penalty,
        presence_penalty,
        prefix = "",
        api_base = "",
        api_key = ""
    ):
        """
        OpenAI机器人
        """

        self.prefix = prefix
        self.last_chat_time = None
        self.model = model
        self.temperature = temperature
        self.api_base = api_base
        self.api_key = api_key
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        
        # prefix_template = ChatPromptTemplate.from_messages([("system", self.prefix)])
        # prompt = hub.pull("hwchase17/react-multi-input-json")
        # self.prompt = prefix_template + prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", agent_prompt.SYSTEM),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human",agent_prompt.HUMAN)
            ])

    def init_agent(self, prefix=""):
        self.callback = CustomFinalAnswerCallbackHandler()
        self.llm = ChatOpenAI(model=self.model, temperature=self.temperature,openai_api_key=self.api_key, openai_api_base=self.api_base, verbose=True, streaming=True, callbacks=[self.callback])

        # tools = load_tools(["serpapi", "llm-math"], llm=self.llm)
        # tools = load_tools(["ddg-search", "llm-math"], llm=self.llm)
        tools = load_tools(["bing-search", "llm-math"], llm=self.llm)
        tools.append(SummaryWebpage())
        tools.append(VolumeControl())
        tools.append(Weather())
        tools.append(Hotnews())
        tools.append(Stock())
        tools.append(DrawImage())
        if (config.get("/gpt_tool/hass/enable")):
            tools.append(DeviceControl())

        tools.append(
            Tool.from_function(
                func=self.get_information,
                name="get_information",
                description="get user informations, return user name and user city and current datetime."
            )
        )

        tools.append(
            Tool.from_function(
                func=self.reset_conversation,
                name="reset_conversation",
                description="useful when user want to reset conversation or clear chat history."
            )
        )

        self.prompt = self.prompt.partial(
            prefix=self.prefix,
            tools=render_text_description_and_args(tools),
            tool_names=", ".join([t.name for t in tools]),
        )
        llm_with_stop = self.llm.bind(stop=["Observation"])
        # 注意这里memory的用法，"chat_history": lambda x: self.memory.buffer_as_messages,配合prompt模板里的MessagesPlaceholder(variable_name="chat_history")一起用
        agent = {
            "chat_history": lambda x: self.memory.buffer_as_messages,
            "input": lambda x: x["input"],
            "agent_scratchpad": lambda x: format_log_to_str(x['intermediate_steps']),
        } | self.prompt | llm_with_stop | JSONAgentOutputParser()
        self.agent_executor = AgentExecutor(agent=agent,tools=tools, memory=self.memory,verbose=True,handle_parsing_errors=True,callbacks=[self.callback],max_iterations=15)

        # # 使用CHAT_CONVERSATIONAL_REACT_DESCRIPTION
        # https://python.langchain.com/docs/modules/agents/agent_types/chat_conversation_agent
        # agentType = AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION
        # PREFIX = f"{prefix}{conversational_chat_prompt.PREFIX}"
        # parser = FixConvoOutputParser()
        # self.agent_chain = initialize_agent(
        #     tools,
        #     self.llm,
        #     agent=agentType,
        #     verbose=True,
        #     memory=self.memory,
        #     callbacks=[self.callback],
        #     handle_parsing_errors=True, 
        #     agent_kwargs={
        #         'system_message': PREFIX,
        #         'output_parser': parser,
        #         }
        #     )

        # # 使用STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION
        # agentType = AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION
        # # PREFIX = f"{prefix}{structured_chat_prompt.PREFIX}"
        # self.agent_chain = initialize_agent(
        #     tools,
        #     self.llm,
        #     agent=agentType,
        #     verbose=True,
        #     memory=self.memory,
        #     callbacks=[self.callback],
        #     handle_parsing_errors=True, 
        #     # agent_kwargs={
        #     #     'system_message': PREFIX,
        #     #     }
        #     )

        # OPENAI_MULTI_FUNCTIONS
        # agentType = AgentType.OPENAI_FUNCTIONS
        # PREFIX = f"{prefix}"

        # self.agent_chain = initialize_agent(
        #     tools,
        #     self.llm,
        #     agent=agentType,
        #     verbose=True,
        #     memory=self.memory,
        #     callbacks=[self.callback],
        #     handle_parsing_errors=True, 
        #     system_message=PREFIX
        #     # agent_kwargs={
        #     #     'system_message': PREFIX,
        #     #     # 'output_parser': parser,
        #     #     }
        #     )

    def chat(self, texts):

        self.init_agent(prefix=self.prefix)

        # 如果上一次聊天超过一段时间了，则清空张上下文，减少token消耗
        current_time = datetime.now()
        if (self.last_chat_time is not None):
            time_difference = current_time - self.last_chat_time
            if time_difference > timedelta(seconds=context_expiration):
                self.reset_conversation()

        self.last_chat_time = current_time

        try:
            # respond = self.agent_chain.run(input=texts)
            response = self.agent_executor.invoke({"input":texts})["output"]
            logger.info("gpt chat result:%s",response)
            return response
        except openai.error.InvalidRequestError as e:
            import traceback
            traceback.print_exc()
            logger.critical(
                "openai robot failed to response for %r", texts, exc_info=True)
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

    def stream_chat(self, texts):

        # 如果上一次聊天超过一段时间了，则清空张上下文，减少token消耗
        current_time = datetime.now()
        if (self.last_chat_time is not None):
            time_difference = current_time - self.last_chat_time
            if time_difference > timedelta(seconds=context_expiration):
                self.reset_conversation()

        self.last_chat_time = current_time

        try:
            self.init_agent(prefix=self.prefix)
            # TODO 这里改成协程来调用

            def task():
                try:
                    response = self.agent_executor.invoke({"input":texts})["output"]
                    logger.info("gpt chat result:%s",response)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    logger.error("gpt stream_chat error:%s",e)
                
            thread = threading.Thread(target=task, name="GPT_Agent")
            thread.start()

            def generate():
                self.callback.answer_reached = False
                last_content = ""
                # TODO 这里用sleep性能不好，改成queue或者锁的方式，另外不要一个个字符返回，做些合并，避免换行转义符被断开
                while self.callback.agent_running:
                    time.sleep(0.3)
                    output_content = self.callback.output_queue.getvalue()
                    trimmed_content = output_content.replace(last_content, "")
                    if (len(trimmed_content)):
                        logger.info("gpt stream_chat yield result:" + trimmed_content)
                        last_content = output_content
                        yield trimmed_content

                output_content = self.callback.output_queue.getvalue()
                trimmed_content = output_content.replace(last_content, "")
                if (len(trimmed_content)):
                    logger.info("gpt stream_chat yield result:" +
                                trimmed_content)
                    last_content = output_content
                    yield trimmed_content
                # TODO 如果出错了，这里要兜底返回错误信息

            return generate
        except openai.error.InvalidRequestError as e:
            import traceback
            traceback.print_exc()
            logger.critical(
                "openai robot failed to response for %r", texts, exc_info=True)
            logger.warning("token超出长度限制，丢弃历史会话")
            # self.memory.clear()
            # return self.chat(texts, parsed)

            def generate():
                yield "抱歉，Token长度超了。"
            return generate

        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.critical(
                "openai robot failed to response for %r", texts, exc_info=True
            )
            return "抱歉，OpenAI 回答失败"

            def generate():
                yield "抱歉，OpenAI 回答失败。"
            return generate

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

    def get_information(self, query:str = None):
        """get information about current datetime/user name/user city."""
        now = datetime.now()
        city = "深圳"
        name = "小彬"
        data = {
            "datetime": str(now),
            "user city": city,
            "user name": name
        }
        result = json.dumps(data, ensure_ascii=False)

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


    def reset_conversation(self, input="") -> str:
        '''
        useful when user want to reset conversation or clear chat history.
        '''
        logger.info("reset_conversation")
        self.memory.clear()

        return "执行成功。"


# # Define a class that parses output for conversational agents
# class FixConvoOutputParser(AgentOutputParser):
#     """Output parser for the conversational agent."""

#     def get_format_instructions(self) -> str:
#         """Returns formatting instructions for the given output parser."""
#         return FORMAT_INSTRUCTIONS

#     def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
#         """Attempts to parse the given text into an AgentAction or AgentFinish.

#         Raises:
#              OutputPar·serException if parsing fails.
#         """
#         try:
#             # Attempt to parse the text into a structured format (assumed to be JSON
#             # stored as markdown)
#             response = parse_json_markdown(text)

#             # If the response contains an 'action' and 'action_input'
#             if "action" in response and "action_input" in response:
#                 action, action_input = response["action"], response["action_input"]

#                 # If the action indicates a final answer, return an AgentFinish
#                 if action == "Final Answer":
#                     return AgentFinish({"output": action_input}, text)
#                 else:
#                     # Otherwise, return an AgentAction with the specified action and
#                     # input
#                     return AgentAction(action, action_input, text)
#             else:
#                 # # If the necessary keys aren't present in the response, raise an
#                 # # exception
#                 # raise OutputParserException(
#                 #     f"Missing 'action' or 'action_input' in LLM output: {text}"
#                 # )
#                 # GPT 3.5 经常不会正确返回json，兼容下
#                 logger.error(
#                     "parse error, gpt does not response json formate. text=" + text)
#                 return AgentFinish({"output": text}, text)
#         except Exception as e:
#             # # If any other exception is raised during parsing, also raise an
#             # # OutputParserException
#             # raise OutputParserException(f"Could not parse LLM output: {text}") from e
#             logger.error(
#                 "parse error, gpt does not response json formate. text=" + text)
#             return AgentFinish({"output": text}, text)

#     @property
#     def _type(self) -> str:
#         return "conversational_chat"


"""Callback Handler streams to stdout on new llm token."""
DEFAULT_ANSWER_PREFIX_TOKENS = '''
"action":"FinalAnswer","action_input":"
'''
class CustomFinalAnswerCallbackHandler(BaseCallbackHandler):
    def __init__(
        self,
        answer_prefix_tokens: Optional[str] = None
    ) -> None:
        """Instantiate FinalStreamingStdOutCallbackHandler.

        Args:
            answer_prefix_tokens: Token sequence that prefixes the answer.
        """
        super().__init__()
        if answer_prefix_tokens is None:
            self.answer_prefix_tokens = DEFAULT_ANSWER_PREFIX_TOKENS
        else:
            self.answer_prefix_tokens = answer_prefix_tokens

        self.answer_prefix_tokens = self.answer_prefix_tokens.strip()
        self.last_tokens = ""
        self.answer_reached = False
        self.output_queue = StringIO()
        self.answer_ended = False
        self.agent_running = True

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Run when LLM starts running."""
        self.answer_reached = False
        self.answer_ended = False
        self.output_queue = StringIO()
        self.last_tokens = ""


    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when LLM ends running."""

    def check_if_answer_reached(self) -> bool:
        if self.last_tokens.endswith(self.answer_prefix_tokens):
            return True
        else:
            return False

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Run on new LLM token. Only available when streaming is enabled."""

        self.last_tokens += (token.strip())

        # print(token)
        if self.check_if_answer_reached():
            self.answer_reached = True
            return

        if self.answer_reached and (not self.answer_ended):
            # 把转义的双引号去掉之后，判断是否有json双引号结束符
            if "\"" in token.replace("\\\"", ""):
                self.answer_ended = True
                # 把引号前面的正文部分读取出来
                for i in range(len(token)):
                    if token[i] == "\"" and (i == 0 or token[i-1] != "\\"):
                        token = token[:i]
                        break            
            self.output_queue.write(token)
            self.output_queue.flush()


    def on_agent_finish(self, finish: AgentFinish, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any) -> Any:
        # 如果之前没有解析到response，说明出错了，这里把结果设置回去，让外部能读取到
        logger.info("on_agent_finish finish=%s",finish)
        if not self.answer_ended:
            if(self.output_queue.getvalue() != finish.return_values["output"]):
                self.output_queue.truncate(0)
                self.output_queue.write(finish.return_values["output"])
        self.agent_running = False
        return super().on_agent_finish(finish, run_id=run_id, parent_run_id=parent_run_id, **kwargs)

    def on_chain_error(self, error: Exception | KeyboardInterrupt, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any) -> Any:
        logger.error("on_chain_error error=%s",error)
        if not self.answer_ended:
            self.output_queue.write(str(error))
        self.agent_running = False
        return super().on_chain_error(error, run_id=run_id, parent_run_id=parent_run_id, **kwargs)

    def on_chain_end(self, outputs: Dict[str, Any], *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any) -> Any:
        return super().on_chain_end(outputs, run_id=run_id, parent_run_id=parent_run_id, **kwargs)

    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], *, run_id: UUID, parent_run_id: UUID | None = None, tags: List[str] | None = None, metadata: Dict[str, Any] | None = None, **kwargs: Any) -> Any:
        return super().on_chain_start(serialized, inputs, run_id=run_id, parent_run_id=parent_run_id, tags=tags, metadata=metadata, **kwargs)
