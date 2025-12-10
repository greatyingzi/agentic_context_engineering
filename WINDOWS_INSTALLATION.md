# Windows Installation Guide

## 🪟 Windows系统安装指南

本指南专门针对Windows系统的特殊要求进行优化。

## 📋 系统要求

- **Windows 10 或更高版本**
- **Node.js 16+** (从 [nodejs.org](https://nodejs.org) 下载)
- **Python 3.8+** (从 [python.org](https://python.org) 下载)
- **Git** (从 [git-scm.com](https://git-scm.com) 下载)

## 🔧 前置设置

### 1. Python安装（关键步骤）

1. 从 [python.org](https://python.org) 下载Python
2. **运行安装程序时必须勾选**：
   - ☑️ **"Add Python to PATH"**
   - ☑️ **"Install for all users"**（可选）
3. 验证安装：打开CMD或PowerShell运行
   ```cmd
   python --version
   pip --version
   ```

### 2. PowerShell执行策略（重要）

如果使用PowerShell，需要设置执行策略：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

验证策略：
```powershell
Get-ExecutionPolicy
```

### 3. 防病毒软件设置

由于需要修改系统文件，建议：
- 将 `%USERPROFILE%\.claude` 目录添加到防病毒软件排除列表
- 或在安装过程中暂时禁用实时保护

## 📦 安装步骤

### 方法1：使用标准安装

```cmd
# 克隆项目
git clone https://github.com/greatyingzi/agentic_context_engineering.git
cd agentic_context_engineering

# 安装Node.js依赖
npm install

# 运行安装脚本
npm run install
```

### 方法2：手动安装（如果自动安装失败）

1. **创建虚拟环境**：
   ```cmd
   python -m venv %USERPROFILE%\.claude\.venv
   ```

2. **激活虚拟环境并安装依赖**：
   ```cmd
   %USERPROFILE%\.claude\.venv\Scripts\activate
   pip install --upgrade pip
   pip install anthropic
   ```

3. **复制文件**：
   ```cmd
   xcopy src %USERPROFILE%\.claude /E /I /Y
   xcopy scripts %USERPROFILE%\.claude\scripts /E /I /Y
   ```

## ⚠️ 常见Windows问题及解决方案

### 问题1：Python找不到

**错误**：`'python' is not recognized...`

**解决方案**：
1. 确认Python安装时勾选了"Add to PATH"
2. 手动添加到PATH：
   - `%USERPROFILE%\AppData\Local\Programs\Python\PythonXX\`
   - `%USERPROFILE%\AppData\Local\Programs\Python\PythonXX\Scripts\`

### 问题2：PowerShell执行策略限制

**错误**：`cannot be loaded because running scripts is disabled`

**解决方案**：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 问题3：虚拟环境创建失败

**错误**：`Error creating virtual environment`

**解决方案**：
1. 确保有管理员权限
2. 检查路径是否包含中文字符
3. 尝试：`python -m venv --clear %USERPROFILE%\.claude\.venv`

### 问题4：Hook脚本不执行

**症状**：安装完成但hooks不触发

**解决方案**：
1. 检查防病毒软件是否删除了Python文件
2. 验证路径：
   ```cmd
   dir "%USERPROFILE%\.claude\hooks"
   ```
3. 手动测试：
   ```cmd
   "%USERPROFILE%\.claude\.venv\Scripts\python.exe" "%USERPROFILE%\.claude\hooks\user_prompt_inject.py"
   ```

### 问题5：Git钩子不工作

**症状**：/compact命令不触发PreCompact hook

**解决方案**：
1. 重新安装hooks：
   ```cmd
   npm run install
   ```
2. 检查Git配置：
   ```cmd
   git config --list | findstr hook
   ```
3. 验证设置文件：
   ```cmd
   type "%USERPROFILE%\.claude\settings.json"
   ```

## 🧪 验证安装

### 1. 检查文件结构

```cmd
dir "%USERPROFILE%\.claude"
```

应该看到：
```
hooks/
prompts/
scripts/
.venv/
settings.json
```

### 2. 测试Python依赖

```cmd
"%USERPROFILE%\.claude\.venv\Scripts\python.exe" -c "import anthropic; print('anthropic imported successfully')"
```

### 3. 验证Hook注册

```cmd
type "%USERPROFILE%\.claude\settings.json" | findstr python.exe
```

应该看到包含完整路径的hook命令。

## 🔧 高级配置

### 使用uv（推荐）

如果需要更快的依赖管理：

1. 安装uv：
   ```cmd
   winget install astral-sh.uv
   ```

2. 重新运行安装：
   ```cmd
   npm run install
   ```

### 环境变量优化

添加到系统环境变量：
- `ANTHROPIC_API_KEY` - 如果使用Anthropic API
- `AGENTIC_CONTEXT_MODEL` - 指定模型（可选）

## 📞 获取帮助

如果遇到问题：

1. **检查诊断日志**：
   ```cmd
   type "%USERPROFILE%\.claude\diagnostic\*.txt"
   ```

2. **启用诊断模式**：
   ```cmd
   echo. > "%USERPROFILE%\.claude\diagnostic_mode"
   ```

3. **重新安装**：
   ```cmd
   rmdir /s /q "%USERPROFILE%\.claude"
   npm run install
   ```

## 📝 Windows特定说明

- 使用 `python.exe` 而不是 `python3`
- 路径使用反斜杠 `\` 但JavaScript会自动处理
- PowerShell需要特殊执行策略设置
- 某些企业环境可能有额外限制

**安装成功后，重启Claude Code即可开始使用！** 🎉