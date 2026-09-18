import os

import spaces
import gradio as gr
from fastapi.responses import RedirectResponse

from src.client.app import (
    CARD_UI_CSS,
    MOBILE_UI_CSS,
    create_card_demo,
    create_demo,
)
from src.server.service import translate_text


os.environ.setdefault("GRADIO_SSR_MODE", "false")


@spaces.GPU
def gradio_translate(text: str):
    return translate_text(text)


demo = create_demo(gradio_translate)
card_demo = create_card_demo()


# ---------------------------------------------------------------------------
# Inject the /card Gradio app into the FastAPI app created by Gradio launch()
# ---------------------------------------------------------------------------

import gradio.routes as gradio_routes

_original_create_app = gradio_routes.App.create_app


def _create_app_with_card(*args, **kwargs):
    app = _original_create_app(*args, **kwargs)

    # /card -> /card/?1
    @app.middleware("http")
    async def redirect_card(request, call_next):
        if (
            request.method == "GET"
            and request.url.path in {"/card", "/card/"}
            and not request.url.query
        ):
            return RedirectResponse("/card/?1", status_code=307)

        return await call_next(request)

    # Health endpoint
    @app.get("/health")
    async def health():
        return {"status": "ok"}

    # Create the Gradio ASGI app for the card demo and mount it.
    card_app = gradio_routes.App.create_app(
        card_demo,
        app_kwargs={"ssr_mode": False},
    )

    app.mount("/card", card_app)

    return app


gradio_routes.App.create_app = staticmethod(_create_app_with_card)


# ---------------------------------------------------------------------------
# Start Gradio normally.
#
# This is important for ZeroGPU:
# @spaces.GPU + demo.launch() lets the spaces package register the GPU
# functions through Gradio's normal startup lifecycle.
# ---------------------------------------------------------------------------

demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    ssr_mode=False,
)