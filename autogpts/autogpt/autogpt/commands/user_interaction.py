"""Commands to interact with the user"""

from __future__ import annotations

from autogpt.agents.agent import Agent
from autogpt.app.utils import clean_input
from autogpt.command_decorator import command
from autogpt.core.utils.json_schema import JSONSchema

COMMAND_CATEGORY = "user_interaction"
COMMAND_CATEGORY_TITLE = "User Interaction"


@command(
    "ask_user",
    (
        "If you need more details or information regarding the given goals,"
        " you can ask the user for input"
    ),
    {
        "question": JSONSchema(
            type=JSONSchema.Type.STRING,
            description="The question or prompt to the user",
            required=True,
        )
    },
    enabled=lambda config: not config.noninteractive_mode,
)
async def ask_user(question: str, agent: Agent) -> str:
    print(f"\nQ: {question}")
    resp = await clean_input(agent.legacy_config, "A:")
    return f"The user's answer: '{resp}'"

@command(
    "respond",
    (
        "Respond your analysis/diagnosis in details to user if no more questions to ask"
    ),
    {
        "diagnosis": JSONSchema(
            type=JSONSchema.Type.STRING,
            description="detailed diagnosis/analysis including suggestions",
            required=True,
        )
    },
    enabled=lambda config: not config.noninteractive_mode,
)
async def respond(diagnosis: str, agent: Agent) -> str:
    return diagnosis

@command(
    "finish_dialogue",
    (
        "Summarize the previous dialogue when the the task could not be proceeded"
        " or the dialogue is unrelated to the task"
    ), 
    {
        "summary": JSONSchema(
            type=JSONSchema.Type.STRING,
            description="summary of dialogue and reason to finish",
            required=True,
        )
    },
)
async def finish_dialogue(summary: str, agent: Agent) -> str:
    print("!!!!!!!!!!!!!!!!", summary)
    return summary