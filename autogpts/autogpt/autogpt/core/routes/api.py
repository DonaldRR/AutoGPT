import json
from typing import Optional
import time
# autogpt
from autogpt.config.ai_directives import AIDirectives
from autogpt.agents.agent import Agent, AgentSettings
from autogpt.agents.mtagent import MTAgent
from autogpt.agent_factory.profile_generator import generate_agent_profile_for_task
from autogpt.agent_factory.generators import generate_agent_for_task
from autogpt.agent_factory.configurators import _configure_agent, create_agent_state
from autogpt.plugins import scan_plugins
from autogpt.commands.user_interaction import ask_user, respond, finish_dialogue
from autogpt.commands import MT_COMMAND_CATEGORIES
from autogpt.models.command_registry import CommandRegistry
from autogpt.models.action_history import ActionSuccessResult, ActionErrorResult, Action
from autogpt.models.command import Command
from autogpt.llm.utils import create_openai_embedding
from autogpt.core.model import ChatRequestBody, SignInRequestBody, PetProfileRequestBody, PetProfile
from autogpt.core.resource.model_providers import CompletionModelFunction
from autogpt.logs import color_logger
# fastapi
from fastapi import (
    APIRouter, 
    Request,
    Response
    )
# forge
from forge.sdk.model import StepRequestBody, Step

# logger
import logging 
logger = logging.getLogger(__name__)
color_logger(logger)

m_router = APIRouter()

@m_router.get("/dump", tags=["root"])
async def root():
    
    logger.debug("Dump Called ")

    return  Response(content="Hello world")

@m_router.get("/heartbeat", tags=["server"])
async def check_server_status():
    
    return Response(content="Server is ok", status_code=200)


@m_router.post("/agent/sign_in", tags=["user"])
async def sign_in(request: Request, request_body: SignInRequestBody) -> Response:

    protocol = request['protocol']
    agent = request['agent']
    if protocol.db.sign_in(**request_body.dict()):
        try:
            agent_state: AgentSettings = protocol.db.get_agent(agent.state)
            agent_state.history.reset()
            agent.reset(
                settings=agent_state,
                llm_provider=agent.llm_provider,
                command_registry=agent.command_registry,
                legacy_config=agent.legacy_config)

            commands_desc_list = []
            for cmd in agent.command_registry.commands.values():
                available = cmd.available
                if callable(cmd.available):
                    available = cmd.available(agent)
                if available:
                    commands_desc_list.append(CompletionModelFunction(
                        name=cmd.name,
                        description=cmd.description,
                        parameters={param.name: param.spec for param in cmd.parameters},
                    ).fmt_line())
            logger.info(request['agent'].state.ai_profile)
            response_dict = agent_state.dict()
            response_dict['commands'] = commands_desc_list
            return Response(content=json.dumps(response_dict),
                            status_code=200,
                            media_type="application/json")
        except Exception as e:
            logger.warning(f"Load user data failed: {e}")

    return Response(content="",
                    status_code=400,
                    media_type="application/json")

@m_router.post("/agent/sign_out", tags=["user"])
async def sign_out(request: Request, request_body: ChatRequestBody) -> Response:

    return Response(content="",
                    status_code=200,
                    media_type="application/json")

@m_router.post("/agent/setting/profile")
async def update_profile(request: Request, request_body: ChatRequestBody) -> Response:

    protocol = request['protocol']
    agent = request['agent']

    request_input = eval(request_body.input)
    agent_state = agent.state
    agent_state.ai_profile.ai_name = request_input.get("name", "")
    agent_state.ai_profile.ai_role = request_input.get("role", "")
    if protocol.db.update_agent(agent_state):
        return Response(content=json.dumps(agent_state.ai_profile.json()),
            status_code=200,
            media_type="application/json")
    else:
        agent_state = protocol.db.get_agent(agent_state)
        agent.settings = agent_state
        return Response(content=json.dumps(agent_state.ai_profile.json()),
            status_code=400,
            media_type="application/json")

@m_router.post("/agent/setting/directives")
async def update_directives(request: Request, request_body: ChatRequestBody) -> Response:

    protocol = request['protocol']
    agent = request['agent']

    request_input = eval(request_body.input)
    agent_state = agent.state
    agent_state.directives.resources = request_input.get("Resources", [])
    agent_state.directives.constraints = request_input.get("Constraints", [])
    agent_state.directives.best_practices = request_input.get("Best Practices", [])
    if protocol.db.update_agent(agent_state):
        return Response(content=json.dumps(agent_state.directives.json()),
            status_code=200,
            media_type="application/json")
    else:
        agent_state = protocol.db.get_agent(agent_state)

@m_router.post("/agent/setting/task")
async def set_task(request: Request, request_body: ChatRequestBody) -> Response:
    protocol = request['protocol']
    agent = request['agent']
    try:
        request_input = request_body.input
        agent.state.task = request_input

        return Response(content="setting task succeed",
                        status_code=200,
                        media_type="text/plain")
    except Exception as e:
        return Response(content=f"{e}",
                        status_code=400,
                        media_type="text/plain")

@m_router.post("/agent/setting/pet")
async def set_pet(request: Request, request_body: PetProfileRequestBody) -> Response:
    
    protocol = request["protocol"]
    agent = request["agent"]

    try:
        pet_profile = None
        cur_profile = protocol.db.fetch(table_name="PetProfile", 
                          data={
                              "UserId": protocol.db.user_id,
                              "PetName": request_body.pet_name,
                              "PetType": request_body.pet_type,
                              })
        if cur_profile:
            # set agent pet profile
            cur_profile = cur_profile[0]
            pet_profile = PetProfile(pet_name=cur_profile['PetName'],
                                     pet_type=cur_profile['PetType'],
                                     pet_breed=cur_profile['PetBreed'],
                                     desc=cur_profile["Desc"])
        else:
            protocol.db.upsert(table_name="PetProfile",
                               data={
                                   "UserId": protocol.db.user_id,
                                   "PetName": request_body.pet_name,
                                   "PetType": request_body.pet_type,
                                   "PetBreed": request_body.pet_breed,
                                   "Desc": request_body.desc
                               })
            pet_profile = PetProfile(pet_name=request_body.pet_name,
                                     pet_type=request_body.pet_type,
                                     pet_breed=request_body.pet_breed,
                                     desc=request_body.desc)
        agent.pet_profile = pet_profile
        print("=========", agent.pet_profile)

        return Response(content="update profile succeed",
                        status_code=200,
                        media_type="text/plain")
    except Exception as e:
        logger.error(e)
        return Response(content=f"{e}",
                        status_code=400,
                        media_type="text/plain")

@m_router.post("/agent/create")
async def create_agent(request: Request, request_body: ChatRequestBody) -> Response:
    
    logger.info(request)
    # logger.info("request body:", request_body.json())

    protocol = request["protocol"]
    agent = request["agent"]
    base_directives = AIDirectives.from_file(protocol.app_config.prompt_settings_file)
    t1 = time.time()
    response = None
    try:
        ai_profile, ai_directives = await generate_agent_profile_for_task(
            task=request_body.input,
            app_config=protocol.app_config,
            llm_provider=protocol.get_llm_provider())
        
        agent_state = create_agent_state(
            task="",
            ai_profile=ai_profile,
            directives=base_directives + ai_directives,
            app_config=protocol.app_config
        )
        agent_state.history.reset()

        new_agent = MTAgent(
            settings=agent_state,
            llm_provider=protocol.get_llm_provider(),
            command_registry=CommandRegistry.with_command_modules(
                modules=MT_COMMAND_CATEGORIES,
                config=protocol.app_config),
            legacy_config=protocol.app_config
        )
        agent.reset(
            settings=new_agent.state,
            llm_provider=new_agent.llm_provider,
            command_registry=new_agent.command_registry,
            legacy_config=new_agent.legacy_config)

        commands_desc_list = []
        for cmd in agent.command_registry.commands.values():
            available = cmd.available
            if callable(cmd.available):
                available = cmd.available(agent)
            if available:
                commands_desc_list.append(CompletionModelFunction(
                    name=cmd.name,
                    description=cmd.description,
                    parameters={param.name: param.spec for param in cmd.parameters},
                ).fmt_line())
        # request['agent'] = agent

        logger.info(f"================== DB upsert agent")
        protocol.db.update_agent(settings=agent_state)
            
        response_dict = {
            "profile": agent.ai_profile.json(),
            "directives": agent.directives.json(),
            "commands": commands_desc_list
        }
        response = Response(
            content=json.dumps(response_dict),
            status_code=200,
            media_type="application/json"
        )
    except Exception as e:
        logger.warning(f"Generate agent profile error: {e}")
        response = Response(
            content="Error generating agent",
            status_code=400,
            media_type="application/json"
        )
    
    t2 = time.time()
    logger.info(f"{__file__}:creat_agent() - Cost {t2 - t1}s")
    # logger.info(f"base_directives: {base_directives}")
    # logger.info(f"ai_profile:\n{ai_profile}\nai_directives:{ai_directives}")

    return response

@m_router.post("/agent/history/reset")
async def reset_history(request: Request, request_body: ChatRequestBody) -> Response:
    
    agent = request['agent']

    try:
        agent.state.history.reset()
        agent.event_history.reset()
        return Response(content="reset succeeded",
                        status_code=200,
                        media_type="text/plain")
    except Exception as e:
        return Response(content=f"{e}",
                        status_code=400,
                        media_type="text/plain")


@m_router.post("/agent/step")
async def execute_step(request: Request, request_body: ChatRequestBody) -> Response:

    logger.info(f"Request Input:{request_body.input}")

    protocol = request['protocol']
    agent = request["agent"]

    agent.memory.append_message("user", request_body.input)

    cur_episode = agent.event_history.current_episode
    execute_command, execute_command_args = None, None
    if cur_episode is not None:
        execute_command = cur_episode.action.name
        Execute_command_args = cur_episode.action.args

    logger.info(f"last command: {execute_command}({execute_command_args})")

    # execute last command 
    if execute_command and execute_command == ask_user.__name__:
        execute_result = ActionSuccessResult(outputs=request_body.input)
        agent.event_history.register_result(execute_result)
    else:
        agent.event_history.register_action(Action(name="user_prompt", args={}, reasoning="New user input"))
        agent.event_history.register_result(ActionSuccessResult(outputs=request_body.input))

    logger.info(f"history: {agent.event_history}")

    request_input_vec = create_openai_embedding(input=[request_body.input])[0]
    fetch_memory = protocol.db.rpc("memory_search", 
                                   {"user_id": protocol.db.user_id,
                                    "pet_name": agent.pet_profile.pet_name,
                                    "query_embedding": request_input_vec,
                                    "match_count": 1}).data
    agent.memory.fetched_memory = fetch_memory
    
    try:
        next_command, next_command_args, raw_output = await agent.propose_action()
        logger.info(f"Propose action: {next_command}({next_command_args})")
    except Exception as e:
        logger.warning(f"Propose action error: {e}")
        return Response(
            content="propose action error",
            status_code=400,
            media_type="application/json"
        )
    
    if next_command == ask_user.__name__:
        agent.memory.append_message("system", next_command_args['question'])
        return Response(
            content=json.dumps({"output": next_command_args['question'],
                                "memory": fetch_memory,
                                "reference": ""}),
            status_code=200,
            media_type="application/json"
        )
    else:
        next_execute_result = await agent.execute(
            command_name=next_command,
            command_args=next_command_args)
        
        agent.memory.append_message("system", next_execute_result)
        memory_dict = agent.memory.summarize()
        memory_dict['PetName'] = agent.pet_profile.pet_name if agent.pet_profile else ""
        protocol.db.upsert(table_name="ChatMemory", data=memory_dict)
        logger.info(f"Next command result: {next_execute_result}")
        return Response(
            content=json.dumps({"output": str(next_execute_result),
                                "memory": fetch_memory,
                                "reference": ""}),
            status_code=200,
            media_type="application/json"
        )