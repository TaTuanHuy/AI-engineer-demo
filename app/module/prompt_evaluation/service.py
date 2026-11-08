import html
import json
import re
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.common.gemini.client import DEFAULT_MODEL, GeminiClient
from app.config import settings
from app.module.dataset.service import DatasetService
from app.module.prompt_evaluation.schemas import (
    DATASET_SCHEMA,
    FRAMEWORK_DATASET_SCHEMA,
    GRADE_SCHEMA,
    DatasetRequest,
)


class PromptEvaluationService:
    data_dir = Path(__file__).resolve().parent / "data"
    async def generate_framework_dataset(
        self,
        *,
        module: str,
        key: str,
        rule: str,
        example: list[dict[str, Any]],
        num_cases: int,
        model: str | None = None,
        max_token: int = 4000,
    ) -> dict[str, Any]:
        """Generate a reusable evaluation dataset and upsert it into MongoDB."""
        gemini = GeminiClient()
        selected_model = model or settings.gemini_dataset_model or settings.gemini_model
        prompt = f"""You are generating evaluation test cases for a prompt-evaluation framework.
    Follow the rule exactly and use the examples to understand the task and expected data shape.
    Generate exactly {num_cases} diverse, non-duplicate test cases. Include easy, typical,
    boundary, ambiguous, and constraint-heavy cases where they make sense.
    
    Rule/task:
    {rule}
    
    Examples supplied by the user:
    {json.dumps(example, ensure_ascii=False, indent=2)}
    
    Return JSON matching the schema. Each test case must contain:
    - inputs: object of values to provide to the prompt being evaluated
    - scenario: short description of what this case tests
    - solution_criteria: measurable criteria used to score the answer
    Do not copy an example verbatim. Do not add fields outside the schema."""
        generated = gemini.generate_json(
            prompt,
            schema=FRAMEWORK_DATASET_SCHEMA,
            model=selected_model,
            temperature=settings.gemini_dataset_temperature,
            max_output_tokens=max_token,
        )
        cases = generated.get("test_cases") if isinstance(generated, dict) else None
        if not isinstance(cases, list) or not cases:
            raise ValueError("Model must return a non-empty test_cases array")
        if len(cases) > num_cases:
            cases = cases[:num_cases]
        for index, case in enumerate(cases):
            if not isinstance(case, dict):
                raise ValueError(f"Test case {index} must be an object")
            if not isinstance(case.get("inputs"), dict):
                raise ValueError(f"Test case {index} must contain inputs as an object")
            if not isinstance(case.get("solution_criteria"), list) or not case["solution_criteria"]:
                raise ValueError(f"Test case {index} must contain solution_criteria")
            case.setdefault("scenario", f"Generated test case {index + 1}")
    
        dataset = {
            "rule": rule,
            "examples": example,
            "model": selected_model,
            "max_token": max_token,
            "test_cases": cases,
        }
        record = await DatasetService.upsert(module=module, key=key, value=dataset)
        return {
            "id": str(record.id),
            "module": module,
            "key": key,
            **dataset,
        }
    
    
    async def evaluate_framework_prompt(
        self,
        *,
        module: str,
        key: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """Run a prompt against a stored dataset, grade every case, and summarize."""
        stored = await DatasetService.get_by_key(module=module, key=key)
        if stored is None:
            raise LookupError(f"Dataset not found for module={module!r}, key={key!r}")
        dataset = stored.value
        if not isinstance(dataset, dict) or not isinstance(dataset.get("test_cases"), list):
            raise ValueError("Stored dataset value must contain a test_cases array")
        cases = dataset["test_cases"]
        if not cases:
            raise ValueError("Stored dataset has no test cases")
    
        gemini = GeminiClient()
        results: list[dict[str, Any]] = []
        for index, case in enumerate(cases):
            inputs = case.get("inputs", {})
            if not isinstance(inputs, dict):
                raise ValueError(f"Stored test case {index} has invalid inputs")
            case_context = json.dumps(inputs, ensure_ascii=False, indent=2)
            execution_prompt = f"""Apply the following user prompt to this evaluation case.
    User prompt:
    {user_prompt}
    
    Evaluation case:
    Scenario: {case.get('scenario', '')}
    Inputs (JSON):
    {case_context}
    
    Return the answer requested by the user prompt. Do not describe this evaluation process."""
            output = gemini.generate(
                execution_prompt,
                model=settings.gemini_output_model or None,
                temperature=settings.gemini_output_temperature,
            )
            criteria = case.get("solution_criteria", [])
            grade_prompt = f"""You are a strict and fair evaluator. Score the generated answer only against the task rule and criteria. Do not invent requirements.
    Task rule: {dataset.get('rule', '')}
    User prompt: {user_prompt}
    Scenario: {case.get('scenario', '')}
    Inputs: {case_context}
    Criteria: {json.dumps(criteria, ensure_ascii=False)}
    Generated answer: {output}
    Return strengths, weaknesses, concise reasoning, and an integer score from 1 to 10 as JSON."""
            grade = gemini.generate_json(
                grade_prompt,
                schema=GRADE_SCHEMA,
                model=settings.gemini_grading_model or None,
                temperature=settings.gemini_grading_temperature,
            )
            results.append({
                "case_index": index + 1,
                "scenario": case.get("scenario", f"Test case {index + 1}"),
                "inputs": inputs,
                "criteria": criteria,
                "output": output,
                **grade,
            })
    
        average_score = sum(row["score"] for row in results) / len(results)
        return {
            "module": module,
            "key": key,
            "dataset_id": str(stored.id),
            "user_prompt": user_prompt,
            "model": gemini.model or DEFAULT_MODEL,
            "average_score": round(average_score, 2),
            "pass_rate": round(sum(row["score"] >= 7 for row in results) * 100 / len(results), 1),
            "results": results,
        }
    
    
    def generate_dataset(self, request: DatasetRequest, gemini: GeminiClient) -> dict[str, Any]:
        seeds = [case.model_dump() for case in request.test_cases]
        generated: list[dict[str, Any]] = []
        if request.additional_cases:
            prompt = f"""
            Create {request.additional_cases} distinct, realistic evaluation cases that expand the human-provided examples. Cover ordinary, boundary, ambiguous, and constraint-heavy scenarios where relevant. Keep the same input keys and value types as the examples. Write measurable criteria that directly reflect the task; include the provided criteria where relevant. Do not duplicate examples.
            Task: {request.task_description}
            Human-provided examples: {json.dumps(seeds, ensure_ascii=False)}
            Required criteria: {json.dumps(request.criteria, ensure_ascii=False)}
            Return only JSON matching the requested schema."""
            result = gemini.generate_json(
                prompt,
                schema=DATASET_SCHEMA,
                model=settings.gemini_dataset_model or None,
                temperature=settings.gemini_dataset_temperature,
            )
            generated = result["test_cases"]
    
        cases = []
        for seed in seeds:
            cases.append({
                "inputs": seed["inputs"],
                "scenario": seed["notes"] or "Human-provided test case",
                "solution_criteria": request.criteria or ["Answer addresses the task correctly", "Answer follows the requested output format"],
                "source": "human",
            })
        for case in generated:
            cases.append({**case, "source": "generated"})
    
        dataset_id = uuid.uuid4().hex
        dataset = {
            "id": dataset_id,
            "created_at": datetime.now(UTC).isoformat(),
            "model": gemini.model,
            "task_description": request.task_description,
            "test_cases": cases,
        }
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / f"dataset-{dataset_id}.json").write_text(
            json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return dataset
    
    
    def load_dataset_url(self, url: str) -> dict[str, Any]:
        request = urllib.request.Request(url, headers={"User-Agent": "DemoAIPromptEvaluator/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                if response.status != 200:
                    raise ValueError(f"Dataset URL returned HTTP {response.status}.")
                raw = response.read(2_000_001)
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ValueError(f"Could not fetch dataset URL: {exc}") from exc
        if len(raw) > 2_000_000:
            raise ValueError("Dataset file exceeds the 2 MB limit.")
        try:
            dataset = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Dataset URL must return a valid JSON file.") from exc
        if not isinstance(dataset, dict) or not isinstance(dataset.get("test_cases"), list):
            raise ValueError("Dataset JSON must contain a test_cases array.")
        if not dataset["test_cases"]:
            raise ValueError("Dataset must contain at least one test case.")
        return dataset
    
    
    def evaluate_prompt(self, prompt_template: str, dataset: dict[str, Any], gemini: GeminiClient) -> dict[str, Any]:
        results = []
        for case in dataset["test_cases"]:
            inputs = case.get("inputs", {})
            rendered_prompt = prompt_template
            for key, value in inputs.items():
                rendered_prompt = rendered_prompt.replace("{{" + str(key) + "}}", str(value))
            output = gemini.generate(
                rendered_prompt,
                model=settings.gemini_output_model or None,
                temperature=settings.gemini_output_temperature,
            )
            grade_prompt = f"""You are a strict but fair prompt evaluator. Score only against the supplied task and criteria. Do not invent requirements. A score of 10 means all criteria are met; 1 means the answer fails.
    Task: {dataset.get('task_description', '')}
    Inputs: {json.dumps(inputs, ensure_ascii=False)}
    Criteria: {json.dumps(case.get('solution_criteria', []), ensure_ascii=False)}
    Prompt output: {output}
    Return strengths, weaknesses, concise reasoning, and an integer score from 1 to 10 as JSON."""
            grade = gemini.generate_json(
                grade_prompt,
                schema=GRADE_SCHEMA,
                model=settings.gemini_grading_model or None,
                temperature=settings.gemini_grading_temperature,
            )
            results.append({
                "scenario": case.get("scenario", "Test case"),
                "inputs": inputs,
                "criteria": case.get("solution_criteria", []),
                "output": output,
                **grade,
            })
        average = sum(row["score"] for row in results) / len(results)
        return {
            "id": uuid.uuid4().hex,
            "created_at": datetime.now(UTC).isoformat(),
            "model": gemini.model or DEFAULT_MODEL,
            "task_description": dataset.get("task_description", ""),
            "prompt": prompt_template,
            "dataset_id": dataset.get("id"),
            "average_score": round(average, 2),
            "pass_rate": round(sum(row["score"] >= 7 for row in results) * 100 / len(results), 1),
            "results": results,
        }
    
    
    def save_report(self, report: dict[str, Any]) -> str:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        report_id = report["id"]
        (self.data_dir / f"report-{report_id}.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        rows = []
        for result in report["results"]:
            rows.append(
                "<tr>"
                f"<td>{html.escape(result['scenario'])}</td>"
                f"<td><pre>{html.escape(json.dumps(result['inputs'], ensure_ascii=False, indent=2))}</pre></td>"
                f"<td><pre>{html.escape(result['output'])}</pre></td>"
                f"<td>{result['score']}/10</td>"
                f"<td>{html.escape(result['reasoning'])}</td>"
                "</tr>"
            )
        page = f"""<!doctype html><html lang="vi"><meta charset="utf-8"><title>Prompt evaluation report</title>
    <style>body{{font:16px system-ui;max-width:1200px;margin:32px auto;padding:0 20px;color:#172033}}table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid #ddd}}th{{background:#eef2ff}}pre{{white-space:pre-wrap;max-width:360px}}.stats{{padding:16px;background:#f5f7fb;border-radius:10px}}</style>
    <h1>BÃ¡o cÃ¡o Ä‘Ã¡nh giÃ¡ prompt</h1><div class="stats"><b>Task:</b> {html.escape(report['task_description'])}<br><b>Model:</b> {html.escape(report['model'])}<br><b>Äiá»ƒm trung bÃ¬nh:</b> {report['average_score']}/10<br><b>Tá»‰ lá»‡ Ä‘áº¡t (â‰¥7):</b> {report['pass_rate']}%</div>
    <h2>Káº¿t quáº£ tá»«ng test case</h2><table><thead><tr><th>TÃ¬nh huá»‘ng</th><th>Input</th><th>Output</th><th>Äiá»ƒm</th><th>Nháº­n xÃ©t</th></tr></thead><tbody>{''.join(rows)}</tbody></table></html>"""
        path = self.data_dir / f"report-{report_id}.html"
        path.write_text(page, encoding="utf-8")
        return path.name
    
    
    def safe_report_path(self, filename: str) -> Path:
        if not re.fullmatch(r"(dataset|report)-[a-f0-9]{32}\.(json|html)", filename):
            raise FileNotFoundError(filename)
        path = self.data_dir / filename
        if not path.is_file():
            raise FileNotFoundError(filename)
        return path
    
    

