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

The existing `/save_word` and `/card` endpoints continue to use Notion. Set `NOTION_TOKEN` and `NOTION_DATABASE_ID` to enable them; the integration must have access to that database.

Mongo-backed equivalents are also available at `POST /mongo/save_word` and `GET /mongo/card`. Set `MONGO_URI` to enable them; they use the `japan-dict` database and `vocab` collection. Existing Notion vocabulary is not copied to MongoDB.

Optional LangSmith variables can also be configured in Space Secrets.

[render: https://groq-japanese-dict.onrender.com/](https://groq-japanese-dict.onrender.com/)

[hugging face: https://mason00-groq-japanese-dict.hf.space](https://mason00-groq-japanese-dict.hf.space)
