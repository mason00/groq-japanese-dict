import os
import sys
from importlib.metadata import PackageNotFoundError, version

print("[startup] app.py import started", flush=True)

import gradio as gr
import spaces


# 仅用于通过 ZeroGPU 启动校验，空函数，毫秒级执行，不会超时。
@spaces.GPU(duration=10)
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
from src.server.service import translate_text


print("[startup] project modules imported", flush=True)


def gradio_translate(text: str) -> tuple[str, str, str, str]:
	return translate_text(text)


demo = create_demo(gradio_translate)
print("[startup] Gradio demo is ready", flush=True)

if __name__ == "__main__":
	server_name = "0.0.0.0" if os.getenv("SPACE_ID") else "127.0.0.1"
	print(
		f"[startup] launching Gradio on {server_name}:{os.getenv('PORT', '7860')}",
		flush=True,
	)
	demo.launch(
		server_name=server_name,
		server_port=int(os.getenv("PORT", "7860")),
		debug=True,
		show_error=True,
	)
