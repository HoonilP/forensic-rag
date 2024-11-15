from langchain.tools import tool
from pydantic import BaseModel, Field

class RunSearchInput(BaseModel):
    image_description: str = Field(
        description="A detailed description of the desired image."
    )

@tool("run_search", args_schema=RunSearchInput)
def run_search(param: str) -> None:
    return