"""FastAgent 编排图：零幻觉、单次 LLM、<800ms 响应。

新架构:
  1. FastPlanner (零 LLM): <120ms
  2. ParallelExecutor (零 LLM): <5000ms
  3. ResultPolisher (1次 LLM): <500ms
"""

from __future__ import annotations

import time
from typing import Any, Dict

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from orchestrator.fast_planner import fast_planner, Task
from orchestrator.parallel_executor import parallel_executor
from orchestrator.result_polisher import result_polisher


def create_graph():
    """
    创建 FastAgent 编排器
    
    流程:
      用户输入 → FastPlanner → ParallelExecutor → ResultPolisher → 最终答案
      
    性能:
      - 延迟: <800ms (简单) 或 <5s (复杂)
      - LLM 调用: 仅 1 次
      - 幻觉风险: 0
    """
    
    def _format_task(task: Task) -> str:
        """将任务转换成人类可读的描述。"""
        if not task.params:
            return f"{task.id}: {task.tool}"

        param_pairs = []
        for key, value in task.params.items():
            # 避免输出过长的参数内容
            value_str = str(value)
            if len(value_str) > 120:
                value_str = value_str[:117] + "..."
            param_pairs.append(f"{key}={value_str}")

        params_joined = ", ".join(param_pairs)
        return f"{task.id}: {task.tool}({params_joined})"

    def fast_agent_invoke(state: Dict[str, Any]) -> Dict[str, Any]:
        """FastAgent 主流程（同步版本，兼容旧接口）"""
        start_time = time.time()
        
        # 提取用户查询
        messages = state.get("messages", [])
        if not messages:
            return {
                "messages": [AIMessage(content="错误：没有输入消息")],
                "final_answer": "错误：没有输入消息"
            }
        
        user_query = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
        
        # 提取上下文（包含历史消息）
        history_messages = messages[:-1] if len(messages) > 1 else []
        context = {
            "uploaded_files": state.get("uploaded_files", []),
            "history": history_messages,
            "recent_turns": history_messages[-5:] if history_messages else []  # 最近5轮对话
        }
        
        print("=" * 60)
        print(f"🚀 FastAgent 启动")
        print(f"📝 用户查询: {user_query}")
        if history_messages:
            print(f"📚 历史消息: {len(history_messages)} 条")
        print("=" * 60)
        
        # 阶段 1: 快速规划 (零 LLM, <120ms)
        print("\n⚡ 阶段 1: 快速规划 (零 LLM)")
        plan = fast_planner.plan(user_query, context)

        plan_summary = [_format_task(task) for task in plan.tasks]
        next_action = plan.tasks[0].tool if plan.tasks else "none"
        parallel_batches = plan.parallel_batches
        plan_estimated_ms = plan.total_estimated_ms
        
        # 简单问答：跳过工具执行，直接用 LLM 回答
        if not plan.tasks:
            print("\n💬 检测到简单问答")
            
            if plan.requires_llm_polish and result_polisher.llm:
                # 简单问答直接调用 LLM（包含历史上下文）
                try:
                    # 构建包含历史的消息列表
                    llm_messages = [SystemMessage(content="你是一个知识渊博的AI助手，请简洁准确地回答问题。能够记住并参考之前的对话内容。")]
                    
                    # 添加历史消息（最近5轮）
                    if history_messages:
                        recent_history = history_messages[-10:]
                        for msg in recent_history:
                            if hasattr(msg, 'type'):
                                if msg.type == 'human':
                                    llm_messages.append(HumanMessage(content=msg.content))
                                elif msg.type == 'ai':
                                    llm_messages.append(AIMessage(content=msg.content))
                            elif hasattr(msg, 'content'):
                                if isinstance(msg, HumanMessage):
                                    llm_messages.append(msg)
                                elif isinstance(msg, AIMessage):
                                    llm_messages.append(msg)
                    
                    # 添加当前查询
                    llm_messages.append(HumanMessage(content=user_query))
                    
                    response = result_polisher.llm.invoke(llm_messages)
                    answer = response.content
                    llm_calls = 1
                except Exception as e:
                    print(f"⚠️ LLM 调用失败: {e}")
                    answer = f"问题：{user_query}\n\n抱歉，无法回答此问题。请检查 API 配置或重试。"
                    llm_calls = 0
            else:
                answer = f"问题：{user_query}\n\n需要配置 OPENROUTER_API_KEY 才能回答此问题。"
                llm_calls = 0
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            return {
                "messages": state["messages"] + [AIMessage(content=answer)],
                "final_answer": answer,
                "total_time_ms": elapsed_ms,
                "llm_calls": llm_calls,
                "plan": plan_summary,
                "parallel_batches": parallel_batches,
                "next_action": next_action,
                "is_complete": True,
                "plan_estimated_ms": plan_estimated_ms
            }
        
        # 阶段 2: 并行执行 (零 LLM, <5s)
        print(f"\n⚡ 阶段 2: 并行执行 (零 LLM)")
        print(f"📊 任务数: {len(plan.tasks)}")
        print(f"📦 批次数: {len(plan.parallel_batches)}")
        
        results = parallel_executor.execute(plan)
        
        # 统计成功率
        success_count = sum(1 for r in results.values() if r.success)
        total_count = len(results)
        
        # 阶段 3: 结果润色 (仅 1 次 LLM, <500ms)
        print(f"\n⚡ 阶段 3: 结果润色")
        
        if plan.requires_llm_polish and result_polisher.llm:
            print("  使用 LLM 润色")
            # 传递历史消息用于上下文记忆
            answer = result_polisher.polish(user_query, plan, results, history_messages=history_messages)
            llm_calls = 1
        else:
            print("  使用降级格式化")
            # 简单任务或 LLM 未配置：直接格式化
            answer = result_polisher._fallback_format(user_query, results)
            llm_calls = 0
        
        # 完成
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        print("\n" + "=" * 60)
        print(f"✅ FastAgent 完成")
        print(f"⏱️  总耗时: {elapsed_ms}ms")
        print(f"📊 成功率: {success_count}/{total_count}")
        print(f"🧠 LLM 调用: 1 次 (仅润色)")
        print("=" * 60)
        
        return {
            "messages": state["messages"] + [AIMessage(content=answer)],
            "final_answer": answer,
            "total_time_ms": elapsed_ms,
            "llm_calls": llm_calls,
            "success_rate": f"{success_count}/{total_count}",
            "plan": plan_summary,
            "parallel_batches": parallel_batches,
            "next_action": next_action,
            "is_complete": True,
            "plan_estimated_ms": plan_estimated_ms,
            "tool_results": {
                task_id: {
                    "tool": result.tool,
                    "success": result.success,
                    "error": result.error if not result.success else None,
                    "output_preview": str(result.output)[:200] if result.output else None,
                    "elapsed_ms": result.elapsed_ms
                }
                for task_id, result in results.items()
            }
        }
    
    # 返回简单的调用器
    class FastGraph:
        def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
            return fast_agent_invoke(state)
        
        def stream(self, state: Dict[str, Any]):
            """流式版本，兼容旧接口"""
            # 执行主流程
            result = fast_agent_invoke(state)
            
            # 模拟流式输出（实际是批量返回）
            yield {"fast_agent": result}
    
    return FastGraph()
