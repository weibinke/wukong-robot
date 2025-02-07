import os
import threading
import time
from datetime import datetime, timedelta
from io import StringIO
from typing import Any, Dict, List, Optional
from uuid import UUID

import openai
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import (format_log_to_str,
                                                format_to_openai_functions)
from langchain.agents.output_parsers import (JSONAgentOutputParser,
                                             OpenAIFunctionsAgentOutputParser)
from langchain.callbacks.base import BaseCallbackHandler
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import AgentFinish, LLMResult
from langchain.tools.render import (format_tool_to_openai_function,
                                    render_text_description_and_args)
from langfuse.callback import CallbackHandler

from robot import config, logging
from robot.gptplugin import prompt as agent_prompt
from robot.gptplugin.device_control import DeviceControl, DeviceStatus
from robot.gptplugin.image import DrawImage
from robot.gptplugin.information import Information
from robot.gptplugin.news import Hotnews, Hotnews_vvhan
from robot.gptplugin.reset_conversation import ResetConversation
from robot.gptplugin.search import BingSearchTool, Browser, SummaryWebpage
from robot.gptplugin.stock import Stock
from robot.gptplugin.volume import VolumeControl
from robot.gptplugin.weather import Weather

# langchain.debug = True

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
        if self.api_base:
            os.environ["OPENAI_API_BASE"] = api_base
            openai.api_base = api_base # 有些组件不支持设置openai_api_base，通过这个规避下

        self.api_key = api_key
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        
        tools = []
        tools.append(BingSearchTool())
        tools.append(Browser())
        tools.append(SummaryWebpage())
        tools.append(VolumeControl())
        tools.append(DeviceStatus())
        tools.append(Weather())
        tools.append(Hotnews_vvhan())
        tools.append(Hotnews())
        tools.append(Stock())
        tools.append(DrawImage())
        tools.append(Information())
        tools.append(ResetConversation(memory=self.memory))
        if (config.get("/gpt_tool/hass/enable")):
            tools.append(DeviceControl())
        self.tools = tools

        self.callbacks = []
        langfuse_public_key = config.get("/gpt_tool/langfuse_public_key")
        langfuse_secret_key = config.get("/gpt_tool/langfuse_secret_key")
        if langfuse_public_key and langfuse_secret_key:
            self.langfuse_handler = CallbackHandler(public_key=langfuse_public_key, secret_key=langfuse_secret_key)

        streaming = False
        if streaming:
            self.callbacks.append(CustomFinalAnswerCallbackHandler())

        self.init_agent()

    def init_agent_opeanai_functions(self):
        '''使用openai function call实现agent'''
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.prefix),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user","{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])

        self.llm = ChatOpenAI(model=self.model, temperature=self.temperature,openai_api_key=self.api_key, openai_api_base=self.api_base, verbose=True, streaming=True, callbacks=self.callbacks)

        llm_with_tools = self.llm.bind(functions=[format_tool_to_openai_function(t) for t in self.tools])
        # 注意这里memory的用法，"chat_history": lambda x: self.memory.buffer_as_messages,配合prompt模板里的MessagesPlaceholder(variable_name="chat_history")一起用
        agent = {
            "chat_history": lambda x: self.memory.buffer_as_messages,
            "input": lambda x: x["input"],
            "agent_scratchpad": lambda x: format_to_openai_functions(x['intermediate_steps']),
        } | self.prompt | llm_with_tools | OpenAIFunctionsAgentOutputParser()
        
        self.agent_executor = AgentExecutor(agent=agent,tools=self.tools, memory=self.memory,verbose=True,handle_parsing_errors=True,callbacks=self.callbacks,max_iterations=15)

    def init_agent_with_react(self):
        '''使用react-multi-input-json实现agent'''
        # prompt = hub.pull("hwchase17/react-multi-input-json")
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", agent_prompt.SYSTEM),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human",agent_prompt.HUMAN)
            ])
        
        self.llm = ChatOpenAI(model=self.model, temperature=self.temperature,openai_api_key=self.api_key, openai_api_base=self.api_base, verbose=True, streaming=True, callbacks=self.callbacks)
        self.prompt = self.prompt.partial(
            prefix=self.prefix,
            tools=render_text_description_and_args(self.tools),
            tool_names=", ".join([t.name for t in self.tools]),
        )
        llm_with_stop = self.llm.bind(stop=["Observation"])
        # 注意这里memory的用法，"chat_history": lambda x: self.memory.buffer_as_messages,配合prompt模板里的MessagesPlaceholder(variable_name="chat_history")一起用
        agent = {
            "chat_history": lambda x: self.memory.buffer_as_messages,
            "input": lambda x: x["input"],
            "agent_scratchpad": lambda x: format_log_to_str(x['intermediate_steps']),
        } | self.prompt | llm_with_stop | JSONAgentOutputParser()
        
        self.agent_executor = AgentExecutor(agent=agent,tools=self.tools, memory=self.memory,verbose=True,handle_parsing_errors=True,callbacks=self.callbacks,max_iterations=15)

    def init_agent(self):
        self.init_agent_opeanai_functions()

    def chat(self, texts):
        # 如果上一次聊天超过一段时间了，则清空张上下文，减少token消耗
        current_time = datetime.now()
        if (self.last_chat_time is not None):
            time_difference = current_time - self.last_chat_time
            if time_difference > timedelta(seconds=context_expiration):
                self.memory.clear()

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
                self.memory.clear()

        self.last_chat_time = current_time

        try:
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
                accumulated_content = ""  # 累积的完整句子 
                while self.callback.agent_running: 
                    time.sleep(0.3) 
                    output_content = self.callback.output_queue.getvalue() 
                    trimmed_content = output_content.replace(last_content, "") 
                    if len(trimmed_content): 
                        accumulated_content += trimmed_content 
                        last_content: str = output_content 
                        if not self.callback.agent_running or any(p in accumulated_content for p in ["\\n", "。", "！", "？", ".", "!", "?"]):  # 判断是否满一句话 
                            logger.debug("gpt stream_chat yield result:" + accumulated_content) 
                            yield accumulated_content 
                            accumulated_content = "" 
                        else:
                            logger.debug("gpt stream_chat not reach line result:" + accumulated_content) 

                output_content = self.callback.output_queue.getvalue() 
                trimmed_content = output_content.replace(last_content, "") 
                if trimmed_content or accumulated_content: 
                    accumulated_content += trimmed_content 
                    logger.debug("gpt stream_chat yield result:" + accumulated_content) 
                    yield accumulated_content 
                    accumulated_content = ""
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

        # logger.debug("on_llm_new_token: %s", token)
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

    def on_agent_finish(
        self,
        finish: AgentFinish,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
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
