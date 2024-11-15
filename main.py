import functools
import operator
from typing import Annotated, Sequence, TypedDict

from colorama import Fore, Style
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.output_parsers.openai_functions import JsonOutputFunctionsParser
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from setup_environment import set_environment_variables
from tools import (
    run_analysis,
    run_prefetch_collection,
    run_event_log_collection,
    run_save,
    run_search,
    run_visualization,
    TEAM_SUPERVISOR_SYSTEM_PROMPT,
    DATA_COLLECTION_PREFETCH_AGENT_SYSTEM_PROMPT,
    DATA_COLLECTION_EVENT_LOG_AGENT_SYSTEM_PROMPT,
    DATA_SAVE_AGENT_SYSTEM_PROMPT,
    DATA_SEARCH_AGENT_SYSTEM_PROMPT,
    DATA_VISUALIZATION_AGENT_SYSTEM_PROMPT,
    DATA_ANALYSIS_AGENT_SYSTEM_PROMPT,
)

set_environment_variables("Multi_Agent_Forensic")

TEAM_SUPERVISOR = "team_supervisor"

DATA_COLLECTION_PREFETCH_AGENT='data_collection_prefetch_agent'
DATA_COLLECTION_EVENT_LOG_AGENT='data_collection_EVENT_LOG_agent'
DATA_SAVE_AGENT='data_save_agent'
DATA_SEARCH_AGENT='data_search_agent'
DATA_ANALYSIS_AGENT='data_analysis_agent'
DATA_VISUALIZATION_AGENT='data_visualization_agent'

MEMBERS = [
    DATA_COLLECTION_PREFETCH_AGENT,
    DATA_COLLECTION_EVENT_LOG_AGENT,
    DATA_SAVE_AGENT,
    DATA_SEARCH_AGENT,
    DATA_ANALYSIS_AGENT
]
OPTIONS = ["FINISH"] + MEMBERS

LLM = ChatOpenAI(model="gpt-3.5-turbo-0125")

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next: str

def create_agent(llm: BaseChatModel, tools: list, system_prompt: str):
    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="messages"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )
    agent = create_openai_tools_agent(llm, tools, prompt_template)
    agent_executor = AgentExecutor(agent=agent, tools=tools)  # type: ignore
    return agent_executor

def agent_node(state, agent, name):
    result = agent.invoke(state)
    return {"messages": [HumanMessage(content=result["output"], name=name)]}

router_function_def = {
    "name": "route",
    "description": "Select the next role.",
    "parameters": {
        "title": "routeSchema",
        "type": "object",
        "properties": {
            "next": {
                "title": "next",
                "anyOf": [
                    {"enum": OPTIONS},
                ],
            }
        },
        "required": ["next"],
    },
}

team_supervisor_prompt_template = ChatPromptTemplate.from_messages(
    [
        ("system", TEAM_SUPERVISOR_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
        (
            "system",
            "Given the conversation above, who should act next?"
            " Or should we FINISH? Select one of: {options}",
        ),
    ]
).partial(options=", ".join(OPTIONS), members=", ".join(MEMBERS))

team_supervisor_chain = (
    team_supervisor_prompt_template
    | LLM.bind_functions(functions=[router_function_def], function_call="route")
    | JsonOutputFunctionsParser()
)

data_collection_agent = create_agent(LLM, [run_prefetch_collection], DATA_COLLECTION_PREFETCH_AGENT_SYSTEM_PROMPT)
data_collection_agent_node = functools.partial(agent_node, agent=data_collection_agent, name=DATA_COLLECTION_PREFETCH_AGENT)

data_collection_agent = create_agent(LLM, [run_event_log_collection], DATA_COLLECTION_EVENT_LOG_AGENT_SYSTEM_PROMPT)
data_collection_agent_node = functools.partial(agent_node, agent=data_collection_agent, name=DATA_COLLECTION_EVENT_LOG_AGENT)

data_save_agent = create_agent(LLM, [run_save], DATA_SAVE_AGENT_SYSTEM_PROMPT)
data_save_agent_node = functools.partial(agent_node, agent=data_save_agent, name=DATA_SAVE_AGENT)

data_search_agent = create_agent(LLM, [run_search], DATA_SEARCH_AGENT_SYSTEM_PROMPT)
data_search_agent_node = functools.partial(agent_node, agent=data_search_agent, name=DATA_SEARCH_AGENT)

data_visualization_agent = create_agent(LLM, [run_visualization], DATA_VISUALIZATION_AGENT_SYSTEM_PROMPT)
data_visualization_agent_node = functools.partial(agent_node, agent=data_visualization_agent, name=DATA_VISUALIZATION_AGENT)

data_analysis_agent = create_agent(LLM, [run_analysis], DATA_ANALYSIS_AGENT_SYSTEM_PROMPT)
data_analysis_agent_node = functools.partial(agent_node, agent=data_analysis_agent, name=DATA_ANALYSIS_AGENT)

workflow = StateGraph(AgentState)
workflow.add_node(DATA_COLLECTION_PREFETCH_AGENT, data_collection_agent_node)
workflow.add_node(DATA_COLLECTION_EVENT_LOG_AGENT, data_collection_agent_node)
workflow.add_node(DATA_SAVE_AGENT, data_save_agent_node)
workflow.add_node(DATA_SEARCH_AGENT, data_search_agent_node)
workflow.add_node(DATA_VISUALIZATION_AGENT, data_visualization_agent_node)
workflow.add_node(DATA_ANALYSIS_AGENT, data_analysis_agent_node)
workflow.add_node(TEAM_SUPERVISOR, team_supervisor_chain)

for member in MEMBERS:
    workflow.add_edge(member, TEAM_SUPERVISOR)

workflow.add_edge(DATA_VISUALIZATION_AGENT, END)

conditional_map = {name: name for name in MEMBERS}
conditional_map["FINISH"] = DATA_VISUALIZATION_AGENT
workflow.add_conditional_edges(
    TEAM_SUPERVISOR, lambda x: x["next"], conditional_map
)

workflow.set_entry_point(TEAM_SUPERVISOR)

travel_agent_graph = workflow.compile()

for chunk in travel_agent_graph.stream(
    {"messages": [HumanMessage(content="I want to go to Paris for three days")]}
):
    if "__end__" not in chunk:
        print(chunk)
        print(f"{Fore.GREEN}#############################{Style.RESET_ALL}")