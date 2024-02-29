from fastapi import FastAPI

class MTAgentMiddleware:
    """
    Middleware that injects the agent instance into the request scope.
    """

    def __init__(self, app: FastAPI, protocol, agent: "Agent"):
        """

        Args:
            app: The FastAPI app - automatically injected by FastAPI.
            agent: The agent instance to inject into the request scope.

        Examples:
            >>> from fastapi import FastAPI, Request
            >>> from agent_protocol.agent import Agent
            >>> from agent_protocol.middlewares import AgentMiddleware
            >>> app = FastAPI()
            >>> @app.get("/")
            >>> async def root(request: Request):
            >>>     agent = request["agent"]
            >>>     task = agent.db.create_task("Do something.")
            >>>     return {"task_id": a.task_id}
            >>> agent = Agent()
            >>> app.add_middleware(AgentMiddleware, agent=agent)
        """
        self.app = app
        self.protocol = protocol
        self.agent = agent

    async def __call__(self, scope, receive, send):
        scope["agent"] = self.agent
        scope["protocol"] = self.protocol
        await self.app(scope, receive, send)