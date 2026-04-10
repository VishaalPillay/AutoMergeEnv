from __future__ import annotations

from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from environment.env import AutoMergeEnv
from environment.models import AutoMergeAction

app = FastAPI(title="AutoMergeEnv API", version="1.0.0")
env = AutoMergeEnv()


class ResetRequest(BaseModel):
    task_id: Optional[str] = None


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/reset")
async def reset(request: ResetRequest = ResetRequest()):
    observation = env.reset(task_id=request.task_id)
    return observation.model_dump()


@app.post("/step")
async def step(action: AutoMergeAction) -> dict:
    result = env.step(action)
    return {
        "observation": result.observation.model_dump(),
        "reward": result.reward.model_dump(),
        "done": result.done,
        "info": result.info,
    }


@app.get("/state")
async def state() -> dict:
    s = env.state()
    return s.model_dump()


def main():
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()