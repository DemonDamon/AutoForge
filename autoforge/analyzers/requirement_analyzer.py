"""需求分析器"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base import BaseAnalyzer
from ..prompts import PromptManager
from ..docparser import MultiModalDocParser

logger = logging.getLogger(__name__)

class RequirementAnalyzer(BaseAnalyzer):
    """需求分析器"""
    
    def __init__(self, llm_client=None, output_dir: str = "outputs", 
                 save_intermediate: bool = True, prompt_manager: Optional[PromptManager] = None):
        super().__init__(llm_client, output_dir, save_intermediate)
        self.prompt_manager = prompt_manager or PromptManager()
        
        # 检查LLM客户端是否支持多模态
        multimodal_client = None
        if llm_client and hasattr(llm_client, 'analyze_image'):
            multimodal_client = llm_client
            logger.info("检测到多模态LLM客户端，启用图片分析功能")
        
        self.doc_parser = MultiModalDocParser(
            use_multimodal=multimodal_client is not None,
            multimodal_client=multimodal_client
        )
    
    def analyze(self, document_path: Optional[str] = None, 
                document_content: Optional[str] = None,
                manual_description: Optional[str] = None) -> Dict[str, Any]:
        logger.info("开始需求分析...")
        
        if document_content is None:
            document_content = self._prepare_document_content(document_path, manual_description)
        
        if self.save_intermediate:
            self.save_result(document_content, "raw_document_content.md", "requirement_analysis")
        
        prompt = self.prompt_manager.get_prompt("DOCUMENT_UNDERSTANDING", document_content=document_content)
        analysis_result = self.call_llm(prompt, temperature=0.3)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_filename = f"requirement_analysis_{timestamp}.md"
        
        if self.save_intermediate:
            self.save_result(analysis_result, result_filename, "requirement_analysis")
        
        return {
            "status": "success",
            "timestamp": timestamp,
            "raw_content": document_content,
            "analysis": analysis_result,
            "parsed": self._parse_analysis_result(analysis_result),
            "output_file": str(self.output_dir / "requirement_analysis" / result_filename)
        }
    
    def _prepare_document_content(self, document_path: Optional[str], 
                                 manual_description: Optional[str]) -> str:
        content_parts = []
        
        if document_path:
            logger.info(f"解析文档: {document_path}")
            from pathlib import Path
            path = Path(document_path)
            
            if path.is_file():
                result = self.doc_parser.parse_file(document_path)
                if result["status"] == "success":
                    content_parts.append(result["content"])
                else:
                    logger.warning(f"文档解析失败: {result.get('error', 'Unknown error')}")
            elif path.is_dir():
                results = self.doc_parser.parse_directory(document_path)
                merged_content = self.doc_parser.merge_results(results)
                content_parts.append(merged_content)
            else:
                raise ValueError(f"无效的文档路径: {document_path}")
        
        if manual_description:
            content_parts.append(f"\n## 补充说明\n\n{manual_description}")
        
        if not content_parts:
            raise ValueError("未提供任何文档内容或描述")
        
        return "\n\n---\n\n".join(content_parts)
    
    def _parse_analysis_result(self, analysis_result: str) -> Dict[str, Any]:
        return {
            "requirement_summary": "",
            "algorithm_tasks": [],
            "evaluation_metrics": {"effectiveness": [], "performance": []},
            "data_requirements": {},
            "technical_constraints": {}
        }
