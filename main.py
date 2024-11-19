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
    run_visualization,
    TEAM_SUPERVISOR_SYSTEM_PROMPT,
    FORENSIC_AGENT_SYSTEM_PROMPT,
    VISUALIZER_SYSTEM_PROMPT
)

import json
file_path = './all_logs.json'

with open(file_path, "r") as f:
    json_loaded_data = json.load(f)
    json_loaded_data = json.dumps(json_loaded_data)

# 환경 변수 설정
set_environment_variables("Multi_Agent_Forensic")

# 에이전트 이름 정의
TEAM_SUPERVISOR = 'team_supervisor'
DATA_ANALYSIS_AGENT = 'data_analysis_agent'
DATA_VISUALIZATION_AGENT = 'data_visualization_agent'

# 에이전트 목록 및 옵션 정의
MEMBERS = [
    DATA_ANALYSIS_AGENT,
    DATA_VISUALIZATION_AGENT
]
OPTIONS = ["FINISH"] + MEMBERS

# 언어 모델 초기화
LLM = ChatOpenAI(model="gpt-4o-mini")

# 에이전트 상태 타입 정의
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next: str

# 에이전트 생성 함수
def create_agent(llm: BaseChatModel, tools: list, system_prompt: str, data: json = None):
    if data:
        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="messages"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        ).partial(json_loaded_data=data)
    else:
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

# 에이전트 노드 처리 함수
def agent_node(state, agent, name):
    result = agent.invoke(state)
    return {"messages": [HumanMessage(content=result["output"], name=name)]}

async def async_agent_node(state: AgentState, agent, name):
    result = await agent.ainvoke(state)
    return {"messages": [HumanMessage(content=result["output"], name=name)]}

# 라우터 함수 정의
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

# 팀 감독자 프롬프트 템플릿 정의
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

# 팀 감독자 체인 정의
team_supervisor_chain = (
    team_supervisor_prompt_template
    | LLM.bind_functions(functions=[router_function_def], function_call="route")
    | JsonOutputFunctionsParser()
)

# 각 에이전트 생성
data_analysis_agent = create_agent(LLM, [run_analysis], FORENSIC_AGENT_SYSTEM_PROMPT, json_loaded_data)
data_analysis_agent_node = functools.partial(agent_node, agent=data_analysis_agent, name=DATA_ANALYSIS_AGENT)

data_visualization_agent = create_agent(LLM, [run_visualization], VISUALIZER_SYSTEM_PROMPT)
data_visualization_agent_node = functools.partial(agent_node, agent=data_visualization_agent, name=DATA_VISUALIZATION_AGENT)

# 상태 그래프 생성
workflow = StateGraph(AgentState)

# 나머지 에이전트 추가
workflow.add_node(DATA_VISUALIZATION_AGENT, data_visualization_agent_node)
workflow.add_node(DATA_ANALYSIS_AGENT, data_analysis_agent_node)
workflow.add_node(TEAM_SUPERVISOR, team_supervisor_chain)

# # 각 시작 노드에서 나머지 노드로 연결 설정
# workflow.add_edge(DATA_ANALYSIS_AGENT, DATA_VISUALIZATION_AGENT)

# 팀 감독자 연결 설정
workflow.add_edge(DATA_ANALYSIS_AGENT, TEAM_SUPERVISOR)
workflow.add_edge(DATA_VISUALIZATION_AGENT, TEAM_SUPERVISOR)

# 데이터 시각화 에이전트와 종료 노드 연결
workflow.add_edge(DATA_VISUALIZATION_AGENT, END)

# 조건부 엣지 설정
conditional_map = {name: name for name in MEMBERS}
# conditional_map["FINISH"] = DATA_VISUALIZATION_AGENT
conditional_map["FINISH"] = END
workflow.add_conditional_edges(
    TEAM_SUPERVISOR,
    lambda x: debug_return_next(x),  # 디버깅 함수로 변경
    conditional_map
)

# 디버깅 함수 정의
def debug_return_next(x):
    print("Returned next value:", x["next"])  # 반환 값 출력
    return x["next"]  # 원래 반환값 그대로 리턴

workflow.set_entry_point(TEAM_SUPERVISOR)

# 그래프 컴파일
my_agent_graph = workflow.compile()

for chunk in my_agent_graph.stream(
    {"messages": [HumanMessage(content="이벤트 로그 분석해.")]}
):
    if "__end__" in chunk:
        print("Process finished!")
        break  # 종료 상태에 도달하면 반복 종료
    else:
        print(chunk)
        print(f"{Fore.GREEN}#############################{Style.RESET_ALL}")
