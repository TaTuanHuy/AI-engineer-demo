from app.common.gemini.client import GeminiClient

low_model="gemini-3.1-flash-lite"
medium_model="gemini-3.5-flash"
high_model="gemini-3.6-flash"

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

