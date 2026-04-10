import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import config

def get_client():
    """Create a fresh client per call to avoid event loop conflicts on Windows."""
    from openai import AsyncOpenAI
    return AsyncOpenAI(
        api_key=config.LLM_API_KEY,
        base_url=config.LLM_BASE_URL,
    )

async def call_llm(prompt: str, system: str = None, temperature: float = 0.7) -> str:
    client = get_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    try:
        response = await client.chat.completions.create(
            model=config.LLM_MODEL_NAME,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content
    finally:
        await client.close()

async def call_llm_json(prompt: str, system: str = None) -> str:
    client = get_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    try:
        response = await client.chat.completions.create(
            model=config.LLM_MODEL_NAME,
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content
    finally:
        await client.close()