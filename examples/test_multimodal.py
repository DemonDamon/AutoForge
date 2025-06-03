"""
AutoForge 多模态功能测试示例
演示如何使用通义千问多模态模型分析图片
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 自动加载同级目录下的.env文件
load_dotenv(dotenv_path=Path(__file__).parent / '.env')

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from autoforge.llm import BaiLianClient
from autoforge.docparser import MultiModalDocParser

# 配置日志
from loguru import logger
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def test_image_analysis():
    """测试图片分析功能"""
    
    print("🖼️ AutoForge 多模态功能测试")
    print("=" * 50)
    
    # 1. 初始化多模态LLM客户端
    try:
        llm_client = BaiLianClient(
            model="qwen-vl-plus"  # 使用通义千问多模态模型
        )
        
        # 验证连接
        if llm_client.validate_connection():
            print("✅ 多模态LLM连接正常")
        else:
            print("❌ LLM连接失败")
            return
            
    except Exception as e:
        print(f"❌ 初始化LLM客户端失败: {e}")
        return
    
    # 2. 测试单张图片分析
    print("\n📸 测试1: 单张图片分析")
    test_image_dir = Path("examples/test_images")
    
    if not test_image_dir.exists():
        test_image_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 已创建测试图片目录: {test_image_dir}")
        print("请在该目录下放置一些测试图片（jpg/png格式）")
        return
    
    # 查找测试图片
    image_files = list(test_image_dir.glob("*.jpg")) + list(test_image_dir.glob("*.png"))
    
    if not image_files:
        print(f"📁 在 {test_image_dir} 目录下没有找到测试图片")
        print("请放置一些jpg或png格式的图片进行测试")
        return
    
    # 分析第一张图片
    test_image = str(image_files[0])
    print(f"📸 正在分析图片: {test_image}")
    
    try:
        result = llm_client.analyze_image(
            image_path=test_image,
            prompt="请详细分析这张图片，包括：1. 整体描述 2. 文字内容 3. 图表数据 4. 关键信息",
            temperature=0.3
        )
        
        print("✅ 图片分析完成")
        print("📄 分析结果:")
        print("-" * 40)
        print(result)
        print("-" * 40)
        
    except Exception as e:
        print(f"❌ 图片分析失败: {e}")
        return
    
    # 3. 测试批量图片分析
    if len(image_files) > 1:
        print(f"\n📸 测试2: 批量图片分析（共{len(image_files)}张图片）")
        
        try:
            # 最多分析3张图片
            batch_images = [str(img) for img in image_files[:3]]
            results = llm_client.analyze_images_batch(
                image_paths=batch_images,
                prompt="请简要描述这张图片的主要内容",
                temperature=0.3
            )
            
            print("✅ 批量分析完成")
            for i, (img_path, result) in enumerate(zip(batch_images, results), 1):
                print(f"\n📸 图片{i}: {Path(img_path).name}")
                print(f"📄 分析结果: {result[:100]}...")
                
        except Exception as e:
            print(f"❌ 批量分析失败: {e}")
    
    # 4. 测试文档解析器的多模态功能
    print(f"\n📁 测试3: 文档解析器多模态功能")
    
    try:
        # 创建多模态文档解析器
        doc_parser = MultiModalDocParser(
            use_multimodal=True,
            multimodal_client=llm_client
        )
        
        # 解析包含图片的目录
        results = doc_parser.parse_directory(
            directory_path=test_image_dir,
            recursive=False
        )
        
        print(f"✅ 解析完成，共处理 {len(results)} 个文件")
        
        # 显示解析结果摘要
        for result in results:
            if result["status"] == "success":
                print(f"📄 {result['file_path']}: 解析成功")
            else:
                print(f"❌ {result['file_path']}: {result.get('error', '解析失败')}")
        
        # 合并结果并保存
        merged_content = doc_parser.merge_results(results, "examples/multimodal_test_result.md")
        print(f"📁 合并结果已保存到: examples/multimodal_test_result.md")
        
    except Exception as e:
        print(f"❌ 文档解析器测试失败: {e}")
    
    print("\n🎉 多模态功能测试完成！")


def create_sample_images():
    """创建一些示例图片说明"""
    
    sample_dir = Path("examples/test_images")
    sample_dir.mkdir(parents=True, exist_ok=True)
    
    readme_content = """# 测试图片目录

请在此目录下放置一些测试图片，支持的格式：
- JPG/JPEG
- PNG
- BMP
- GIF
- TIFF

建议测试的图片类型：
1. 包含文字的图片（如截图、文档照片）
2. 图表、表格类图片
3. 流程图、架构图
4. 普通照片

示例文件名：
- chart.png
- document.jpg
- flowchart.png
- photo.jpg
"""
    
    readme_path = sample_dir / "README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"📁 已创建测试目录说明: {readme_path}")


if __name__ == "__main__":
    # 如果测试目录不存在，先创建说明
    if not Path("examples/test_images").exists():
        create_sample_images()
    
    test_image_analysis() 