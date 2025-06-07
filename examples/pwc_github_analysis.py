#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Papers with Code 论文爬取和GitHub仓库分析示例
"""

import os
import sys
import logging
import json
import time
from pathlib import Path
import traceback
import requests

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from autoforge.crawler import PapersWithCodeCrawler
from autoforge.analyzers import GitHubRepoAnalyzer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pwc_github_analysis.log')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """主函数"""
    # 创建输出目录
    output_dir = Path("outputs/pwc_analysis")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 初始化爬虫和分析器
    pwc_crawler = PapersWithCodeCrawler(
        output_dir=str(output_dir / "papers"),
        max_retries=5,         # 增加重试次数
        timeout=120,           # 更长的超时时间
        delay=2.0              # 更长的请求间隔
    )
    repo_analyzer = GitHubRepoAnalyzer(
        workspace_dir=str(output_dir / "repos"),
        keep_repos=False,      # 分析后删除仓库以节省空间
        output_dir=str(output_dir / "repos_analysis")
    )
    
    trending_papers = []
    area_papers = []
    search_papers = []
    papers_to_analyze = []
    
    # 首先使用搜索功能（直接从用户输入获取搜索关键词）
    try:
        # 使用数字关键词，这种搜索结果丰富
        search_term = "2"  # 关键词可以是数字、模型名称、技术名称等
        logger.info(f"使用关键词搜索论文: {search_term}")
        search_papers = pwc_crawler.search_papers(search_term, top_k=10)
        logger.info(f"搜索到 {len(search_papers)} 篇相关论文")
        
        if search_papers:
            papers_to_analyze = search_papers
            logger.info("将使用搜索结果进行分析")
    except Exception as e:
        logger.error(f"搜索论文失败: {e}")
        logger.debug(traceback.format_exc())
    
    # 如果搜索失败，尝试爬取热门论文
    if not papers_to_analyze:
        try:
            logger.info("开始爬取热门论文...")
            trending_papers = pwc_crawler.crawl_trending_papers(top_k=10)
            logger.info(f"成功爬取 {len(trending_papers)} 篇热门论文")
            papers_to_analyze = trending_papers
        except Exception as e:
            logger.error(f"爬取热门论文失败: {e}")
            logger.debug(traceback.format_exc())
    
    # 如果前两种方式都失败，尝试按研究领域爬取
    if not papers_to_analyze:
        try:
            research_area = "computer-vision"  # 可选: natural-language-processing, reinforcement-learning 等
            logger.info(f"开始爬取 {research_area} 领域论文...")
            area_papers = pwc_crawler.crawl_papers_by_area(research_area, top_k=10)
            logger.info(f"成功爬取 {len(area_papers)} 篇 {research_area} 领域论文")
            papers_to_analyze = area_papers
        except Exception as e:
            logger.error(f"爬取领域论文失败: {e}")
            logger.debug(traceback.format_exc())
    
    # 如果所有爬取方式都失败，则退出
    if not papers_to_analyze:
        logger.error("所有爬取论文的方式都失败，无法继续分析")
        return
    
    # 输出爬取到的论文标题
    logger.info("爬取到的论文:")
    for i, paper in enumerate(papers_to_analyze):
        logger.info(f"{i+1}. {paper.get('title', 'Unknown Title')} - URL: {paper.get('url', 'No URL')}")
    
    # 爬取论文详情（包括GitHub仓库信息）
    detailed_papers = []
    try:
        logger.info("开始获取论文详情...")
        detailed_papers = pwc_crawler.crawl_papers_batch(papers_to_analyze)
        
        # 保存详细结果
        papers_file = output_dir / "detailed_papers.json"
        with open(papers_file, 'w', encoding='utf-8') as f:
            json.dump({
                'count': len(detailed_papers),
                'papers': detailed_papers
            }, f, ensure_ascii=False, indent=2)
        logger.info(f"论文详情已保存至: {papers_file}")
    except Exception as e:
        logger.error(f"获取论文详情失败: {e}")
        logger.debug(traceback.format_exc())
        # 如果获取详情失败，使用基本信息继续
        detailed_papers = papers_to_analyze
    
    # 提取GitHub仓库URL
    repo_urls = []
    for paper in detailed_papers:
        # 尝试从详情中获取仓库
        github_repos = paper.get('github_repos', [])
        if github_repos:
            for repo in github_repos:
                repo_url = repo.get('url', '')
                if repo_url and repo_url not in repo_urls:
                    repo_urls.append(repo_url)
        
        # 如果详情中没有仓库信息，尝试从实现数量猜测是否有实现
        elif paper.get('implementation_count', 0) > 0:
            # 获取论文URL，尝试直接爬取详情
            paper_url = paper.get('url', '')
            if paper_url:
                try:
                    logger.info(f"从论文页面获取仓库链接: {paper_url}")
                    paper_detail = pwc_crawler.crawl_paper_details(paper_url)
                    repos = paper_detail.get('github_repos', [])
                    for repo in repos:
                        repo_url = repo.get('url', '')
                        if repo_url and repo_url not in repo_urls:
                            repo_urls.append(repo_url)
                except Exception as e:
                    logger.error(f"获取论文 {paper_url} 的仓库链接失败: {e}")
    
    logger.info(f"共发现 {len(repo_urls)} 个GitHub仓库")
    
    # 如果没有找到仓库，添加一些已知的好仓库作为示例
    if not repo_urls:
        logger.warning("未找到GitHub仓库链接，使用示例仓库")
        repo_urls = [
            "https://github.com/CompVis/stable-diffusion",
            "https://github.com/facebookresearch/llama",
            "https://github.com/huggingface/transformers"
        ]
    
    # 分析GitHub仓库
    try:
        logger.info("开始分析GitHub仓库...")
        # 限制分析数量，避免耗时过长
        repos_to_analyze = repo_urls[:3]
        analysis_results = repo_analyzer.batch_analyze_repos(repos_to_analyze)
        
        # 保存分析结果
        analysis_file = output_dir / "repo_analysis.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, ensure_ascii=False, indent=2)
        logger.info(f"仓库分析结果已保存至: {analysis_file}")
        
        # 打印分析摘要
        print("\n==== 仓库分析摘要 ====")
        for i, result in enumerate(analysis_results):
            status = result.get('status', 'unknown')
            repo_url = result.get('repo_url', 'N/A')
            
            if status == 'success':
                language_stats = result.get('language_stats', {})
                main_languages = [
                    lang for lang, stats in language_stats.items()
                    if stats.get('percentage', 0) > 5.0
                ]
                
                deps = result.get('dependencies', {})
                has_python = 'python' in deps
                has_js = 'javascript' in deps
                
                readme_len = len(result.get('readme', ''))
                has_readme = readme_len > 0
                
                print(f"\n仓库 {i+1}: {repo_url}")
                print(f"  - 状态: 成功")
                print(f"  - 主要语言: {', '.join(main_languages)}")
                print(f"  - Python依赖: {'是' if has_python else '否'}")
                print(f"  - JavaScript依赖: {'是' if has_js else '否'}")
                print(f"  - README: {'有 (%d 字符)' % readme_len if has_readme else '无'}")
            else:
                print(f"\n仓库 {i+1}: {repo_url}")
                print(f"  - 状态: 失败")
                print(f"  - 原因: {result.get('message', 'Unknown')}")
    except Exception as e:
        logger.error(f"分析GitHub仓库失败: {e}")
        logger.debug(traceback.format_exc())
    
    logger.info("分析完成")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception(f"执行过程中发生错误: {e}") 