#!/bin/bash
# Install documentation consistency pre-commit hook

echo "🚀 Installing documentation consistency pre-commit hook..."

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

# Git hooks directory
HOOKS_DIR=$(git rev-parse --git-dir)/hooks

# Source hook file (use .githooks if it exists, otherwise use .git/hooks)
if [ -f "$(dirname "$0")/.githooks/pre-commit" ]; then
    SOURCE_HOOK="$(dirname "$0")/.githooks/pre-commit"
    echo "📁 Using hook from .githooks directory"
else
    SOURCE_HOOK="$(dirname "$0")/.git/hooks/pre-commit"
    echo "📁 Using hook from .git/hooks directory"
fi

TARGET_HOOK="$HOOKS_DIR/pre-commit"

# Copy hook
cp "$SOURCE_HOOK" "$TARGET_HOOK"

# Make it executable
chmod +x "$TARGET_HOOK"

echo "✅ Pre-commit hook installed successfully!"
echo ""
echo "📋 What it does:"
echo "   - Warns if README.md is modified but README.zh.md is not"
echo "   - Warns if README.zh.md is modified but README.md is not"
echo "   - Checks for other documentation file pairs"
echo "   - Suggests adding Chinese versions for new English documentation"
echo ""
echo "🎯 The hook will run automatically when you commit changes."
echo ""
echo "💡 To configure git to use .githooks directory by default:"
echo "   git config core.hooksPath .githooks"