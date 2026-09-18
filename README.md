---
title: Japanese Furigana Translator
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 6.26.0
app_file: app.py
python_version: "3.12"
pinned: false
---

# Japanese Furigana Translator

This Space provides a Gradio web interface for Japanese furigana translation.

Translator and vocabulary cards are available as tabs in the Gradio interface.

Configure `GROQ_API_KEY` in the Space Settings under **Secrets**.

Set `NOTION_TOKEN` and `NOTION_DATABASE_ID` to enable vocabulary cards; the integration must have access to that database.

Optional LangSmith variables can also be configured in Space Secrets.