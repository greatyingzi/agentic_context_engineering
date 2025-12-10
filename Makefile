# Makefile for Cross-Platform Compatibility Testing

.PHONY: help test-quick test-comprehensive test-windows ci-test install-hooks clean-report

# Default target
help:
	@echo "Cross-Platform Compatibility Testing"
	@echo "===================================="
	@echo ""
	@echo "Available targets:"
	@echo "  help              - Show this help message"
	@echo "  test-quick        - Run quick compatibility check"
	@echo "  test-comprehensive - Run comprehensive validation"
	@echo "  test-windows       - Generate Windows test script"
	@echo "  ci-test           - Run CI-like tests locally"
	@echo "  install-hooks     - Install Claude hooks"
	@echo "  clean-report      - Clean test reports"
	@echo ""
	@echo "Examples:"
	@echo "  make test-quick"
	@echo "  make test-comprehensive"
	@echo "  make ci-test"

# Run quick compatibility check
test-quick:
	@echo "🔧 Running quick compatibility check..."
	python3 scripts/quick_check.py

# Run comprehensive validation
test-comprehensive:
	@echo "🚀 Running comprehensive cross-platform validation..."
	python3 scripts/cross_platform_validator.py

# Generate Windows test script
test-windows:
	@echo "🪟 Preparing Windows compatibility test..."
	@echo "Copy scripts/test-windows-compatibility.ps1 to Windows and run:"
	@echo "  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser"
	@echo "  .\\test-windows-compatibility.ps1"

# Run CI-like tests locally
ci-test: test-quick test-comprehensive
	@echo "✅ CI-like tests completed"

# Install Claude hooks
install-hooks:
	@echo "📦 Installing Agentic Context Engineering hooks..."
	node install.js
	@echo "✅ Hooks installed. Restart Claude Code to activate."

# Clean test reports
clean-report:
	@echo "🧹 Cleaning test reports..."
	rm -rf test_reports/
	rm -f quick_compatibility_report.json
	rm -f windows_compatibility_report.json
	@echo "✅ Test reports cleaned"

# Check if required tools are available
check-tools:
	@echo "🔍 Checking required tools..."
	@which python3 > /dev/null && echo "✅ Python3 found" || echo "❌ Python3 not found"
	@which node > /dev/null && echo "✅ Node.js found" || echo "❌ Node.js not found"
	@which npm > /dev/null && echo "✅ npm found" || echo "❌ npm not found"

# Initialize development environment
dev-init: check-tools
	@echo "🚀 Initializing development environment..."
	npm install
	@echo "✅ Development environment ready"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Run 'make test-quick' to verify compatibility"
	@echo "  2. Run 'make install-hooks' to install the system"
	@echo "  3. Check 'docs/cross-platform-testing.md' for detailed guide"

# Generate test report
report:
	@echo "📊 Generating test report..."
	@mkdir -p test_reports
	@echo "# Test Report - $(shell date)" > test_reports/README.md
	@echo "" >> test_reports/README.md
	@echo "Run tests to generate detailed reports:" >> test_reports/README.md
	@echo "  make test-quick" >> test_reports/README.md
	@echo "  make test-comprehensive" >> test_reports/README.md
	@echo "✅ Report template created"

# Show system information
system-info:
	@echo "🖥️  System Information"
	@echo "======================"
	@echo "Platform: $(shell uname -s)"
	@echo "Architecture: $(shell uname -m)"
	@echo "Python Version: $(shell python3 --version 2>/dev/null || echo 'Not found')"
	@echo "Node.js Version: $(shell node --version 2>/dev/null || echo 'Not found')"
	@echo "npm Version: $(shell npm --version 2>/dev/null || echo 'Not found')"
	@echo ""
	@echo "Claude Directory: $(shell echo $$HOME)/.claude"
	@echo "Project Directory: $(shell pwd)"

# Verify installation
verify-install:
	@echo "🔍 Verifying installation..."
	@if [ -f "$(shell echo $$HOME)/.claude/settings.json" ]; then \
		echo "✅ Settings file found"; \
	else \
		echo "⚠ Settings file not found (run 'make install-hooks')"; \
	fi
	@if [ -d "$(shell echo $$HOME)/.claude/hooks" ]; then \
		echo "✅ Hooks directory found"; \
	else \
		echo "⚠ Hooks directory not found"; \
	fi
	@if python3 -c "import hooks.common" 2>/dev/null; then \
		echo "✅ Python modules importable"; \
	else \
		echo "❌ Python modules not importable"; \
	fi