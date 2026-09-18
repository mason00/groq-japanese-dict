import os
import sys

import spaces
import gradio as gr

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from src.client.app import (
    CARD_UI_CSS,
    MOBILE_UI_CSS,
    create_card_demo,
    create_demo,
)
from src.server.service import translate_text


print("[startup] app.py import started", flush=True)


@spaces.GPU
def gradio_translate(text: str):
    return translate_text(text)


print("[startup] GPU function registered", flush=True)


demo = create_demo(gradio_translate)
card_demo = create_card_demo()

print("[startup] Gradio demos initialized", flush=True)


app = FastAPI()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.middleware("http")
async def add_initial_card_position(request: Request, call_next):
    if (
        request.method == "GET"
        and request.url.path in {"/card", "/card/"}
        and not request.url.query
    ):
        return RedirectResponse("/card/?1", status_code=307)

    return await call_next(request)


app = gr.mount_gradio_app(
    app,
    card_demo,
    path="/card",
    css=CARD_UI_CSS,
)

app = gr.mount_gradio_app(
    app,
    demo,
    path="/",
    css=MOBILE_UI_CSS,
)


# Critical for ZeroGPU when using mount_gradio_app()
try:
    from spaces.zero import startup

    startup()

    print("[startup] ZeroGPU startup report sent", flush=True)

except Exception as e:
    print(
        f"[startup] ZeroGPU startup report failed: {e}",
        flush=True,
    )