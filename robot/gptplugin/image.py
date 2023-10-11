import os
from typing import Optional, Type
from langchain import OpenAI

from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from langchain.utilities.dalle_image_generator import DallEAPIWrapper
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI

from robot import config, logging

logger = logging.getLogger(__name__)
class ToolInputSchema(BaseModel):
    prompt: str = Field(description="For image descriptions, use multiple phrases to summarize the entity")

class DrawImage(BaseTool):
    name = "DrawImage"
    description = "Generate image by text description."
    args_schema: Type[BaseModel] = ToolInputSchema

    def _run(
        self, prompt: str = None, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        result = [
            {"url": f"https://image.pollinations.ai/prompt/{prompt}"},
            # {"url": f"https://images.unsplash.com/{prompt}"},
            ]
        return result
        # api_key = config.get("/gpt_tool/sumary_openai_api_key")
        # llm = OpenAI(temperature=0.9, openai_api_key=api_key)
        # prompt = PromptTemplate(
        #     input_variables=["image_desc"],
        #     template="Generate a detailed prompt to generate an image based on the following description: {image_desc}",
        # )
        # chain = LLMChain(llm=llm, prompt=prompt)
        # image_desc = chain.run(prompt)
        # logger.info("DrawImage image_desc: {}".format(image_desc))
        # image_url = DallEAPIWrapper(openai_api_key=api_key).run(image_desc)

        # return image_url