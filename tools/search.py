from langchain.tools import tool
from pydantic import BaseModel, Field

import bs4
from langchain import hub
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from . import RETRIEVER
MODEL_NAME = 'gpt-4o'
PROMPT = hub.pull('rlm/rag-prompt')

class RunSearchInput(BaseModel):
    question: str = Field(
        description="A detailed description of the desired velociraptor api action."
    )

@tool("run_velociraptor_search", args_schema=RunSearchInput)
def run_search(param: str) -> str:
    query = get_search_response(param.question)
    return query

def get_search_response(question: str) -> str:
    llm = ChatOpenAI(model_name=MODEL_NAME, temperature=0)

    def format_docs(docs):
        return '\n\n'.join(doc.page_content for doc in docs)

    rag_chain = (
        {'context': RETRIEVER | format_docs, 'question': RunnablePassthrough()}
        | PROMPT
        | llm
        | StrOutputParser()
    )

    query = rag_chain.invoke(
        question
    )

    return query

def load_data():
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

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=0
    )

    splits = text_splitter.split_documents(docs)

    vectorstore = FAISS.from_documents(
        documents=splits, embedding=OpenAIEmbeddings()
    )

    retriever = vectorstore.as_retriever()

    return retriever