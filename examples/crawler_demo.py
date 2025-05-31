"""
AutoForge HuggingFace爬虫示例
演示如何使用爬虫功能获取最新的模型信息
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from autoforge.crawler import HuggingFaceCrawler, TaskManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def demo_task_manager():
    """演示任务管理器功能"""
    print("\n=== 任务管理器演示 ===\n")
    
    # 创建任务管理器
    task_manager = TaskManager()
    
    # 1. 显示所有可用任务
    print("所有可用的任务类型：")
    print(task_manager.format_task_list())
    
    # 2. 搜索特定任务
    print("\n搜索包含'分类'的任务：")
    tasks = task_manager.search_tasks("分类")
    for task in tasks:
        print(f"- {task['name']} ({task['tag']})")
    
    # 3. 获取特定类别的任务
    print("\n计算机视觉类别的任务：")
    cv_tasks = task_manager.get_tasks_by_category("computer_vision")
    for task in cv_tasks[:5]:  # 只显示前5个
        print(f"- {task['name']}: {task['description']}")


def demo_crawler_basic():
    """演示基本爬虫功能"""
    print("\n=== 基本爬虫功能演示 ===\n")
    
    # 创建爬虫实例
    crawler = HuggingFaceCrawler(
        base_url="https://hf-mirror.com",
        output_dir="outputs/crawler_demo",
        delay=1.0  # 请求间隔1秒
    )
    
    # 1. 爬取文本分类任务的热门模型
    print("爬取文本分类任务的热门模型（Top 5）...")
    try:
        models = crawler.crawl_models_by_task(
            task_tag="text-classification",
            sort="trending",
            top_k=5
        )
        
        print(f"\n成功爬取 {len(models)} 个模型：")
        for i, model in enumerate(models, 1):
            print(f"\n{i}. {model.get('model_id', 'Unknown')}")
            print(f"   名称: {model.get('name', 'N/A')}")
            print(f"   下载量: {model.get('downloads', 'N/A')}")
            print(f"   点赞数: {model.get('likes', 'N/A')}")
            print(f"   链接: {model.get('url', 'N/A')}")
    
    except Exception as e:
        print(f"爬取失败: {e}")
    
    # 2. 查看已爬取的模型
    print("\n\n已爬取的模型列表：")
    crawled = crawler.list_crawled_models()
    for task, files in crawled.items():
        print(f"\n任务 '{task}':")
        for file in files:
            print(f"  - {file}")


def demo_model_card_crawling():
    """演示ModelCard爬取功能"""
    print("\n=== ModelCard爬取演示 ===\n")
    
    crawler = HuggingFaceCrawler(
        output_dir="outputs/crawler_demo"
    )
    
    # 爬取特定模型的详细信息
    model_ids = [
        "fixie-ai/ultravox-v0_5-llama-3_2-1b",  # 从用户提供的例子
        # 可以添加更多模型ID
    ]
    
    for model_id in model_ids:
        print(f"\n爬取模型 '{model_id}' 的详细信息...")
        try:
            model_info = crawler.crawl_model_card(model_id)
            
            print(f"✅ 成功爬取模型信息")
            print(f"   - URL: {model_info.get('url')}")
            print(f"   - 爬取时间: {model_info.get('crawled_at')}")
            
            if 'model_card' in model_info:
                print(f"   - ModelCard长度: {len(model_info['model_card'])} 字符")
                print(f"   - ModelCard预览: {model_info['model_card'][:200]}...")
        
        except Exception as e:
            print(f"❌ 爬取失败: {e}")


def demo_batch_crawling():
    """演示批量爬取功能"""
    print("\n=== 批量爬取演示 ===\n")
    
    crawler = HuggingFaceCrawler(
        output_dir="outputs/crawler_demo",
        max_workers=2  # 使用2个线程并发爬取
    )
    
    # 批量爬取音频转文本任务的模型（包括详细信息）
    print("批量爬取Audio-Text-to-Text任务的模型...")
    
    try:
        models = crawler.crawl_models_batch(
            task_tag="audio-text-to-text",
            sort="downloads",  # 按下载量排序
            top_k=3,  # 爬取前3个
            fetch_details=True  # 获取详细信息
        )
        
        print(f"\n批量爬取完成，共 {len(models)} 个模型")
        
        for model in models:
            print(f"\n模型: {model.get('model_id')}")
            if 'model_card' in model:
                print("  ✓ 已获取ModelCard")
            if 'metadata' in model:
                print("  ✓ 已获取元数据")
            if 'files' in model:
                print(f"  ✓ 已获取文件列表 ({len(model['files'])} 个文件)")
    
    except Exception as e:
        print(f"批量爬取失败: {e}")


def demo_search():
    """演示搜索功能"""
    print("\n=== 搜索功能演示 ===\n")
    
    crawler = HuggingFaceCrawler()
    
    # 搜索关键词
    keywords = ["chinese", "llama", "bert"]
    
    for keyword in keywords:
        print(f"\n搜索关键词 '{keyword}'...")
        try:
            results = crawler.search_models(keyword, top_k=3)
            print(f"找到 {len(results)} 个结果：")
            
            for model in results:
                print(f"  - {model.get('model_id', 'Unknown')}")
        
        except Exception as e:
            print(f"搜索失败: {e}")


def main():
    """主函数"""
    print("🚀 AutoForge HuggingFace爬虫演示\n")
    
    # 选择要运行的演示
    demos = {
        "1": ("任务管理器", demo_task_manager),
        "2": ("基本爬虫功能", demo_crawler_basic),
        "3": ("ModelCard爬取", demo_model_card_crawling),
        "4": ("批量爬取", demo_batch_crawling),
        "5": ("搜索功能", demo_search),
    }
    
    print("请选择要运行的演示：")
    for key, (name, _) in demos.items():
        print(f"{key}. {name}")
    print("0. 运行所有演示")
    
    choice = input("\n请输入选择 (0-5): ").strip()
    
    if choice == "0":
        # 运行所有演示
        for name, func in demos.values():
            print(f"\n{'='*50}")
            func()
    elif choice in demos:
        # 运行选定的演示
        demos[choice][1]()
    else:
        print("无效的选择")
        return
    
    print("\n\n✅ 演示完成！")
    print(f"💡 提示：爬取的数据保存在 outputs/crawler_demo/ 目录中")


if __name__ == "__main__":
    main() 