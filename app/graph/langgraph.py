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
from tools import run_analysis, run_visualization, TEAM_SUPERVISOR_SYSTEM_PROMPT, FORENSIC_AGENT_SYSTEM_PROMPT, VISUALIZER_SYSTEM_PROMPT
import json

class MultiAgentForensic:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.json_loaded_data = self.load_data()
        set_environment_variables("Multi_Agent_Forensic")
        
        self.agents = {
            'team_supervisor': 'team_supervisor',
            'data_analysis_agent': 'data_analysis_agent',
            'data_visualization_agent': 'data_visualization_agent',
        }
        
        self.options = ["FINISH"] + list(self.agents.values())
        self.llm = ChatOpenAI(model="gpt-4o-mini")
        self.workflow = StateGraph(self.AgentState)

        self.create_agents()
        self.setup_workflow()

    def load_data(self):
        with open(self.file_path, "r") as f:
            return json.dumps(json.load(f))

    class AgentState(TypedDict):
        messages: Annotated[Sequence[BaseMessage], operator.add]
        next: str

    def create_agent(self, name: str, tools: list, system_prompt: str, data: json = None):
        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="messages"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        ).partial(json_loaded_data=data) if data else prompt_template
        
        agent = create_openai_tools_agent(self.llm, tools, prompt_template)
        return AgentExecutor(agent=agent, tools=tools)  # type: ignore

    def create_agents(self):
        self.data_analysis_agent = self.create_agent(
            self.agents['data_analysis_agent'],
            [run_analysis],
            FORENSIC_AGENT_SYSTEM_PROMPT,
            self.json_loaded_data
        )
        
        self.data_visualization_agent = self.create_agent(
            self.agents['data_visualization_agent'],
            [run_visualization],
            VISUALIZER_SYSTEM_PROMPT
        )

    def setup_workflow(self):
        self.workflow.add_node(self.agents['data_visualization_agent'], functools.partial(self.agent_node, agent=self.data_visualization_agent, name=self.agents['data_visualization_agent']))
        self.workflow.add_node(self.agents['data_analysis_agent'], functools.partial(self.agent_node, agent=self.data_analysis_agent, name=self.agents['data_analysis_agent']))
        
        # Setup team supervisor
        team_supervisor_chain = self.create_team_supervisor_chain()
        self.workflow.add_node(self.agents['team_supervisor'], team_supervisor_chain)
        
        # Define edges
        self.workflow.add_edge(self.agents['data_analysis_agent'], self.agents['team_supervisor'])
        self.workflow.add_edge(self.agents['data_visualization_agent'], self.agents['team_supervisor'])
        self.workflow.add_edge(self.agents['data_visualization_agent'], END)
        
        # Conditional edges
        conditional_map = {name: name for name in self.agents.values()}
        conditional_map["FINISH"] = END
        self.workflow.add_conditional_edges(
            self.agents['team_supervisor'],
            lambda x: self.debug_return_next(x),
            conditional_map
        )
        
        self.workflow.set_entry_point(self.agents['team_supervisor'])
        self.my_agent_graph = self.workflow.compile()

    def create_team_supervisor_chain(self):
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
        ).partial(options=", ".join(self.options), members=", ".join(self.agents.values()))

        team_supervisor_chain = (
            team_supervisor_prompt_template
            | self.llm.bind_functions(functions=[self.router_function_def()], function_call="route")
            | JsonOutputFunctionsParser()
        )
        return team_supervisor_chain

    def router_function_def(self):
        return {
            "name": "route",
            "description": "Select the next role.",
            "parameters": {
                "title": "routeSchema",
                "type": "object",
                "properties": {
                    "next": {
                        "title": "next",
                        "anyOf": [
                            {"enum": self.options},
                        ],
                    }
                },
                "required": ["next"],
            },
        }

    def agent_node(self, state, agent, name):
        result = agent.invoke(state)
        return {"messages": [HumanMessage(content=result["output"], name=name)]}

    async def async_agent_node(self, state: AgentState, agent, name):
        result = await agent.ainvoke(state)
        return {"messages": [HumanMessage(content=result["output"], name=name)]}

    def debug_return_next(self, x):
        print("Returned next value:", x["next"])  # 디버깅 출력
        return x["next"]  # 원래 반환값 그대로 리턴

    def run(self, initial_message: str):
        for chunk in self.my_agent_graph.stream({"messages": [HumanMessage(content=initial_message)]}):
            if "__end__" in chunk:
                print("Process finished!")
                break  # 종료 상태에 도달하면 반복 종료
            else:
                print(chunk)
                print(f"{Fore.GREEN}#############################{Style.RESET_ALL}")

