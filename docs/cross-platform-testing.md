# Cross-Platform Testing Guide

This guide provides comprehensive instructions for testing cross-platform compatibility in the Agentic Context Engineering project.

## Overview

The cross-platform validation system ensures that the Agentic Context Engineering hooks work correctly across:
- **macOS (darwin)** - Primary development platform
- **Linux** - Server and development environments
- **Windows** - User deployment platform

## Testing Tools

### 1. Cross-Platform Validator (`scripts/cross_platform_validator.py`)

The main validation script that tests all critical components without requiring physical hardware.

#### Features:
- **Platform Simulator**: Simulates different platform environments
- **Path Generation Tests**: Validates path handling across platforms
- **Command Generation Tests**: Ensures proper command formatting
- **Installation Verification**: Tests actual installation on current system
- **Regression Testing**: Detects unintended changes from baseline
- **Windows Fix Verification**: Validates Windows-specific compatibility

#### Usage:

```bash
# Run all tests
python scripts/cross_platform_validator.py

# Run specific test categories
python -m unittest scripts.cross_platform_validator.PathGeneratorTest
python -m unittest scripts.cross_platform_validator.CommandGeneratorTest
python -m unittest scripts.cross_platform_validator.InstallationVerifier
python -m unittest scripts.cross_platform_validator.WindowsFixVerifier
```

### 2. CI/CD Pipeline (`.github/workflows/cross-platform-validation.yml`)

Automated testing that runs on:
- Push to main/master branches
- Pull requests
- Weekly schedule (Mondays at 9 AM UTC)

#### CI Matrix:
- **Operating Systems**: Ubuntu, macOS, Windows
- **Python Versions**: 3.9, 3.10, 3.11
- **Special Windows Tests**: PowerShell execution policy, path handling

## Manual Testing Procedures

### 1. macOS/Linux Testing

#### Prerequisites:
```bash
# Install required tools
brew install python3 node  # macOS
sudo apt install python3 nodejs  # Ubuntu/Debian

# Verify Python 3.9+
python3 --version  # Should be 3.9 or higher
```

#### Test Execution:
```bash
# Clone and install
git clone <repository>
cd agentic_context_engineering
npm install

# Run validation
python scripts/cross_platform_validator.py

# Test actual installation
node install.js
```

#### Verification Points:
- ✅ Python executable detection (`python3`)
- ✅ Virtual environment creation (`python3 -m venv`)
- ✅ Path separator (`/`)
- ✅ Command quoting (single quotes)
- ✅ Hook command generation
- ✅ File permissions (755 for scripts)

### 2. Windows Testing (Remote)

Since you don't have physical Windows access, use these remote testing methods:

#### Method 1: Windows Subsystem for Linux (WSL)
```bash
# Install WSL on Windows machine
wsl --install

# In WSL Ubuntu environment
sudo apt update
sudo apt install python3 nodejs
git clone <repository>
cd agentic_context_engineering
npm install
python scripts/cross_platform_validator.py
```

#### Method 2: GitHub Actions (Recommended)
- Push changes to trigger CI pipeline
- Check results at: https://github.com/your-repo/actions

#### Method 3: Windows Remote Testing Script
Create a test script for Windows users:

```powershell
# test-windows.ps1
Write-Host "Testing Windows compatibility..."

# Check Python
python --version

# Check execution policy
Get-ExecutionPolicy

# Test path handling
$venvPath = "$env:USERPROFILE\.claude\.venv\Scripts\python.exe"
$scriptPath = "$env:USERPROFILE\.claude\hooks\session_end.py"
$command = "`"$venvPath`" `"$scriptPath`""
Write-Host "Test command: $command"

# Test long paths
$longPath = "C:\Users\$env:USERNAME\.claude\.venv\Scripts\python.exe"
if ($longPath.Length -gt 260) {
    Write-Host "Warning: Long path may cause issues"
}
```

### 3. Virtual Environment Testing

Test with different Python environments:

```bash
# Test with uv (recommended)
uv venv ~/.claude/.venv
uv pip install anthropic

# Test with standard venv
python3 -m venv test_venv
source test_venv/bin/activate  # Linux/macOS
test_venv\Scripts\activate     # Windows
pip install anthropic
```

## Test Categories

### 1. Path Generation Tests
- **Test Case**: Path joining and resolution
- **Expected**: Correct path separators and quoting
- **Platforms**: All three platforms

### 2. Command Generation Tests
- **Test Case**: Hook command formatting
- **Expected**: Proper quoting and executable paths
- **Critical for**: Windows command execution

### 3. Installation Verification
- **Test Case**: Complete installation process
- **Expected**: All files copied, settings merged
- **Verifies**: End-to-end deployment

### 4. Regression Testing
- **Test Case**: Comparison with baseline
- **Expected**: No unintended changes
- **Protects**: Against breaking changes

### 5. Windows-Specific Tests
- **Test Case**: Windows compatibility issues
- **Expected**: PowerShell, long paths, antivirus
- **Critical for**: Windows user experience

## Troubleshooting Common Issues

### 1. Path Issues
```bash
# Check path separators
echo $PATH  # Linux/macOS
echo %PATH%  # Windows

# Verify Python installation
which python3  # Linux/macOS
where python  # Windows
```

### 2. Permission Issues (macOS/Linux)
```bash
# Fix script permissions
chmod +x install.js
chmod +x src/hooks/*.py

# Check Claude directory permissions
ls -la ~/.claude/
```

### 3. Windows Issues
```powershell
# Check execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Test long paths (Windows 10+)
# Enable in registry or use path normalization
```

### 4. Virtual Environment Issues
```bash
# Rebuild venv
rm -rf ~/.claude/.venv
node install.js

# Check Python version
python3 --version
```

## Continuous Integration Setup

### 1. GitHub Secrets
Configure these secrets in repository settings:
- `AGENTIC_CONTEXT_API_KEY`: For API testing
- `SLACK_WEBHOOK_URL`: For failure notifications

### 2. Test Reports
- Location: `test_reports/`
- Format: Markdown with JSON details
- Generated: After each test run

### 3. Compatibility Matrix
- Generated: `compatibility_matrix.json`
- Shows: Test results across all platforms
- Updated: After each CI run

## Best Practices

### 1. Development Workflow
1. Make changes on primary platform (macOS/Linux)
2. Run local validation tests
3. Push to trigger CI pipeline
4. Review Windows test results
5. Address any platform-specific issues

### 2. Testing Strategy
- **Before Commit**: Run local validation
- **Before PR**: Ensure all tests pass
- **Weekly**: Review CI results and trends
- **Before Release**: Full matrix validation

### 3. Platform-Specific Considerations
- **macOS**: Focus on path separators and permissions
- **Linux**: Test various distributions and Python versions
- **Windows**: PowerShell, long paths, antivirus

## Windows Testing Without Hardware

Since you don't have physical Windows access:

### 1. Use CI/CD Pipeline
- GitHub Actions tests on Windows runner
- Results available immediately after push
- Full test coverage including Windows-specific checks

### 2. Remote Testing Partners
- Collaborate with Windows users
- Share test scripts and instructions
- Collect feedback from real Windows environments

### 3. Simulation and Validation
- Platform simulator in validator script
- Windows-specific test cases
- Path and command format validation

### 4. Community Testing
- Use GitHub Issues for Windows bug reports
- Encourage user feedback
- Monitor for Windows-specific patterns

## Maintenance

### 1. Update Test Baselines
- When making intentional changes
- Update expected values in regression tests
- Document changes in test reports

### 2. Add New Tests
- When adding new features
- Include platform-specific test cases
- Update CI matrix if needed

### 3. Monitor Test Results
- Review weekly CI results
- Look for platform-specific failures
- Update Windows fixes as needed

## Conclusion

This cross-platform testing system ensures that Agentic Context Engineering works reliably across all supported platforms without requiring physical hardware for Windows. The combination of local validation, CI/CD automation, and remote testing provides comprehensive coverage while maintaining development efficiency.

Key benefits:
- ✅ No Windows hardware required
- ✅ Automated testing on all platforms
- ✅ Early detection of compatibility issues
- ✅ Comprehensive reporting and monitoring
- ✅ Sustainable long-term maintenance