"""
简单的论文分析功能测试
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from autoforge.crawler import PapersWithCodeCrawler
from autoforge.crawler.paper_downloader import PaperDownloader
from autoforge.analyzers.paper_analyzer import PaperAnalyzer
from autoforge.llm import BaiLianClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_basic_functionality():
    """测试基本功能"""
    
    logger.info("开始测试论文分析基本功能...")
    
    # 1. 测试LLM客户端初始化
    api_key = os.environ.get("BAILIAN_API_KEY")
    model = os.environ.get("BAILIAN_MODEL", "qwen-plus")
    
    if not api_key:
        logger.warning("未设置BAILIAN_API_KEY环境变量，将跳过LLM相关测试")
        llm_client = None
    else:
        try:
            llm_client = BaiLianClient(api_key=api_key, model=model)
            logger.info("✓ LLM客户端初始化成功")
        except Exception as e:
            logger.error(f"✗ LLM客户端初始化失败: {e}")
            return False
    
    # 2. 测试输出目录创建
    try:
        output_dir = Path("outputs/test_paper_analysis")
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("✓ 输出目录创建成功")
    except Exception as e:
        logger.error(f"✗ 输出目录创建失败: {e}")
        return False
    
    # 3. 测试组件初始化
    try:
        pwc_crawler = PapersWithCodeCrawler(output_dir=str(output_dir / "pwc_results"))
        logger.info("✓ PapersWithCodeCrawler 初始化成功")
        
        paper_downloader = PaperDownloader(output_dir=str(output_dir / "papers"))
        logger.info("✓ PaperDownloader 初始化成功")
        
        paper_analyzer = PaperAnalyzer(llm_client=llm_client, output_dir=str(output_dir))
        logger.info("✓ PaperAnalyzer 初始化成功")
        
    except Exception as e:
        logger.error(f"✗ 组件初始化失败: {e}")
        return False
    
    # 4. 测试论文搜索（使用多个不同的搜索词）
    search_terms = [
        "attention mechanism",  # 更具体的术语
        "bert model",          # 具体的模型名
        "neural network",      # 通用术语
        "deep learning"        # 通用术语
    ]
    
    search_success = False
    for search_term in search_terms:
        try:
            logger.info(f"测试搜索词: '{search_term}'")
            papers = pwc_crawler.search_papers(search_term, top_k=3)
            if papers:
                logger.info(f"✓ 搜索 '{search_term}' 成功，找到 {len(papers)} 篇论文")
                for i, paper in enumerate(papers):
                    logger.info(f"  论文 {i+1}: {paper.get('title', '未知标题')}")
                search_success = True
                break
            else:
                logger.warning(f"! 搜索 '{search_term}' 未返回结果")
        except Exception as e:
            logger.error(f"✗ 搜索 '{search_term}' 失败: {e}")
    
    if not search_success:
        logger.warning("! 所有搜索词都未返回结果，可能是网站结构变化")
    
    logger.info("基本功能测试完成！")
    return True


if __name__ == "__main__":
    success = test_basic_functionality()
    if success:
        logger.info("🎉 所有基本功能测试通过！")
    else:
        logger.error("❌ 部分功能测试失败")
        sys.exit(1) 