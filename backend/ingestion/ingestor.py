import asyncio
import aiohttp
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import config
from backend.utils.text_utils import chunk_text, clean_text

async def search_web(topic: str, num_results: int = 10) -> list[dict]:
    """Search web using Tavily and return raw results."""
    url = "https://api.tavily.com/search"
    
    payload = {
        "api_key": config.TAVILY_API_KEY,
        "query": topic,
        "num_results": num_results,
        "search_depth": "advanced",
        "include_raw_content": True,
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            data = await response.json()
            results = data.get("results", [])
            
            chunks = []
            for r in results:
                content = clean_text(r.get("raw_content") or r.get("content", ""))
                if content:
                    for chunk in chunk_text(content):
                        chunks.append({
                            "text": chunk,
                            "source": r.get("url", ""),
                            "title": r.get("title", ""),
                            "type": "web"
                        })
            return chunks

async def parse_pdf(filepath: str) -> list[dict]:
    """Parse a PDF and return chunked text with source attribution."""
    import pymupdf
    
    chunks = []
    doc = pymupdf.open(filepath)
    
    for page_num, page in enumerate(doc):
        raw_text = page.get_text()
        content = clean_text(raw_text)
        if content:
            for chunk in chunk_text(content):
                chunks.append({
                    "text": chunk,
                    "source": filepath,
                    "title": f"Page {page_num + 1}",
                    "type": "pdf"
                })
    
    doc.close()
    return chunks

async def ingest(topic: str, pdf_paths: list[str] = []) -> list[dict]:
    """
    Main ingestion function.
    Runs web search and PDF parsing in parallel.
    Returns unified list of chunks ready for graph building.
    """
    tasks = [search_web(topic)]
    
    for path in pdf_paths:
        tasks.append(parse_pdf(path))
    
    results = await asyncio.gather(*tasks)
    
    all_chunks = []
    for result in results:
        all_chunks.extend(result)
    
    print(f"[Ingestor] {len(all_chunks)} chunks collected for topic: {topic}")
    return all_chunks