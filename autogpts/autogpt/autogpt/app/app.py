from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from .ui import demo

app = FastAPI(
    title="AutoGPT Server",
    description="Forked from AutoGPT Forge; "
    "Modified version of The Agent Protocol.",
    version="v0.4",
)

@app.get("/")
def home():
    demo.launch()
    
    return RedirectResponse(url="http://127.0.0.1:7860")