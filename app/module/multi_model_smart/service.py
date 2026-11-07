import json
from pathlib import Path
from app.common.gemini.client import GeminiClient

list_model = [
    "gemini-3.1-flash-lite",
	"gemini-3.8-flash",
	"gemini-3.6-flash",
	"gemini-3.5-flash-lite",
    "gemini-3-flash",
	"gemini-2.5-flash-lite",
	"gemini-2.5-flash"
]

low_model="gemini-3.5-flash-lite"
medium_model="gemini-3.6-flash"
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

def generate_dataset_scoring_question_complexity(num_cases: int) -> str:
    gemini = GeminiClient()

    prompt = f"""
    You are a professional data engineer.
    Task: Generate {num_cases} unique test cases for each complexity tier (LOW, MEDIUM, HIGH).
    Total output: {num_cases * 3} test cases.

    Output ONLY valid JSON array, no explanations:

    <example>
        [
            {{"id": "tc_01", "prompt": "Thủ đô của Việt Nam là gì", "category": "qa", "expected_tier": "LOW"}},
            {{"id": "tc_02", "prompt": "So sánh Python vs Node.js", "category": "comparison", "expected_tier": "MEDIUM"}},
            {{"id": "tc_03", "prompt": "Tối ưu QuickSort algorithm", "category": "coding", "expected_tier": "HIGH"}}
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
        temperature=0.3,
        max_output_tokens=4000,
    )

    output_dir = Path(__file__).parent / "outputs"
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "dataset_scoring_question_complexity.json"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result)

    return result

def classify_prompt_llm(user_prompt: str) -> str:
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
                <user_prompt>Liệt kê 3 loại trái cây?</user_prompt>
                <response>LOW</response>
            </example>
            <example>
                <user_prompt>Viết một kịch bản kiểm thử (test case) cho chức năng đăng nhập</user_prompt>
                <response>MEDIUM</response>
            </example>
            <example>
                <user_prompt>Thiết kế hệ thống thanh toán trực tuyến đảm bảo tính toàn vẹn dữ liệu</user_prompt>
                <response>HIGH</response>
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

        Output result LOW or MEDIUM or HARD, no explanations, no reasons:
        <user_prompt>{user_prompt}</user_prompt>

        {xml_tag}
        {few_shot_prompting}
        {chain_of_thought_prompting}
    """

    result = gemini.generate(
        prompt=prompt,
        model="gemini-3.1-flash-lite",
        temperature=0.3,
        max_output_tokens=100,
    )

    print(f"Result: {result}")

    return result



    
   

