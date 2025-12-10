#!/usr/bin/env python3
"""
A/B Testing Framework for KPT Context-Aware Parameter Weighting System

This framework compares the old hardcoded weights vs new contextual weights
across multiple dimensions including knowledge quality, performance, and UX.
"""

import json
import time
import statistics
import tracemalloc
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
import sys
import os

# Add the src directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from hooks.playbook_engine import (
        select_relevant_keypoints,
        _get_contextual_weights,
        load_playbook,
        generate_keypoint_name
    )
    from hooks.utils.tag_utils import normalize_tags, infer_tags_from_text
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "hooks"))
    from playbook_engine import (
        select_relevant_keypoints,
        _get_contextual_weights,
        load_playbook,
        generate_keypoint_name
    )
    sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "hooks" / "utils"))
    from tag_utils import normalize_tags, infer_tags_from_text


@dataclass
class TestScenario:
    """Represents a test scenario with context and expected characteristics"""
    name: str
    tags: List[str]
    description: str
    expected_context_type: str  # "urgent", "production", "exploratory", "generic"
    temperature: float
    limit: int = 6


@dataclass
class TestMetrics:
    """Container for test metrics"""
    execution_time: float
    memory_usage: float
    selected_knowledge_count: int
    high_confidence_count: int
    recommendation_count: int
    avg_relevance_score: float
    diversity_score: float
    layer_balance_ratio: float
    token_usage_estimate: int
    effectiveness_score: float
    risk_score: float


@dataclass
class TestResult:
    """Single test result"""
    scenario_name: str
    system_type: str  # "old" or "new"
    metrics: TestMetrics
    selected_knowledge: List[Dict]
    context_weights: Dict[str, float]


class ABTestFramework:
    """A/B Testing Framework for KPT Parameter Weighting"""

    def __init__(self):
        self.test_results: List[TestResult] = []
        self.test_scenarios = self._create_test_scenarios()
        self.sample_knowledge_base = self._generate_test_knowledge_base()

    def _create_test_scenarios(self) -> List[TestScenario]:
        """Create standardized test scenarios"""
        return [
            TestScenario(
                name="urgent_bug_fix",
                tags=["fix", "bug", "error", "critical", "urgent", "production"],
                description="Urgent bug fix context with critical priority",
                expected_context_type="urgent",
                temperature=0.2  # Conservative mode
            ),
            TestScenario(
                name="production_deployment",
                tags=["deploy", "release", "customer", "production", "enterprise", "stable"],
                description="Production deployment with customer impact",
                expected_context_type="production",
                temperature=0.5  # Balanced mode
            ),
            TestScenario(
                name="research_exploration",
                tags=["explore", "research", "innovative", "experimental", "learn", "alternative"],
                description="Research exploration with innovation focus",
                expected_context_type="exploratory",
                temperature=0.8  # Exploratory mode
            ),
            TestScenario(
                name="generic_development",
                tags=["feature", "implementation", "development", "coding", "build"],
                description="Generic development work",
                expected_context_type="generic",
                temperature=0.5  # Balanced mode
            )
        ]

    def _generate_test_knowledge_base(self) -> List[Dict]:
        """Generate comprehensive test knowledge base with known characteristics"""
        knowledge_points = [
            # High confidence, proven solutions
            {
                "name": "kpt_001",
                "text": "Implement proper error handling with try-catch blocks",
                "score": 5,
                "tags": ["error-handling", "best-practices", "production"],
                "effect_rating": 0.9,
                "risk_level": -0.8,
                "innovation_level": 0.2
            },
            {
                "name": "kpt_002",
                "text": "Use established design patterns for maintainability",
                "score": 4,
                "tags": ["design-patterns", "architecture", "proven"],
                "effect_rating": 0.8,
                "risk_level": -0.6,
                "innovation_level": 0.3
            },
            # Medium confidence, useful recommendations
            {
                "name": "kpt_003",
                "text": "Implement comprehensive unit test coverage",
                "score": 2,
                "tags": ["testing", "quality", "development"],
                "effect_rating": 0.7,
                "risk_level": -0.4,
                "innovation_level": 0.4
            },
            {
                "name": "kpt_004",
                "text": "Add logging for debugging and monitoring",
                "score": 1,
                "tags": ["logging", "debugging", "observability"],
                "effect_rating": 0.6,
                "risk_level": -0.5,
                "innovation_level": 0.2
            },
            # Innovative approaches
            {
                "name": "kpt_005",
                "text": "Experiment with AI-powered code optimization",
                "score": 1,
                "tags": ["ai", "optimization", "experimental", "innovative"],
                "effect_rating": 0.5,
                "risk_level": 0.1,
                "innovation_level": 0.9
            },
            {
                "name": "kpt_006",
                "text": "Implement cutting-edge quantum computing algorithm",
                "score": 0,
                "tags": ["quantum", "algorithm", "research", "breakthrough"],
                "effect_rating": 0.4,
                "risk_level": 0.3,
                "innovation_level": 1.0
            },
            # Risk/High innovation items
            {
                "name": "kpt_007",
                "text": "Use experimental blockchain for data storage",
                "score": -1,
                "tags": ["blockchain", "experimental", "unstable"],
                "effect_rating": 0.3,
                "risk_level": 0.6,
                "innovation_level": 0.8
            },
            {
                "name": "kpt_008",
                "text": "Deploy to production with minimal testing",
                "score": -2,
                "tags": ["production", "risky", "shortcut"],
                "effect_rating": 0.2,
                "risk_level": 0.8,
                "innovation_level": 0.1
            },
            # Standard development practices
            {
                "name": "kpt_009",
                "text": "Follow clean code principles and standards",
                "score": 3,
                "tags": ["clean-code", "standards", "development"],
                "effect_rating": 0.8,
                "risk_level": -0.7,
                "innovation_level": 0.2
            },
            {
                "name": "kpt_010",
                "text": "Implement proper CI/CD pipeline automation",
                "score": 4,
                "tags": ["ci-cd", "automation", "deployment", "production"],
                "effect_rating": 0.9,
                "risk_level": -0.5,
                "innovation_level": 0.4
            }
        ]
        return knowledge_points

    def _old_hardcoded_weights(self, layer_type: str, all_tags_text: str) -> Tuple[float, float, float]:
        """Old hardcoded weight system (baseline)"""
        # These are the default values that were used before context-aware weights
        if layer_type == "HIGH_CONFIDENCE":
            return 0.3, 0.4, -0.2  # Fixed weights regardless of context
        else:
            return 0.3, 0.4, -0.2  # Same weights for recommendation layer

    def _patch_select_function(self, use_context_weights: bool) -> callable:
        """Create a patched version of select_relevant_keypoints with or without context weights"""
        def patched_select(
            playbook: dict,
            tags: List[str],
            limit: int = 6,
            prompt_tags: Optional[List[str]] = None,
            temperature: float = 0.5
        ) -> List[dict]:
            key_points = playbook.get("key_points", [])
            if not key_points:
                return []

            desired_tags = [t.lower() for t in tags or [] if isinstance(t, str)]
            prompt_tag_set = {t.lower() for t in (prompt_tags or [])}

            # Create text for context analysis
            all_tags_text = " ".join(desired_tags).lower()

            # Define clear classification boundaries
            HIGH_CONFIDENCE_THRESHOLD = 2.0

            def tag_match_score(kp_tag: str, desired: str) -> int:
                """Exact =3, substring = 2, token overlap = 1, else 0."""
                import re
                if kp_tag == desired:
                    return 3
                if kp_tag in desired or desired in kp_tag:
                    return 2
                kp_tokens = set(re.split(r"[^a-z0-9]+", kp_tag))
                desired_tokens = set(re.split(r"[^a-z0-9]+", desired))
                kp_tokens.discard("")
                desired_tokens.discard("")
                return 1 if kp_tokens & desired_tokens else 0

            def score_and_coverage(kp_tags: list[str]) -> tuple[int, int, int]:
                best = 0
                matched = set()
                prompt_hits = 0
                for kp_tag in kp_tags:
                    kp_norm = kp_tag.lower()
                    for desired in desired_tags:
                        s = tag_match_score(kp_norm, desired)
                        if s > 0:
                            matched.add(desired)
                            if desired in prompt_tag_set:
                                prompt_hits += 1
                            best = max(best, s)
                            if best == 3 and len(matched) == len(desired_tags):
                                return best, len(matched), prompt_hits
                return best, len(matched), prompt_hits

            # CLASSIFICATION PHASE: Separate into two distinct layers
            high_confidence_layer = []  # Layer 1: score >= 2
            recommendation_layer = []    # Layer 2: 0 <= score < 2

            for kp in key_points:
                kp_tags = [t for t in kp.get("tags", []) if isinstance(t, str)]
                score, coverage, prompt_hits = score_and_coverage(kp_tags)

                # Skip negative scoring items entirely
                kp_score = kp.get("score", 0)
                if kp_score < 0:
                    continue

                if score > 0 and coverage > 0:
                    # Calculate base weight
                    base_weight = 10 * coverage + 3 * score + 5 * prompt_hits + kp_score

                    # LAYER-SPECIFIC TEMPERATURE APPLICATION
                    if kp_score >= HIGH_CONFIDENCE_THRESHOLD:
                        # LAYER 1: High-Confidence Matching
                        layer_type = "HIGH_CONFIDENCE"

                        # Temperature affects high-confidence items INVERSELY
                        # Low temperature = HIGH weight for proven solutions
                        temp_multiplier = 2.5 - temperature * 1.5

                        # Additional layer-specific adjustments
                        if temperature <= 0.3:
                            temp_multiplier += 0.5  # Conservative boost for proven items
                        elif temperature >= 0.7:
                            temp_multiplier -= 0.3  # Exploratory mode reduces proven item weight

                    else:
                        # LAYER 2: Recommendation-Based
                        layer_type = "RECOMMENDATION"

                        # Temperature affects recommendation items DIRECTLY
                        # High temperature = HIGH weight for exploration
                        temp_multiplier = temperature * 2.0

                        # Additional layer-specific adjustments
                        if temperature <= 0.3:
                            temp_multiplier *= 0.3  # Conservative suppresses recommendations
                        elif temperature >= 0.7:
                            temp_multiplier += 0.5  # Exploratory boosts recommendations

                    # Apply multi-dimensional adjustments
                    effect_rating = kp.get("effect_rating", 0.5)
                    risk_level = kp.get("risk_level", -0.5)
                    innovation_level = kp.get("innovation_level", 0.5)

                    # Use either context-aware or hardcoded weights
                    if use_context_weights:
                        effect_weight, innovation_weight, risk_threshold = _get_contextual_weights(
                            layer_type, all_tags_text
                        )
                    else:
                        effect_weight, innovation_weight, risk_threshold = self._old_hardcoded_weights(
                            layer_type, all_tags_text
                        )

                    if layer_type == "HIGH_CONFIDENCE":
                        # High confidence items get effectiveness boost
                        temp_multiplier += effect_rating * effect_weight
                        # Risk reduction for proven items
                        if risk_level < risk_threshold:
                            temp_multiplier += 0.2
                    else:
                        # Recommendations get innovation boost
                        temp_multiplier += innovation_level * innovation_weight
                        # Risk awareness for new ideas
                        if risk_level > risk_threshold:
                            temp_multiplier *= 0.8

                    # Store metadata for debugging
                    kp["_layer"] = layer_type
                    kp["_base_weight"] = base_weight
                    kp["_temp_multiplier"] = temp_multiplier
                    kp["_total_match"] = base_weight * temp_multiplier
                    kp["_match_score"] = score
                    kp["_match_coverage"] = coverage
                    kp["_prompt_hits"] = prompt_hits

                    # CLASSIFY INTO CORRECT LAYER
                    if layer_type == "HIGH_CONFIDENCE":
                        high_confidence_layer.append(kp)
                    else:
                        recommendation_layer.append(kp)

            # TEMPERATURE-BASED ALLOCATION PHASE
            if temperature <= 0.3:
                # CONSERVATIVE: Prioritize proven solutions
                high_confidence_limit = max(4, int(limit * 0.7))  # Up to 70%
                recommendation_limit = max(1, limit - high_confidence_limit)  # At least 1
            elif temperature >= 0.7:
                # EXPLORATORY: Prioritize new ideas
                recommendation_limit = max(4, int(limit * 0.7))  # Up to 70%
                high_confidence_limit = max(1, limit - recommendation_limit)  # At least 1
            else:
                # BALANCED: Equal allocation
                high_confidence_limit = limit // 2
                recommendation_limit = limit - high_confidence_limit

            # Sort each layer internally
            sorted_high_confidence = sorted(high_confidence_layer, key=lambda kp: -kp["_total_match"])[:high_confidence_limit]
            sorted_recommendations = sorted(recommendation_layer, key=lambda kp: -kp["_total_match"])[:recommendation_limit]

            # MERGE WITH LAYER PRIORITY
            final_selection = []

            # Layer-specific ranking
            for i, kp in enumerate(sorted_high_confidence):
                kp["_layer_rank"] = f"HC-{i+1}"
                final_selection.append(kp)

            for i, kp in enumerate(sorted_recommendations):
                kp["_layer_rank"] = f"RC-{i+1}"
                final_selection.append(kp)

            # FINAL SORTING: Temperature-aware global ordering
            if temperature <= 0.3:
                # Conservative: High confidence items first
                final_selection = sorted(final_selection, key=lambda kp: (
                    0 if kp["_layer"] == "HIGH_CONFIDENCE" else 2,  # HC first
                    1 if kp["_layer"] == "RECOMMENDATION" else 3,  # RC second
                    -kp["_total_match"]  # Then by score
                ))
            elif temperature >= 0.7:
                # Exploratory: Recommendations first
                final_selection = sorted(final_selection, key=lambda kp: (
                    0 if kp["_layer"] == "RECOMMENDATION" else 2,  # RC first
                    1 if kp["_layer"] == "HIGH_CONFIDENCE" else 3,  # HC second
                    -kp["_total_match"]  # Then by score
                ))
            else:
                # Balanced: Mix by score but preserve layer identity
                final_selection = sorted(final_selection, key=lambda kp: -kp["_total_match"])

            # Return only the requested limit
            return final_selection[:limit]

        return patched_select

    def _calculate_metrics(self, selected_knowledge: List[Dict], context_weights: Dict[str, float]) -> TestMetrics:
        """Calculate comprehensive metrics for the test result"""
        if not selected_knowledge:
            return TestMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        # Basic counts
        total_count = len(selected_knowledge)
        high_conf_count = sum(1 for kp in selected_knowledge if kp.get("_layer") == "HIGH_CONFIDENCE")
        rec_count = sum(1 for kp in selected_knowledge if kp.get("_layer") == "RECOMMENDATION")

        # Layer balance ratio (0 = all HC, 1 = all RC)
        layer_balance = rec_count / total_count if total_count > 0 else 0

        # Average relevance score
        avg_relevance = sum(kp.get("_total_match", 0) for kp in selected_knowledge) / total_count

        # Diversity score (based on tag variety)
        all_tags = []
        for kp in selected_knowledge:
            all_tags.extend(kp.get("tags", []))
        unique_tags = len(set(all_tags))
        diversity_score = unique_tags / max(len(all_tags), 1)  # Ratio of unique to total tags

        # Effectiveness and risk scores
        effectiveness_scores = [kp.get("effect_rating", 0.5) for kp in selected_knowledge]
        risk_scores = [kp.get("risk_level", -0.5) for kp in selected_knowledge]
        avg_effectiveness = sum(effectiveness_scores) / len(effectiveness_scores)
        avg_risk = sum(risk_scores) / len(risk_scores)

        # Token usage estimate (rough approximation)
        token_estimate = sum(
            len(kp.get("text", "")) +
            len(", ".join(kp.get("tags", [])))
            for kp in selected_knowledge
        )

        return TestMetrics(
            execution_time=0,  # Will be set during test
            memory_usage=0,    # Will be set during test
            selected_knowledge_count=total_count,
            high_confidence_count=high_conf_count,
            recommendation_count=rec_count,
            avg_relevance_score=avg_relevance,
            diversity_score=diversity_score,
            layer_balance_ratio=layer_balance,
            token_usage_estimate=token_estimate,
            effectiveness_score=avg_effectiveness,
            risk_score=avg_risk
        )

    def run_single_test(self, scenario: TestScenario, use_context_weights: bool) -> TestResult:
        """Run a single test with specified scenario and system type"""
        # Create test playbook
        test_playbook = {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "key_points": self.sample_knowledge_base.copy()
        }

        # Start memory tracking
        tracemalloc.start()
        start_time = time.time()

        # Patch the select function based on system type
        select_func = self._patch_select_function(use_context_weights)

        # Run the selection
        selected_knowledge = select_func(
            playbook=test_playbook,
            tags=scenario.tags,
            limit=scenario.limit,
            temperature=scenario.temperature
        )

        # Measure performance
        execution_time = time.time() - start_time
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Get context weights used
        all_tags_text = " ".join(scenario.tags).lower()
        layer_type = "HIGH_CONFIDENCE"  # We'll use this as representative
        effect_weight, innovation_weight, risk_threshold = _get_contextual_weights(
            layer_type, all_tags_text
        ) if use_context_weights else self._old_hardcoded_weights(layer_type, all_tags_text)

        context_weights = {
            "effect_weight": effect_weight,
            "innovation_weight": innovation_weight,
            "risk_threshold": risk_threshold
        }

        # Calculate metrics
        metrics = self._calculate_metrics(selected_knowledge, context_weights)

        # Update metrics with actual performance data
        metrics.execution_time = execution_time
        metrics.memory_usage = peak / 1024 / 1024  # Convert to MB

        return TestResult(
            scenario_name=scenario.name,
            system_type="new" if use_context_weights else "old",
            metrics=metrics,
            selected_knowledge=selected_knowledge,
            context_weights=context_weights
        )

    def run_ab_tests(self, iterations: int = 10) -> None:
        """Run A/B tests for all scenarios"""
        print(f"Running A/B tests with {iterations} iterations per scenario...")

        for scenario in self.test_scenarios:
            print(f"\nTesting scenario: {scenario.name}")

            for iteration in range(iterations):
                # Test old system
                old_result = self.run_single_test(scenario, use_context_weights=False)
                self.test_results.append(old_result)

                # Test new system
                new_result = self.run_single_test(scenario, use_context_weights=True)
                self.test_results.append(new_result)

                if iteration % 5 == 0:
                    print(f"  Completed iteration {iteration + 1}/{iterations}")

        print("\nA/B testing completed!")

    def analyze_results(self) -> Dict[str, Any]:
        """Analyze test results with statistical significance"""
        # Group results by scenario and system type
        scenario_results = {}

        for result in self.test_results:
            if result.scenario_name not in scenario_results:
                scenario_results[result.scenario_name] = {"old": [], "new": []}

            scenario_results[result.scenario_name][result.system_type].append(result)

        analysis = {}

        for scenario_name, results in scenario_results.items():
            old_results = results["old"]
            new_results = results["new"]

            # Calculate statistics for each metric
            metrics_comparison = {}

            for metric_name in [
                "execution_time", "memory_usage", "selected_knowledge_count",
                "high_confidence_count", "recommendation_count", "avg_relevance_score",
                "diversity_score", "layer_balance_ratio", "token_usage_estimate",
                "effectiveness_score", "risk_score"
            ]:
                old_values = [getattr(r.metrics, metric_name) for r in old_results]
                new_values = [getattr(r.metrics, metric_name) for r in new_results]

                metrics_comparison[metric_name] = {
                    "old_mean": statistics.mean(old_values),
                    "old_std": statistics.stdev(old_values) if len(old_values) > 1 else 0,
                    "new_mean": statistics.mean(new_values),
                    "new_std": statistics.stdev(new_values) if len(new_values) > 1 else 0,
                    "improvement": statistics.mean(new_values) - statistics.mean(old_values),
                    "improvement_percent": (statistics.mean(new_values) - statistics.mean(old_values)) / statistics.mean(old_values) * 100 if statistics.mean(old_values) != 0 else 0,
                    "p_value": self._calculate_t_test(old_values, new_values)
                }

            analysis[scenario_name] = {
                "scenario_description": next(s.description for s in self.test_scenarios if s.name == scenario_name),
                "expected_context": next(s.expected_context_type for s in self.test_scenarios if s.name == scenario_name),
                "metrics_comparison": metrics_comparison,
                "old_system_samples": len(old_results),
                "new_system_samples": len(new_results)
            }

        return analysis

    def _calculate_t_test(self, old_values: List[float], new_values: List[float]) -> float:
        """Simple t-test approximation (returns p-value estimate)"""
        if len(old_values) < 2 or len(new_values) < 2:
            return 1.0

        # Calculate means and standard deviations
        old_mean = statistics.mean(old_values)
        new_mean = statistics.mean(new_values)
        old_std = statistics.stdev(old_values)
        new_std = statistics.stdev(new_values)

        # Calculate t-statistic
        n1, n2 = len(old_values), len(new_values)
        pooled_std = ((n1 - 1) * old_std**2 + (n2 - 1) * new_std**2) / (n1 + n2 - 2)
        pooled_std = pooled_std**0.5

        if pooled_std == 0:
            return 1.0

        t_stat = (old_mean - new_mean) / (pooled_std * (1/n1 + 1/n2)**0.5)

        # Approximate p-value (very rough approximation)
        # In reality, you'd use scipy.stats.t.sf for accurate p-values
        if abs(t_stat) < 1.96:
            return 0.05  # Not significant
        elif abs(t_stat) < 2.58:
            return 0.01  # Significant
        else:
            return 0.001  # Highly significant

    def generate_report(self, analysis: Dict[str, Any], output_path: str = None) -> str:
        """Generate comprehensive A/B testing report"""
        if output_path is None:
            output_path = f"ab_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>KPT A/B Testing Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .scenario {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .metric {{ margin: 10px 0; padding: 10px; background-color: #f9f9f9; }}
        .improvement {{ font-weight: bold; }}
        .positive {{ color: green; }}
        .negative {{ color: red; }}
        .neutral {{ color: orange; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>KPT Context-Aware Parameter Weighting A/B Test Report</h1>
        <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Comparing Old Hardcoded Weights vs New Context-Aware Weights</p>
    </div>
"""

        for scenario_name, scenario_data in analysis.items():
            html_content += f"""
    <div class="scenario">
        <h2>Scenario: {scenario_name}</h2>
        <p><strong>Description:</strong> {scenario_data['scenario_description']}</p>
        <p><strong>Expected Context:</strong> {scenario_data['expected_context']}</p>
        <p><strong>Sample Size:</strong> {scenario_data['old_system_samples']} (Old) vs {scenario_data['new_system_samples']} (New)</p>

        <h3>Metrics Comparison</h3>
        <table>
            <tr>
                <th>Metric</th>
                <th>Old System (μ±σ)</th>
                <th>New System (μ±σ)</th>
                <th>Improvement</th>
                <th>P-Value</th>
                <th>Significance</th>
            </tr>
"""

            metrics = scenario_data['metrics_comparison']
            for metric_name, metric_data in metrics.items():
                improvement = metric_data['improvement']
                improvement_pct = metric_data['improvement_percent']

                # Determine significance and styling
                if metric_data['p_value'] < 0.01:
                    significance = "Highly Significant"
                    significance_class = "positive"
                elif metric_data['p_value'] < 0.05:
                    significance = "Significant"
                    significance_class = "positive"
                else:
                    significance = "Not Significant"
                    significance_class = "neutral"

                # Determine improvement direction
                if improvement_pct > 0:
                    improvement_text = f"+{improvement_pct:.1f}%"
                    improvement_class = "positive"
                elif improvement_pct < 0:
                    improvement_text = f"{improvement_pct:.1f}%"
                    improvement_class = "negative"
                else:
                    improvement_text = "0.0%"
                    improvement_class = "neutral"

                old_mean_std = f"{metric_data['old_mean']:.3f}±{metric_data['old_std']:.3f}"
                new_mean_std = f"{metric_data['new_mean']:.3f}±{metric_data['new_std']:.3f}"

                html_content += f"""
            <tr>
                <td><strong>{metric_name.replace('_', ' ').title()}</strong></td>
                <td>{old_mean_std}</td>
                <td>{new_mean_std}</td>
                <td class="{improvement_class} improvement">{improvement_text}</td>
                <td>{metric_data['p_value']:.3f}</td>
                <td class="{significance_class}">{significance}</td>
            </tr>
"""

            html_content += """
        </table>
    </div>
"""

        # Overall summary
        html_content += """
    <div class="header">
        <h2>Overall Summary</h2>
        <p><strong>Key Findings:</strong></p>
        <ul>
"""

        improvements = []
        for scenario_name, scenario_data in analysis.items():
            for metric_name, metric_data in scenario_data['metrics_comparison'].items():
                if metric_data['p_value'] < 0.05 and metric_data['improvement_percent'] != 0:
                    improvements.append({
                        'scenario': scenario_name,
                        'metric': metric_name,
                        'improvement': metric_data['improvement_percent'],
                        'direction': 'improved' if metric_data['improvement_percent'] > 0 else 'degraded'
                    })

        improvements.sort(key=lambda x: abs(x['improvement']), reverse=True)

        for imp in improvements[:10]:  # Top 10 improvements
            direction_icon = "📈" if imp['direction'] == 'improved' else "📉"
            html_content += f"            <li>{direction_icon} {imp['scenario']} - {imp['metric'].replace('_', ' ').title()}: {imp['improvement']:+.1f}%</li>\n"

        html_content += """
        </ul>
    </div>
</body>
</html>
"""

        # Save report
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"A/B testing report generated: {output_path}")
        return output_path

    def generate_visualizations(self, analysis: Dict[str, Any], output_dir: str = None) -> List[str]:
        """Generate visualizations for the A/B test results"""
        if output_dir is None:
            output_dir = f"ab_test_visualizations_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        os.makedirs(output_dir, exist_ok=True)

        visualization_files = []

        # 1. Performance comparison chart
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Performance Metrics Comparison', fontsize=16)

        metrics_to_plot = ['execution_time', 'memory_usage', 'token_usage_estimate']
        titles = ['Execution Time (s)', 'Memory Usage (MB)', 'Token Usage Estimate']

        for idx, (metric, title) in enumerate(zip(metrics_to_plot, titles)):
            ax = axes[idx // 2, idx % 2]

            old_means = []
            new_means = []
            scenario_names = []

            for scenario_name, scenario_data in analysis.items():
                old_means.append(scenario_data['metrics_comparison'][metric]['old_mean'])
                new_means.append(scenario_data['metrics_comparison'][metric]['new_mean'])
                scenario_names.append(scenario_name[:20])  # Truncate for readability

            x = np.arange(len(scenario_names))
            width = 0.35

            ax.bar(x - width/2, old_means, width, label='Old System', alpha=0.7)
            ax.bar(x + width/2, new_means, width, label='New System', alpha=0.7)

            ax.set_title(title)
            ax.set_xticks(x)
            ax.set_xticklabels(scenario_names, rotation=45, ha='right')
            ax.legend()
            ax.grid(True, alpha=0.3)

        # Remove empty subplot
        fig.delaxes(axes[1, 1])
        plt.tight_layout()

        perf_chart_path = os.path.join(output_dir, 'performance_comparison.png')
        plt.savefig(perf_chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        visualization_files.append(perf_chart_path)

        # 2. Knowledge quality metrics radar chart
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))

        metrics_radar = ['avg_relevance_score', 'diversity_score', 'effectiveness_score']
        angles = np.linspace(0, 2 * np.pi, len(metrics_radar), endpoint=False).tolist()
        angles += angles[:1]  # Complete the circle

        # Plot first scenario as example
        scenario_name = list(analysis.keys())[0]
        scenario_data = analysis[scenario_name]

        old_values = [scenario_data['metrics_comparison'][m]['old_mean'] for m in metrics_radar]
        new_values = [scenario_data['metrics_comparison'][m]['new_mean'] for m in metrics_radar]

        old_values += old_values[:1]
        new_values += new_values[:1]

        ax.plot(angles, old_values, 'o-', linewidth=2, label='Old System', color='blue')
        ax.fill(angles, old_values, alpha=0.25, color='blue')
        ax.plot(angles, new_values, 'o-', linewidth=2, label='New System', color='red')
        ax.fill(angles, new_values, alpha=0.25, color='red')

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels([m.replace('_', ' ').title() for m in metrics_radar])
        ax.set_ylim(0, 1)
        ax.set_title('Knowledge Quality Metrics - ' + scenario_name, fontsize=14, pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
        ax.grid(True)

        radar_chart_path = os.path.join(output_dir, 'knowledge_quality_radar.png')
        plt.savefig(radar_chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        visualization_files.append(radar_chart_path)

        # 3. Layer distribution comparison
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Layer Distribution Analysis', fontsize=16)

        for idx, scenario_name in enumerate(analysis.keys()):
            if idx >= 4:  # Limit to 4 subplots
                break

            ax = axes[idx // 2, idx % 2]
            scenario_data = analysis[scenario_name]

            old_hc = scenario_data['metrics_comparison']['high_confidence_count']['old_mean']
            old_rc = scenario_data['metrics_comparison']['recommendation_count']['old_mean']
            new_hc = scenario_data['metrics_comparison']['high_confidence_count']['new_mean']
            new_rc = scenario_data['metrics_comparison']['recommendation_count']['new_mean']

            x = ['Old System', 'New System']
            hc_counts = [old_hc, new_hc]
            rc_counts = [old_rc, new_rc]

            width = 0.35
            ax.bar(x, hc_counts, width, label='High Confidence', alpha=0.7, color='blue')
            ax.bar(x, rc_counts, width, bottom=hc_counts, label='Recommendations', alpha=0.7, color='orange')

            ax.set_title(scenario_name)
            ax.set_ylabel('Count')
            ax.legend()
            ax.grid(True, alpha=0.3)

        plt.tight_layout()

        layer_dist_path = os.path.join(output_dir, 'layer_distribution.png')
        plt.savefig(layer_dist_path, dpi=300, bbox_inches='tight')
        plt.close()
        visualization_files.append(layer_dist_path)

        print(f"Visualizations saved to: {output_dir}")
        return visualization_files


def main():
    """Main function to run the A/B testing framework"""
    print("KPT Context-Aware Parameter Weighting A/B Testing Framework")
    print("=" * 60)

    # Initialize framework
    framework = ABTestFramework()

    # Run tests
    framework.run_ab_tests(iterations=10)

    # Analyze results
    print("\nAnalyzing results...")
    analysis = framework.analyze_results()

    # Generate report
    print("\nGenerating report...")
    report_path = framework.generate_report(analysis)

    # Generate visualizations
    print("\nGenerating visualizations...")
    viz_files = framework.generate_visualizations(analysis)

    # Print summary
    print("\n" + "=" * 60)
    print("A/B TESTING SUMMARY")
    print("=" * 60)

    total_improvements = 0
    total_degradations = 0

    for scenario_name, scenario_data in analysis.items():
        print(f"\nScenario: {scenario_name}")
        print(f"Description: {scenario_data['scenario_description']}")
        print(f"Expected Context: {scenario_data['expected_context']}")

        scenario_improvements = 0
        scenario_degradations = 0

        for metric_name, metric_data in scenario_data['metrics_comparison'].items():
            if metric_data['p_value'] < 0.05:  # Significant results
                improvement_pct = metric_data['improvement_percent']
                if improvement_pct > 0:
                    scenario_improvements += 1
                    total_improvements += 1
                elif improvement_pct < 0:
                    scenario_degradations += 1
                    total_degradations += 1

                status = "📈 IMPROVED" if improvement_pct > 0 else "📉 DEGRADED" if improvement_pct < 0 else "➡️ NO CHANGE"
                print(f"  {metric_name.replace('_', ' ').title()}: {status} ({improvement_pct:+.1f}%, p={metric_data['p_value']:.3f})")

        print(f"  Summary: {scenario_improvements} improvements, {scenario_degradations} degradations")

    print(f"\nOverall Summary:")
    print(f"  Total Improvements: {total_improvements}")
    print(f"  Total Degradations: {total_degradations}")
    print(f"  Net Improvement: {total_improvements - total_degradations}")

    if total_improvements + total_degradations > 0:
        improvement_rate = total_improvements / (total_improvements + total_degradations) * 100
        print(f"  Improvement Rate: {improvement_rate:.1f}%")

    print(f"\nReport: {report_path}")
    print(f"Visualizations: {viz_files[0] if viz_files else 'None'}")

    print("\nA/B testing completed successfully!")


if __name__ == "__main__":
    main()