from langchain.tools import tool
from pydantic import BaseModel, Field

import bs4
from langchain import hub
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

def lode_data():
    urls = []
    with open('velociraptor_doc_urls.txt', 'r') as file:
        urls = [line.replace('\n', '') for line in file]

    loader = WebBaseLoader(
        web_paths=(
            urls
        ),
        bs_kwargs=dict(
            parse_only=bs4.SoupStrainer(
                'div',
                attrs={'id': ['body-inner']}
            )
        )
    )
    docs = loader.load()


class RunSearchInput(BaseModel):
    image_description: str = Field(
        description="A detailed description of the desired image."
    )

@tool("run_search", args_schema=RunSearchInput)
def run_search(param: str) -> None:
    return

