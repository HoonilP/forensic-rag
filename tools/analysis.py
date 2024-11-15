from langchain.tools import tool
from pydantic import BaseModel, Field

class RunAnalysisInput(BaseModel):
    image_description: str = Field(
        description="A detailed description of the desired image."
    )

@tool("run_analysis", args_schema=RunAnalysisInput)
def run_analysis(param: str) -> None:
    return