import gradio as gr
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# --- 路径和环境设置 ---
# 自动加载项目根目录下的.env文件
try:
    load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / '.env')
except Exception as e:
    print(f"Warning: Could not load .env file. {e}")

# 将项目根目录添加到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from autoforge import AutoForgeAgent
from autoforge.llm import BaiLianClient, DeepSeekClient, OpenAIClient
from autoforge.llm.base import BaseLLMClient

# --- 全局变量和常量 ---
LLM_PROVIDERS = {
    "Bailian": BaiLianClient,
    "DeepSeek": DeepSeekClient,
    "OpenAI": OpenAIClient,
}

LLM_MODELS = {
    "Bailian": ["qwen-plus", "qwen-max", "qwen-long"],
    "DeepSeek": ["deepseek-chat", "deepseek-coder"],
    "OpenAI": ["gpt-4-turbo", "gpt-4o", "gpt-3.5-turbo"],
}

LATEX_DELIMITERS = [{"left": "$$", "right": "$$", "display": True}, {"left": "$", "right": "$", "display": False}]


# --- 后端核心逻辑 ---

def get_llm_client(provider_name: str, api_key: str = None, model_name: str = None) -> BaseLLMClient:
    """根据提供商名称、API Key和模型获取LLM客户端实例"""
    if not api_key:
        api_key = os.getenv(f"{provider_name.upper()}_API_KEY")
    
    if not api_key:
        raise ValueError(f"未提供API Key，且未在环境变量中找到 {provider_name.upper()}_API_KEY")

    client_class = LLM_PROVIDERS.get(provider_name)
    if not client_class:
        raise ValueError(f"不支持的LLM提供商: {provider_name}")
    
    # 如果未提供模型，使用该提供商的默认模型
    if not model_name:
        model_name = LLM_MODELS.get(provider_name, [None])[0]
        
    return client_class(api_key=api_key, model=model_name)

def test_llm_connection(provider_name: str, api_key: str, model_name: str):
    """测试LLM连接"""
    try:
        client = get_llm_client(provider_name, api_key, model_name)
        if client.validate_connection():
            return "✅ 连接成功"
        else:
            return "❌ 连接失败: 未知错误"
    except Exception as e:
        return f"❌ 连接失败: {e}"


def run_analysis_pipeline(
    llm_provider, 
    api_key, 
    llm_model,
    manual_description,
    # top_k,
    # skip_experiment
):
    """运行完整的分析流程，并流式更新UI"""
    if not manual_description:
        raise gr.Error("需求描述不能为空", "请输入您的需求。")

    output_dir = Path("outputs") / f"webui_run_{int(time.time())}"
    
    # 初始化状态和输出内容
    status_updates = []
    req_md_content = "分析中，请稍候..."
    model_search_content = "等待中..."

    def update_status_msg(msg):
        """仅更新状态文本"""
        status_updates.append(msg)
        return (
            "\n".join(status_updates),
            gr.Markdown(value=req_md_content, latex_delimiters=LATEX_DELIMITERS),
            gr.Markdown(value=model_search_content, latex_delimiters=LATEX_DELIMITERS)
        )

    yield update_status_msg("1. 初始化LLM客户端...")
    try:
        llm_client = get_llm_client(llm_provider, api_key, llm_model)
        if not llm_client.validate_connection():
            raise ValueError("LLM连接验证失败")
        yield update_status_msg("   ✅ LLM客户端初始化成功")
    except Exception as e:
        yield update_status_msg(f"   ❌ LLM客户端初始化失败: {e}")
        raise gr.Error("LLM客户端初始化失败", str(e))

    yield update_status_msg("\n2. 创建AutoForge Agent...")
    try:
        agent = AutoForgeAgent(
            llm_client=llm_client,
            output_dir=str(output_dir)
        )
        yield update_status_msg("   ✅ Agent创建成功")
    except Exception as e:
        yield update_status_msg(f"   ❌ Agent创建失败: {e}")
        raise gr.Error("Agent创建失败", str(e))
        
    yield update_status_msg("\n3. 开始执行分析流程...")
    
    try:
        # 使用for循环处理生成器返回的每个阶段结果
        for result in agent.run_full_pipeline(
            manual_description=manual_description,
            skip_experiment_execution=True, # MVP阶段固定为True
        ):
            stage = result.get("stage")
            stage_result = result.get("result", {})
            
            if stage == "requirement_analysis":
                status_updates.append("   - ✅ 需求分析完成")
                output_file = stage_result.get("output_file", "")
                if output_file and Path(output_file).exists():
                    req_md_content = Path(output_file).read_text(encoding="utf-8")
                else:
                    req_md_content = f"### 需求分析报告\n\n文件未找到或生成失败。\n(路径: {output_file or 'N/A'})"
                model_search_content = "分析中，请稍候..." # 更新下一阶段的状态
                yield (
                    "\n".join(status_updates),
                    gr.Markdown(value=req_md_content, latex_delimiters=LATEX_DELIMITERS),
                    gr.Markdown(value=model_search_content, latex_delimiters=LATEX_DELIMITERS)
                )

            elif stage == "model_search":
                status_updates.append("   - ✅ 模型搜索完成")
                output_file = stage_result.get("output_file", "")
                if output_file and Path(output_file).exists():
                    model_search_content = Path(output_file).read_text(encoding="utf-8")
                else:
                    model_search_content = f"### 模型搜索报告\n\n文件未找到或生成失败。\n(路径: {output_file or 'N/A'})"
                yield (
                    "\n".join(status_updates),
                    gr.Markdown(value=req_md_content, latex_delimiters=LATEX_DELIMITERS),
                    gr.Markdown(value=model_search_content, latex_delimiters=LATEX_DELIMITERS)
                )

    except Exception as e:
        status_updates.append(f"\n   ❌ 分析流程出错: {e}")
        yield (
            "\n".join(status_updates),
            gr.Markdown(value=req_md_content, latex_delimiters=LATEX_DELIMITERS),
            gr.Markdown(value=model_search_content, latex_delimiters=LATEX_DELIMITERS)
        )
        raise gr.Error("分析流程执行失败", str(e))

    status_updates.append(f"\n🎉 全部完成！结果保存在目录: {output_dir.resolve()}")
    yield (
        "\n".join(status_updates),
        gr.Markdown(value=req_md_content, latex_delimiters=LATEX_DELIMITERS),
        gr.Markdown(value=model_search_content, latex_delimiters=LATEX_DELIMITERS)
    )

# --- Gradio UI 构建 ---

with gr.Blocks(theme=gr.themes.Soft(), title="AutoForge WebUI") as demo:
    gr.Markdown("# AutoForge 智能体-AI解决方案探索工具")
    
    with gr.Row():
        # 左侧：配置与输入
        with gr.Column(scale=1):
            gr.Markdown("## 1. 配置LLM")
            with gr.Group():
                llm_provider = gr.Dropdown(
                    list(LLM_PROVIDERS.keys()), 
                    label="选择LLM提供商", 
                    value="Bailian"
                )
                llm_model = gr.Dropdown(
                    LLM_MODELS["Bailian"],
                    label="选择模型",
                    value=LLM_MODELS["Bailian"][0]
                )
                api_key_input = gr.Textbox(
                    label="API Key", 
                    placeholder="留空则从环境变量加载",
                    type="password"
                )
                test_conn_btn = gr.Button("测试连接")
                test_conn_output = gr.Markdown()
            
            gr.Markdown("## 2. 输入需求")
            with gr.Tabs():
                with gr.TabItem("手动描述"):
                    manual_description_input = gr.Textbox(
                        label="详细需求描述",
                        placeholder="例如：我需要一个图像质量评估模型，用于自动评估图片的质量好坏...",
                        lines=15
                    )
                with gr.TabItem("文档分析 (即将推出)"):
                    gr.Markdown("功能正在开发中...")

            # gr.Markdown("## 3. 高级选项")
            # with gr.Accordion("展开配置", open=False):
            #     top_k_slider = gr.Slider(10, 100, value=30, step=1, label="模型搜索数量 (Top K)")
            #     skip_experiment_checkbox = gr.Checkbox(True, label="跳过实验执行")

            gr.Markdown("## 3. 开始分析")
            start_button = gr.Button("🚀 开始分析", variant="primary")

        # 右侧：状态与结果
        with gr.Column(scale=2):
            gr.Markdown("## 分析状态")
            status_text = gr.Textbox(
                label="实时状态更新", 
                lines=8, 
                max_lines=8,
                interactive=False,
                autoscroll=True
            )
            
            gr.Markdown("## 分析报告")
            with gr.Tabs():
                with gr.TabItem("需求分析"):
                    req_analysis_md = gr.Markdown("这里将显示需求分析报告...", latex_delimiters=LATEX_DELIMITERS)
                    copy_req_btn = gr.Button("📋 复制报告内容")
                with gr.TabItem("模型搜索"):
                    model_search_md = gr.Markdown("这里将显示模型搜索报告...", latex_delimiters=LATEX_DELIMITERS)
                    copy_model_btn = gr.Button("📋 复制报告内容")

    # --- 事件绑定 ---
    
    def update_model_choices(provider_name):
        models = LLM_MODELS.get(provider_name, [])
        return gr.Dropdown(choices=models, value=models[0] if models else None)

    llm_provider.change(
        fn=update_model_choices,
        inputs=llm_provider,
        outputs=llm_model
    )

    copy_req_btn.click(
        None,
        req_analysis_md,
        None,
        js="""
        (req_md) => {
            const temp_ta = document.createElement('textarea');
            temp_ta.value = req_md;
            document.body.appendChild(temp_ta);
            temp_ta.select();
            document.execCommand('copy');
            document.body.removeChild(temp_ta);
            
            // A simple way to give feedback.
            const original_text = this.querySelector('button').innerText;
            this.querySelector('button').innerText = '✅ 已复制!';
            setTimeout(() => { this.querySelector('button').innerText = original_text; }, 2000);
        }
        """
    )
    
    copy_model_btn.click(
        None,
        model_search_md,
        None,
        js="""
        (model_md) => {
            const temp_ta = document.createElement('textarea');
            temp_ta.value = model_md;
            document.body.appendChild(temp_ta);
            temp_ta.select();
            document.execCommand('copy');
            document.body.removeChild(temp_ta);
            
            const original_text = this.querySelector('button').innerText;
            this.querySelector('button').innerText = '✅ 已复制!';
            setTimeout(() => { this.querySelector('button').innerText = original_text; }, 2000);
        }
        """
    )

    test_conn_btn.click(
        fn=test_llm_connection,
        inputs=[llm_provider, api_key_input, llm_model],
        outputs=[test_conn_output]
    )
    
    start_button.click(
        fn=run_analysis_pipeline,
        inputs=[
            llm_provider,
            api_key_input,
            llm_model,
            manual_description_input,
            # top_k_slider,
            # skip_experiment_checkbox
        ],
        outputs=[
            status_text,
            req_analysis_md,
            model_search_md
        ]
    )

if __name__ == "__main__":
    demo.launch(share=True) 