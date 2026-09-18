import os

import spaces
import gradio as gr

from src.client.app import create_card_demo, create_demo
from src.client.ui_assets import CARD_UI_CSS, MOBILE_UI_CSS
from src.server.notion_client import NotionClient
from src.server.service import translate_text


os.environ.setdefault("GRADIO_SSR_MODE", "false")


@spaces.GPU
def gradio_translate(text: str):
    return translate_text(text)


notion_client = NotionClient()
demo = gr.TabbedInterface(
    [
        create_demo(gradio_translate, notion_client=notion_client),
        create_card_demo(notion_client),
    ],
    ["翻译", "词汇卡"],
    title="日文振假名翻译工具",
)


demo.launch(css=f"{MOBILE_UI_CSS}\n{CARD_UI_CSS}")