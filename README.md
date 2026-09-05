---
title: Japanese Furigana Translator
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 6.26.0
app_file: app.py
pinned: false
---

# Japanese Furigana Translator

This Space provides a Gradio web interface and a FastAPI API from the same application.

- Web UI: `/`
- Health check: `/health`
- Translation API: `POST /translate`

Configure `GROQ_API_KEY` in the Space Settings under **Secrets**. Optional LangSmith variables can be configured there as well.
