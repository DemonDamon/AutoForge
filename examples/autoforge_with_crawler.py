"""
AutoForge 集成爬虫功能示例
演示如何在AutoForge工作流中使用爬虫获取最新模型信息
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from autoforge import AutoForgeAgent
from autoforge.llm import OpenAIClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def demo_with_crawler():
    """演示集成爬虫的AutoForge工作流"""
    
    # 1. 初始化LLM客户端
    print("📝 初始化LLM客户端...")
    try:
        llm_client = OpenAIClient(
            # api_key="your-api-key-here",  # 或从环境变量读取
            model="gpt-4"
        )
        
        # 验证连接
        if llm_client.validate_connection():
            print("✅ LLM连接正常")
        else:
            print("❌ LLM连接失败")
            return
    except Exception as e:
        print(f"❌ 初始化LLM客户端失败: {e}")
        print("\n💡 提示：您可以跳过LLM部分，直接测试爬虫功能")
        llm_client = None
    
    # 2. 创建AutoForge Agent（启用爬虫）
    print("\n📝 创建AutoForge Agent...")
    agent = AutoForgeAgent(
        llm_client=llm_client,
        output_dir="outputs/demo_with_crawler"
    )
    
    # 确保模型搜索器启用了爬虫
    if hasattr(agent.model_searcher, 'use_crawler'):
        print(f"✅ 爬虫状态: {'启用' if agent.model_searcher.use_crawler else '未启用'}")
    
    # 3. 示例需求
    requirements = [
        {
            "name": "中文文本分类",
            "description": """
            我需要一个中文文本分类模型，用于对新闻文章进行分类。
            
            具体要求：
            1. 输入：中文新闻文章文本（100-1000字）
            2. 输出：新闻类别（政治、经济、科技、体育、娱乐）
            3. 准确率要求：>90%
            4. 推理速度：<100ms/条
            5. 部署环境：CPU服务器
            """,
            "expected_task": "text-classification"
        },
        {
            "name": "语音识别",
            "description": """
            我需要一个语音识别模型，能够将中文语音转换为文字。
            
            要求：
            1. 支持中文普通话
            2. 支持实时转录
            3. 准确率>95%
            4. 支持噪音环境
            """,
            "expected_task": "automatic-speech-recognition"
        }
    ]
    
    # 4. 执行分析（可以选择一个需求）
    print("\n请选择要分析的需求：")
    for i, req in enumerate(requirements):
        print(f"{i+1}. {req['name']}")
    
    choice = input("\n请输入选择 (1-2): ").strip()
    
    if choice not in ["1", "2"]:
        print("使用默认需求（中文文本分类）")
        choice = "1"
    
    selected_req = requirements[int(choice) - 1]
    
    # 5. 执行需求分析
    print(f"\n📝 分析需求: {selected_req['name']}")
    
    if llm_client:
        # 完整流程
        try:
            # 需求分析
            req_result = agent.analyze_requirements(
                manual_description=selected_req['description']
            )
            print("✅ 需求分析完成")
            
            # 模型搜索（集成爬虫）
            print("\n🔍 开始模型搜索（将自动爬取HuggingFace最新模型）...")
            model_result = agent.search_models()
            
            print("✅ 模型搜索完成")
            
            # 检查是否成功爬取了模型
            if model_result.get('crawled_models'):
                print(f"\n📊 爬取到 {len(model_result['crawled_models'])} 个相关模型:")
                for model in model_result['crawled_models'][:5]:
                    print(f"  - {model.get('model_id', 'Unknown')}")
            
            print(f"\n📁 完整结果保存在: {agent.output_dir}")
            
        except Exception as e:
            print(f"\n❌ 分析过程出错: {e}")
    
    else:
        # 仅测试爬虫功能
        print("\n🔍 仅测试爬虫功能...")
        demo_crawler_only(selected_req)


def demo_crawler_only(requirement):
    """仅测试爬虫功能（不使用LLM）"""
    from autoforge.crawler import HuggingFaceCrawler
    
    crawler = HuggingFaceCrawler(
        output_dir="outputs/demo_with_crawler/hf_models"
    )
    
    # 根据需求爬取相关模型
    task_tag = requirement['expected_task']
    print(f"\n爬取任务 '{task_tag}' 的相关模型...")
    
    try:
        # 爬取不同排序方式的模型
        for sort in ['trending', 'downloads']:
            print(f"\n按 {sort} 排序爬取...")
            models = crawler.crawl_models_by_task(
                task_tag=task_tag,
                sort=sort,
                top_k=5
            )
            
            print(f"成功爬取 {len(models)} 个模型:")
            for model in models:
                print(f"  - {model.get('model_id', 'Unknown')} "
                      f"(下载: {model.get('downloads', 'N/A')}, "
                      f"点赞: {model.get('likes', 'N/A')})")
    
    except Exception as e:
        print(f"爬取失败: {e}")


def demo_advanced_search():
    """演示高级搜索功能"""
    print("\n=== 高级搜索功能演示 ===\n")
    
    from autoforge.analyzers import ModelSearcher
    from autoforge.crawler import TaskManager
    
    # 创建任务管理器查看所有任务
    task_manager = TaskManager()
    
    # 创建模型搜索器（不需要LLM）
    searcher = ModelSearcher(
        use_crawler=True,
        crawler_config={
            'base_url': 'https://hf-mirror.com',
            'delay': 0.5
        }
    )
    
    # 1. 显示可用任务
    print("可用的任务类型:")
    print(searcher.get_available_tasks())
    
    # 2. 搜索特定关键词的模型
    print("\n搜索关键词 'chinese bert'...")
    try:
        results = searcher.search_models_by_keyword("chinese bert", top_k=5)
        print(f"找到 {len(results)} 个模型:")
        for model in results:
            print(f"  - {model.get('model_id', 'Unknown')}")
    except Exception as e:
        print(f"搜索失败: {e}")


def main():
    """主函数"""
    print("🚀 AutoForge 集成爬虫功能演示\n")
    
    demos = {
        "1": ("完整AutoForge工作流（需要LLM）", demo_with_crawler),
        "2": ("高级搜索功能（不需要LLM）", demo_advanced_search),
    }
    
    print("请选择演示：")
    for key, (name, _) in demos.items():
        print(f"{key}. {name}")
    
    choice = input("\n请输入选择 (1-2): ").strip()
    
    if choice in demos:
        demos[choice][1]()
    else:
        print("运行默认演示...")
        demo_with_crawler()
    
    print("\n\n✅ 演示完成！")
    print("\n💡 提示：")
    print("1. 爬虫功能已集成到ModelSearcher中")
    print("2. 爬取的数据会自动保存到outputs目录")
    print("3. 可以通过crawler_config参数自定义爬虫配置")


if __name__ == "__main__":
    main() 