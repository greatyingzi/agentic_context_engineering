# 设计讨论文档

这些文档记录了系统设计过程中的重要讨论和决策过程。

## 文档说明

- **01-enhanced-knowledge-extraction.md** - 关于知识提取机制的设计讨论
- **02-knowledge-lifecycle-proposal.md** - 知识生命周期管理的探索
- **03-personalized-recommendation-system.md** - 个性化推荐系统的权衡分析

## 重要说明

这些是**历史讨论记录**，不是当前实现：
- 可能包含过时的想法
- 记录了决策过程而非最终决定
- 保留用于理解"为什么"而非"是什么"

## 实际实现

请查看源代码了解当前的实现：
- `src/hooks/session_end.py` - 会话知识提取
- `src/hooks/document_scanner.py` - 文档知识扫描
- `src/hooks/git_scanner.py` - Git历史分析
- `src/hooks/bootstrap_playbook.py` - 知识库初始化

## 使用建议

1. 要了解当前功能，看代码
2. 要了解决策背景，看这些文档
3. 要评估设计权衡，对比当时的讨论和现在的实现