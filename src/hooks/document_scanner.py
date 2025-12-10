"""
Document scanning utilities for extracting project-specific knowledge.
Focuses on high-value documents while avoiding noise.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional
import json

async def scan_project_documents(max_documents: int = 10) -> List[Dict]:
    """
    Scan project for high-value documents containing actionable knowledge.

    Returns list of document contents with metadata.
    """
    project_root = Path.cwd()
    documents = []

    # Priority document patterns (highest to lowest)
    document_patterns = [
        # Architecture and decision records
        {"pattern": "README*", "priority": 100, "category": "overview"},
        {"pattern": "docs/ADR*", "priority": 90, "category": "decisions"},
        {"pattern": "docs/architecture*", "priority": 85, "category": "architecture"},

        # Configuration and deployment
        {"pattern": ".env.example", "priority": 80, "category": "config"},
        {"pattern": "docker-compose*.yml", "priority": 75, "category": "deployment"},
        {"pattern": "*.prod.conf", "priority": 70, "category": "config"},

        # Development documentation
        {"pattern": "CONTRIBUTING*", "priority": 65, "category": "development"},
        {"pattern": "docs/guide*", "priority": 60, "category": "guide"},
        {"pattern": "docs/*tutorial*", "priority": 55, "category": "tutorial"},

        # Code with heavy documentation
        {"pattern": "src/**/*.py", "priority": 40, "category": "core_code",
         "filter": is_heavily_documented},

        # Configuration files
        {"pattern": "*.json", "priority": 30, "category": "config",
         "filter": is_meaningful_config},
        {"pattern": "*.yaml", "priority": 30, "category": "config",
         "filter": is_meaningful_config},
    ]

    # Scan and prioritize
    for pattern_info in document_patterns:
        if len(documents) >= max_documents:
            break

        pattern = pattern_info["pattern"]
        priority = pattern_info["priority"]
        category = pattern_info["category"]
        filter_func = pattern_info.get("filter")

        # Find matching files
        matches = list(project_root.glob(pattern))
        matches.sort(key=lambda x: str(x))  # Consistent ordering

        for file_path in matches[:2]:  # Limit per pattern to avoid domination
            if len(documents) >= max_documents:
                break

            # Skip if file doesn't exist or is too large
            if not file_path.exists() or file_path.stat().st_size > 50000:
                continue

            # Apply custom filter if provided
            if filter_func and not filter_func(file_path):
                continue

            try:
                content = read_document_content(file_path, category)
                if content and is_content_valuable(content):
                    documents.append({
                        "path": str(file_path.relative_to(project_root)),
                        "content": content,
                        "priority": priority,
                        "category": category
                    })
            except Exception as e:
                # Skip files that can't be read
                continue

    # Sort by priority
    documents.sort(key=lambda x: x["priority"], reverse=True)
    return documents[:max_documents]

def is_heavily_documented(file_path: Path) -> bool:
    """Check if Python file has substantial documentation."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Count documentation indicators
        docstring_count = content.count('"""') + content.count("'''")
        comment_lines = len([l for l in content.split('\n') if l.strip().startswith('#')])
        content_lines = len([l for l in content.split('\n') if l.strip() and not l.strip().startswith('#')])

        # Consider heavily documented if:
        # - Has at least 2 docstrings OR
        # - Comment ratio > 20% AND at least 5 comments
        if docstring_count >= 2:
            return True
        if content_lines > 0 and (comment_lines / content_lines) > 0.2 and comment_lines >= 5:
            return True

        return False
    except:
        return False

def is_meaningful_config(file_path: Path) -> bool:
    """Check if configuration file has meaningful content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Skip empty or template-only configs
        if len(content.strip()) < 50:
            return False

        # Skip package configs (package.json, requirements.txt unless with comments)
        if file_path.name in ['package.json', 'requirements.txt', 'yarn.lock']:
            return '#' in content or '//' in content

        return True
    except:
        return False

def read_document_content(file_path: Path, category: str) -> Optional[str]:
    """Read document content with appropriate processing."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Apply category-specific processing
        if category == "core_code":
            # For Python files, extract just the documentation
            return extract_code_documentation(content)
        elif category == "config":
            # For configs, include comments
            return include_config_comments(content)
        else:
            # For documentation, include as-is
            return content[:5000]  # Limit size
    except:
        return None

def extract_code_documentation(python_code: str) -> str:
    """Extract documentation and key comments from Python code."""
    lines = python_code.split('\n')
    extracted = []

    in_docstring = False
    docstring_char = None

    for line in lines:
        stripped = line.strip()

        # Track docstrings
        if '"""' in stripped or "'''" in stripped:
            in_docstring = not in_docstring
            if in_docstring:
                docstring_char = '"""' if '"""' in stripped else "'''"
            extracted.append(line)
        elif in_docstring and docstring_char in line:
            in_docstring = False
            extracted.append(line)
        elif in_docstring:
            extracted.append(line)
        # Extract important comments
        elif stripped.startswith('#') and any(keyword in stripped.lower()
                                          for keyword in ['note:', 'warning:', 'fixme:', 'todo:', 'important:']):
            extracted.append(line)
        # Extract class/function definitions with docstrings
        elif (stripped.startswith('def ') or stripped.startswith('class ') or
              stripped.startswith('async def ')):
            extracted.append(line)

    return '\n'.join(extracted)

def include_config_comments(config_content: str) -> str:
    """Include config lines with their comments."""
    lines = config_content.split('\n')
    commented_lines = []

    for line in lines:
        # Include if it has a comment or is a meaningful setting
        if '#' in line or '=' in line:
            commented_lines.append(line)

    return '\n'.join(commented_lines)

def is_content_valuable(content: str) -> bool:
    """Quick check if content likely contains valuable knowledge."""
    if len(content.strip()) < 100:
        return False

    # Look for indicators of valuable content
    valuable_indicators = [
        'because', 'reason', 'note:', 'important', 'warning',
        'best practice', 'avoid', 'remember', 'consider',
        'fix:', 'solution', 'approach', 'decision',
        'performance', 'security', 'optimize'
    ]

    content_lower = content.lower()
    indicator_count = sum(1 for indicator in valuable_indicators if indicator in content_lower)

    # Consider valuable if multiple indicators found
    return indicator_count >= 2

# Utility function to integrate with existing extraction flow
async def extract_document_knowledge(playbook: Dict) -> Dict:
    """Extract knowledge from project documents."""
    from common import extract_keypoints

    documents = await scan_project_documents()

    if not documents:
        return {"new_key_points": [], "merged_key_points": []}

    # Prepare document content for analysis
    document_content = "\n\n".join([
        f"--- {doc['path']} ({doc['category']}) ---\n{doc['content']}"
        for doc in documents
    ])

    # Extract knowledge using the document-specific prompt
    extraction_result = await extract_keypoints(
        [{"role": "user", "content": document_content}],
        playbook,
        "document_extraction"
    )

    # Add source information to extracted points
    for point in extraction_result.get("new_key_points", []):
        point["source_document"] = documents[0]["path"] if documents else "unknown"
        point["source_type"] = "document"

    return extraction_result