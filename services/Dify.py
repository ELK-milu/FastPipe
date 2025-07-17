import aiohttp
import httpx
import requests
import json

def SetSessionConfig(key:str,session: httpx.AsyncClient)->httpx.AsyncClient:
    session.headers.update({
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
        'Connection': 'Keep-Alive'
    })
    return session

def get_payload(text:str):
    payload = {
        "inputs": {},
        "query": text,
        "response_mode": "streaming",
        "conversation_id": "",
        "user": "user",
        "files": []
    }
    return payload
