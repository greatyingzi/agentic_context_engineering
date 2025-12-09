# Documentation Consistency Pre-commit Hook

This project includes a pre-commit hook that ensures documentation consistency between different language versions.

## What it does

- **Checks README files**: Warns if `README.md` is modified but `README.zh.md` is not (and vice versa)
- **Checks other documentation**: Monitors other doc pairs like `docs/README.md` and `docs/README.zh.md`
- **Suggests translations**: When adding new English markdown files, suggests adding Chinese versions

## Installation

### Option 1: One-time setup
```bash
./install-docs-hook.sh
```

### Option 2: Use .githooks directory (recommended for teams)
```bash
# Configure git to use .githooks directory by default
git config core.hooksPath .githooks

# Install hooks
cp .githooks/pre-commit .git/hooks/
chmod +x .git/hooks/pre-commit
```

## Usage Examples

### Scenario 1: Only modify README.md
```bash
# Edit README.md
git add README.md
git commit -m "Update English README"
# Hook will warn about missing README.zh.md changes
```

Output:
```
⚠️  WARNING: README.md was modified but README.zh.md was not.
   Please ensure both language versions are updated for consistency.
   If you only meant to update the English version, consider updating README.zh.md as well.
```

### Scenario 2: Modify both files
```bash
# Edit both README.md and README.zh.md
git add README.md README.zh.md
git commit -m "Update documentation"
# Hook will pass without warnings
```

Output:
```
✅ Documentation consistency check passed!
```

### Scenario 3: Add new documentation
```bash
# Create new doc file
echo "# API Guide" > docs/API.md
git add docs/API.md
git commit -m "Add API guide"
# Hook will suggest adding Chinese version
```

Output:
```
⚠️  INFO: New documentation file docs/API.md was added.
   Consider adding a Chinese version docs/API.zh.md for bilingual documentation.
```

## Configuration

You can customize which file pairs to check by modifying the `check_doc_pair` calls in the hook:

```bash
# Add your own documentation pairs
check_doc_pair "path/to/your/doc.md" "path/to/your/doc.zh.md"
```

## Bypassing the Hook

If you need to bypass the hook (not recommended), you can use:
```bash
git commit --no-verify
```

## Why This Matters

- **Consistency**: Ensures all documentation is kept in sync
- **Team Collaboration**: Prevents forgotten translations
- **Quality**: Maintains professional bilingual documentation