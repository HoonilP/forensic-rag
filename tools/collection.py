from langchain.tools import tool
from pydantic import BaseModel, Field

class RunCollectionInput(BaseModel):
    image_description: str = Field(
        description="A detailed description of the desired image."
    )

@tool("run_collection", args_schema=RunCollectionInput)
def run_collection(param: str) -> None:
    return