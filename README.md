# Agentic Context Engineering

[中文](README.zh.md) | English

Agentic Context Engineering (ACE) - An intelligent knowledge accumulation and context injection system designed for Claude Code.

Automatically extracts, evaluates, and integrates key insights from conversation trajectories to enable continuous knowledge evolution and intelligent injection.

## ✨ Core Value

- **Zero-Friction Learning**: Automatically extracts valuable insights from conversations without manual maintenance
- **Intelligent Evaluation**: Dynamically scores based on actual effectiveness, retaining valuable knowledge while eliminating irrelevant content
- **Precision Injection**: Intelligently matches relevant knowledge based on conversation topics to enhance Claude Code's response quality
- **Continuous Evolution**: Avoids duplication through semantic similarity merging (≥80%) and continuously optimizes through scoring mechanism

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/greatyingzi/agentic_context_engineering.git
cd agentic_context_engineering
npm install
```

### Environment Setup

```bash
# Install dependencies (uv recommended)
uv venv ~/.claude/.venv
uv pip install --python ~/.claude/.venv/bin/python3 anthropic

# Configure API (optional, supports fallback)
export AGENTIC_CONTEXT_API_KEY="your-api-key"
export AGENTIC_CONTEXT_MODEL="claude-3-5-sonnet-20241022"
```

### Activate System

Restart Claude Code and the system will automatically take effect across all projects.

## 🏗️ System Architecture

### Core Hook Mechanism

The system achieves full automation through three key hooks:

1. **UserPromptSubmit** - Intelligently injects relevant knowledge at the start of new sessions
2. **SessionEnd** - Extracts and evaluates insights when sessions end
3. **PreCompact** - Protects important knowledge before context compaction

### Knowledge Lifecycle

```
Extract → Evaluate → Score → Merge → Tag → Clean → Inject
```

- **Scoring Mechanism**: Helpful +1, Harmful -3, Neutral 0
- **Intelligent Merging**: Semantic similarity ≥80% auto-merge with score accumulation
- **Auto Cleanup**: Items with score ≤ -5 automatically removed
- **Precise Tagging**: Each knowledge point tagged for accurate topic matching

### Data Flow Architecture

```
Conversation Trajectory → Feature Extraction → LLM Analysis → Knowledge Storage → Intelligent Injection → Enhanced Response
```

## 📋 Advanced Features

### `/init-playbook` - Batch Historical Knowledge Extraction

Batch extract insights from historical conversations to quickly build knowledge base:

```bash
/init-playbook
```

- Automatically identifies project history records
- Defaults to processing last 200 conversations
- Supports custom parameters via environment variables

### Diagnostic Mode

Enable detailed logging:

```bash
touch .claude/diagnostic_mode  # Enable
rm .claude/diagnostic_mode      # Disable
```

### Behavior Configuration

Customize in `~/.claude/settings.json`:

```json
{
  "playbook_update_on_exit": true,   # Update knowledge base on /exit
  "playbook_update_on_clear": true   # Update knowledge base on /clear
}
```

## 📁 Directory Structure

```
.
├── install.js                 # Global installation script
├── package.json               # npm configuration
├── src/
│   ├── hooks/                 # Core hook implementations
│   │   ├── common.py          # Shared utilities
│   │   ├── session_end.py     # Session end handler
│   │   ├── precompact.py      # Context compaction handler
│   │   └── user_prompt_inject.py  # Knowledge injection
│   ├── prompts/               # LLM prompt templates
│   │   ├── reflection.txt     # Knowledge extraction template
│   │   └── playbook.txt       # Knowledge injection template
│   ├── commands/              # Custom commands
│   │   └── init-playbook.md   # /init-playbook command
│   ├── scripts/               # Helper scripts
│   │   └── bootstrap_playbook.py  # Knowledge base initialization
│   └── settings.json          # Configuration template
└── README.md
```

## 🔧 Tech Stack

- **Python** - Core logic and hook implementation
- **Node.js** - Installation and deployment automation
- **Anthropic Claude API** - Intelligent analysis engine
- **JSON** - Lightweight knowledge storage

## 🎯 Design Philosophy

ACE follows the "Elegant Automation" principle:

- **Non-Intrusive**: Fully leverages Claude Code's native hook mechanism
- **Intelligent Adaptation**: Continuously optimizes knowledge quality based on actual effectiveness
- **Lightweight & Efficient**: JSON storage with minimal performance overhead
- **Progressive Enhancement**: Builds knowledge system from scratch gradually

## 📈 Impact

After using ACE, Claude Code will:

- Understand project-specific requirements and context faster
- Avoid repetitive errors and suggestions
- Provide more precise code and architecture recommendations
- Remember project-specific development patterns and preferences

## 📄 License

MIT License