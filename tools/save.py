from langchain.tools import tool
from pydantic import BaseModel, Field

class RunSaveInput(BaseModel):
    image_description: str = Field(
        description="A detailed description of the desired image."
    )

@tool("run_save", args_schema=RunSaveInput)
def run_save(param: str) -> None:
    return