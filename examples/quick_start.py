"""
AutoForge 快速开始示例
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 自动加载同级目录下的.env文件
load_dotenv(dotenv_path=Path(__file__).parent / '.env')

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from autoforge import AutoForgeAgent
from autoforge.llm import BaiLianClient, DeepSeekClient

# 配置日志
from loguru import logger
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def main():
    """主函数"""
    
    # 1. 初始化LLM客户端
    # 请确保设置了OPENAI_API_KEY环境变量
    # 或者直接传入api_key参数
    try:
        llm_client = BaiLianClient(
            # api_key="your-api-key-here",
            model="qwen-plus-latest"
        )
        
        # # 如果不需要图片分析功能，可以使用DeepSeek
        # llm_client = DeepSeekClient(
        #     # api_key="your-api-key-here",  # 或从环境变量DEEPSEEK_API_KEY读取
        #     model="deepseek-reasoner"  # 使用DeepSeek的大模型
        # )
        
        # 验证连接
        if llm_client.validate_connection():
            print("✅ LLM连接正常")
            
            # 如果是多模态客户端，测试图片分析功能
            if hasattr(llm_client, 'analyze_image'):
                print("✅ 检测到多模态功能，支持图片分析")
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
    # print("\n📝 示例1: 使用手动描述分析需求")
    # manual_description = """
    # 我需要一个图像质量评估模型，用于自动评估图片的质量好坏。
    
    # 具体要求：
    # 1. 输入：各种类型的图像（JPG、PNG格式，分辨率不限）
    # 2. 输出：质量评分（0-100分）及缺陷检测（模糊、噪点、曝光不足/过度、色彩失真等）
    # 3. 准确率要求：与人类评价一致性>85%
    # 4. 推理速度：<200ms/张图片
    # 5. 部署环境：GPU服务器或云端API
    # 6. 特殊要求：能够处理不同光照条件和拍摄场景下的图像
    # """
    
    try:
        # # 使用手动描述
        # result = agent.run_full_pipeline(
        #     manual_description=manual_description,
        #     skip_experiment_execution=True
        # )
        # 使用文档目录
        document_path = "examples/tmp/"
        
        # 设置模型搜索显示30个模型
        additional_info = {"top_k": 30}
        
        result = agent.run_full_pipeline(
            document_path=document_path,
            skip_experiment_execution=True,
            additional_info=additional_info
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
    
    # # 4. 单独使用某个分析器
    # print("\n📝 示例3: 单独使用需求分析器")
    # requirement_result = agent.analyze_requirements(
    #     manual_description=manual_description
    # )
    # print(f"需求分析结果保存在: {requirement_result['output_file']}")
    
    # 5. 保存工作流状态（便于后续继续）
    agent.save_workflow_state()
    print(f"\n💾 工作流状态已保存")
    
    # 6. 单独测试图片分析功能（如果支持多模态）
    if hasattr(llm_client, 'analyze_image'):
        print("\n🖼️ 示例4: 单独测试图片分析功能")
        
        # 创建一个测试图片目录（如果不存在）
        test_image_dir = Path("examples/test_images")
        if test_image_dir.exists() and any(test_image_dir.glob("*.jpg")) or any(test_image_dir.glob("*.png")):
            # 找到第一张图片进行测试
            image_files = list(test_image_dir.glob("*.jpg")) + list(test_image_dir.glob("*.png"))
            if image_files:
                test_image = str(image_files[0])
                print(f"📸 正在分析图片: {test_image}")
                
                try:
                    result = llm_client.analyze_image(
                        image_path=test_image,
                        prompt="请详细描述这张图片的内容，包括文字、图表、关键信息等。"
                    )
                    print(f"✅ 图片分析完成")
                    print(f"📄 分析结果:\n{result[:200]}...")  # 只显示前200个字符
                except Exception as e:
                    print(f"❌ 图片分析失败: {e}")
            else:
                print("📁 在 examples/test_images/ 目录下没有找到测试图片")
        else:
            print("📁 请在 examples/test_images/ 目录下放置一些测试图片（jpg/png格式）")


if __name__ == "__main__":
    main() 