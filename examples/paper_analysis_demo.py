"""
论文分析示例
展示如何爬取Papers with Code上的论文、下载PDF、分析内容和相关代码仓库
"""

import os
import sys
import logging
from pathlib import Path
import json

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autoforge.crawler import PapersWithCodeCrawler
from autoforge.crawler.paper_downloader import PaperDownloader
from autoforge.analyzers.paper_analyzer import PaperAnalyzer
from autoforge.analyzers.paper_code_analyzer import PaperCodeAnalyzer
from autoforge.llm import BaiLianClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """主函数"""
    
    # 1. 初始化LLM客户端（使用百炼API）
    api_key = os.environ.get("BAILIAN_API_KEY")
    model = os.environ.get("BAILIAN_MODEL", "qwen-plus")
    
    if not api_key:
        logger.warning("未设置BAILIAN_API_KEY环境变量，将无法进行深度分析")
        llm_client = None
    else:
        llm_client = BaiLianClient(
            api_key=api_key,
            model=model
        )
    
    # 2. 设置输出目录
    output_dir = Path("outputs/paper_analysis_demo")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 3. 初始化组件
    pwc_crawler = PapersWithCodeCrawler(output_dir=str(output_dir / "pwc_results"))
    paper_downloader = PaperDownloader(output_dir=str(output_dir / "papers"))
    paper_analyzer = PaperAnalyzer(llm_client=llm_client, output_dir=str(output_dir))
    paper_code_analyzer = PaperCodeAnalyzer(llm_client=llm_client, output_dir=str(output_dir))
    
    # 4. 选择要分析的领域和关键词
    search_keyword = "transformer"  # 可替换为其他关键词
    num_papers = 2  # 设置较小的值以便快速演示
    
    logger.info(f"开始分析与 '{search_keyword}' 相关的论文及代码实现")
    
    # 5. 搜索论文
    try:
        papers = pwc_crawler.search_papers(search_keyword, top_k=num_papers)
        logger.info(f"搜索到 {len(papers)} 篇论文")
        
        if not papers:
            logger.error("未找到相关论文，退出程序")
            return
    except Exception as e:
        logger.error(f"搜索论文失败: {e}")
        return
    
    # 6. 获取论文详情
    try:
        detailed_papers = []
        for paper in papers:
            if "url" in paper:
                paper_details = pwc_crawler.crawl_paper_details(paper["url"])
                detailed_papers.append(paper_details)
            else:
                detailed_papers.append(paper)
        
        logger.info(f"成功获取 {len(detailed_papers)} 篇论文的详细信息")
    except Exception as e:
        logger.error(f"获取论文详情失败: {e}")
        detailed_papers = papers
    
    # 7. 下载论文PDF
    downloaded_papers = []
    for paper in detailed_papers:
        try:
            # 获取PDF链接
            pdf_url = None
            paper_links = paper.get("paper_links", {})
            
            # 优先使用arxiv链接
            if "arxiv" in paper_links:
                pdf_url = paper_links["arxiv"]
                if not pdf_url.endswith(".pdf"):
                    pdf_url = pdf_url.replace("abs", "pdf") + ".pdf"
            # 其次使用pdf链接
            elif "pdf" in paper_links:
                pdf_url = paper_links["pdf"]
            
            if pdf_url:
                logger.info(f"下载论文: {paper.get('title', '未知标题')}")
                pdf_path = paper_downloader.download_paper(pdf_url)
                
                if pdf_path:
                    downloaded_papers.append({
                        "path": pdf_path,
                        "meta": {
                            "title": paper.get("title", ""),
                            "authors": paper.get("authors", []),
                            "url": paper.get("url", ""),
                            "github_repos": paper.get("github_repos", [])
                        }
                    })
                    logger.info(f"论文下载成功: {pdf_path}")
                else:
                    logger.warning(f"论文下载失败: {paper.get('title', '未知标题')}")
            else:
                logger.warning(f"未找到PDF链接: {paper.get('title', '未知标题')}")
        
        except Exception as e:
            logger.error(f"处理论文时出错: {e}")
    
    logger.info(f"成功下载 {len(downloaded_papers)} 篇论文")
    
    if not downloaded_papers:
        logger.error("未成功下载任何论文，退出程序")
        return
    
    # 8. 分析论文内容
    paper_analyses = []
    for paper in downloaded_papers:
        try:
            logger.info(f"分析论文: {paper['meta'].get('title', '未知标题')}")
            
            analysis_result = paper_analyzer.analyze_paper(
                paper_path=paper["path"],
                paper_meta=paper["meta"],
                options={
                    "analysis_type": "full",
                    "max_tokens": 6000
                }
            )
            
            if analysis_result["success"]:
                paper_analyses.append(analysis_result)
                logger.info(f"论文分析成功: {paper['meta'].get('title', '未知标题')}")
            else:
                logger.warning(f"论文分析失败: {analysis_result.get('error', '未知错误')}")
        
        except Exception as e:
            logger.error(f"分析论文时出错: {e}")
    
    logger.info(f"成功分析 {len(paper_analyses)} 篇论文")
    
    if not paper_analyses:
        logger.error("未成功分析任何论文，退出程序")
        return
    
    # 9. 分析GitHub仓库
    relation_analyses = []
    for paper_analysis in paper_analyses:
        paper_meta = paper_analysis.get("paper_meta", {})
        github_repos = paper_meta.get("github_repos", [])
        
        if not github_repos:
            logger.warning(f"论文没有关联的GitHub仓库: {paper_meta.get('title', '未知标题')}")
            continue
        
        # 限制仓库数量，避免处理时间过长
        repo_urls = [repo["url"] for repo in github_repos[:2]]
        
        logger.info(f"分析论文与 {len(repo_urls)} 个GitHub仓库的关系")
        
        try:
            paper_repo_analyses = paper_code_analyzer.analyze_paper_with_repos(
                paper_analysis=paper_analysis,
                repo_urls=repo_urls
            )
            
            relation_analyses.extend(paper_repo_analyses)
            
            logger.info(f"成功分析 {len(paper_repo_analyses)} 个仓库")
        
        except Exception as e:
            logger.error(f"分析GitHub仓库时出错: {e}")
    
    # 10. 对实现进行排名
    if relation_analyses:
        ranked_implementations = paper_code_analyzer.rank_implementations(relation_analyses)
        
        # 输出排名结果
        logger.info("\n论文实现质量排名:")
        for i, impl in enumerate(ranked_implementations):
            paper_title = impl.get("paper", {}).get("title", "未知论文")
            repo_name = impl.get("repo", {}).get("name", "未知仓库")
            relation = impl.get("relation_analysis", {})
            
            completeness = relation.get("implementation_completeness", 0)
            consistency = relation.get("consistency_with_paper", 0)
            quality = relation.get("code_quality", 0)
            
            logger.info(f"第 {i+1} 名: {paper_title} - {repo_name}")
            logger.info(f"  完整度: {completeness}/10, 一致性: {consistency}/10, 代码质量: {quality}/10")
            logger.info(f"  总结: {relation.get('summary', '无总结')[:100]}...")
        
        # 保存最终结果
        final_result = {
            "search_keyword": search_keyword,
            "papers_found": len(papers),
            "papers_analyzed": len(paper_analyses),
            "repos_analyzed": len(relation_analyses),
            "top_implementation": ranked_implementations[0] if ranked_implementations else None,
            "timestamp": paper_analyses[0].get("timestamp") if paper_analyses else None
        }
        
        with open(output_dir / "final_result.json", "w", encoding="utf-8") as f:
            json.dump(final_result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"最终结果已保存到: {output_dir / 'final_result.json'}")
    else:
        logger.warning("没有成功分析任何论文与代码的关系")


if __name__ == "__main__":
    main() 