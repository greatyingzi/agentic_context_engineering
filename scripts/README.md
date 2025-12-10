# Cross-Platform Compatibility Tools

This directory contains tools for validating cross-platform compatibility of the Agentic Context Engineering project.

## Files

### 1. `cross_platform_validator.py` - Comprehensive Validator
**Main validation script** that tests all critical components across simulated platforms.

**Features:**
- Platform simulation (darwin, linux, win32)
- Path generation testing
- Command format validation
- Installation verification
- Regression testing
- Windows-specific fix verification

**Usage:**
```bash
python scripts/cross_platform_validator.py
```

**Output:**
- Detailed test report in `test_reports/` directory
- JSON results for CI integration
- Pass/fail summary with recommendations

### 2. `quick_check.py` - Quick Compatibility Checker
**Lightweight script** for rapid validation of basic compatibility.

**Features:**
- Python version check
- Node.js availability
- Path handling validation
- Basic command generation
- Quick report generation

**Usage:**
```bash
python scripts/quick_check.py
```

**Output:**
- Quick summary of compatibility status
- JSON report (`quick_compatibility_report.json`)
- Exit code (0 for pass, 1 for fail)

### 3. `test-windows-compatibility.ps1` - Windows-Specific Tester
**PowerShell script** for Windows users to run on their systems.

**Features:**
- Python installation validation
- PowerShell execution policy check
- Long path support testing
- Virtual environment creation
- Antivirus interference detection

**Usage (on Windows):**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\scripts\test-windows-compatibility.ps1
```

**Output:**
- Windows-specific compatibility report
- Detailed recommendations
- PowerShell-friendly output

## Testing Workflow

### For Developers (macOS/Linux)

1. **Before Making Changes**
   ```bash
   python scripts/quick_check.py
   ```

2. **After Making Changes**
   ```bash
   python scripts/cross_platform_validator.py
   ```

3. **Before Committing**
   - Ensure all tests pass
   - Check for platform-specific issues

### For Windows Users

1. **Initial Testing**
   ```powershell
   .\scripts\test-windows-compatibility.ps1
   ```

2. **After Installation**
   ```powershell
   node install.js
   .\scripts\test-windows-compatibility.ps1
   ```

3. **Reporting Issues**
   - Share the generated report file
   - Include PowerShell output

### For CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/cross-platform-validation.yml`) automatically:

1. Runs on push/PR
2. Tests on Ubuntu, macOS, and Windows
3. Tests multiple Python versions
4. Generates compatibility matrix
5. Reports failures

## Test Categories

### Platform Simulation Tests
- **darwin**: macOS environment simulation
- **linux**: Linux environment simulation
- **win32**: Windows environment simulation

### Path Generation Tests
- Path joining and resolution
- Home directory expansion
- Platform-specific separators
- Quote handling

### Command Generation Tests
- Python executable detection
- Virtual environment commands
- Hook command formatting
- Pip installation commands

### Installation Verification
- File structure validation
- Python import tests
- Settings.json structure
- Hook registration

### Regression Testing
- Baseline comparison
- Change detection
- Version tracking
- Historical analysis

### Windows-Specific Tests
- PowerShell execution policy
- Long path support
- Antivirus considerations
- Command quoting

## Integration

### Pre-commit Hook
Add to `.git/hooks/pre-commit`:
```bash
#!/bin/bash
python scripts/quick_check.py
if [ $? -ne 0 ]; then
    echo "❌ Compatibility check failed"
    exit 1
fi
```

### CI Pipeline Integration
The workflow includes:
- Matrix testing across platforms
- Security scanning
- Compatibility matrix generation
- Failure notifications

### Documentation
- `docs/cross-platform-testing.md` - Comprehensive testing guide
- Test result templates
- Troubleshooting guide

## Troubleshooting

### Common Issues

1. **Python Version Mismatch**
   ```bash
   # Check Python version
   python3 --version
   # Should be 3.9 or higher
   ```

2. **Permission Issues (macOS/Linux)**
   ```bash
   chmod +x install.js
   chmod +x scripts/*.py
   ```

3. **PowerShell Policy (Windows)**
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

4. **PATH Issues**
   ```bash
   # Check if Python is in PATH
   which python3  # Linux/macOS
   where python   # Windows
   ```

### Getting Help

1. **Check the generated reports**
2. **Review the troubleshooting guide**
3. **Run tests with verbose output**
4. **Share test results with the team**

## Best Practices

1. **Test Early, Test Often**
   - Run quick checks before commits
   - Run full validation before releases

2. **Platform-Specific Considerations**
   - macOS: Focus on path separators
   - Linux: Test various distributions
   - Windows: PowerShell and long paths

3. **Documentation**
   - Update tests when adding features
   - Document platform-specific behavior
   - Maintain testing guides

4. **Community Involvement**
   - Encourage Windows user feedback
   - Share test results
   - Report compatibility issues

## Contributing

When adding new tests:

1. Add to appropriate test class
2. Include platform-specific cases
3. Update documentation
4. Add to CI matrix if needed

For more information, see `docs/cross-platform-testing.md`.