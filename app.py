import os

import spaces
import gradio as gr

from src.client.app import (
    MOBILE_UI_CSS,
    create_demo,
)
from src.server.service import translate_text


os.environ.setdefault("GRADIO_SSR_MODE", "false")


@spaces.GPU
def gradio_translate(text: str):
    return translate_text(text)


demo = create_demo(gradio_translate)


demo.launch()