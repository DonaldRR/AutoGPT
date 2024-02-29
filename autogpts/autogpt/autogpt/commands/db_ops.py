import logging 
from typing import Callable, ParamSpec, TypeVar
from autogpt.command_decorator import command
from autogpt.core.utils.json_schema import JSONSchema
from autogpt.models.command import CommandOutput

COMMAND_CATEGORY = "db_ops"
COMMAND_CATEGORY_TITLE = "Database Operations"

logger = logging.getLogger(__name__)

P = ParamSpec("P") 
CO = TypeVar("CO", bound=CommandOutput)

@command(
    "search_related_diseases",
    "Search related diseases on Wikipedia given collected symptoms",
    {
        "symptoms": JSONSchema(
            type=JSONSchema.Type.STRING,
            description="The symptoms(query) to search",
            required=True,
        ),
    },
)
def search_related_diseases(symptoms: str) -> str:

    return ""