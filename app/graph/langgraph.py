import functools
import json
from typing import Annotated, Sequence, TypedDict
import operator

from colorama import Fore, Style
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.output_parsers.openai_functions import JsonOutputFunctionsParser
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langchain_core.tools import Tool
from langchain_experimental.utilities import PythonREPL

from app.graph.setup_environment import set_environment_variables

TEAM_SUPERVISOR_SYSTEM_PROMPT = """
You are a supervisor managing agents: {members}. Your goal is to analyze forensic logs and provide insights with a visualization. 

- **Data Analysis Agent**: Analyzes logs to identify suspicious activities, anomalies, and key events, returning a summary.
- **Data Visualization Agent**: Creates visualizations from the analysis, returning the file path to the image.

Ensure the following before finishing:
1. A forensic analysis summary.
2. A visualization file path.

Call the visualizer just once in the whole process. Please don't call the visualizer two or several times.
Once all tasks are complete, respond with FINISH.
"""

FORENSIC_AGENT_SYSTEM_PROMPT = """
You are a forensic analysis assistant specializing in log analysis. Your task is to analyze the provided logs based on their type and generate a forensic summary, along with quantifiable data suitable for visualization.

Inputs:
- `logtype`: Specifies the type of log to analyze (e.g., "prefetch", "Application", "System").
- `json_loaded_data`: Contains the parsed log data.

Instructions:
1. If `logtype` is "prefetch":
   - Analyze the Prefetch log to identify the top 10 most-used applications by usage frequency.
   - Include a ranked list of these applications and their frequencies.

2. If `logtype` is not "prefetch":
   - Analyze Windows Event Logs of type `{logtype}`.
   - Summarize key findings (e.g., event counts, timestamps, anomalies).
   - Provide a breakdown of log types (e.g., Information, Warning, Error) with their occurrence frequencies.

Output:
- A concise forensic summary highlighting key insights and suspicious activities.
- Quantifiable data (e.g., counts, frequencies) formatted for visualization.
- Ensure the output is structured and clear, avoiding any follow-up questions.

logtype: {logtype}
json_loaded_data: {json_loaded_data}
"""

VISUALIZER_SYSTEM_PROMPT = """
You are a visualization assistant specializing in creating graphs from forensic log analysis results. Your task is to use the provided Python functions to generate visualizations based on the given summary and quantifiable data, save the graphs as image files, and return their file paths.

Inputs:
- `analysis_summary`: The summary and quantifiable data from the forensic analysis agent.

Instructions:
1. Extract quantifiable data from `analysis_summary`.
2. Identify suitable graph types (e.g., bar chart, pie chart, timeline) to visualize the data.
3. Write Python code to generate the graphs using the provided functions, and save the images as files (e.g., PNG format).
   - Ensure to call the provided functions to handle graph generation.
4. Save each graph with a descriptive file name and return the file paths in a structured format, such as:
   ['./images/current_timestamp_1.png', './images/current_timestamp_2.png', ...] (current_timestamp means round(time.mktime(datetime.today().timetuple())) in python code)
5. Don't generate multiple images for the same analysis data. Just 2 images is fine.
6. Don't use the function twice or more. JUST ONCE FUCK SAKE (This is important.)

Output(Return):
- A list of file paths to the generated image files.

Ensure that all visualizations are relevant to the forensic analysis, and that Python code strictly adheres to using the provided functions. Don't make multiple codes for same data.
After executing the code don't return an output just except the image paths in list type. PLEASE RETURN THE IMAGES PATHS IN LIST.
"""

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next: str
    analysis_result: str

class MultiAgentForensic:
    def __init__(self, log_data: str, log_type: str) -> None:
        self.json_loaded_data = log_data
        self.log_type = log_type
        self.final_result = ''

        set_environment_variables("Multi_Agent_Forensic")

        # 에이전트 이름 정의
        self.TEAM_SUPERVISOR = 'team_supervisor'
        self.DATA_ANALYSIS_AGENT = 'data_analysis_agent'
        self.DATA_VISUALIZATION_AGENT = 'data_visualization_agent'

        # 에이전트 목록 및 옵션 정의
        self.MEMBERS = [
            self.DATA_ANALYSIS_AGENT,
            self.DATA_VISUALIZATION_AGENT
        ]
        self.OPTIONS = ["FINISH"] + self.MEMBERS

        # 언어 모델 초기화
        self.LLM = ChatOpenAI(model="gpt-4o-mini")

        self.router_function_def = {
            "name": "route",
            "description": "Select the next role.",
            "parameters": {
                "title": "routeSchema",
                "type": "object",
                "properties": {
                    "next": {
                        "title": "next",
                        "anyOf": [
                            {"enum": self.OPTIONS},
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
        ).partial(options=", ".join(self.OPTIONS), members=", ".join(self.MEMBERS))

        team_supervisor_chain = (
            team_supervisor_prompt_template
            | self.LLM.bind_functions(functions=[self.router_function_def], function_call="route")
            | JsonOutputFunctionsParser()
        )

        dummy_tool = Tool(
            name="dummy_tool",
            func=lambda x: "This is a dummy tool and does nothing.",
            description="A placeholder tool that does nothing but satisfies the tools requirement."
        )
        data_analysis_agent = self.create_agent(self.LLM, [dummy_tool], FORENSIC_AGENT_SYSTEM_PROMPT, self.json_loaded_data, self.log_type)

        data_analysis_agent_node = functools.partial(
            self.analysis_agent_node,
            agent=data_analysis_agent,
            name=self.DATA_ANALYSIS_AGENT
        )

        python_repl = PythonREPL()
        repl_tool = Tool(
            name="python_repl",
            description="A Python shell. Use this to execute python commands. Input should be a valid python command. If you want to see the output of a value, you should print it out with `print(...)`.",
            func=lambda command: python_repl.run(
                "import matplotlib; matplotlib.use('Agg'); " + command
            ),
        )
        data_visualization_agent = self.create_agent(self.LLM, [repl_tool], VISUALIZER_SYSTEM_PROMPT)

        data_visualization_agent_node = functools.partial(
            self.visualizer_agent_node,
            agent=data_visualization_agent,
            name=self.DATA_VISUALIZATION_AGENT
        )

        self.workflow = StateGraph(AgentState)

        self.workflow.add_node(self.DATA_VISUALIZATION_AGENT, data_visualization_agent_node)
        self.workflow.add_node(self.DATA_ANALYSIS_AGENT, data_analysis_agent_node)
        self.workflow.add_node(self.TEAM_SUPERVISOR, team_supervisor_chain)

        self.workflow.add_edge(self.DATA_ANALYSIS_AGENT, self.DATA_VISUALIZATION_AGENT)

        self.workflow.add_edge(self.DATA_ANALYSIS_AGENT, self.TEAM_SUPERVISOR)
        self.workflow.add_edge(self.DATA_VISUALIZATION_AGENT, self.TEAM_SUPERVISOR)

        self.workflow.add_edge(self.DATA_VISUALIZATION_AGENT, END)

        conditional_map = {name: name for name in self.MEMBERS}
        conditional_map["FINISH"] = END
        self.workflow.add_conditional_edges(
            self.TEAM_SUPERVISOR,
            lambda x: self.debug_return_next(x),  # 디버깅 함수로 변경
            conditional_map
        )

        self.workflow.set_entry_point(self.TEAM_SUPERVISOR)


    def debug_return_next(self, x):
        return x["next"]

    def load_data(self):
        with open(self.file_path, "r") as f:
            return json.dumps(json.load(f))

    def create_agent(self, llm: BaseChatModel, tools: list, system_prompt: str, log_data: json=None, log_type: str=None):
        if log_data:
            prompt_template = ChatPromptTemplate.from_messages(
                [
                    ("system", system_prompt),
                    MessagesPlaceholder(variable_name="messages"),
                    MessagesPlaceholder(variable_name="agent_scratchpad"),
                ]
            ).partial(json_loaded_data=log_data, logtype=log_type)
            agent = create_openai_tools_agent(llm, tools, prompt_template)
            agent_executor = AgentExecutor(agent=agent, tools=tools, return_intermediate_steps=True)
        else:
            prompt_template = ChatPromptTemplate.from_messages(
                [
                    ("system", system_prompt),
                    MessagesPlaceholder(variable_name="messages"),
                    MessagesPlaceholder(variable_name="agent_scratchpad"),
                ]
            )
            agent = create_openai_tools_agent(llm, tools, prompt_template)
            agent_executor = AgentExecutor(agent=agent, tools=tools, max_execution_time=15)

        return agent_executor

    def analysis_agent_node(self, state: AgentState, agent, name):
        result = agent.invoke(state)
        state["analysis_result"] = result["output"]
        return {"messages": [HumanMessage(content=result["output"], name=name)]}
    
    def visualizer_agent_node(self, state: AgentState, agent, name):
        import ast
        analysis_result = state['messages'][1]
        self.final_result['summary'] = state['messages'][1].content
        
        result = agent.invoke({"analysis_result": analysis_result, **state})
        self.final_result['images'] = ast.literal_eval(result["output"])
        return {"messages": [HumanMessage(content=result["output"], name=name)]}
    
    async def run(self):
        initial_state = {
            "messages": [HumanMessage(content="이벤트 로그 분석해서 ...")],
            "next": "",
            "analysis_result": None
        }

        my_agent_graph = self.workflow.compile()

        for chunk in my_agent_graph.stream(initial_state):
            if "__end__" in chunk:
                print("Process finished!")
                break
            else:
                print(chunk)
                print(f"{Fore.GREEN}#############################{Style.RESET_ALL}")

        return self.final_result
