# Enhanced Knowledge Extraction Prompt Template

## Task
Extract high-quality knowledge points from reasoning trajectories with enhanced temporal context and actionability assessment.

## Key Improvements

### 1. Knowledge Context Enrichment
```yaml
Contextual Information Required:
  - Project Context: [web|mobile|ml|infra|data]
  - Scenario Type: [bug_fix|feature_dev|refactor|optimization|learning]
  - Time Sensitivity: [immediate|short_term|long_term]
  - Applicability Scope: [general|specific|personal]
```

### 2. Actionability Assessment
```yaml
Evaluate Actionability:
  - action_complexity: [low|medium|high] - How hard is it to implement?
  - impact_scope: [local|module|system|cross_system] - What's the impact radius?
  - prerequisite_knowledge: [basic|intermediate|advanced] - Required skill level?
  - repeatability: [one_off|occasional|frequent] - How often will this be used?
```

### 3. Temporal Dynamics
```yaml
Temporal Factors:
  - longevity_estimate: "Estimated useful lifetime in days/months"
  - freshness_indicator: "How quickly does this knowledge decay?"
  - version_dependency: "Specific version requirements (if any)"
  - maintenance_overhead: "Ongoing effort to maintain this knowledge"
```

### 4. Success Metrics
```yaml
Define Success Criteria:
  - measurable_outcomes: ["What specific improvements does this yield?"]
  - risk_mitigation: "What risks does this prevent or reduce?"
  - time_savings: "Estimated time saved per application"
  - confidence_level: "How confident are we in this knowledge?"
```

## Enhanced Extraction Instructions

### Part 1: Enhanced Contextual Analysis
1. **Project Context Classification**:
   - Identify the domain and technology stack
   - Determine if the knowledge is framework-specific or language-agnostic
   - Note any platform dependencies

2. **Scenario Type Detection**:
   - Classify the problem-solving context
   - Identify patterns in user intent
   - Note any recurring themes

### Part 2: Actionability Enhancement
For each knowledge point, assess:
```json
{
  "text": "Use async/await with proper error boundaries for API calls",
  "actionability": {
    "complexity": "medium",
    "scope": "module",
    "prerequisites": "basic_javascript",
    "repeatability": "frequent",
    "estimated_time_to_implement": "30_minutes"
  }
}
```

### Part 3: Temporal Validity
```json
{
  "temporal": {
    "created_at": "2025-12-10",
    "estimated_valid_until": "2026-06-10",
    "decay_rate": "slow",
    "seasonal_relevance": false,
    "version_constraints": ["node>=14", "react>=16"]
  }
}
```

### Part 4: Success Story Integration
For each successful pattern, capture:
```json
{
  "success_metrics": {
    "problem_solved": "Unhandled promise rejections causing crashes",
    "improvement_measured": "Zero unhandled errors after implementation",
    "time_saved_per_occurrence": "15_minutes_debug_time",
    "confidence_score": 0.9
  }
}
```

## Enhanced Output Format

```json
{
  "knowledge_points": [
    {
      "id": "kp_async_error_boundaries",
      "text": "Use async/await with proper error boundaries for API calls",
      "tags": ["javascript", "async", "error_handling"],
      "context": {
        "domain": "web_development",
        "scenario": "error_handling",
        "applicability": "general"
      },
      "actionability": {
        "complexity": "medium",
        "scope": "module",
        "prerequisites": "basic_javascript",
        "repeatability": "frequent",
        "estimated_time_to_implement": "30_minutes"
      },
      "quality_scores": {
        "effectiveness": 0.9,
        "risk_level": -0.7,
        "innovation_level": 0.2,
        "actionability_score": 0.8
      },
      "temporal": {
        "created_at": "2025-12-10",
        "estimated_valid_until": "2026-06-10",
        "decay_rate": "slow",
        "version_constraints": ["node>=14"]
      },
      "success_metrics": {
        "problem_solved": "Unhandled promise rejections",
        "improvement_measured": "Zero unhandled errors",
        "time_saved_per_occurrence": "15_minutes",
        "confidence_score": 0.9
      },
      "sources": ["conv_123_msg_45"]
    }
  ],
  "quality_gates": {
    "min_actionability_score": 0.6,
    "max_decay_rate": "medium",
    "required_success_metrics": true
  }
}
```

## Quality Gates

Filter out knowledge that doesn't meet minimum criteria:
- Actionability score < 0.6 (too hard to implement)
- Decay rate = "fast" with lifetime < 7 days (too transient)
- No measurable success metrics (unclear value)
- High complexity with low repeatability (not worth the effort)