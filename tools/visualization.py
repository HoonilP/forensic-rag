from langchain.tools import tool
from pydantic import BaseModel, Field
from typing import Annotated
from langchain_experimental.utilities import PythonREPL

repl = PythonREPL()

class RunVisualizationInput(BaseModel):
    image_description: str = Field(description="A detailed description of the desired image.")

@tool("run_visualization", args_schema=RunVisualizationInput)
def run_visualization(
    code: Annotated[str, "The python code to execute to generate your chart."]
):
    """Use this to execute python code. If you want to see the output of a value,
    you should print it out with `print(...)`. This is visible to the user."""
    try:
        result = repl.run(code)
    except BaseException as e:
        return f"Failed to execute. Error: {repr(e)}"
    return f"Succesfully executed:\n```python\n{code}\n```\nStdout: {result}"