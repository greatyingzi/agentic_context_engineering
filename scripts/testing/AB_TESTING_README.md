# KPT Context-Aware Parameter Weighting A/B Testing Framework

This framework provides comprehensive A/B testing capabilities to compare the old hardcoded weights vs the new context-aware parameter weighting system in the KPT (Key Point Tracking) system.

## Overview

The A/B testing framework evaluates the new context-aware parameter weighting system (`_get_contextual_weights` function) against the old hardcoded weights across multiple dimensions:

### Key Metrics Tracked
1. **Knowledge Selection Quality**
   - Context relevance (how well selected knowledge points match the context)
   - Diversity (avoiding knowledge concentration)
   - Layer balance (HIGH_CONFIDENCE vs RECOMMENDATION distribution)

2. **Performance Metrics**
   - Token usage (should not increase significantly)
   - Execution time (should maintain efficiency)
   - Memory usage (no resource bloat)

3. **User Experience**
   - Relevance scores (quantify match quality)
   - Parameter weight effectiveness (do contextual weights improve outcomes?)

### Test Scenarios
The framework includes 4 standardized test scenarios:
- **Urgent Bug Fix** (`urgent_bug_fix`): Critical priority context with conservative temperature (0.2)
- **Production Deployment** (`production_deployment`): Customer-facing context with balanced temperature (0.5)
- **Research Exploration** (`research_exploration`): Innovation-focused context with exploratory temperature (0.8)
- **Generic Development** (`generic_development`): Standard development work with balanced temperature (0.5)

## Installation

1. Install the required dependencies:
```bash
cd scripts
pip install -r ab_testing_requirements.txt
```

2. Ensure the KPT system is properly installed and the `src/hooks` directory is accessible.

## Usage

### Running the A/B Tests

Execute the framework from the project root directory:
```bash
cd /Users/viture/work/agentic_context_engineering
python scripts/ab_testing_framework.py
```

The framework will:
1. Run 10 iterations of A/B tests for each scenario (80 total tests)
2. Collect comprehensive metrics for both old and new systems
3. Perform statistical analysis to determine significance
4. Generate an HTML report with detailed comparisons
5. Create visualizations for key metrics

### Output Files

- **HTML Report**: `ab_test_report_YYYYMMDD_HHMMSS.html`
  - Detailed comparison of all metrics
  - Statistical significance indicators
  - Overall summary of findings
- **Visualizations**: `ab_test_visualizations_YYYYMMDD_HHMMSS/`
  - Performance comparison charts
  - Knowledge quality radar charts
  - Layer distribution analysis

### Understanding the Results

The framework uses statistical significance testing (p-values) to determine if improvements are meaningful:

- **p < 0.01**: Highly significant result
- **p < 0.05**: Significant result
- **p ≥ 0.05**: Not significant result

Improvement percentages show the relative change from old to new system:
- **📈**: Positive improvement (better performance)
- **📉**: Negative improvement (performance degradation)
- **➡️**: No significant change

## Framework Architecture

### Core Components

1. **TestScenario**: Defines test parameters including tags, temperature, and expected context
2. **TestMetrics**: Container for calculated metrics
3. **TestResult**: Individual test result with system type and metrics
4. **ABTestFramework**: Main orchestrator for running tests and analysis

### Test Methodology

1. **Baseline Comparison**: Old system uses hardcoded weights (0.3, 0.4, -0.2)
2. **Context-Aware System**: New system uses `_get_contextual_weights` function
3. **Statistical Rigor**: Multiple iterations (default 10) for statistical significance
4. **Comprehensive Metrics**: 11 different metrics across quality, performance, and UX

### Sample Knowledge Base

The framework includes a carefully crafted knowledge base with:
- High confidence proven solutions (positive scores)
- Medium confidence recommendations (neutral scores)
- Innovative approaches (high innovation, moderate risk)
- Risk/high innovation items (for filtering validation)

## Customization

### Adding New Test Scenarios

Modify the `_create_test_scenarios` method in `ABTestFramework` class:

```python
TestScenario(
    name="custom_scenario",
    tags=["custom", "tags", "here"],
    description="Custom scenario description",
    expected_context_type="custom",
    temperature=0.5,
    limit=6
)
```

### Modifying Test Parameters

- **Iterations**: Change the `iterations` parameter in `run_ab_tests()`
- **Metrics**: Add new metrics to `_calculate_metrics()` method
- **Knowledge Base**: Update `_generate_test_knowledge_base()` with different KPT data

### Statistical Analysis

The framework includes:
- T-test approximation for significance testing
- Mean and standard deviation calculations
- Confidence interval estimation
- P-value calculation for determining significance

## Integration with Existing KPT System

The framework integrates seamlessly with the existing KPT system by:

1. **Patching the Selection Function**: Creates modified versions of `select_relevant_keypoints` that use either old or new weight systems
2. **Using Real KPT Data**: Works with actual KPT knowledge base structure and scoring
3. **Preserving Context**: Maintains all context parameters (temperature, tags, limit)
4. **Metadata Tracking**: Extends KPT items with debugging metadata for analysis

## Performance Considerations

- **Memory Usage**: Tracks memory consumption during selection
- **Execution Time**: Measures performance impact of context-aware weights
- **Token Estimation**: Approximates token usage for Claude API calls
- **Scalability**: Tests with realistic knowledge base sizes

## Validation and Quality Assurance

The framework provides:

1. **Reproducible Results**: Fixed random seed and deterministic scenarios
2. **Statistical Significance**: Multiple iterations with proper statistical testing
3. **Comprehensive Metrics**: Multi-dimensional evaluation beyond simple accuracy
4. **Error Handling**: Graceful degradation when dependencies are missing

## Example Output Interpretation

```
Scenario: urgent_bug_fix
Description: Urgent bug fix context with critical priority
Expected Context: urgent
Summary: 3 improvements, 1 degradations

  Avg Relevance Score: 📈 IMPROVED (+12.5%, p=0.023)
  Diversity Score: 📈 IMPROVED (+8.3%, p=0.041)
  Execution Time: 📉 DEGRADED (-5.2%, p=0.032)
  Memory Usage: ➡️ NO CHANGE (0.0%, p=0.876)
```

This indicates the new system improves knowledge quality and diversity with minimal performance impact in urgent contexts.

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure the `src` directory is in Python path
2. **Missing Dependencies**: Install all requirements from `ab_testing_requirements.txt`
3. **Memory Issues**: Reduce iterations or knowledge base size if memory constrained
4. **Path Issues**: Run from project root directory for proper imports

### Debug Mode

Enable detailed debugging by adding:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

Potential improvements for future versions:
- Real KPT data integration
- Multi-dimensional context analysis
- Adaptive temperature testing
- Cross-validation with different knowledge bases
- Long-term performance tracking
- Integration with CI/CD pipelines

## Contributing

To contribute to the A/B testing framework:
1. Ensure all new tests include comprehensive metrics
2. Maintain statistical rigor with proper sample sizes
3. Document any changes to test methodology
4. Add appropriate visualizations for new metrics
5. Validate results against multiple scenarios

## License

This A/B testing framework is part of the Agentic Context Engineering project and follows the same license terms.