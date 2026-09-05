# LangChain 基础

本项目使用 `langchain-core`，不直接依赖某个模型供应商。Groq 和 Ollama 仍由 `src/llm_client.py` 的统一接口负责，因此切换供应商不会改变业务链。

## 当前链路

`JapanesePipeline._build_chain()` 使用 LangChain Runnable 组合出这条链：

```text
输入 text
  -> tokenize: Sudachi 分词
  -> format_prompt: PromptTemplate 渲染版本化 prompt
  -> complete: 调用统一 LLMClient
  -> parse: Pydantic 校验 JSON
  -> Gradio 三项输出
```

## 基础组件

- `PromptTemplate`：带变量的提示词模板。本项目把用户日文填入 `{text}`，并保留 prompt 文件中的 JSON 花括号。
- `RunnableLambda`：把普通 Python 函数包装成 LangChain 步骤，例如分词、调用 LLM 和解析响应。
- `RunnablePassthrough.assign`：保留输入字典，同时追加中间结果，例如 `words`、`system_prompt` 和 `response`。
- `invoke()`：同步执行链。当前 Gradio 回调使用 `self._chain.invoke({"text": text})`。
- `get_graph()`：查看 Runnable 链的节点和连接，适合调试链式编排。

## 为什么暂时不使用 langchain-groq

当前项目已经有统一的 `LLMClient`，里面集中处理超时、重试、Windows 证书和 token 统计。直接换成 `langchain-groq` 会把这些行为分散到供应商适配器中。先用 `RunnableLambda` 接入，可以学习 LangChain 编排，同时保持现有架构边界。

## 运行配置

```text
LLM_PROVIDER=groq 或 ollama
PROMPT_VERSION=v1、v2 或 ab
```

修改 `src/pipeline.py` 中的 `_build_chain()`，即可练习替换、插入或并行 Runnable 步骤。

## LangSmith 追踪和评估

在 `start_groq.bat` 中填入 `LANGSMITH_API_KEY` 后，脚本会自动开启 tracing。每次调用会记录 `llm_translation` 和 `evaluate_current_output` 节点，项目名由 `LANGSMITH_PROJECT` 指定。

当前评估函数位于 `src/evaluation.py`：

- `furigana_correctness`：检查汉字 ruby 结构、平假名读音和源文本汉字覆盖率。
- `translation_accuracy`：有参考译文时计算文本相似度；没有参考译文时返回 `None`，避免伪造准确率。
- `hallucination_score`：根据日文信息保留率和译文长度给出启发式风险分数。它不是事实级别判定，适合筛选样本，最终应结合人工或 LLM judge。

LangSmith key 不需要写进 Python 代码，也不要提交到 Git。未填写 key 时，本地链和本地评估仍然正常工作，只是不上传 trace。