# 知识生命周期管理提案

## 核心问题

当前知识库缺少有效的生命周期管理，导致：
1. 过时知识仍在推荐
2. 知识质量随时间下降
3. 缺少知识演化追踪

## 改进方案

### 1. 知识时间戳和过期机制

```python
knowledge_point = {
    "created_at": "2025-12-10T10:00:00Z",
    "last_updated": "2025-12-10T15:30:00Z",
    "last_applied": "2025-12-10T14:20:00Z",
    "expiry_hint": "30d",  # 建议过期时间
    "stale_score": 0.0  # 陈旧度评分
}
```

### 2. 知识依赖关系

```python
knowledge_point = {
    "prerequisites": ["git-basic", "python-install"],
    "conflicts_with": ["old-workflow"],
    "supersedes": ["deprecated-method"],
    "version": "2.1.0"
}
```

### 3. 动态质量评估

结合多因素计算知识健康度：

```python
def calculate_knowledge_health(kp):
    base_score = kp.get("score", 0)

    # 时效性衰减
    days_since_update = (now - kp["last_updated"]).days
    time_decay = max(0, 1 - days_since_update / 180)  # 6个月衰减期

    # 使用频率奖励
    usage_bonus = min(kp["usage_stats"]["applied_count"] * 0.1, 2)

    # 反馈奖励/惩罚
    feedback_score = (kp["feedback"]["helpful_count"] -
                     kp["feedback"]["not_helpful_count"]) * 0.5

    return base_score * time_decay + usage_bonus + feedback_score
```

## 实施优先级

1. **高优先级**：添加反馈机制
2. **中优先级**：实现时间戳跟踪
3. **低优先级**：构建完整依赖关系

## 预期收益

- 通过用户反馈提升知识相关性
- 通过时间衰减确保知识新鲜度
- 通过使用统计识别高价值知识