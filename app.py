import os
import sys
from importlib.metadata import PackageNotFoundError, version

print("[startup] app.py import started", flush=True)

from fastapi import FastAPI
import gradio as gr
import uvicorn
import spaces


@spaces.GPU(duration=1)
def _zerogpu_probe():
	return "probe ok"

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

from src.client.app import create_demo
from src.server.api import app as api_app


print("[startup] project modules imported", flush=True)
demo = create_demo()
app: FastAPI = gr.mount_gradio_app(api_app, demo, path="/")
print("[startup] Gradio mounted at /; FastAPI routes are ready", flush=True)

# local debug only
# if __name__ == "__main__":
# 	uvicorn.run(
# 		app,
# 		host="0.0.0.0",
# 		port=int(os.getenv("PORT", "7860")),
# 	)
