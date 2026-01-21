#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal CORS test
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允許所有來源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/test")
async def test():
    return {"message": "CORS test successful"}


@app.options("/test")
async def test_options():
    return {"message": "OPTIONS test successful"}


if __name__ == "__main__":
    import uvicorn

    print("Starting minimal CORS test on http://0.0.0.0:8002")
    uvicorn.run(app, host="0.0.0.0", port=8002)
