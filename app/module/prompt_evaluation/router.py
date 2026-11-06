import html
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from app.common.gemini.client import GeminiClient
from app.module.prompt_evaluation.schemas import DatasetRequest, EvaluateRequest
from app.module.prompt_evaluation.service import (
    DATA_DIR,
    evaluate_prompt,
    generate_dataset,
    load_dataset_url,
    safe_report_path,
    save_report,
)


router = APIRouter(prefix="/prompt-evaluation", tags=["Prompt Evaluation"])


def get_gemini() -> GeminiClient:
    try:
        return GeminiClient()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/datasets", status_code=201)
def create_dataset(body: DatasetRequest) -> dict:
    try:
        dataset = generate_dataset(body, get_gemini())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Dataset generation failed: {exc}") from exc
    dataset_id = dataset["id"]
    return {
        "dataset_id": dataset_id,
        "test_case_count": len(dataset["test_cases"]),
        "human_cases": sum(case["source"] == "human" for case in dataset["test_cases"]),
        "generated_cases": sum(case["source"] == "generated" for case in dataset["test_cases"]),
        "json_url": f"/prompt-evaluation/files/dataset-{dataset_id}.json",
        "datasets_html_url": "/prompt-evaluation/datasets",
    }


@router.get("/datasets", response_class=HTMLResponse)
def list_datasets() -> HTMLResponse:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(DATA_DIR.glob("dataset-*.json"), reverse=True):
        try:
            dataset = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        rows.append(
            f"<tr><td>{html.escape(dataset.get('created_at', ''))}</td>"
            f"<td>{html.escape(dataset.get('task_description', ''))}</td>"
            f"<td>{len(dataset.get('test_cases', []))}</td>"
            f"<td><a href='/prompt-evaluation/files/{html.escape(path.name)}'>JSON</a></td></tr>"
        )
    page = """<!doctype html><html lang="vi"><meta charset="utf-8"><title>Prompt datasets</title>
<style>body{font:16px system-ui;max-width:1000px;margin:32px auto;padding:0 20px}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:12px;border-bottom:1px solid #ddd}th{background:#eef2ff}</style>
<h1>Prompt evaluation datasets</h1><table><thead><tr><th>Tạo lúc</th><th>Task</th><th>Số test case</th><th>Tệp</th></tr></thead><tbody>""" + "".join(rows) + "</tbody></table></html>"
    return HTMLResponse(page)


@router.post("/evaluate")
def run_evaluation(body: EvaluateRequest) -> dict:
    try:
        dataset = load_dataset_url(str(body.dataset_url))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        report = evaluate_prompt(body.prompt, dataset, get_gemini())
        html_file = save_report(report)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Prompt evaluation failed: {exc}") from exc
    return {
        "report_id": report["id"],
        "model": report["model"],
        "test_case_count": len(report["results"]),
        "average_score": report["average_score"],
        "pass_rate": report["pass_rate"],
        "html_report_url": f"/prompt-evaluation/files/{html_file}",
        "json_report_url": f"/prompt-evaluation/files/report-{report['id']}.json",
    }


@router.get("/files/{filename}")
def get_file(filename: str):
    try:
        path = safe_report_path(filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc
    if path.suffix == ".html":
        return HTMLResponse(path.read_text(encoding="utf-8"))
    return JSONResponse(json.loads(path.read_text(encoding="utf-8")))

