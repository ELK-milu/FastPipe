import aiohttp
import requests
import json

def SetSessionConfig(key:str,session: aiohttp.ClientSession)->aiohttp.ClientSession:
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
