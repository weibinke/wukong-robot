# Import things that are needed genericallyI
from langchain.tools import BaseTool, StructuredTool, Tool, tool
from typing import Optional, Type
from robot import config, logging
import requests
import json

from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain.document_loaders import WebBaseLoader
from langchain.chat_models import ChatOpenAI

from langchain.chains.llm import LLMChain
from langchain.prompts import PromptTemplate
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.document_loaders import OnlinePDFLoader
from langchain.document_loaders import PyPDFLoader
from langchain.chains.summarize import load_summarize_chain

logger = logging.getLogger(__name__)

class SummaryWebpage(BaseTool):
    name = "Summary Webpage"
    description = "useful when you need to know the overall content of a webpage."

    def _run(
        self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool."""

        if (query.endswith(".pdf")):
            loader = PyPDFLoader(query)
            docs = loader.load_and_split()
        else:
            loader = WebBaseLoader(query)
            docs = loader.load()

        prompt_template = """Write a concise summary of the following:
        {text}
        CONCISE SUMMARY:"""
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
        llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo-16k")
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

        return result["output_text"]
