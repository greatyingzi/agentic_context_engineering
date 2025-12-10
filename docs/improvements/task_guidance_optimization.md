# Task Guidance 智能引导优化总结

## 优化背景

原有的 task guidance prompt 过度简化了任务切换处理，对创造性任务直接忽略工程背景，可能导致主agent失去对核心工程任务的注意力。用户需要智能的引导机制来平衡响应性和焦点保护。

## 核心改进

### 1. 上下文连续性检测
- **连续性评分** (0.0-1.0): 量化任务相关性
- **任务偏离检测**: 识别工程任务vs创造性任务
- **紧急程度评估**: 区分即时需求vs随意探索
- **会话状态感知**: 判断是否在活跃的工程工作中

### 2. 三层引导策略

#### HIGH 连续性 (0.8-1.0)
- 正常工程流程，无需中断
- 保持原有工作节奏

#### MEDIUM 连续性 (0.4-0.7)
- 简要确认上下文转换
- 提供选择权：继续当前任务或处理新请求

#### LOW 连续性 (0.0-0.3)
- **温和提醒**任务转换
- 提供清晰的用户选择菜单
- 防止注意力碎片化

### 3. 智能温度调节
- LOW连续性的创造性请求：增加温度鼓励探索
- HIGH连续性的技术任务：降低温度确保精度
- 保持工程上下文感知的同时支持灵活性

### 4. 增强的JSON输出格式
```json
{
  "context_analysis": {
    "continuity_score": 0.X,
    "task_relevance": "HIGH|MEDIUM|LOW",
    "current_engineering_context": "...",
    "reasoning": "..."
  },
  "task_guidance": {
    "context_reminder": "可选的温和提醒",
    "user_choice_prompt": "可选的用户选择提示"
  }
}
```

## 实际应用示例

### 场景1: 工程中途请求诗歌
```
Context Reminder: We're currently implementing temperature-based classification system.
Your poetry request appears unrelated.

Would you like to:
1. Continue with current implementation
2. Take a creative break with poetry
3. Save current progress and return later
```

### 场景2: 相关任务转换
```
I notice we're shifting from debugging to documentation.
Should we continue with the current fix or update documentation first?
```

## 优势

1. **注意力保护**: 防止工程任务被无关请求打断
2. **用户友好**: 温和提醒而非生硬拒绝
3. **灵活响应**: 支持用户自主选择处理优先级
4. **上下文感知**: 智能评估任务关联性和紧急程度
5. **工程焦点**: 确保核心工程工作不被遗忘

## 技术实现

- 更新了 `src/prompts/task_guidance.txt`
- 添加了上下文连续性检测算法
- 实现了分层引导策略
- 扩展了JSON输出格式以支持智能引导

## 向后兼容性

- 保持了原有的任务分类和温度设置机制
- 新增的context_analysis字段为可选
- 原有的simple/moderate/complex复杂度评估继续有效

---

*优化完成时间: 2025-12-10*
*影响范围: UserPromptSubmit hook 的 task guidance 逻辑*