"""
AutoForge 爬虫功能测试
"""

import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def test_task_manager():
    """测试任务管理器"""
    print("🧪 测试任务管理器...")
    
    try:
        from autoforge.crawler import TaskManager
        
        manager = TaskManager()
        
        # 测试获取所有任务
        all_tasks = manager.get_all_tasks()
        print(f"✅ 成功加载 {len(all_tasks)} 个任务类型")
        
        # 测试获取特定任务
        task = manager.get_task_by_tag("text-classification")
        if task:
            print(f"✅ 找到任务: {task['name']}")
        
        # 测试搜索功能
        results = manager.search_tasks("分类")
        print(f"✅ 搜索'分类'找到 {len(results)} 个结果")
        
        return True
        
    except Exception as e:
        print(f"❌ 任务管理器测试失败: {e}")
        return False


def test_parsers():
    """测试解析器"""
    print("\n🧪 测试HTML解析器...")
    
    try:
        from autoforge.crawler.parsers import HFModelListParser, HFModelCardParser
        
        # 测试模型列表解析器
        test_html = """
        <article>
            <a href="/bert-base-chinese">BERT Base Chinese</a>
            <span>100k</span>
            <span>downloads</span>
        </article>
        """
        
        models = HFModelListParser.parse_model_list(test_html, top_k=1)
        print(f"✅ 解析器测试通过，解析出 {len(models)} 个模型")
        
        return True
        
    except Exception as e:
        print(f"❌ 解析器测试失败: {e}")
        return False


def test_crawler_basic():
    """测试基本爬虫功能"""
    print("\n🧪 测试HuggingFace爬虫...")
    
    try:
        from autoforge.crawler import HuggingFaceCrawler
        
        crawler = HuggingFaceCrawler(
            output_dir="outputs/test_crawler"
        )
        
        print("✅ 爬虫初始化成功")
        
        # 测试获取可用任务
        tasks = crawler.get_available_tasks()
        print("✅ 成功获取任务列表")
        
        return True
        
    except Exception as e:
        print(f"❌ 爬虫测试失败: {e}")
        return False


def test_model_searcher_integration():
    """测试模型搜索器集成"""
    print("\n🧪 测试模型搜索器集成...")
    
    try:
        from autoforge.analyzers import ModelSearcher
        
        # 创建不使用LLM的搜索器
        searcher = ModelSearcher(
            use_crawler=True,
            output_dir="outputs/test_crawler"
        )
        
        print("✅ 模型搜索器初始化成功（已集成爬虫）")
        
        # 测试任务识别
        test_requirements = "我需要一个文本分类模型"
        task = searcher._identify_task_from_requirements(test_requirements)
        if task:
            print(f"✅ 成功识别任务类型: {task['name']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 模型搜索器测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 开始AutoForge爬虫功能测试\n")
    
    tests = [
        ("任务管理器", test_task_manager),
        ("HTML解析器", test_parsers),
        ("HuggingFace爬虫", test_crawler_basic),
        ("模型搜索器集成", test_model_searcher_integration),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"运行测试: {name}")
        print('='*50)
        
        if test_func():
            passed += 1
        else:
            failed += 1
    
    print(f"\n\n📊 测试结果汇总:")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"🏆 总计: {len(tests)}")
    
    if failed == 0:
        print("\n🎉 所有测试通过！")
        print("\n💡 下一步:")
        print("1. 运行爬虫示例: python examples/crawler_demo.py")
        print("2. 运行集成示例: python examples/autoforge_with_crawler.py")
    else:
        print("\n⚠️ 部分测试失败，请检查错误信息")


if __name__ == "__main__":
    main() 