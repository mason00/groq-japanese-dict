import os
import sys
from importlib.metadata import PackageNotFoundError, version

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


# ---------------------------------------------------------------------------
# Runtime diagnostics
# ---------------------------------------------------------------------------

def _package_version(package_name: str) -> str:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "not-installed"


def _configured(name: str) -> str:
    value = os.getenv(name, "")
    return "configured" if value and not value.startswith("PASTE_") else "missing"


print(
    "[startup] runtime "
    f"python={sys.version.split()[0]} "
    f"gradio={_package_version('gradio')} "
    f"fastapi={_package_version('fastapi')} "
    f"spaces={_package_version('spaces')}",
    flush=True,
)

print(
    "[startup] environment "
    f"SPACE_ID={os.getenv('SPACE_ID', 'missing')} "
    f"SPACE_HARDWARE={os.getenv('SPACE_HARDWARE', 'missing')} "
    f"PORT={os.getenv('PORT', 'missing')} "
    f"LLM_PROVIDER={os.getenv('LLM_PROVIDER', 'groq')} "
    f"GROQ_API_KEY={_configured('GROQ_API_KEY')} "
    f"LANGSMITH_API_KEY={_configured('LANGSMITH_API_KEY')} "
    f"LANGSMITH_TRACING={os.getenv('LANGSMITH_TRACING', 'missing')} "
    f"LANGSMITH_PROJECT={os.getenv('LANGSMITH_PROJECT', 'missing')}",
    flush=True,
)


# ---------------------------------------------------------------------------
# ZeroGPU function
# ---------------------------------------------------------------------------

@spaces.GPU
def gradio_translate(text: str):
    return translate_text(text)


print(
    f"[startup] GPU function registered: {gradio_translate}",
    flush=True,
)


# ---------------------------------------------------------------------------
# Gradio applications
# ---------------------------------------------------------------------------

demo = create_demo(gradio_translate)
card_demo = create_card_demo()

print("[startup] Gradio demos initialized", flush=True)


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Mount Gradio applications
#
# /card -> vocabulary/card application
# /     -> main translator application
#
# Mount /card first because "/" is the catch-all root.
# ---------------------------------------------------------------------------

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

print("[startup] Gradio apps mounted successfully", flush=True)