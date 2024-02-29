from __future__ import annotations

import inspect
import logging
import time
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Any

if TYPE_CHECKING:
    from autogpt.config import Config
    from autogpt.models.command_registry import CommandRegistry

from pydantic import Field

from autogpt.core.configuration import Configurable
from autogpt.core.prompting.schema import ChatPrompt, CompletionModelFunction
from autogpt.core.resource.model_providers import (
    AssistantChatMessageDict,
    ChatMessage,
    ChatModelProvider,
)
from autogpt.core.runner.client_lib.logging.helpers import dump_prompt
from autogpt.llm.api_manager import ApiManager
from autogpt.logs.log_cycle import (
    CURRENT_CONTEXT_FILE_NAME,
    NEXT_ACTION_FILE_NAME,
    USER_INPUT_FILE_NAME,
    LogCycleHandler,
)
from autogpt.logs.utils import fmt_kwargs
from autogpt.models.action_history import (
    Action,
    ActionErrorResult,
    ActionInterruptedByHuman,
    ActionResult,
    ActionSuccessResult,
)
from autogpt.models.command import CommandOutput
from autogpt.models.context_item import ContextItem
from autogpt.agents.utils.prompt_scratchpad import PromptScratchpad
from autogpt.llm.providers.openai import get_openai_command_specs
from autogpt.core.memory.base import AgentMemory
from autogpt.core.model import PetProfile

from .base import BaseAgent, BaseAgentConfiguration, BaseAgentSettings
from .features.context import ContextMixin
from .features.file_workspace import FileWorkspaceMixin
from .features.watchdog import WatchdogMixin
from .prompt_strategies.one_shot import (
    OneShotAgentPromptConfiguration,
    OneShotAgentPromptStrategy,
)
from .utils.exceptions import (
    AgentException,
    AgentTerminated,
    CommandExecutionError,
    UnknownCommandError,
)

logger = logging.getLogger(__name__)


from .agent import Agent, AgentConfiguration, AgentSettings
from copy import deepcopy


CommandName = str
CommandArgs = dict[str, str]
AgentThoughts = dict[str, Any]
ThoughtProcessOutput = tuple[CommandName, CommandArgs, AgentThoughts]


class MTAgent(Agent):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.memory = AgentMemory()
        self.pet_profile = None
        
    def reset(self, **kwargs):
        self.__init__(**kwargs)

    async def propose_action(self) -> ThoughtProcessOutput:
        """Proposes the next action to execute, based on the task and current state.

        Returns:
            The command name and arguments, if any, and the agent's thoughts.
        """

        # Scratchpad as surrogate PromptGenerator for plugin hooks
        self._prompt_scratchpad = PromptScratchpad()

        prompt: ChatPrompt = self.build_prompt(scratchpad=self._prompt_scratchpad)
        prompt = self.on_before_think(prompt, scratchpad=self._prompt_scratchpad)
        logger.info(f"[ {__file__} ] | Executing prompt:\n{dump_prompt(prompt)}")

        response = await self.llm_provider.create_chat_completion(
            prompt.messages,
            functions=get_openai_command_specs(
                self.command_registry.list_available_commands(self)
            )
            + list(self._prompt_scratchpad.commands.values())
            if self.config.use_functions_api
            else [],
            model_name=self.llm.name,
            completion_parser=lambda r: self.parse_and_process_response(
                r,
                prompt,
                scratchpad=self._prompt_scratchpad,
            ),
        )
        logger.info(f"[ {__file__} ] | Response from prompt:\n{response}")
        self.config.cycle_count += 1

        return self.on_response(
            llm_response=response,
            prompt=prompt,
            scratchpad=self._prompt_scratchpad,
        )

    def build_prompt(
        self,
        *args,
        extra_messages: Optional[list[ChatMessage]] = None,
        include_os_info: Optional[bool] = None,
        **kwargs,
    ) -> ChatPrompt:
        if not extra_messages:
            extra_messages = []

        # Clock
        extra_messages.append(
            ChatMessage.system(f"The current time and date is {time.strftime('%c')}"),
        )

        # Add budget information (if any) to prompt
        api_manager = ApiManager()
        if api_manager.get_total_budget() > 0.0:
            remaining_budget = (
                api_manager.get_total_budget() - api_manager.get_total_cost()
            )
            if remaining_budget < 0:
                remaining_budget = 0

            budget_msg = ChatMessage.system(
                f"Your remaining API budget is ${remaining_budget:.3f}"
                + (
                    " BUDGET EXCEEDED! SHUT DOWN!\n\n"
                    if remaining_budget == 0
                    else " Budget very nearly exceeded! Shut down gracefully!\n\n"
                    if remaining_budget < 0.005
                    else " Budget nearly exceeded. Finish up.\n\n"
                    if remaining_budget < 0.01
                    else ""
                ),
            )
            logger.info(budget_msg)
            extra_messages.append(budget_msg)

        if include_os_info is None:
            include_os_info = self.legacy_config.execute_local_commands

        prompt = super().build_prompt(
            *args,
            extra_messages=extra_messages,
            include_os_info=include_os_info,
            **kwargs)
        if self.memory.fetched_memory:
            prompt.messages.insert(1, self.memory.fmt_fetched_memory())
        if self.pet_profile:
            prompt.messages.insert(1, self.pet_profile.fmt_profile())

        return prompt
        