# 全局异常处理系统使用说明

## 概述

Agentic Context Engineering 现已集成全局异常处理系统，提供统一的错误日志记录和用户友好的错误反馈。

## 功能特性

### 🎯 核心功能
- **统一异常捕获**: 所有hook执行时的异常都会被自动捕获和记录
- **详细日志记录**: 包含完整的堆栈跟踪、上下文信息和时间戳
- **用户友好反馈**: 提供清晰的错误信息和日志位置提示
- **诊断模式支持**: 在诊断模式下显示完整的异常详情

### 📁 日志文件位置
- **异常日志**: `~/.claude/logs/exceptions.log`
- **诊断目录**: `~/.claude/diagnostic/`
- **日志格式**: 结构化JSON格式，便于分析和调试

## 日志条目结构

每个异常日志条目包含以下信息：

```json
{
  "log_id": "唯一标识符",
  "timestamp": "ISO-8601时间戳",
  "hook_name": "发生异常的hook名称",
  "session_id": "会话ID",
  "exception_type": "异常类型",
  "exception_message": "异常消息",
  "traceback": "完整堆栈跟踪",
  "context": {
    "input_data": "输入数据",
    "hook_stage": "执行阶段"
  },
  "python_version": "Python版本"
}
```

## 使用方法

### 启用诊断模式
创建诊断模式标志文件：
```bash
touch ~/.claude/diagnostic_mode
```

### 查看异常日志
```bash
# 查看完整日志
cat ~/.claude/logs/exceptions.log

# 查看最近的异常
tail -20 ~/.claude/logs/exceptions.log

# 搜索特定hook的异常
grep "hook_name.*user_prompt_inject" ~/.claude/logs/exceptions.log
```

### 清理旧日志（可选）
```python
from exception_handler import cleanup_old_logs
cleanup_old_logs(keep_days=30)  # 保留30天
```

## 异常处理流程

1. **异常发生**: Hook执行时遇到异常
2. **日志记录**: 自动记录到 `~/.claude/logs/exceptions.log`
3. **用户反馈**: 在stderr显示错误信息和日志位置
4. **诊断模式**: 如果启用，显示详细堆栈跟踪
5. **优雅退出**: 使用适当的退出码退出

## 错误消息示例

### 标准模式
```
❌ Hook execution failed in user_prompt_inject
📝 Error logged with ID: 20251209T230548.157534_user_prompt_inject
📂 Check logs at: /Users/liheng/.claude/logs/exceptions.log
```

### 诊断模式
```
❌ Hook execution failed in session_end
📝 Error logged with ID: 20251209T230547.897292_session_end
📂 Check logs at: /Users/liheng/.claude/logs/exceptions.log

🐛 Full exception details:
Traceback (most recent call last):
  File ".../session_end.py", line 26, in main
    messages = load_transcript(transcript_path)
  ...
FileNotFoundError: [Errno 2] No such file or directory: '/nonexistent/path'
```

## 已集成的Hook

- ✅ `user_prompt_inject.py` - 用户提示注入hook
- ✅ `session_end.py` - 会话结束hook
- ✅ `precompact.py` - 上下文压缩前hook

## 开发者信息

### 添加异常处理到新模块

```python
from common import get_exception_handler

def main():
    handler = get_exception_handler()
    try:
        # 你的逻辑
        pass
    except Exception as e:
        context_data = {
            "input_data": input_data if 'input_data' in locals() else "Unable to capture",
            "hook_stage": "main_execution"
        }
        handler.handle_and_exit(e, "hook_name", context_data, session_id)
```

### 手动记录异常（不退出）

```python
from common import log_hook_error

try:
    # 你的逻辑
    pass
except Exception as e:
    log_id = log_hook_error("hook_name", e, context_data, session_id)
    # 继续执行...
```

## 故障排除

### 常见问题

1. **日志文件未创建**
   - 检查 `~/.claude/` 目录权限
   - 确保Python有写入权限

2. **异常未被记录**
   - 检查是否正确导入异常处理模块
   - 验证是否使用了 `handler.handle_and_exit()`

3. **诊断模式无效**
   - 确认 `~/.claude/diagnostic_mode` 文件存在
   - 检查文件权限

### 日志分析建议

1. **按hook名分组统计**:
   ```bash
   grep "hook_name" ~/.claude/logs/exceptions.log | sort | uniq -c
   ```

2. **查看最近异常**:
   ```bash
   tail -50 ~/.claude/logs/exceptions.log | grep -A 20 "exception_type"
   ```

3. **查找特定异常类型**:
   ```bash
   grep "FileNotFoundError" ~/.claude/logs/exceptions.log
   ```

## 更新记录

- 2025-12-09: 实现全局异常处理系统
- 集成到所有核心hook文件
- 添加诊断模式支持
- 实现结构化日志记录