"""
AutoForge 配置示例
"""

# LLM配置
LLM_CONFIG = {
    "provider": "openai",  # 可选: openai, anthropic, azure, custom
    "api_key": "your-api-key-here",  # 或从环境变量读取
    "model": "gpt-4",  # 模型名称
    "base_url": None,  # 自定义API端点（可选）
    "temperature": 0.7,  # 默认生成温度
    "max_tokens": 4000,  # 默认最大token数
}

# 文档解析配置
DOCPARSER_CONFIG = {
    "use_multimodal": True,  # 是否使用多模态模型分析图片
    "multimodal_api_key": None,  # 多模态模型API密钥
    "max_workers": 4,  # 并行处理线程数
    "ocr_language": "chi_sim+eng",  # OCR语言设置
}

# 输出配置
OUTPUT_CONFIG = {
    "base_dir": "outputs",  # 输出根目录
    "save_intermediate": True,  # 是否保存中间结果
    "report_format": "markdown",  # 报告格式
}

# 日志配置
LOGGING_CONFIG = {
    "level": "INFO",  # 日志级别: DEBUG, INFO, WARNING, ERROR
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": None,  # 日志文件路径（None表示不保存到文件）
}

# 提示词配置
PROMPT_CONFIG = {
    "custom_prompts_dir": None,  # 自定义提示词目录
    "language": "zh-CN",  # 提示词语言
}

# 实验配置
EXPERIMENT_CONFIG = {
    "max_experiments": 100,  # 最大实验数量
    "timeout_hours": 24,  # 实验超时时间（小时）
    "early_stop": True,  # 是否启用早停
    "resource_limit": {
        "gpu_memory": "8GB",
        "cpu_cores": 4,
    }
} 