import os
import sys
from importlib.metadata import PackageNotFoundError, version
from fastapi import FastAPI
import gradio as gr
import spaces
from src.client.app import CARD_UI_CSS, MOBILE_UI_CSS, create_card_demo, create_demo

print("[startup] app.py import started", flush=True)


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

from src.client.app import create_card_demo, create_demo
from src.server.service import translate_text

print("[startup] project modules imported", flush=True)


@spaces.GPU
def gradio_translate(text: str):
    return translate_text(text)


# Create individual Gradio Blocks apps
demo = create_demo(gradio_translate)
card_demo = create_card_demo()

print("[startup] Gradio demos initialized", flush=True)

# Initialize FastAPI app
app = FastAPI()


@app.get("/health")
def health_check():
    return {"status": "ok"}

# Mount Sub-Apps
# 1. Card demo accessible via /card
app = gr.mount_gradio_app(
    app, 
    card_demo, 
    path="/card",
    css=CARD_UI_CSS
)

# 2. Main translation demo accessible via /
app = gr.mount_gradio_app(
    app, 
    demo, 
    path="/",
    css=MOBILE_UI_CSS
)

print("[startup] Gradio apps mounted successfully", flush=True)