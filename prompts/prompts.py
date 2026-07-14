"""Prompt templates for the retrieval-vs-reasoning experiment."""

from __future__ import annotations

from typing import Any

SYSTEM_PROMPT = (
    "You are an expert Python programmer. Your task is to implement the requested function correctly. "
    "Return only valid Python code. Do not include markdown fences or explanations."
)

NO_RETRIEVAL_TEMPLATE = """{system}

Task:
{task_description}

Function signature:
{signature}

Requirements:
- Implement the function exactly as requested.
- Do not change the function name or signature.
- Return only Python code.
"""

GOLD_RETRIEVAL_TEMPLATE = """{system}

You are given relevant snippets from a Python library. They may be useful for solving the task.
Use the snippets when appropriate, but ensure the final implementation satisfies the task.

Relevant snippets:
```python
{retrieved_code}
```

Task:
{task_description}

Function signature:
{signature}

Requirements:
- Implement the function exactly as requested.
- You may call, adapt, or combine the provided snippets.
- Do not assume the snippets alone are the final answer.
- Return only Python code.
"""

DISTRACTOR_RETRIEVAL_TEMPLATE = """{system}

You are given relevant snippets from a Python library. They may be useful for solving the task.
Use the snippets when appropriate, but ensure the final implementation satisfies the task.

Relevant snippets:
```python
{retrieved_code}
```

Task:
{task_description}

Function signature:
{signature}

Requirements:
- Implement the function exactly as requested.
- You may call, adapt, or combine the provided snippets.
- Do not assume the snippets alone are the final answer.
- Return only Python code.
"""

DISTRACTOR_REMINDER_MILD_TEMPLATE = """{system}

You are given code snippets retrieved from a Python library by an automatic retriever.
Some snippets may be relevant, partially relevant, outdated, or erroneous.
Use them carefully and implement the requested function correctly.

Retrieved snippets:
```python
{retrieved_code}
```

Task:
{task_description}

Function signature:
{signature}

Requirements:
- Implement the function exactly as requested.
- Treat the retrieved snippets as potentially outdated or incorrect.
- Use a snippet only after confirming it matches the task.
- Return only Python code.
"""

DISTRACTOR_REMINDER_STRONG_TEMPLATE = """{system}

You are given code snippets retrieved from a Python library by an automatic retriever.
Before using any snippet, you MUST verify it item by item.

Retrieved snippets:
```python
{retrieved_code}
```

Task:
{task_description}

Function signature:
{signature}

Requirements:
1. Check the task description word by word.
2. Check every constant, boundary condition, and branch in each snippet.
3. Check that the snippet's logic matches the task requirements.
4. Only use a snippet if it passes all checks; otherwise write the function independently.
- Implement the function exactly as requested.
- Do not change the function name or signature.
- Return only Python code.
"""

GOLD_REMINDER_MILD_TEMPLATE = """{system}

You are given relevant snippets from a Python library. They are intended to be helpful for solving the task.
However, even relevant snippets may not exactly match the task requirements.
Use them carefully and ensure the final implementation satisfies the task.

Relevant snippets:
```python
{retrieved_code}
```

Task:
{task_description}

Function signature:
{signature}

Requirements:
- Implement the function exactly as requested.
- Verify that each snippet matches the task before using it.
- Do not assume the snippets alone are the final answer.
- Return only Python code.
"""

GOLD_REMINDER_STRONG_TEMPLATE = """{system}

You are given relevant snippets from a Python library. They are intended to be helpful for solving the task.
Before using any snippet, you MUST verify it item by item against the task requirements.

Relevant snippets:
```python
{retrieved_code}
```

Task:
{task_description}

Function signature:
{signature}

Requirements:
1. Check the task description word by word.
2. Check every constant, boundary condition, and branch in each snippet.
3. Check that the snippet's logic matches the task requirements.
4. Only use a snippet if it passes all checks; otherwise write the function independently.
- Implement the function exactly as requested.
- Do not change the function name or signature.
- Return only Python code.
"""

NAIVE_RETRIEVAL_TEMPLATE = """{system}

You are given code snippets retrieved from a Python library by an automatic retriever.
Some snippets may be relevant, partially relevant, or irrelevant.
Use them carefully and implement the requested function correctly.

Retrieved snippets:
```python
{retrieved_code}
```

Task:
{task_description}

Function signature:
{signature}

Requirements:
- Implement the function exactly as requested.
- Use retrieved snippets only when they are helpful.
- Return only Python code.
"""

NAIVE_TOPK_RETRIEVAL_TEMPLATE = """{system}

You are given the top-{top_k} code snippets retrieved from a Python library by an automatic retriever.
Some snippets may be relevant, partially relevant, or irrelevant.
Use them carefully and implement the requested function correctly.

Retrieved snippets:
```python
{retrieved_code}
```

Task:
{task_description}

Function signature:
{signature}

Requirements:
- Implement the function exactly as requested.
- Use retrieved snippets only when they are helpful.
- Return only Python code.
"""


COT_SUFFIX = """INSTRUCTIONS: Before writing the code, you MUST analyze the provided reference snippets step by step:

1. RELEVANCE: For each reference snippet, determine whether it is relevant to the task requirements.
2. CORRECTNESS: Verify whether the snippet's logic correctly implements the required functionality. Check for any errors in constants, conditions, or logic.
3. USAGE DECISION: Based on your analysis, decide whether to use, modify, or ignore each snippet. Explain your reasoning briefly.

After completing your analysis, write your solution code.

ANALYSIS:
"""


def render_prompt(
    condition: str,
    task_description: str,
    signature: str,
    snippets: list[str],
    strategy: str = "standard",
) -> str:
    """Render a prompt from explicit fields.

    For backwards compatibility, the parameters are kept as
    ``task_description``, ``signature``, and ``snippets``.
    See also ``render_prompt_from_task`` for the task-dict form.
    """
    retrieved_code = "\n\n".join(snippets)
    if condition == "no":
        template = NO_RETRIEVAL_TEMPLATE
    elif condition == "gold":
        template = GOLD_RETRIEVAL_TEMPLATE
    elif condition in ("distractor", "distractor_weak", "distractor_strong"):
        template = DISTRACTOR_RETRIEVAL_TEMPLATE
    elif condition in ("naive", "dense", "hybrid"):
        template = NAIVE_RETRIEVAL_TEMPLATE
    elif condition.startswith("naive_topk_"):
        template = NAIVE_TOPK_RETRIEVAL_TEMPLATE
    elif condition == "distractor_reminder_mild":
        template = DISTRACTOR_REMINDER_MILD_TEMPLATE
    elif condition == "distractor_reminder_strong":
        template = DISTRACTOR_REMINDER_STRONG_TEMPLATE
    elif condition == "gold_reminder_mild":
        template = GOLD_REMINDER_MILD_TEMPLATE
    elif condition == "gold_reminder_strong":
        template = GOLD_REMINDER_STRONG_TEMPLATE
    else:
        raise ValueError(f"Unknown condition: {condition}")
    top_k = None
    if condition.startswith("naive_topk_"):
        top_k = condition.split("_")[-1]
    prompt = template.format(
        system=SYSTEM_PROMPT,
        task_description=task_description,
        signature=signature,
        retrieved_code=retrieved_code,
        top_k=top_k or "N",
    )
    if strategy == "cot":
        prompt = prompt + "\n" + COT_SUFFIX
    elif strategy != "standard":
        raise ValueError(f"Unknown strategy: {strategy}")
    return prompt


def render_prompt_from_task(
    task: dict[str, Any],
    condition: str,
    context: dict[str, list[str]],
    strategy: str = "standard",
) -> str:
    """Convenience wrapper that accepts a task dict and a context map.

    ``context`` maps condition names to dictionaries of task_id -> snippets.
    """
    if condition == "no":
        snippets: list[str] = []
    else:
        snippets = context.get(condition, {}).get(task["task_id"], [])
    return render_prompt(
        condition=condition,
        task_description=task["prompt"],
        signature=task["signature"],
        snippets=snippets,
        strategy=strategy,
    )
