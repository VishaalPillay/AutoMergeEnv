FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git findutils grep && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir fastapi uvicorn pydantic pytest openai httpx

RUN git config --global user.email "env@automerge.ai" \
 && git config --global user.name "AutoMergeEnv" \
 && git config --global init.defaultBranch main

COPY . /app

RUN chmod +x setup_tasks.sh && bash setup_tasks.sh

EXPOSE 7860

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
