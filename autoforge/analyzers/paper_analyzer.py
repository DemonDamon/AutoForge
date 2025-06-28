"""
论文分析器模块
负责解析和分析论文内容
"""

import os
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from ..docparser import MultiModalDocParser
from .base import BaseAnalyzer

logger = logging.getLogger(__name__)


class PaperAnalyzer(BaseAnalyzer):
    """论文分析器"""
    
    def __init__(self, 
                 llm_client=None, 
                 output_dir: str = "outputs", 
                 save_intermediate: bool = True):
        """
        初始化论文分析器
        
        Args:
            llm_client: LLM客户端（用于分析论文内容）
            output_dir: 输出目录
            save_intermediate: 是否保存中间结果
        """
        super().__init__(llm_client, output_dir, save_intermediate)
        self.doc_parser = MultiModalDocParser()
        
        # 创建论文分析输出目录
        self.paper_output_dir = Path(output_dir) / "papers"
        self.paper_output_dir.mkdir(parents=True, exist_ok=True)
    
    def analyze(self, paper_path: Union[str, Path], **kwargs) -> Dict[str, Any]:
        """
        实现BaseAnalyzer的抽象方法
        
        Args:
            paper_path: 论文PDF路径
            **kwargs: 其他参数，如paper_meta, options等
            
        Returns:
            分析结果
        """
        paper_meta = kwargs.get('paper_meta')
        options = kwargs.get('options')
        return self.analyze_paper(paper_path, paper_meta, options)
    
    def analyze_paper(self, 
                     paper_path: Union[str, Path], 
                     paper_meta: Optional[Dict[str, Any]] = None,
                     options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        分析论文内容
        
        Args:
            paper_path: 论文PDF路径
            paper_meta: 论文元数据（可选，如标题、作者等）
            options: 分析选项
                - max_pages: 最大处理页数（默认全部）
                - focus_sections: 重点关注的章节（如"方法"、"实验"等）
                - analysis_type: 分析类型（"full", "method", "results"等）
                
        Returns:
            分析结果
        """
        paper_path = Path(paper_path)
        options = options or {}
        
        logger.info(f"开始分析论文: {paper_path}")
        
        # 1. 解析PDF内容
        try:
            parse_result = self.doc_parser.parse_file(str(paper_path))
            if parse_result["status"] != "success":
                logger.error(f"解析PDF失败: {parse_result.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "error": parse_result.get("error", "PDF解析失败"),
                    "paper_path": str(paper_path),
                    "timestamp": datetime.now().isoformat()
                }
            
            paper_content = parse_result["content"]
            
        except Exception as e:
            logger.error(f"解析PDF出现异常: {e}")
            return {
                "success": False,
                "error": str(e),
                "paper_path": str(paper_path),
                "timestamp": datetime.now().isoformat()
            }
        
        # 2. 准备LLM分析
        if not self.llm_client:
            logger.warning("未提供LLM客户端，仅返回解析后的内容")
            return {
                "success": True,
                "paper_path": str(paper_path),
                "paper_meta": paper_meta or {},
                "parsed_content": paper_content,
                "timestamp": datetime.now().isoformat()
            }
        
        # 3. 分析论文内容
        try:
            analysis_result = self._analyze_with_llm(paper_content, paper_meta, options)
            
            # 4. 整合结果
            result = {
                "success": True,
                "paper_path": str(paper_path),
                "paper_meta": paper_meta or {},
                "analysis": analysis_result,
                "timestamp": datetime.now().isoformat()
            }
            
            # 5. 保存结果
            if self.save_intermediate:
                self._save_analysis_result(result, paper_path.stem)
            
            return result
            
        except Exception as e:
            logger.error(f"LLM分析论文失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "paper_path": str(paper_path),
                "paper_meta": paper_meta or {},
                "parsed_content": paper_content,
                "timestamp": datetime.now().isoformat()
            }
    
    def _analyze_with_llm(self, 
                         paper_content: str, 
                         paper_meta: Optional[Dict[str, Any]], 
                         options: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用LLM分析论文内容
        
        Args:
            paper_content: 解析后的论文内容
            paper_meta: 论文元数据
            options: 分析选项
            
        Returns:
            LLM分析结果
        """
        analysis_type = options.get("analysis_type", "full")
        focus_sections = options.get("focus_sections", [])
        
        # 根据分析类型选择合适的提示词
        prompt = self._get_analysis_prompt(analysis_type, focus_sections, paper_meta)
        
        # 调用LLM生成分析
        logger.info(f"使用LLM分析论文，类型: {analysis_type}")
        
        # 如果文本过长，进行适当截断
        max_tokens = options.get("max_tokens", 8000)
        truncated_content = self._truncate_content(paper_content, max_tokens)
        
        analysis_response = self.llm_client.generate(
            prompt=prompt,
            context=truncated_content,
            temperature=0.2
        )
        
        # 根据分析类型处理响应
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
    
    def _get_analysis_prompt(self, 
                            analysis_type: str, 
                            focus_sections: List[str],
                            paper_meta: Optional[Dict[str, Any]]) -> str:
        """
        获取分析提示词
        
        Args:
            analysis_type: 分析类型
            focus_sections: 重点关注章节
            paper_meta: 论文元数据
            
        Returns:
            提示词
        """
        # 准备论文元数据
        meta_info = ""
        if paper_meta:
            meta_items = []
            for key, value in paper_meta.items():
                if key in ["title", "authors", "year", "venue", "url"]:
                    meta_items.append(f"{key.capitalize()}: {value}")
            if meta_items:
                meta_info = "论文信息:\n" + "\n".join(meta_items) + "\n\n"
        
        # 焦点章节信息
        focus_info = ""
        if focus_sections:
            focus_info = f"请特别关注以下章节: {', '.join(focus_sections)}\n\n"
        
        # 根据分析类型选择提示词模板
        if analysis_type == "method":
            prompt = f"""
{meta_info}{focus_info}分析下面这篇论文的方法部分。请提取并总结:
1. 核心方法和算法
2. 创新点和技术贡献
3. 方法框架和工作流程
4. 关键公式和数学模型
5. 算法伪代码或实现细节

请以JSON格式返回分析结果，包含以下字段:
{{
    "core_methods": ["方法1", "方法2", ...],
    "innovations": ["创新点1", "创新点2", ...],
    "framework": "方法框架描述",
    "key_formulas": ["公式1", "公式2", ...],
    "implementation_details": "实现细节",
    "method_summary": "方法部分的总体概述"
}}
"""
        elif analysis_type == "results":
            prompt = f"""
{meta_info}{focus_info}分析下面这篇论文的实验和结果部分。请提取并总结:
1. 数据集信息和使用方法
2. 评估指标
3. 实验设置和参数
4. 主要实验结果
5. 与其他方法的比较
6. 消融实验和分析

请以JSON格式返回分析结果，包含以下字段:
{{
    "datasets": ["数据集1", "数据集2", ...],
    "metrics": ["指标1", "指标2", ...],
    "experimental_setup": "实验设置描述",
    "main_results": "主要结果摘要",
    "comparisons": "与其他方法比较",
    "ablation_studies": "消融实验结果",
    "results_summary": "结果部分的总体概述"
}}
"""
        else:  # 默认为全面分析
            prompt = f"""
{meta_info}{focus_info}全面分析下面这篇论文的内容。请提取并总结:
1. 研究背景和动机
2. 研究问题和挑战
3. 主要方法和技术贡献
4. 实验设置和数据集
5. 核心结果和发现
6. 优缺点和局限性
7. 未来工作方向
8. 实际应用价值

请以JSON格式返回分析结果，包含以下字段:
{{
    "background": "研究背景概述",
    "research_problems": ["问题1", "问题2", ...],
    "methods": {{
        "core_algorithms": ["算法1", "算法2", ...],
        "innovations": ["创新点1", "创新点2", ...],
        "technical_contributions": "技术贡献概述"
    }},
    "experiments": {{
        "datasets": ["数据集1", "数据集2", ...],
        "metrics": ["指标1", "指标2", ...],
        "main_results": "主要结果摘要"
    }},
    "findings": ["发现1", "发现2", ...],
    "limitations": ["局限性1", "局限性2", ...],
    "future_work": ["方向1", "方向2", ...],
    "practical_value": "实际应用价值",
    "summary": "论文整体概述"
}}
"""
        
        return prompt
    
    def _truncate_content(self, content: str, max_tokens: int) -> str:
        """
        截断内容以适应模型上下文窗口
        
        Args:
            content: 原始内容
            max_tokens: 最大token数
            
        Returns:
            截断后的内容
        """
        # 简单估计：每个字符约0.5个token
        char_limit = max_tokens * 2
        
        if len(content) <= char_limit:
            return content
        
        # 保留开头和结尾，截断中间部分
        # 开头通常包含摘要、引言等重要信息
        # 结尾通常包含结论、未来工作等
        head_size = int(char_limit * 0.6)  # 分配60%给开头
        tail_size = int(char_limit * 0.4)  # 分配40%给结尾
        
        head = content[:head_size]
        tail = content[-tail_size:]
        
        return f"{head}\n\n[...内容过长，中间部分已省略...]\n\n{tail}"
    
    def _save_analysis_result(self, result: Dict[str, Any], base_name: str) -> None:
        """
        保存分析结果
        
        Args:
            result: 分析结果
            base_name: 基础文件名
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{base_name}_{timestamp}.json"
        filepath = self.paper_output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"分析结果已保存到: {filepath}")
    
    def analyze_papers_batch(self, 
                           papers: List[Dict[str, Union[str, Dict]]], 
                           options: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        批量分析论文
        
        Args:
            papers: 论文列表，每项包含路径和元数据
                   [{"path": "path/to/paper.pdf", "meta": {...}}, ...]
            options: 分析选项
            
        Returns:
            分析结果列表
        """
        logger.info(f"开始批量分析 {len(papers)} 篇论文...")
        
        results = []
        for paper in papers:
            try:
                paper_path = paper.get("path")
                paper_meta = paper.get("meta", {})
                
                if not paper_path or not os.path.exists(paper_path):
                    logger.warning(f"论文路径不存在: {paper_path}")
                    continue
                
                result = self.analyze_paper(paper_path, paper_meta, options)
                results.append(result)
                
            except Exception as e:
                logger.error(f"分析论文失败: {e}")
                results.append({
                    "success": False,
                    "error": str(e),
                    "paper_path": paper.get("path", "Unknown"),
                    "timestamp": datetime.now().isoformat()
                })
        
        logger.info(f"批量分析完成，成功: {sum(1 for r in results if r.get('success', False))}/{len(papers)}")
        return results 