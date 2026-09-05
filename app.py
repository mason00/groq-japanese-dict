import os

from fastapi import FastAPI
import gradio as gr
import uvicorn

from src.client.app import demo
from src.server.api import app as api_app


app: FastAPI = gr.mount_gradio_app(api_app, demo, path="/")


if __name__ == "__main__":
	uvicorn.run(
		app,
		host="0.0.0.0",
		port=int(os.getenv("PORT", "7860")),
	)
