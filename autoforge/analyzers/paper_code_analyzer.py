"""
论文与代码关联分析器
分析论文内容与GitHub代码仓库之间的关系
"""

import os
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime

from .base import BaseAnalyzer
from .github_repo_analyzer import GitHubRepoAnalyzer

logger = logging.getLogger(__name__)


class PaperCodeAnalyzer(BaseAnalyzer):
    """论文与代码关联分析器"""
    
    def __init__(self, 
                 llm_client=None, 
                 output_dir: str = "outputs", 
                 save_intermediate: bool = True):
        """
        初始化论文与代码关联分析器
        
        Args:
            llm_client: LLM客户端
            output_dir: 输出目录
            save_intermediate: 是否保存中间结果
        """
        super().__init__(llm_client, output_dir, save_intermediate)
        
        # 创建输出目录
        self.analysis_output_dir = Path(output_dir) / "paper_code_analysis"
        self.analysis_output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化GitHub仓库分析器
        self.repo_analyzer = GitHubRepoAnalyzer(
            workspace_dir=str(self.analysis_output_dir / "repos"),
            keep_repos=False,  # 分析后删除仓库以节省空间
            llm_client=llm_client,
            output_dir=str(self.analysis_output_dir),
            save_intermediate=save_intermediate
        )
    
    def analyze(self, paper_analysis: Dict[str, Any], repo_analysis: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        实现BaseAnalyzer的抽象方法
        
        Args:
            paper_analysis: 论文分析结果
            repo_analysis: 代码仓库分析结果
            **kwargs: 其他参数
            
        Returns:
            关联分析结果
        """
        return self.analyze_paper_code_relation(paper_analysis, repo_analysis)
    
    def analyze_paper_code_relation(self, 
                                  paper_analysis: Dict[str, Any],
                                  repo_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析论文与代码的关系
        
        Args:
            paper_analysis: 论文分析结果
            repo_analysis: 代码仓库分析结果
            
        Returns:
            关联分析结果
        """
        logger.info(f"分析论文与代码关系: {paper_analysis.get('paper_meta', {}).get('title', 'Unknown')} - {repo_analysis.get('name', 'Unknown')}")
        
        if not self.llm_client:
            logger.warning("未提供LLM客户端，无法进行深度关联分析")
            return {
                "success": False,
                "error": "未提供LLM客户端",
                "paper": paper_analysis.get("paper_meta", {}),
                "repo": repo_analysis.get("name", "Unknown"),
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            # 1. 提取关键信息
            paper_info = self._extract_paper_info(paper_analysis)
            repo_info = self._extract_repo_info(repo_analysis)
            
            # 2. 使用LLM分析关联性
            analysis_result = self._analyze_relation_with_llm(paper_info, repo_info)
            
            # 3. 整合结果
            result = {
                "success": True,
                "paper": paper_analysis.get("paper_meta", {}),
                "paper_path": paper_analysis.get("paper_path", ""),
                "repo": {
                    "name": repo_analysis.get("name", ""),
                    "url": repo_analysis.get("url", ""),
                    "owner": repo_analysis.get("owner", "")
                },
                "relation_analysis": analysis_result,
                "timestamp": datetime.now().isoformat()
            }
            
            # 4. 保存结果
            if self.save_intermediate:
                self._save_analysis_result(result)
            
            return result
            
        except Exception as e:
            logger.error(f"分析论文与代码关系失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "paper": paper_analysis.get("paper_meta", {}),
                "repo": repo_analysis.get("name", "Unknown"),
                "timestamp": datetime.now().isoformat()
            }
    
    def _extract_paper_info(self, paper_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取论文关键信息
        
        Args:
            paper_analysis: 论文分析结果
            
        Returns:
            论文关键信息
        """
        paper_info = {}
        
        # 基本元数据
        paper_info["meta"] = paper_analysis.get("paper_meta", {})
        
        # 从分析结果中提取
        analysis = paper_analysis.get("analysis", {})
        
        if isinstance(analysis, dict):
            # 提取方法相关信息
            paper_info["methods"] = analysis.get("methods", {})
            if not paper_info["methods"] and "core_methods" in analysis:
                paper_info["methods"] = {
                    "core_algorithms": analysis.get("core_methods", []),
                    "innovations": analysis.get("innovations", [])
                }
            
            # 提取实验相关信息
            paper_info["experiments"] = analysis.get("experiments", {})
            if not paper_info["experiments"] and "datasets" in analysis:
                paper_info["experiments"] = {
                    "datasets": analysis.get("datasets", []),
                    "metrics": analysis.get("metrics", [])
                }
            
            # 提取其他关键信息
            paper_info["summary"] = analysis.get("summary", "")
            if not paper_info["summary"] and "method_summary" in analysis:
                paper_info["summary"] = analysis.get("method_summary", "")
        
        # 确保有summary字段
        if not paper_info.get("summary") and "raw_analysis" in analysis:
            paper_info["summary"] = analysis.get("raw_analysis", "")
        
        return paper_info
    
    def _extract_repo_info(self, repo_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取仓库关键信息
        
        Args:
            repo_analysis: 仓库分析结果
            
        Returns:
            仓库关键信息
        """
        repo_info = {}
        
        # 基本信息
        repo_info["name"] = repo_analysis.get("name", "")
        repo_info["url"] = repo_analysis.get("url", "")
        repo_info["owner"] = repo_analysis.get("owner", "")
        repo_info["description"] = repo_analysis.get("description", "")
        
        # 编程语言
        repo_info["languages"] = repo_analysis.get("languages", {})
        
        # 依赖关系
        repo_info["dependencies"] = repo_analysis.get("dependencies", {})
        
        # 关键文件
        repo_info["key_files"] = repo_analysis.get("key_files", {})
        
        # 文件统计
        repo_info["file_stats"] = {
            "file_count": repo_analysis.get("file_count", 0),
            "total_lines": repo_analysis.get("total_lines", 0),
            "code_lines": repo_analysis.get("code_lines", 0)
        }
        
        # 仓库结构
        repo_info["structure"] = repo_analysis.get("structure", {})
        
        return repo_info
    
    def _analyze_relation_with_llm(self, 
                                  paper_info: Dict[str, Any], 
                                  repo_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用LLM分析论文与代码的关联性
        
        Args:
            paper_info: 论文关键信息
            repo_info: 仓库关键信息
            
        Returns:
            关联分析结果
        """
        # 构建提示词
        prompt = self._build_relation_analysis_prompt(paper_info, repo_info)
        
        # 调用LLM
        logger.info("使用LLM分析论文与代码关联性")
        analysis_response = self.llm_client.generate(
            prompt=prompt,
            temperature=0.2
        )
        
        # 解析响应
        try:
            # 尝试解析为JSON
            if "{" in analysis_response and "}" in analysis_response:
                start_idx = analysis_response.find("{")
                end_idx = analysis_response.rfind("}") + 1
                json_str = analysis_response[start_idx:end_idx]
                parsed_analysis = json.loads(json_str)
                return parsed_analysis
            else:
                # 结构化为简单字典
                return {
                    "summary": analysis_response.strip()
                }
        except json.JSONDecodeError:
            # 解析失败，返回原始文本
            return {
                "raw_analysis": analysis_response.strip()
            }
    
    def _build_relation_analysis_prompt(self, 
                                       paper_info: Dict[str, Any], 
                                       repo_info: Dict[str, Any]) -> str:
        """
        构建关联分析提示词
        
        Args:
            paper_info: 论文关键信息
            repo_info: 仓库关键信息
            
        Returns:
            提示词
        """
        # 提取论文信息
        paper_title = paper_info.get("meta", {}).get("title", "未知论文")
        paper_methods = paper_info.get("methods", {})
        core_algorithms = paper_methods.get("core_algorithms", [])
        innovations = paper_methods.get("innovations", [])
        paper_summary = paper_info.get("summary", "")
        
        # 提取仓库信息
        repo_name = repo_info.get("name", "未知仓库")
        repo_description = repo_info.get("description", "")
        repo_languages = repo_info.get("languages", {})
        main_language = next(iter(repo_languages), "未知") if repo_languages else "未知"
        dependencies = repo_info.get("dependencies", {})
        key_files = repo_info.get("key_files", {})
        
        # 构建提示词
        prompt = f"""分析论文《{paper_title}》与代码仓库"{repo_name}"之间的关联性。

论文信息:
- 核心算法: {', '.join(core_algorithms) if core_algorithms else '未提供'}
- 创新点: {', '.join(innovations) if innovations else '未提供'}
- 论文概述: {paper_summary}

代码仓库信息:
- 描述: {repo_description}
- 主要语言: {main_language}
- 依赖库: {', '.join(list(dependencies.get('python', []))[:5]) if 'python' in dependencies else '未提供'}
- 关键文件: {', '.join(list(key_files.values())[:5]) if key_files else '未提供'}

请分析两者之间的关联性，包括:
1. 代码是否完整实现了论文中的算法和方法
2. 代码与论文中描述的一致性程度
3. 代码实现的质量和可用性
4. 关键算法与代码文件的映射关系
5. 缺失或未完全实现的部分
6. 代码中可能的扩展或改进

请以JSON格式返回分析结果，包含以下字段:
{{
    "implementation_completeness": 0-10的分数，表示实现完整度,
    "consistency_with_paper": 0-10的分数，表示与论文一致性,
    "code_quality": 0-10的分数，表示代码质量,
    "algorithm_to_code_mapping": [
        {{"algorithm": "算法名称", "files": ["相关文件路径"], "completeness": 0-10分数}}
    ],
    "missing_components": ["未实现的组件1", "未实现的组件2", ...],
    "extensions": ["代码中的扩展1", "代码中的扩展2", ...],
    "summary": "总体评估摘要"
}}
"""
        
        return prompt
    
    def _save_analysis_result(self, result: Dict[str, Any]) -> None:
        """
        保存分析结果
        
        Args:
            result: 分析结果
        """
        # 生成文件名
        paper_title = result.get("paper", {}).get("title", "unknown_paper")
        repo_name = result.get("repo", {}).get("name", "unknown_repo")
        
        # 简化标题和仓库名用于文件名
        paper_title = paper_title.replace(" ", "_").replace("/", "_")[:30]
        repo_name = repo_name.replace(" ", "_").replace("/", "_")[:30]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"relation_{paper_title}_{repo_name}_{timestamp}.json"
        filepath = self.analysis_output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"关联分析结果已保存到: {filepath}")
    
    def analyze_paper_with_repos(self, 
                               paper_analysis: Dict[str, Any],
                               repo_urls: List[str]) -> List[Dict[str, Any]]:
        """
        分析论文与多个代码仓库的关系
        
        Args:
            paper_analysis: 论文分析结果
            repo_urls: 代码仓库URL列表
            
        Returns:
            关联分析结果列表
        """
        logger.info(f"分析论文与 {len(repo_urls)} 个代码仓库的关系")
        
        results = []
        for repo_url in repo_urls:
            try:
                # 1. 分析代码仓库
                logger.info(f"分析代码仓库: {repo_url}")
                repo_analysis = self.repo_analyzer.analyze_repo_from_url(repo_url)
                
                # 2. 分析关联性
                relation_analysis = self.analyze_paper_code_relation(
                    paper_analysis, 
                    repo_analysis
                )
                
                results.append(relation_analysis)
                
            except Exception as e:
                logger.error(f"分析代码仓库失败: {repo_url}, 错误: {e}")
                results.append({
                    "success": False,
                    "error": str(e),
                    "paper": paper_analysis.get("paper_meta", {}),
                    "repo_url": repo_url,
                    "timestamp": datetime.now().isoformat()
                })
        
        return results
    
    def rank_implementations(self, relation_analyses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        对多个实现进行排名
        
        Args:
            relation_analyses: 关联分析结果列表
            
        Returns:
            排序后的结果列表
        """
        # 过滤出成功的分析结果
        valid_analyses = [a for a in relation_analyses if a.get("success", False)]
        
        if not valid_analyses:
            logger.warning("没有有效的关联分析结果可供排名")
            return relation_analyses
        
        # 计算综合得分
        scored_analyses = []
        for analysis in valid_analyses:
            relation = analysis.get("relation_analysis", {})
            
            # 提取评分
            implementation_score = relation.get("implementation_completeness", 0)
            consistency_score = relation.get("consistency_with_paper", 0)
            quality_score = relation.get("code_quality", 0)
            
            # 计算综合得分 (可根据需要调整权重)
            total_score = (implementation_score * 0.4 + 
                          consistency_score * 0.4 + 
                          quality_score * 0.2)
            
            scored_analyses.append({
                "analysis": analysis,
                "score": total_score
            })
        
        # 按分数降序排序
        scored_analyses.sort(key=lambda x: x["score"], reverse=True)
        
        # 返回排序后的分析结果
        return [item["analysis"] for item in scored_analyses] 