import sys
import os
import json
import time
from dotenv import load_dotenv

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量（必须在导入其他模块之前）
load_dotenv()

# 导入通义千问
try:
    from dashscope import Generation
    # 设置 API Key
    API_KEY = os.getenv("ALIYUN_API_KEY")
    if API_KEY:
        import dashscope
        dashscope.api_key = API_KEY
    else:
        print("警告: 未设置 ALIYUN_API_KEY 环境变量")
except ImportError:
    print("警告: dashscope 未安装，请运行 pip install dashscope")
    Generation = None

# 导入 rag 模块
from modules.rag import search_similar

# ============ 工具函数 =============

def search_clauses(query: str, top_k=1) -> list:
    """
    检索与query相关的标准条款
    """
    try:
        return search_similar(query, top_k=top_k)
    except Exception as e:
        return [{"error": str(e)}]

# ============ ReAct agent主流程 =============

REACT_SYSTEM_PROMPT = """你是一名资深合同审计专家，请遵循 ReAct 框架逐步分析合同。

可用工具：
- search_clauses(query: str): 检索与 query 相关的历史合同条款

你必须始终以 JSON 格式输出，格式如下：
{
  "thought": "你当前的思考...",
  "action": "工具名称（如 'search_clauses'）或 'final_answer'",
  "action_input": "工具的参数（如果是工具调用）或 最终审计报告（如果是 final_answer）"
}

分析步骤：
1. 首先，仔细阅读合同，识别出所有关键条款类型（如付款条款、违约责任、保密条款、知识产权等）
2. 对每种条款类型，调用 search_clauses 检索标准条款进行对比
3. 根据对比结果，分析风险
4. 当所有条款都分析完毕，输出最终审计报告（此时 action 为 'final_answer'，action_input 为报告内容）

最终审计报告应包含：
- 总体风险评估（0-100分）
- 各条款的风险等级及原因（high/mid/low）
- 具体的修改建议

注意：每次只输出一个 JSON 对象，不要包含其他文本。"""

def call_llm(history, temperature=0.1):
    """
    用通义千问 API 调用大模型。history为[
        {"role": "system", "content": ...},
        {"role": "user", "content": ...},
        {"role": "assistant", "content": ...},
        ...
    ]
    """
    if Generation is None:
        raise RuntimeError("dashscope 未安装")
    response = Generation.call(
        model="qwen-plus",
        messages=history,
        temperature=temperature,
        result_format='message',
    )
    return response.output.choices[0].message.content

def parse_react_response(response):
    """
    从大模型输出解析出 思考/行动/输入/最终答案
    支持JSON和常见文本格式
    返回: {"thought": ..., "action": ..., "action_input": ..., "final_answer": ...}
    """
    ret = {"thought": None, "action": None, "action_input": None, "final_answer": None}
    try:
        # 优先尝试json
        obj = json.loads(response)
        # 兼容多种key
        ret["thought"] = obj.get("thought") or obj.get("思考")
        ret["action"] = obj.get("action") or obj.get("行动")
        ret["action_input"] = obj.get("action_input") or obj.get("行动输入")
        ret["final_answer"] = obj.get("final_answer") or obj.get("最终答案")
    except Exception:
        # 尝试解析常规文本
        lines = response.splitlines()
        buf = []
        for ln in lines:
            l = ln.strip()
            if l.startswith("思考:") or l.lower().startswith("thought:"):
                ret["thought"] = l.split(":",1)[1].strip()
            elif l.startswith("行动:") or l.lower().startswith("action:"):
                ret["action"] = l.split(":",1)[1].strip()
            elif l.startswith("行动输入:") or l.lower().startswith("action input:") or l.lower().startswith("action_input:"):
                ret["action_input"] = l.split(":",1)[1].strip()
            elif l.startswith("最终答案:") or l.lower().startswith("final answer:"):
                ret["final_answer"] = l.split(":",1)[1].strip()
            elif l.startswith("最终结论:"):
                ret["final_answer"] = l.split(":",1)[1].strip()
        # 有时内容在一起展开
        if (not ret["final_answer"]) and "最终答案" in response:
            ret["final_answer"] = response.split("最终答案:",1)[1].strip()
    return ret

def react_agent(contract_text, max_steps=10):
    """
    ReAct 智能体主循环
    """
    step_count = 0
    conversation_history = []
    
    # 系统提示词
    system_prompt = REACT_SYSTEM_PROMPT
    
    while step_count < max_steps:
        step_count += 1
        print(f"\n==== Step {step_count} ====")
        
        # 构建消息
        messages = [
            {"role": "system", "content": system_prompt},
            *conversation_history,
            {"role": "user", "content": f"合同内容：{contract_text}" if step_count == 1 else "请继续分析"}
        ]
        
        # 调用大模型
        response = Generation.call(
            model='qwen-plus',
            messages=messages,
            result_format='message',
            temperature=0.1,
        )
        
        content = response.output.choices[0].message.content
        print(content)
        
        # 解析响应（返回字典）
        parsed = parse_react_response(content)
        thought = parsed.get("thought")
        action = parsed.get("action")
        action_input = parsed.get("action_input")
        final_answer = parsed.get("final_answer")
        
        # 记录到历史
        conversation_history.append({"role": "assistant", "content": content})
        
        # 判断是否应该结束
        if final_answer or action == "final_answer" or step_count >= max_steps:
            if final_answer:
                print(f"最终答案: {final_answer[:200]}...")
                return final_answer
            elif action == "final_answer" and action_input:
                return action_input
            elif step_count >= max_steps:
                return content
            else:
                return content
        
        # 执行工具调用
        elif action == "search_clauses":
            print(f"执行工具: {action} 参数: {action_input}")
            results = search_clauses(action_input, top_k=2)
            print(f"找到 {len(results)} 条结果")
            
            # 将观察结果加入历史
            observation = f"观察: 检索到 {len(results)} 条相关条款"
            if results:
                for i, r in enumerate(results, 1):
                    observation += f"\n{i}. {r['text']} (相似度: {r['score']:.2f})"
            else:
                observation += "\n没有找到相关条款"
            
            conversation_history.append({"role": "user", "content": observation})
            print(observation)
        
        else:
            # 未知工具，告诉模型并继续
            conversation_history.append({"role": "user", "content": f"未知工具: {action}，请使用 search_clauses 或输出 final_answer"})
    
    # 循环结束，返回最后的内容
    return "分析超时，请稍后重试"

# ============== 测试代码 ==============
if __name__ == "__main__":
    demo_contract = """
甲方需向乙方支付总金额100万元，分两期支付。
第一期于2024年6月30日前支付50%，第二期于2024年9月30日前支付剩余50%。
如甲方逾期付款，每天按未付款项的万分之五支付违约金。
双方应对在合同履行过程中获知的对方商业秘密予以保密。
本合同知识产权归乙方所有。
"""
    print(">>> 启动智能体ReAct合同审计 demo ...")
    result = react_agent(demo_contract, max_steps=4, debug=True)
    print("\n=== 智能体审计报告 ===")
    print(result["report"])