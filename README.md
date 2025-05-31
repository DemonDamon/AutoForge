# AutoForge
🤖 AutoForge - 基于HuggingFace的全自动化模型优化框架。自动搜索、评估、微调，直到找到最优解决方案！🚀

## 📖 项目简介

AutoForge 是一个智能化的机器学习模型选型和优化框架，它能够：

1. **📋 需求分析**：自动解析多模态文档（PDF/Word/Excel/图片等），理解项目需求
2. **🔍 模型搜索**：基于需求自动在HuggingFace上搜索最优模型
3. **📊 方案设计**：自动设计数据集构建方案和网格化实验方案
4. **🎯 结果分析**：分析实验结果并给出最终选型建议

📁 项目结构
```
AutoForge/
├── autoforge/              # 核心代码
│   ├── __init__.py
│   ├── core.py            # 主Agent类
│   ├── analyzers/         # 分析器组件
│   ├── docparser/         # 文档解析器
│   ├── llm/              # LLM客户端
│   └── prompts/          # 提示词管理
├── examples/              # 使用示例
│   └── quick_start.py
├── outputs/               # 输出目录（自动创建）
├── requirements.txt       # 项目依赖
├── setup.py              # 安装配置
├── config.example.py     # 配置示例
├── test_basic.py         # 基础测试
├── crawler/              # 爬虫模块
│   ├── __init__.py       # 模块初始化
│   ├── hf_crawler.py     # HuggingFace爬虫主类
│   ├── parsers.py        # HTML页面解析器
│   └── task_manager.py   # 任务类型管理器
├── data/
│   └── hf_tasks.yaml     # HuggingFace任务类型配置（50+任务）
└── README.md             # 详细文档
```

## 🚀 快速开始

### 1. 安装依赖

```bash
# 克隆项目
git clone https://github.com/yourusername/AutoForge.git
cd AutoForge

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置LLM

AutoForge需要一个大语言模型来执行分析任务。目前支持OpenAI API：

```bash
# 设置API密钥
export OPENAI_API_KEY="your-api-key-here"
```

### 3. 运行示例

```python
from autoforge import AutoForgeAgent
from autoforge.llm import OpenAIClient

# 初始化LLM客户端
llm_client = OpenAIClient(model="gpt-4")

# 创建Agent
agent = AutoForgeAgent(llm_client=llm_client)

# 运行完整流程
result = agent.run_full_pipeline(
    manual_description="我需要一个中文文本分类模型..."
)
```

## 📚 详细使用指南

### 1. 需求输入方式

AutoForge支持多种需求输入方式：

#### a) 手动输入描述
```python
agent.analyze_requirements(
    manual_description="你的需求描述..."
)
```

#### b) 解析单个文档
```python
agent.analyze_requirements(
    document_path="path/to/requirement.pdf"
)
```

#### c) 解析文档目录
```python
agent.analyze_requirements(
    document_path="path/to/documents/"
)
```

### 2. 分步执行流程

你可以分步执行各个阶段：

```python
# 步骤1: 需求分析
requirement_result = agent.analyze_requirements(...)

# 步骤2: 模型搜索
model_result = agent.search_models()

# 步骤3.1: 数据集设计
dataset_result = agent.design_dataset()

# 步骤3.2: 实验设计
experiment_result = agent.design_experiments()

# 步骤3.3: 结果分析（需要实验报告）
final_result = agent.analyze_results(
    experiment_reports=[...],
    hardware_info={...}
)
```

### 3. 输出结果

所有分析结果都会保存为Markdown文档，便于查看和分享：

```
outputs/
├── requirement_analysis/      # 需求分析结果
├── model_search/             # 模型搜索结果
├── dataset_design/           # 数据集设计方案
├── experiment_design/        # 实验设计方案
├── result_analysis/          # 最终分析结果
└── autoforge_final_report.md # 汇总报告
```

### 4. HuggingFace爬虫使用 🆕

```python
from autoforge.crawler import HuggingFaceCrawler

# 创建爬虫实例
crawler = HuggingFaceCrawler(
    base_url="https://hf-mirror.com",  # 可以使用镜像站
    output_dir="outputs/hf_models",
    max_workers=4,  # 并发线程数
    delay=1.0       # 请求间隔（秒）
)

# 爬取文本分类任务的热门模型
models = crawler.crawl_models_by_task(
    task_tag="text-classification",
    sort="trending",  # 排序方式: trending/downloads/likes
    top_k=10          # 爬取前10个模型
)

# 爬取特定模型的详细信息
model_info = crawler.crawl_model_card("bert-base-chinese")

# 批量爬取（包括ModelCard）
detailed_models = crawler.crawl_models_batch(
    task_tag="text-classification",
    sort="downloads",
    top_k=5,
    fetch_details=True  # 同时获取详细信息
)
```

### 5. 集成爬虫的模型搜索

```python
# ModelSearcher会自动使用爬虫获取最新模型信息
agent = AutoForgeAgent(llm_client=llm_client)

# 执行模型搜索时会自动爬取相关模型
result = agent.search_models()

# 查看爬取的模型
if result.get('crawled_models'):
    print(f"爬取到 {len(result['crawled_models'])} 个模型")
```

## 🛠️ 高级功能

### 1. 自定义提示词

创建自定义提示词目录：

```python
agent = AutoForgeAgent(
    llm_client=llm_client,
    custom_prompts_dir="path/to/prompts"
)
```

### 2. 实现自定义LLM客户端

```python
from autoforge.llm import BaseLLMClient

class MyLLMClient(BaseLLMClient):
    def generate(self, prompt, **kwargs):
        # 实现你的生成逻辑
        pass
```

### 3. 文档解析器配置

```python
from autoforge.docparser import MultiModalDocParser

parser = MultiModalDocParser(
    use_multimodal=True,  # 使用多模态模型分析图片
    max_workers=8         # 并行处理线程数
)
```

## 📋 核心组件

### 1. 文档解析器 (DocParser)
- 支持格式：PDF, Word, Excel, CSV, 图片, Markdown
- 多线程并行处理
- 自动合并多文档内容

### 2. 分析器 (Analyzers)
- **RequirementAnalyzer**: 需求理解和任务分解
- **ModelSearcher**: HuggingFace模型搜索和推荐（集成爬虫功能）
- **DatasetDesigner**: 数据集构建方案设计
- **ExperimentDesigner**: 网格化实验方案设计
- **ResultAnalyzer**: 实验结果分析和选型建议

### 3. 提示词管理 (PromptManager)
- 内置专业提示词模板
- 支持自定义提示词
- 变量动态替换

### 4. HuggingFace爬虫 (Crawler) 🆕
- **自动爬取模型信息**: 根据任务类型爬取TopK个模型
- **多种排序方式**: trending/downloads/likes/created/updated
- **ModelCard提取**: 自动爬取并保存模型详细文档
- **任务管理**: 内置HuggingFace所有任务类型配置
- **并发爬取**: 支持多线程批量爬取

## 🔧 配置选项

### 环境变量
```bash
OPENAI_API_KEY      # OpenAI API密钥
OPENAI_BASE_URL     # 自定义API端点（可选）
```

### Agent配置
```python
agent = AutoForgeAgent(
    llm_client=llm_client,
    output_dir="outputs",           # 输出目录
    custom_prompts_dir=None,        # 自定义提示词目录
)
```

## 📝 输出示例

### 需求分析结果
- 需求概述
- 算法任务分解
- 评估指标定义
- 数据需求分析
- 技术约束

### 模型推荐结果
- 候选模型列表
- 模型对比分析
- 推荐理由
- 实施建议

### 数据集设计方案
- 数据规模建议
- 数据收集方案
- 标注方案设计
- 质量保证措施

### 实验设计方案
- 超参数网格
- 实验执行计划
- 监控指标
- 报告模板

## 🤝 贡献指南

欢迎贡献代码、提出问题或建议！

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- HuggingFace 社区
- OpenAI
- 所有贡献者

---

**注意**: AutoForge 目前处于活跃开发中，API可能会有变化。建议关注项目更新！

## 🎉 爬虫模块建设完成！

我已经为AutoForge项目成功建设了完整的HuggingFace模型爬虫模块。以下是主要实现内容：

### 📁 新增文件结构

```
<code_block_to_apply_changes_from>
```

### 🚀 核心功能

1. **任务管理系统**
   - 内置50+种HuggingFace任务类型
   - 支持多种排序方式（trending/downloads/likes等）
   - YAML配置文件管理

2. **智能爬虫**
   - 支持爬取TopK个模型（可配置）
   - 自动提取模型信息（ID、名称、下载量、点赞数等）
   - ModelCard详细内容爬取
   - 并发爬取支持

3. **页面解析器**
   - 通用HTML解析器，适应页面变化
   - 多种解析策略，提高成功率

4. **与AutoForge深度集成**
   - ModelSearcher自动调用爬虫
   - 爬取的模型信息增强LLM推荐
   - 本地缓存机制

### 📝 使用示例

```python
# 1. 直接使用爬虫
from autoforge.crawler import HuggingFaceCrawler

crawler = HuggingFaceCrawler()
models = crawler.crawl_models_by_task(
    task_tag="text-classification",
    sort="trending",
    top_k=10
)

# 2. 集成到AutoForge工作流
from autoforge import AutoForgeAgent

agent = AutoForgeAgent(llm_client=llm_client)
result = agent.search_models()  # 自动爬取相关模型
```

### ✅ 测试结果

运行 `python test_crawler.py` 测试结果：
- ✅ 任务管理器：成功加载50个任务类型
- ✅ HTML解析器：解析功能正常
- ✅ HuggingFace爬虫：初始化成功
- ✅ 模型搜索器集成：成功识别任务类型

### 🔧 配置选项

支持灵活配置：
- 爬虫基础URL（支持镜像站）
- 并发线程数
- 请求延迟
- 输出目录

### 📚 文档

- `README.md` - 已更新，添加爬虫功能说明
- `CRAWLER_README.md` - 爬虫模块详细文档
- `requirements.txt` - 已添加必要依赖（beautifulsoup4, requests, pyyaml）

### 💡 下一步建议

1. 运行爬虫示例：`python examples/crawler_demo.py`
2. 测试集成功能：`python examples/autoforge_with_crawler.py`
3. 根据实际HuggingFace页面结构调整解析器
4. 定期更新任务类型配置文件

爬虫模块现已完全集成到AutoForge项目中，可以自动获取HuggingFace最新的模型信息，提升模型推荐的准确性和时效性！
