import asyncio
import hashlib
import html
import json
import math
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

import tiktoken
from app.config import settings
from app.common.gemini.client import GeminiClient
from app.module.dataset.service import DatasetService

list_model = [
    "gemini-3.1-flash-lite",
	"gemini-3.8-flash",
	"gemini-3.6-flash",
	"gemini-3.5-flash-lite",
    "gemini-3-flash",
	"gemini-2.5-flash-lite",
	"gemini-2.5-flash"
]

low_model="gemini-3.1-flash-lite"
medium_model="gemini-3.5-flash-lite"
high_model="gemini-3.8-flash"

complex_keywords_vi = [
    "phân tích", "so sánh", "code", "thuật toán", "lập kế hoạch", 
    "tại sao", "giải thích chi tiết", "tối ưu", "kiến trúc"
]

complex_keywords_en = [
    "analyze", "compare", "code", "algorithm", "plan", 
    "why", "explain in detail", "optimize", "architecture"
]

strict_precision_keywords = [
    "code", "lập trình", "thuật toán", "sửa lỗi", "debug", "sql", "json", "regex",
    "trích xuất", "chuyển đổi format", "tóm tắt", "dịch", "mã số thuế", 
    "tính toán", "công thức", "định nghĩa", "chuẩn hóa", "bảng", "schema",
    "refactor", "extract", "format", "convert", "translate", "summarize",
    "parse", "calculate", "equation", "definition", "fix bug", "unit test"
]

balanced_creative_keywords = [
    "phân tích", "so sánh", "đánh giá", "lập kế hoạch", "giải thích chi tiết",
    "tối ưu", "kiến trúc", "ưu nhược điểm", "gợi ý", "đề xuất", "viết email",
    "luận điểm", "báo cáo", "chiến lược", "hướng dẫn", "tại sao",
    
    "analyze", "compare", "evaluate", "plan", "explain", "optimize", 
    "architecture", "pros and cons", "suggest", "propose", "strategy", 
    "recommend", "guide", "report", "why"
]

full_creative_keywords = [
    "thơ", "bài thơ", "kịch bản", "câu chuyện", "tiểu thuyết", "sáng tác",
    "brainstorm", "slogan", "đặt tên", "ý tưởng độc lạ", "out of the box",
    "viết tiếp", "truyện", "caption bay bổng", "twist", "phong cách",
    
    "poem", "poetry", "script", "story", "novel", "creative writing",
    "name idea", "catchphrase", "out of the box", "fiction", "plot twist",
    "reimagine", "fantasy", "roleplay"
]

# Easy
def assess_complexity(prompt: str) -> str:
    gemini = GeminiClient()
    word_count = len(prompt.split())
    
    
    choose_model = low_model
    temperature = 0.5
    
    if word_count > 300 or any(keyword in prompt.lower() for keyword in complex_keywords_vi + complex_keywords_en):
        choose_model = high_model
    
    if(word_count > 150):
        choose_model = medium_model
    
    if(word_count <= 150):
        choose_model = low_model
        
    if(any(keyword in prompt.lower() for keyword in full_creative_keywords)):
        choose_model = high_model
        temperature = 1
        
    if(any(keyword in prompt.lower() for keyword in balanced_creative_keywords)):
        temperature = 0.5
    
    if(any(keyword in prompt.lower() for keyword in strict_precision_keywords)):
        temperature = 0.2
        
    result= gemini.generate(
            prompt,
            model=choose_model,
            temperature=temperature,
        )
    
    return result

async def generate_dataset_scoring_question_complexity(
    num_cases: int,
    temperature: float = 0.5,
) -> str:
    gemini = GeminiClient()

    prompt = f"""
    You are a professional data engineer.
    Task: Generate {num_cases} unique test cases for each complexity tier (LOW, MEDIUM, HIGH).
    Total output: {num_cases * 3} test cases.

    Output ONLY valid JSON array, no explanations:

    <example>
        [
            {{"id": "tc_01", "prompt": "Thủ đô của Việt Nam là gì", "category": "qa", "expected_tier": "LOW", "temperature": "0"}},
            {{"id": "tc_02", "prompt": "So sánh Python vs Node.js", "category": "comparison", "expected_tier": "MEDIUM", "temperature": "0.3"}},
            {{"id": "tc_03", "prompt": "Tối ưu QuickSort algorithm", "category": "coding", "expected_tier": "HIGH", "temperature": "0.5"}}
            {{"id": "tc_01", "prompt": "Đưa cho tôi 1 vài ví dụ gợi ý phối đồ với áo sơ mi trắng", "category": "style", "expected_tier": "LOW", "temperature": "1"}},
            {{"id": "tc_02", "prompt": "Thiết kế API endpoint cho chức năng đăng nhập", "category": "comparison", "expected_tier": "MEDIUM", "temperature": "0.3"}},
            {{"id": "tc_03", "prompt": "Phân tích chiến lược di chuyển dữ liệu (Data Migration) không downtime", "category": "coding", "expected_tier": "HIGH", "temperature": "0.8"}}
        ]
    </example>

    Rules:
    - Return ONLY JSON array
    - No explanations, no markdown
    - Each test case must be unique and realistic
    - Assign tier based on complexity
    
    """

    result = gemini.generate(
        prompt=prompt,
        model="gemini-3.1-flash-lite",
        temperature=temperature,
        max_output_tokens=4000,
    )

    dataset_value = json.loads(result)
    if not isinstance(dataset_value, list):
        raise ValueError("Gemini dataset output must be a JSON array.")

    print(f"dataset_value: {dataset_value}")
    
    record = await DatasetService.upsert(
        module="multi_model_smart",
        key="dataset_scoring_question_complexity",
        value=dataset_value,
    )
    
    print(f"record: {record}")
    

    return result

def _build_classifier_prompt(
    user_prompt: str,
) -> tuple[str, dict[str, str]]:
    
    system_prompt ="""
        You are a senior LLM Evaluator + Prompt Engineering Expert.
        Analyze the user prompt into and determine its level of complexity tiers: LOW, MEDIUM, HIGH.
    """

    xml_tag = """
        <rules>
            LOW: Simple, straightforward, and easy to understand. Requires minimal reasoning or domain knowledge.
            MEDIUM: Moderately complex, requiring some reasoning, analysis, or domain knowledge.
            HIGH: Complex, requiring advanced reasoning, deep domain knowledge, or creative problem-solving.
        </rules>
    """

    few_shot_prompting = """
        <examples>
            <example>
                <user_prompt>Tên của các hành tinh trong hệ mặt trời</user_prompt>
                {
                    expected_tier: 'LOW',
                    temperature: '0'
                }
            </example>
            <example>
                <user_prompt>Viết một câu cảm thán về thời tiết miền bắc Việt Nam</user_prompt>
                {
                    expected_tier: 'LOW',
                    temperature: '0.5'
                }
            </example>
            <example>
                <user_prompt>Viết một câu đố vui về con mèo</user_prompt>
                {
                    expected_tier: 'LOW',
                    temperature: '1'
                }
            </example>
            <example>
                <user_prompt>Viết code JavaScript để lấy dữ liệu từ API và hiển thị lên console</user_prompt>
                <response>
                {
                    expected_tier: 'MEDIUM',
                    temperature: '0.2'
                }
                </response>
            </example>
            <example>
                <user_prompt>Giải thích nguyên lý hoạt động của Blockchain</user_prompt>
                <response>
                {
                    expected_tier: 'MEDIUM',
                    temperature: '0.4'
                }
                </response>
            </example>
            <example>
                <user_prompt>Viết một kịch bản ngắn cho video quảng cáo sản phẩm cà phê</user_prompt>
                <response>
                {
                    expected_tier: 'MEDIUM',
                    temperature: '0.7'
                }
                </response>
            </example>              
            <example>
                <user_prompt>Phân tích các rào cản pháp lý khi triển khai hệ thống định danh số quốc giau</user_prompt>
                <response>
                {
                    expected_tier: 'HIGH',
                    temperature: '0.5'
                }
                </response>
            </example>
            <example>
                <user_prompt>Thiết kế hệ thống gợi ý sản phẩm (Recommendation System) dựa trên Collaborative Filtering</user_prompt>
                <response>
                {
                    expected_tier: 'HIGH',
                    temperature: '0.3'
                }
                </response>
            </example>
            <example>
                <user_prompt>Đánh giá tác động của biến đổi khí hậu đối với an ninh lương thực toàn cầu</user_prompt>
                <response>
                {
                    expected_tier: 'HIGH',
                    temperature: '0.7'
                }
                </response>
            </example>
        </examples>
    """

    chain_of_thought_prompting = """
        <reasoning>
            Analyze the user prompt and determine its complexity tier based on the provided rules and examples.
            Consider factors such as reasoning required, domain knowledge, and problem-solving complexity.
        </reasoning>
    """

    prompt = f"""
        {system_prompt}

        Return ONLY a valid JSON object with this shape:
        {{"expected_tier": "LOW|MEDIUM|HIGH", "temperature": 0.0}}
        Set temperature between 0.0 and 1.0 based on the response style needed.
        Do not include explanations or markdown.
        <user_prompt>{user_prompt}</user_prompt>

        {xml_tag}
        {few_shot_prompting}
        {chain_of_thought_prompting}
    """

    return prompt, {
        "system_prompt": system_prompt,
        "rules": xml_tag,
        "few_shot_examples": few_shot_prompting,
        "reasoning_instructions": chain_of_thought_prompting,
        "user_prompt": user_prompt,
    }


def classify_prompt_llm(user_prompt: str) -> dict[str, str | float]:
    gemini = GeminiClient()
    prompt, _ = _build_classifier_prompt(user_prompt)
    result = gemini.generate(
        prompt=prompt,
        model="gemini-3.1-flash-lite",
        temperature=0.3,
        max_output_tokens=5000,
    )

    normalized_result = result.strip()
    if normalized_result.startswith("```json"):
        normalized_result = normalized_result[7:]
    elif normalized_result.startswith("```"):
        normalized_result = normalized_result[3:]
    if normalized_result.endswith("```"):
        normalized_result = normalized_result[:-3]

    try:
        classification = json.loads(normalized_result.strip())
    except json.JSONDecodeError as exc:
        raise ValueError("Prompt classifier returned invalid JSON") from exc
    if not isinstance(classification, dict):
        raise ValueError("Prompt classifier result must be a JSON object")

    expected_tier = str(classification.get("expected_tier", "")).upper()
    if expected_tier not in {"LOW", "MEDIUM", "HIGH"}:
        raise ValueError(f"Prompt classifier returned invalid tier: {expected_tier}")
    try:
        classified_temperature = float(classification["temperature"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Prompt classifier returned an invalid temperature") from exc
    if not 0.0 <= classified_temperature <= 2.0:
        raise ValueError("Prompt classifier temperature must be between 0.0 and 2.0")

    return {
        "expected_tier": expected_tier,
        "temperature": classified_temperature,
    }


def _save_classifier_report(report: dict) -> Path:
    """Write a standalone HTML report and return its absolute path."""
    report_dir = Path(__file__).resolve().parent / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"classifier-evaluation-{uuid.uuid4().hex}.html"

    def text(value: object) -> str:
        return html.escape(str(value)) if value is not None else "—"

    rows = []
    for case in report["results"]:
        status = ("Đúng" if case.get("tier_correct") else "Sai") if case["success"] else "Lỗi"
        rows.append(
            "<tr>"
            f"<td>{text(case['case_index'])}</td>"
            f"<td>{text(case.get('id'))}</td>"
            f"<td class=\"prompt\">{text(case['prompt'])}</td>"
            f"<td>{text(case['expected_tier'])}</td>"
            f"<td>{text(case.get('predicted_tier'))}</td>"
            f"<td>{text(case.get('expected_temperature'))}</td>"
            f"<td>{text(case.get('predicted_temperature'))}</td>"
            f"<td>{text(case.get('temperature_absolute_error'))}</td>"
            f"<td>{text(case.get('matching_score'))}</td>"
            f"<td>{'Có' if case['matches_few_shot_example'] else 'Không'}</td>"
            f"<td>{text(case['token_counts']['full_prompt'])}</td>"
            f"<td>{text(case['token_counts']['user_prompt'])}</td>"
            f"<td>{text(case['token_counts']['system_prompt'])} / {text(case['token_counts']['rules'])} / {text(case['token_counts']['few_shot_examples'])} / {text(case['token_counts']['reasoning_instructions'])}</td>"
            f"<td>{text(status)}</td>"
            f"<td>{text(case.get('error'))}</td>"
            "</tr>"
        )
    created_at = datetime.now(UTC).isoformat(timespec="seconds")
    page = f"""<!doctype html>
    <html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Báo cáo đánh giá classifier</title>
    <style>
    body {{ font: 16px system-ui, sans-serif; color: #172033; margin: 32px; }}
    .summary {{ background: #f3f6fb; padding: 16px; border-radius: 8px; }}
    .table-wrap {{ overflow-x: auto; }} table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ text-align: left; vertical-align: top; border-bottom: 1px solid #ddd; padding: 10px; }}
    th {{ background: #eef2ff; }} .prompt {{ white-space: pre-wrap; min-width: 250px; }}
    </style></head><body>
    <h1>Báo cáo đánh giá prompt phân loại</h1>
    <div class="summary">
    <p>Dataset: {text(report['dataset_id'])} · Tạo lúc (UTC): {text(created_at)}</p>
    <p>Tổng case: {text(report['total_cases'])} · Thành công: {text(report['successful_cases'])} · Lỗi: {text(report['failed_cases'])}</p>
    <p>Phân loại đúng: {text(report['correct_tier_cases'])} · Độ chính xác: {text(report['tier_accuracy_percent'])}%</p>
    <p>Điểm matching trung bình (case thành công): {text(report['average_matching_score_successful'])}/100 · Điểm trung bình trên tất cả case: {text(report['average_matching_score_all_cases'])}/100</p>
    <p>Prompt SHA-256: {text(report['classifier_prompt_sha256'])} · Case trùng ví dụ few-shot: {text(report['few_shot_overlap_cases'])}</p>
    <p>Matching: tier đúng = 100, sai = 0; temperature = 100 × (1 − |dự đoán − mong đợi| / 2). Nếu có temperature tham chiếu, điểm case là trung bình hai điểm; nếu không có, chỉ dùng điểm tier. Case lỗi được tính 0 trong điểm trung bình trên tất cả case.</p>
    <p>Sai số temperature trung bình (MAE): {text(report['temperature_mae'])} · Số case được tính: {text(report['temperature_evaluated_cases'])}</p>
    <p>Token input ước tính cho toàn bộ case: {text(report['total_estimated_input_tokens'])} (tiktoken cl100k_base).</p>
    <p>Đây là ước tính theo tokenizer của tiktoken, không phải số token thực tế của Gemini; tổng bao gồm cả case bị lỗi. Số token toàn prompt được đếm trực tiếp; các phần đếm riêng có thể không cộng chính xác thành tổng.</p>
    <p>Độ chính xác tính trên tổng số case, bao gồm các lượt lỗi. Temperature MAE chỉ tính các lượt thành công có giá trị tham chiếu.</p>
    </div>
    <h2>Chi tiết từng case</h2><div class="table-wrap"><table><thead><tr>
    <th>#</th><th>ID</th><th>Prompt</th><th>Tier mong đợi</th><th>Tier dự đoán</th>
    <th>Temperature mong đợi</th><th>Temperature dự đoán</th><th>Sai số temperature</th><th>Matching /100</th><th>Trùng ví dụ</th><th>Token prompt đầy đủ</th><th>Token input</th><th>Token system / rules / examples / reasoning</th><th>Kết quả</th><th>Lỗi</th>
    </tr></thead><tbody>{''.join(rows)}</tbody></table></div></body></html>"""
    path.write_text(page, encoding="utf-8")
    return path


async def score_classify_prompt() -> dict:
    stored = await DatasetService.get_by_key(
        module="multi_model_smart", key="dataset_scoring_question_complexity"
    )
    if stored is None:
        raise LookupError("Classifier evaluation dataset not found")
    if not isinstance(stored.value, list) or not stored.value:
        raise ValueError("Classifier evaluation dataset must be a non-empty list")

    cases = []
    for index, case in enumerate(stored.value, start=1):
        if not isinstance(case, dict):
            raise ValueError(f"Dataset case {index} must be an object")
        prompt = case.get("prompt")
        tier = case.get("expected_tier")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"Dataset case {index} must have a non-empty prompt")
        if not isinstance(tier, str) or tier.upper() not in {"LOW", "MEDIUM", "HIGH"}:
            raise ValueError(f"Dataset case {index} has an invalid expected_tier")
        expected_temperature = case.get("temperature")
        if expected_temperature is not None:
            try:
                if isinstance(expected_temperature, bool):
                    raise ValueError
                expected_temperature = float(expected_temperature)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Dataset case {index} has an invalid temperature") from exc
            if not math.isfinite(expected_temperature) or not 0 <= expected_temperature <= 2:
                raise ValueError(f"Dataset case {index} has an invalid temperature")
        cases.append((case, prompt, tier.upper(), expected_temperature))

    encoding = tiktoken.get_encoding("cl100k_base")
    template, template_parts = _build_classifier_prompt("{{user_prompt}}")
    prompt_hash = hashlib.sha256(template.encode("utf-8")).hexdigest()
    normalize = lambda value: " ".join(value.casefold().split())
    examples = {
        normalize(value)
        for value in re.findall(
            r"<user_prompt>(.*?)</user_prompt>",
            template_parts["few_shot_examples"],
            flags=re.DOTALL,
        )
    }
    results = []
    temperature_errors = []
    correct = 0
    failures = 0
    
    for index, (case, prompt, tier, expected_temperature) in enumerate(cases, start=1):
        full_prompt, parts = _build_classifier_prompt(prompt)
        token_counts = {
            name: len(encoding.encode(value, disallowed_special=()))
            for name, value in parts.items()
        }
        token_counts["full_prompt"] = len(encoding.encode(full_prompt, disallowed_special=()))
        row = {
            "case_index": index,
            "id": case.get("id"),
            "prompt": prompt,
            "expected_tier": tier,
            "expected_temperature": expected_temperature,
            "token_counts": token_counts,
            "matches_few_shot_example": normalize(prompt) in examples,
        }
        try:
            prediction = await asyncio.to_thread(classify_prompt_llm, user_prompt=prompt)
        except Exception as exc:
            failures += 1
            row.update({"success": False, "error": str(exc)})
        else:
            is_correct = prediction["expected_tier"] == tier
            correct += int(is_correct)
            row.update({
                "success": True,
                "predicted_tier": prediction["expected_tier"],
                "predicted_temperature": prediction["temperature"],
                "tier_correct": is_correct,
            })
            tier_score = 100.0 if is_correct else 0.0
            row["tier_matching_score"] = tier_score
            if expected_temperature is not None:
                error = abs(prediction["temperature"] - expected_temperature)
                temperature_errors.append(error)
                row["temperature_absolute_error"] = round(error, 3)
                temperature_score = 100 * max(0.0, 1 - error / 2)
                row["temperature_matching_score"] = round(temperature_score, 2)
                row["matching_score"] = round((tier_score + temperature_score) / 2, 2)
            else:
                row["temperature_matching_score"] = None
                row["matching_score"] = tier_score
        results.append(row)

    report = {
        "dataset_id": str(stored.id),
        "total_cases": len(cases),
        "successful_cases": len(cases) - failures,
        "failed_cases": failures,
        "correct_tier_cases": correct,
        "tier_accuracy_percent": round(correct * 100 / len(cases), 2),
        "classifier_prompt_sha256": prompt_hash,
        "classifier_model": "gemini-3.1-flash-lite",
        "few_shot_overlap_cases": sum(row["matches_few_shot_example"] for row in results),
        "average_matching_score_successful": (
            round(sum(row["matching_score"] for row in results if row["success"]) / (len(cases) - failures), 2)
            if len(cases) > failures else None
        ),
        "average_matching_score_all_cases": round(
            sum(row.get("matching_score", 0) for row in results) / len(cases), 2
        ),
        "temperature_evaluated_cases": len(temperature_errors),
        "tokenizer": "tiktoken cl100k_base (estimate; not Gemini tokenizer)",
        "total_estimated_input_tokens": sum(row["token_counts"]["full_prompt"] for row in results),
        "temperature_mae": (
            round(sum(temperature_errors) / len(temperature_errors), 3)
            if temperature_errors else None
        ),
        "results": results,
    }
    report["html_report_path"] = str(await asyncio.to_thread(_save_classifier_report, report))
    return report


def smart_route_prompt(prompt: str, *, max_output_tokens: int = 2000) -> dict[str, str | float]:
    classification = classify_prompt_llm(user_prompt=prompt)
    tier = str(classification.get("expected_tier", "")).upper()
    if tier not in {"LOW", "MEDIUM", "HIGH"}:
        raise ValueError(f"Prompt classifier returned unsupported tier: {tier}")

    try:
        temperature = float(classification["temperature"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Prompt classifier did not return a valid temperature") from exc
    if not 0.0 <= temperature <= 2.0:
        raise ValueError("Prompt classifier temperature must be between 0.0 and 2.0")

    selected_model = {"LOW": low_model, "MEDIUM": medium_model, "HIGH": high_model}[tier]
    answer = GeminiClient().generate(
        prompt=prompt,
        model=selected_model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )
    return {
        "tier": tier,
        "model": selected_model,
        "temperature": temperature,
        "response": answer,
    }



    
   

