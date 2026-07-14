"""Generate code for all tasks, models, and retrieval conditions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import openai
from dotenv import load_dotenv

# Add project paths.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "prompts"))

from prompts import render_prompt

load_dotenv(ROOT / ".env")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TASKS_PATH = ROOT / "tasks" / "all_tasks.jsonl"
OUTPUT_DIR = ROOT / "outputs" / "raw_generations"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RETRIEVAL_CONTEXTS = {
    "gold": ROOT / "retrieval_contexts" / "gold",
    "distractor": ROOT / "retrieval_contexts" / "distractor",
    "naive": ROOT / "retrieval_contexts" / "naive",
    "naive_topk_1": ROOT / "retrieval_contexts" / "naive_topk_1",
    "naive_topk_3": ROOT / "retrieval_contexts" / "naive_topk_3",
    "naive_topk_10": ROOT / "retrieval_contexts" / "naive_topk_10",
    "dense": ROOT / "retrieval_contexts" / "dense",
    "hybrid": ROOT / "retrieval_contexts" / "hybrid",
    "distractor_weak": ROOT / "retrieval_contexts" / "distractor_weak",
    "distractor_strong": ROOT / "retrieval_contexts" / "distractor_strong",
}

# Conditions that reuse an existing context directory.
CONDITION_CONTEXT_MAP = {
    "distractor_reminder_mild": "distractor",
    "distractor_reminder_strong": "distractor",
    "gold_reminder_mild": "gold",
    "gold_reminder_strong": "gold",
    "naive_topk_5": "naive",
    "dense": "dense",
    "hybrid": "hybrid",
    "distractor_weak": "distractor_weak",
    "distractor_strong": "distractor_strong",
}


def context_key_for_condition(condition: str) -> str:
    return CONDITION_CONTEXT_MAP.get(condition, condition)


def _library_for_task(task_id: str) -> str:
    if task_id.startswith("fluxon_"):
        return "fluxon"
    if task_id.startswith("quorix_"):
        return "quorix"
    if task_id.startswith("nimbla_"):
        return "nimbla"
    raise ValueError(f"Unknown task prefix: {task_id}")

DEFAULT_PARAMS = {
    "temperature": 0.0,
    "top_p": 1.0,
    "max_tokens": 1024,
}

PROJECT_ROOT = ROOT.parent

MODEL_ALIASES = {
    "qwen3b": {
        "name": "Qwen2.5-Coder-3B-Instruct",
        "path": str(PROJECT_ROOT / "model_cache" / "qwen" / "Qwen2___5-Coder-3B-Instruct"),
        "backend": "local",
    },
    "qwen7b": {
        "name": "Qwen2.5-Coder-7B-Instruct",
        "path": str(PROJECT_ROOT / "model_cache" / "qwen" / "Qwen2___5-Coder-7B-Instruct"),
        "backend": "local",
    },
    "codellama": {
        "name": "CodeLlama-7B-Instruct-Q5_K_M",
        "path": str(
            PROJECT_ROOT
            / "model_cache"
            / "codellama_gguf"
            / "CodeLlama-7B-Instruct-GGUF"
            / "codellama-7b-instruct.Q5_K_M.gguf"
        ),
        "backend": "gguf",
    },
    "deepseek_v4_flash": {
        "name": "deepseek-v4-flash",
        "path": "deepseek-v4-flash",
        "backend": "deepseek",
    },
    "longcat_2_0": {
        "name": "LongCat-2.0",
        "path": "LongCat-2.0",
        "backend": "longcat",
    },
    "minimax_m25": {
        "name": "MiniMax-M2.5",
        "path": "MiniMax-M2.5",
        "backend": "minimax",
    },
}


def resolve_model(model_id: str) -> tuple[str, str, str]:
    """Resolve model alias to (display_name, path/name, backend).

    Returns a 3-tuple of (display_name, model_path_or_name, backend).
    """
    if model_id in MODEL_ALIASES:
        cfg = MODEL_ALIASES[model_id]
        return cfg["name"], cfg["path"], cfg["backend"]
    # If not an alias, assume the user passed an explicit backend via --backend.
    raise ValueError(
        f"Unknown model alias: {model_id}. Known aliases: {list(MODEL_ALIASES.keys())}. "
        "Use --model <path/name> together with an explicit --backend for custom models."
    )


def load_tasks(tasks_path: Path | None = None) -> list[dict[str, Any]]:
    path = tasks_path or TASKS_PATH
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def load_contexts() -> dict[str, dict[str, list[str]]]:
    contexts: dict[str, dict[str, list[str]]] = {}
    for name, dir_path in RETRIEVAL_CONTEXTS.items():
        contexts[name] = {}
        for lib in ("fluxon", "quorix", "nimbla"):
            path = dir_path / f"{lib}.json"
            if not path.exists():
                continue
            with path.open(encoding="utf-8") as f:
                contexts[name].update(json.load(f))
    return contexts


def extract_code(text: str) -> str:
    """Extract Python code from model output."""
    text = text.strip()

    # If the output contains a fenced code block, extract its contents.
    # Match both ```python and plain ``` fences, even when preceded by prose.
    fence_match = re.search(r"```(?:python)?\n(.*?)\n```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    lines = text.splitlines()
    # Find first top-level function definition.
    first_def_idx = None
    for i, line in enumerate(lines):
        if re.match(r"^def\s+\w+\s*\(", line):
            first_def_idx = i
            break
    if first_def_idx is None:
        # No function definition; return the stripped text as-is.
        return text.strip()
    # Preserve import statements / comments that appear before the first function.
    import_lines = []
    for line in lines[:first_def_idx]:
        stripped = line.strip()
        if stripped.startswith(("import ", "from ")) or stripped == "":
            import_lines.append(line)
        elif stripped.startswith("#"):
            import_lines.append(line)
        else:
            # Stop at any other leading text.
            break
    code_lines = import_lines + lines[first_def_idx:]
    return "\n".join(code_lines).strip()


# ---------------------------------------------------------------------------
# Model backends
# ---------------------------------------------------------------------------

class APIModel:
    def __init__(self, model_name: str, api: str = "openai"):
        self.model_name = model_name
        self.api = api
        if api == "kimi":
            base_url = os.getenv("KIMI_BASE_URL", "https://api.kimi.com/coding/v1")
            api_key = os.getenv("KIMI_API_KEY")
        elif api == "gpt":
            base_url = os.getenv("GPT_BASE_URL", "https://api.openai.com/v1")
            api_key = os.getenv("GPT_API_KEY")
        elif api == "deepseek":
            base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
            api_key = os.getenv("DEEPSEEK_API_KEY")
        elif api == "longcat":
            base_url = os.getenv("LONGCAT_BASE_URL", "https://api.longcat.chat/openai/v1")
            api_key = os.getenv("LONGCAT_API_KEY")
        elif api == "minimax":
            base_url = os.getenv("MINIMAX_BASE_URL", "https://www.autodl.art/api/v1")
            api_key = os.getenv("MINIMAX_API_KEY")
        elif api == "openai":
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            api_key = os.getenv("OPENAI_API_KEY")
        else:
            raise ValueError(f"Unknown API: {api}")
        if not api_key:
            raise ValueError(f"API key not set for {api}")
        timeout = int(os.getenv(f"{api.upper()}_TIMEOUT", "180"))
        self.client = openai.OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)

    def generate(self, prompt: str, params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        messages = [
            {"role": "system", "content": "You are an expert Python programmer."},
            {"role": "user", "content": prompt},
        ]
        start = time.time()
        api_kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": params.get("temperature", 0.0),
            "top_p": params.get("top_p", 1.0),
            "max_tokens": params.get("max_tokens", 1024),
        }
        seed = params.get("seed")
        if seed is not None:
            api_kwargs["seed"] = seed

        # LongCat provider-native thinking control.
        if self.api == "longcat":
            thinking_type = params.get("thinking", "disabled")
            api_kwargs["extra_body"] = {"thinking": {"type": thinking_type}}

        response = self.client.chat.completions.create(**api_kwargs)
        latency = time.time() - start
        choice = response.choices[0]
        message = choice.message
        content = message.content or ""

        reasoning_content = ""
        reasoning_tokens = None
        if hasattr(message, "reasoning_content") and message.reasoning_content:
            reasoning_content = message.reasoning_content

        usage = response.usage
        if usage:
            if hasattr(usage, "completion_tokens_details") and usage.completion_tokens_details:
                details = usage.completion_tokens_details
                if hasattr(details, "reasoning_tokens"):
                    reasoning_tokens = details.reasoning_tokens
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
        else:
            prompt_tokens = None
            completion_tokens = None

        meta = {
            "latency": latency,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "response_model": response.model,
            "response_id": response.id,
            "finish_reason": choice.finish_reason,
            "reasoning_content": reasoning_content,
            "reasoning_tokens": reasoning_tokens,
        }
        return content, meta


class LocalModel:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._pipe = None

    def _load(self):
        if self._pipe is None:
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
            import torch

            print(f"Loading local model {self.model_name}...")
            tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.bfloat16,
                device_map="cuda",
                trust_remote_code=True,
            )
            self._pipe = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                device_map="cuda",
            )

    def generate(self, prompt: str, params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        self._load()
        import torch

        seed = params.get("seed")
        if seed is not None:
            torch.manual_seed(int(seed))

        messages = [
            {"role": "system", "content": "You are an expert Python programmer."},
            {"role": "user", "content": prompt},
        ]
        start = time.time()
        outputs = self._pipe(
            messages,
            max_new_tokens=params.get("max_tokens", 1024),
            temperature=params.get("temperature", 0.0),
            top_p=params.get("top_p", 1.0),
            do_sample=params.get("temperature", 0.0) > 0,
        )
        latency = time.time() - start
        content = outputs[0]["generated_text"][-1]["content"]
        meta = {
            "latency": latency,
            "prompt_tokens": None,
            "completion_tokens": None,
            "response_model": None,
            "response_id": None,
            "finish_reason": None,
            "reasoning_content": None,
            "reasoning_tokens": None,
        }
        return content, meta


class GGUFModel:
    """Local GGUF model via llama-cpp-python (e.g. CodeLlama)."""

    def __init__(self, model_path: str):
        self.model_path = model_path
        self._llm = None

    def _load(self):
        if self._llm is None:
            from llama_cpp import Llama

            print(f"Loading GGUF model from {self.model_path}...")
            self._llm = Llama(
                model_path=self.model_path,
                n_ctx=16384,
                n_gpu_layers=-1,
                verbose=False,
            )

    @staticmethod
    def _format_codellama_prompt(messages: list[dict[str, str]]) -> str:
        """CodeLlama Instruct prompt format.

        <s>[INST] <<SYS>>\n{system}\n<</SYS>>\n\n{user} [/INST]
        """
        system = ""
        user_parts: list[str] = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            elif msg["role"] == "user":
                user_parts.append(msg["content"])
        user = "\n\n".join(user_parts)
        if system:
            prompt = f"[INST] <<SYS>>\n{system}\n<</SYS>>\n\n{user} [/INST]"
        else:
            prompt = f"[INST] {user} [/INST]"
        return prompt

    def generate(self, prompt: str, params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        self._load()
        messages = [
            {"role": "system", "content": "You are an expert Python programmer."},
            {"role": "user", "content": prompt},
        ]
        formatted_prompt = self._format_codellama_prompt(messages)
        start = time.time()
        llm_kwargs = {
            "max_tokens": params.get("max_tokens", 1024),
            "temperature": params.get("temperature", 0.0),
            "top_p": params.get("top_p", 1.0),
            "stop": ["</s>"],
            "echo": False,
        }
        seed = params.get("seed")
        if seed is not None:
            llm_kwargs["seed"] = int(seed)
        output = self._llm(formatted_prompt, **llm_kwargs)
        latency = time.time() - start
        content = output["choices"][0]["text"].strip()
        meta = {
            "latency": latency,
            "prompt_tokens": output.get("usage", {}).get("prompt_tokens"),
            "completion_tokens": output.get("usage", {}).get("completion_tokens"),
            "response_model": None,
            "response_id": None,
            "finish_reason": output.get("choices", [{}])[0].get("finish_reason"),
            "reasoning_content": None,
            "reasoning_tokens": None,
        }
        return content, meta


def get_model(model_name: str, backend: str) -> APIModel | LocalModel | GGUFModel:
    if backend in ("openai", "deepseek", "kimi", "gpt", "longcat", "minimax"):
        return APIModel(model_name, api=backend)
    if backend == "local":
        return LocalModel(model_name)
    if backend == "gguf":
        return GGUFModel(model_name)
    raise ValueError(f"Unknown backend: {backend}")


def build_output_filename(model_alias: str, strategy: str, n_samples: int, limit: int) -> str:
    parts = [model_alias, strategy]
    if n_samples > 1:
        parts.append(f"n{n_samples}")
    if limit > 0:
        parts.append(f"limit{limit}")
    return "_".join(parts) + ".jsonl"


def now_iso() -> str:
    """Return ISO-8601 timestamp with timezone."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Main generation loop
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Model alias (qwen3b/qwen7b/codellama/deepseek_v4_flash/longcat_2_0/minimax_m25) or path/name")
    parser.add_argument("--backend", choices=["openai", "deepseek", "kimi", "gpt", "longcat", "minimax", "local", "gguf"], help="Required when --model is not a known alias")
    parser.add_argument("--conditions", nargs="+", default=["no", "gold", "distractor"])
    parser.add_argument("--output", help="Output JSONL file (auto-generated if omitted)")
    parser.add_argument("--tasks", default=str(TASKS_PATH))
    parser.add_argument("--strategy", default="standard", choices=["standard", "cot"])
    parser.add_argument("--n-samples", type=int, dest="num_samples", help="Deprecated alias for --num-samples")
    parser.add_argument("--num-samples", type=int, default=1, help="Number of independent samples per task/condition")
    parser.add_argument("--seed", type=int, default=42, help="Base random seed for multi-sample generation")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--thinking", default="disabled", choices=["enabled", "disabled"], help="LongCat provider-native thinking")
    parser.add_argument("--limit", type=int, default=0, help="Only process first N tasks (for testing)")
    parser.add_argument("--resume", action="store_true", help="Skip (task, condition, strategy, sample_id) combos already present in the output file")
    parser.add_argument("--append", action="store_true", help="Safe resume; append to existing output without overwriting")
    args = parser.parse_args()

    # Backward compatibility: --n-samples maps to --num-samples.
    if args.num_samples is None:
        args.num_samples = 1
    if args.num_samples < 1:
        raise ValueError("--num-samples must be >= 1")

    # Resolve model alias or explicit path/backend.
    try:
        display_name, model_path_or_name, backend = resolve_model(args.model)
    except ValueError:
        if not args.backend:
            raise
        display_name = args.model
        model_path_or_name = args.model
        backend = args.backend

    tasks = load_tasks(Path(args.tasks))
    if args.limit > 0:
        tasks = tasks[:args.limit]
    contexts = load_contexts()
    model = get_model(model_path_or_name, backend)

    params = DEFAULT_PARAMS.copy()
    params["temperature"] = args.temperature
    params["top_p"] = args.top_p
    params["max_tokens"] = args.max_tokens
    params["thinking"] = args.thinking
    params["strategy"] = args.strategy

    output_name = args.output or build_output_filename(args.model, args.strategy, args.num_samples, args.limit)
    output_path = OUTPUT_DIR / output_name
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Resume support: collect already-generated keys from an existing output file.
    # Key: (task_id, condition, strategy, sample_id)
    done_keys: set[tuple[str, str, str, int]] = set()
    generated = 0
    if (args.resume or args.append) and output_path.exists():
        with output_path.open(encoding="utf-8") as f_existing:
            for line in f_existing:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                done_keys.add((
                    rec.get("task_id", ""),
                    rec.get("condition", ""),
                    rec.get("strategy", "standard"),
                    rec.get("sample_id", 0),
                ))
                generated += 1
        print(f"Resuming from {generated} existing generations in {output_path}", flush=True)

    file_mode = "a" if (args.resume or args.append) else "w"
    with output_path.open(file_mode, encoding="utf-8") as f:
        for task in tasks:
            for condition in args.conditions:
                if condition == "no":
                    snippets: list[str] = []
                else:
                    ctx_key = context_key_for_condition(condition)
                    snippets = contexts.get(ctx_key, {}).get(task["task_id"], [])

                prompt = render_prompt(
                    condition=condition,
                    task_description=task["prompt"],
                    signature=task["signature"],
                    snippets=snippets,
                    strategy=args.strategy,
                )
                prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]

                for sample_id in range(args.num_samples):
                    key = (task["task_id"], condition, args.strategy, sample_id)
                    if key in done_keys:
                        continue

                    sample_seed = args.seed + sample_id if args.num_samples > 1 else args.seed
                    sample_params = params.copy()
                    if sample_seed is not None:
                        sample_params["seed"] = sample_seed

                    error_message: str | None = None
                    try:
                        raw_output, meta = model.generate(prompt, sample_params)
                        generated_code = extract_code(raw_output)
                    except Exception as e:
                        print(f"ERROR {task['task_id']} / {condition} / sample{sample_id}: {e}")
                        raw_output = ""
                        generated_code = ""
                        meta = {
                            "latency": 0.0,
                            "prompt_tokens": None,
                            "completion_tokens": None,
                            "response_model": None,
                            "response_id": None,
                            "finish_reason": None,
                            "reasoning_content": None,
                            "reasoning_tokens": None,
                        }
                        error_message = str(e)

                    record = {
                        "task_id": task["task_id"],
                        "model": display_name,
                        "model_alias": args.model,
                        "backend": backend,
                        "condition": condition,
                        "strategy": args.strategy,
                        "sample_id": sample_id,
                        "seed": sample_seed,
                        "temperature": args.temperature,
                        "top_p": args.top_p,
                        "max_tokens": args.max_tokens,
                        "thinking": args.thinking,
                        "prompt_hash": prompt_hash,
                        "prompt": prompt,
                        "raw_output": raw_output,
                        "generated_code": generated_code,
                        "timestamp": now_iso(),
                        "error": error_message,
                        **meta,
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    f.flush()
                    generated += 1
                    print(
                        f"Generated {generated}: {task['task_id']} / {condition} / sample{sample_id}",
                        flush=True,
                    )

    print(f"Wrote {generated} generations to {output_path}")


if __name__ == "__main__":
    main()
