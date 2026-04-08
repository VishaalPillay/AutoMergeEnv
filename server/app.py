from __future__ import annotations

from fastapi import FastAPI

from environment.env import AutoMergeEnv
from environment.models import AutoMergeAction

app = FastAPI(title="AutoMergeEnv API", version="0.1.0")
env = AutoMergeEnv()


@app.post("/reset")
async def reset() -> dict:
    observation = await env.reset()
    return observation.model_dump()


@app.post("/step")
async def step(action: AutoMergeAction) -> dict:
    result = await env.step(action)
    return {
        "observation": result.observation.model_dump(),
        "reward": result.reward.model_dump(),
        "done": result.done,
        "info": result.info,
    }


@app.get("/state")
async def state() -> dict:
    observation = await env.state()
    return observation.model_dump()


def main():
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()