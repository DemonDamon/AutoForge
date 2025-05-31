# AutoForge HuggingFace爬虫模块文档

## 🚀 功能概述

AutoForge的爬虫模块提供了自动化爬取HuggingFace模型信息的能力，使得模型搜索器能够获取最新的模型数据，为用户提供更准确的推荐。

## 📋 主要特性

### 1. **任务管理系统**
- 内置50+种HuggingFace任务类型配置
- 支持任务搜索和分类查询
- 配置文件：`autoforge/data/hf_tasks.yaml`

### 2. **智能爬虫**
- 支持多种排序方式：trending, downloads, likes, created, updated
- 可配置爬取数量（TopK）
- 并发爬取支持
- 请求延迟控制，避免过度请求

### 3. **页面解析器**
- 通用的HTML解析器，适应页面结构变化
- 自动提取模型ID、名称、下载量、点赞数等信息
- ModelCard内容提取和保存

### 4. **与AutoForge集成**
- ModelSearcher自动调用爬虫获取最新模型
- 爬取的模型信息会增强LLM的推荐结果
- 所有数据本地缓存，提高效率

## 🛠️ 使用方法

### 基础使用

```python
from autoforge.crawler import HuggingFaceCrawler

# 创建爬虫实例
crawler = HuggingFaceCrawler(
    base_url="https://hf-mirror.com",  # 支持镜像站
    output_dir="outputs/hf_models",
    max_workers=4,
    delay=1.0
)

# 爬取特定任务的模型
models = crawler.crawl_models_by_task(
    task_tag="text-classification",
    sort="trending",
    top_k=10
)

# 爬取模型详细信息
model_info = crawler.crawl_model_card("bert-base-chinese")
```

### 任务管理

```python
from autoforge.crawler import TaskManager

# 创建任务管理器
tm = TaskManager()

# 查看所有任务
print(tm.format_task_list())

# 搜索任务
tasks = tm.search_tasks("分类")

# 获取特定类别的任务
cv_tasks = tm.get_tasks_by_category("computer_vision")
```

### 集成到AutoForge工作流

```python
from autoforge import AutoForgeAgent

# 创建Agent（自动启用爬虫）
agent = AutoForgeAgent(llm_client=llm_client)

# 执行模型搜索时会自动爬取相关模型
result = agent.search_models()

# 爬取的模型信息在result['crawled_models']中
```

## 📁 数据存储

爬取的数据按以下结构组织：

```
outputs/hf_models/
├── text-classification/
│   ├── models_trending_top10.json      # 模型列表
│   └── models_trending_top10_detailed.json  # 详细信息
├── model_cards/
│   └── bert-base-chinese/
│       ├── metadata.json               # 元数据
│       └── README.md                   # ModelCard内容
└── ...
```

## ⚙️ 配置选项

### 爬虫配置

```python
crawler_config = {
    'base_url': 'https://hf-mirror.com',  # HF站点URL
    'output_dir': 'outputs/hf_models',    # 输出目录
    'max_workers': 4,                     # 并发线程数
    'delay': 1.0                          # 请求间隔（秒）
}
```

### ModelSearcher配置

```python
from autoforge.analyzers import ModelSearcher

searcher = ModelSearcher(
    use_crawler=True,              # 启用爬虫
    crawler_config=crawler_config  # 爬虫配置
)
```

## 🎯 使用场景

1. **获取最新模型信息**：定期爬取HuggingFace最新发布的模型
2. **模型趋势分析**：跟踪不同任务类型的热门模型变化
3. **离线模型库**：构建本地的模型信息数据库
4. **增强推荐准确性**：为LLM提供最新的模型数据

## ⚠️ 注意事项

1. **请求频率**：设置合理的delay避免过度请求
2. **镜像站点**：可以使用镜像站提高访问速度
3. **错误处理**：爬虫会自动处理失败的请求
4. **数据更新**：建议定期更新爬取的数据

## 🔧 故障排除

### 常见问题

1. **爬取失败**
   - 检查网络连接
   - 尝试使用镜像站点
   - 增加请求延迟

2. **解析错误**
   - 页面结构可能已更改
   - 查看日志了解详细错误
   - 更新解析器代码

3. **任务类型不匹配**
   - 更新hf_tasks.yaml配置
   - 检查任务标签拼写

## 📝 示例脚本

查看以下示例了解更多用法：
- `examples/crawler_demo.py` - 爬虫功能演示
- `examples/autoforge_with_crawler.py` - 集成使用示例
- `test_crawler.py` - 功能测试脚本 