"""
AutoForge 快速开始示例
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


def main():
    """主函数"""
    
    # 1. 初始化LLM客户端
    # 请确保设置了OPENAI_API_KEY环境变量
    # 或者直接传入api_key参数
    try:
        llm_client = OpenAIClient(
            # api_key="your-api-key-here",  # 或从环境变量读取
            model="gpt-4"  # 可以选择 gpt-3.5-turbo 或其他模型
        )
        
        # 验证连接
        if llm_client.validate_connection():
            print("✅ LLM连接正常")
        else:
            print("❌ LLM连接失败")
            return
    except Exception as e:
        print(f"❌ 初始化LLM客户端失败: {e}")
        return
    
    # 2. 创建AutoForge Agent
    agent = AutoForgeAgent(
        llm_client=llm_client,
        output_dir="outputs/demo"
    )
    
    # 3. 运行完整的分析流程
    # 示例1: 使用手动描述
    print("\n📝 示例1: 使用手动描述分析需求")
    manual_description = """
    我需要一个中文文本分类模型，用于对新闻文章进行分类。
    
    具体要求：
    1. 输入：中文新闻文章文本（100-1000字）
    2. 输出：新闻类别（政治、经济、科技、体育、娱乐）
    3. 准确率要求：>90%
    4. 推理速度：<100ms/条
    5. 部署环境：CPU服务器
    """
    
    try:
        result = agent.run_full_pipeline(
            manual_description=manual_description,
            skip_experiment_execution=True
        )
        
        print(f"\n✅ 分析完成！")
        print(f"📁 结果保存在: {agent.output_dir}")
        
    except Exception as e:
        print(f"\n❌ 分析过程出错: {e}")
        return
    
    # 示例2: 分析文档目录
    # 如果你有需求文档，可以这样使用：
    """
    print("\n📝 示例2: 分析文档目录")
    document_path = "path/to/your/documents"  # 替换为你的文档路径
    
    result = agent.run_full_pipeline(
        document_path=document_path,
        skip_experiment_execution=True
    )
    """
    
    # 4. 单独使用某个分析器
    print("\n📝 示例3: 单独使用需求分析器")
    requirement_result = agent.analyze_requirements(
        manual_description="我需要一个图像分类模型，用于识别猫和狗的照片。"
    )
    print(f"需求分析结果保存在: {requirement_result['output_file']}")
    
    # 5. 保存工作流状态（便于后续继续）
    agent.save_workflow_state()
    print(f"\n💾 工作流状态已保存")


if __name__ == "__main__":
    main() 