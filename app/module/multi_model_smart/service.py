import json
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

def classify_prompt_llm(
    user_prompt: str,
) -> dict[str, str | float]:
    gemini = GeminiClient()
    
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


def smart_route_prompt(prompt: str, *, max_output_tokens: int = 2000) -> dict[str, str | float]:
    """Classify a prompt, choose a model from its tier, then answer the prompt."""
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



    
   

