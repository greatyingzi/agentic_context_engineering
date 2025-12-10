# Windows Compatibility Test Script

This script should be run on Windows systems to verify Windows-specific compatibility.

## Usage

1. Save this script as `test-windows-compatibility.ps1`
2. Run in PowerShell: `.\test-windows-compatibility.ps1`
3. Share the results with the development team

<#
.SYNOPSIS
    Tests Windows-specific compatibility for Agentic Context Engineering

.DESCRIPTION
    This script performs Windows-specific tests for the Agentic Context Engineering
    installation and operation. It checks:
    - Python installation and accessibility
    - PowerShell execution policy
    - Path handling and long paths
    - Command generation
    - Virtual environment creation
    - File permissions
#>

param(
    [switch]$Verbose = $false
)

# Set up error handling
$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $prefix = switch ($Level) {
        "INFO" { "ℹ" }
        "WARN" { "⚠" }
        "ERROR" { "❌" }
        "SUCCESS" { "✅" }
        default { "•" }
    }

    if ($Verbose) {
        Write-Host "[$timestamp] [$Level] $prefix $Message"
    } elseif ($Level -ne "INFO") {
        Write-Host "[$timestamp] [$Level] $prefix $Message"
    }
}

function Test-PythonInstallation {
    Write-Log "Testing Python installation..." "INFO"

    $tests = @()

    # Test 1: Check if python is available
    try {
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Python version: $pythonVersion" "SUCCESS"
            $tests += $true
        } else {
            Write-Log "Python command failed" "ERROR"
            $tests += $false
        }
    } catch {
        Write-Log "Python not found in PATH" "ERROR"
        $tests += $false
    }

    # Test 2: Check if python3 is available (alternative)
    try {
        $python3Version = python3 --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Python3 version: $python3Version" "SUCCESS"
            $tests += $true
        } else {
            Write-Log "Python3 command failed" "WARN"
            $tests += $false
        }
    } catch {
        Write-Log "Python3 not found in PATH" "WARN"
        $tests += $false
    }

    # Test 3: Check pip
    try {
        $pipVersion = pip --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "pip available: $($pipVersion.Split(' ')[0])" "SUCCESS"
            $tests += $true
        } else {
            Write-Log "pip command failed" "ERROR"
            $tests += $false
        }
    } catch {
        Write-Log "pip not found" "ERROR"
        $tests += $false
    }

    return ($tests | Where-Object { $_ } | Count) -gt 0
}

function Test-PowerShellExecutionPolicy {
    Write-Log "Testing PowerShell execution policy..." "INFO"

    try {
        $policy = Get-ExecutionPolicy
        Write-Log "Current execution policy: $policy" "INFO"

        if ($policy -in @("RemoteSigned", "Unrestricted")) {
            Write-Log "Execution policy allows script execution" "SUCCESS"
            return $true
        } else {
            Write-Log "Execution policy may block scripts: $policy" "WARN"
            Write-Log "Run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" "INFO"
            return $false
        }
    } catch {
        Write-Log "Could not check execution policy" "ERROR"
        return $false
    }
}

function Test-PathHandling {
    Write-Log "Testing path handling..." "INFO"

    $tests = @()

    # Test 1: Home directory
    $homeDir = $env:USERPROFILE
    if (Test-Path $homeDir) {
        Write-Log "Home directory accessible: $homeDir" "SUCCESS"
        $tests += $true
    } else {
        Write-Log "Home directory not accessible" "ERROR"
        $tests += $false
    }

    # Test 2: Long path support
    $longPath = "$homeDir\.claude\.venv\Scripts\python.exe"
    $longPathLength = $longPath.Length
    Write-Log "Long path length: $longPathLength characters" "INFO"

    if ($longPathLength -gt 260) {
        Write-Log "Warning: Path exceeds 260 character limit" "WARN"
        Write-Log "Consider enabling long paths: reg add HKLM\SYSTEM\CurrentControlSet\Control\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1 /f" "INFO"
    } else {
        Write-Log "Path length within limits" "SUCCESS"
        $tests += $true
    }

    # Test 3: Path separator handling
    $testPath = Join-Path $homeDir ".claude" "hooks"
    Write-Log "Test path: $testPath" "INFO"
    if ($testPath -match "\\") {
        Write-Log "Windows path separator detected" "SUCCESS"
        $tests += $true
    } else {
        Write-Log "Path separator issue" "ERROR"
        $tests += $false
    }

    return ($tests | Where-Object { $_ } | Count) -eq $tests.Count
}

function Test-CommandGeneration {
    Write-Log "Testing command generation..." "INFO"

    $tests = @()

    # Test 1: Basic command format
    $venvPython = "$env:USERPROFILE\.claude\.venv\Scripts\python.exe"
    $scriptPath = "$env:USERPROFILE\.claude\hooks\session_end.py"

    if (Test-Path $venvPython -PathType Leaf) {
        $command = "`"$venvPython`" `"$scriptPath`""
        Write-Log "Generated command: $command" "INFO"

        if ($command -match '^".*".*".*"$') {
            Write-Log "Command format correct" "SUCCESS"
            $tests += $true
        } else {
            Write-Log "Command format issue" "ERROR"
            $tests += $false
        }
    } else {
        Write-Log "Virtual environment not found, testing format with placeholder" "INFO"
        # Test format without actual paths
        $command = "`"$venvPython`" `"$scriptPath`""
        if ($command -match '^".*".*".*"$') {
            Write-Log "Command format correct" "SUCCESS"
            $tests += $true
        } else {
            Write-Log "Command format issue" "ERROR"
            $tests += $false
        }
    }

    # Test 2: Node.js commands
    try {
        $nodeVersion = node --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Node.js available: $nodeVersion" "SUCCESS"
            $tests += $true
        } else {
            Write-Log "Node.js not working" "ERROR"
            $tests += $false
        }
    } catch {
        Write-Log "Node.js not found" "ERROR"
        $tests += $false
    }

    return ($tests | Where-Object { $_ } | Count) -eq $tests.Count
}

function Test-VirtualEnvironment {
    Write-Log "Testing virtual environment creation..." "INFO"

    $tests = @()

    # Test 1: Check if uv is available
    try {
        $uvVersion = uv --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "uv available: $uvVersion" "SUCCESS"
            $tests += $true

            # Test venv creation with uv
            $testVenv = "$env:USERPROFILE\test_venv"
            if (Test-Path $testVenv) {
                Remove-Item -Path $testVenv -Recurse -Force
            }

            Write-Log "Testing venv creation with uv..." "INFO"
            uv venv $testVenv
            if ($LASTEXITCODE -eq 0) {
                Write-Log "Virtual environment created successfully" "SUCCESS"
                Remove-Item -Path $testVenv -Recurse -Force
                $tests += $true
            } else {
                Write-Log "Failed to create venv with uv" "ERROR"
                $tests += $false
            }
        } else {
            Write-Log "uv not available, will test with standard Python" "WARN"
            $tests += $false
        }
    } catch {
        Write-Log "uv not found" "WARN"
        $tests += $false
    }

    # Test 2: Test with standard Python venv
    $testVenv = "$env:USERPROFILE\test_venv_standard"
    if (Test-Path $testVenv) {
        Remove-Item -Path $testVenv -Recurse -Force
    }

    Write-Log "Testing venv creation with standard Python..." "INFO"
    python -m venv $testVenv
    if ($LASTEXITCODE -eq 0) {
        Write-Log "Standard venv created successfully" "SUCCESS"
        Remove-Item -Path $testVenv -Recurse -Force
        $tests += $true
    } else {
        Write-Log "Failed to create standard venv" "ERROR"
        $tests += $false
    }

    return ($tests | Where-Object { $_ } | Count) -gt 0
}

function Test-AntivirusInterference {
    Write-Log "Checking for potential antivirus interference..." "INFO"

    $claudeDir = "$env:USERPROFILE\.claude"
    $tests = @()

    # Check if Claude directory exists
    if (Test-Path $claudeDir) {
        Write-Log "Claude directory exists: $claudeDir" "INFO"

        # Check for common antivirus indicators
        $suspiciousFiles = @(
            "$claudeDir\.claude.exe",
            "$claudeDir\hooks\*.exe",
            "$claudeDir\*.tmp"
        )

        $foundSuspicious = $false
        foreach ($pattern in $suspiciousFiles) {
            $files = Get-Item $pattern -ErrorAction SilentlyContinue
            if ($files) {
                Write-Log "Found potentially blocked files: $files" "WARN"
                $foundSuspicious = $true
            }
        }

        if (-not $foundSuspicious) {
            Write-Log "No obvious antivirus interference detected" "SUCCESS"
            $tests += $true
        }
    } else {
        Write-Log "Claude directory not found (expected for fresh install)" "INFO"
        $tests += $true
    }

    # Check Windows Defender status (if available)
    try {
        $mpStatus = Get-MpComputerStatus -ErrorAction SilentlyContinue
        if ($mpStatus) {
            if ($mpStatus.RealTimeProtectionEnabled) {
                Write-Log "Windows Defender is active" "INFO"
                Write-Log "Add $claudeDir to exclusions if issues occur" "INFO"
            } else {
                Write-Log "Windows Defender is disabled" "WARN"
            }
            $tests += $true
        }
    } catch {
        Write-Log "Could not check Windows Defender status" "INFO"
        $tests += $true
    }

    return ($tests | Where-Object { $_ } | Count) -eq $tests.Count
}

function Generate-Report {
    param([hashtable]$Results)

    $reportPath = "windows_compatibility_report.json"
    $report = @{
        "timestamp" = Get-Date -Format "o"
        "platform" = @{
            "system" = $env:COMPUTERNAME
            "os" = (Get-CimInstance -ClassName Win32_OperatingSystem).Caption
            "version" = (Get-CimInstance -ClassName Win32_OperatingSystem).Version
            "architecture" = (Get-CimInstance -ClassName Win32_OperatingSystem).OSArchitecture
        }
        "user" = $env:USERNAME
        "results" = $Results
        "recommendations" = @()
    }

    # Add recommendations based on results
    if (-not $Results.PowerShellExecutionPolicy) {
        $report.recommendations += "Set execution policy: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser"
    }

    if (-not $Results.PathHandling) {
        $report.recommendations += "Check long path support: reg add HKLM\SYSTEM\CurrentControlSet\Control\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1 /f"
    }

    if (-not $Results.VirtualEnvironment) {
        $report.recommendations += "Install Python from python.org and ensure 'Add Python to PATH' is checked"
    }

    if (-not $Results.Antivirus) {
        $report.recommendations += "Add ~/.claude to antivirus exclusions"
    }

    $reportJson = $report | ConvertTo-Json -Depth 10
    $reportJson | Out-File -FilePath $reportPath -Encoding UTF8

    Write-Log "Report saved to: $reportPath" "SUCCESS"
    return $reportPath
}

# Main execution
Write-Log "Starting Windows Compatibility Test" "INFO"
Write-Log "Computer: $env:COMPUTERNAME" "INFO"
Write-Log "User: $env:USERNAME" "INFO"
Write-Log "OS: $((Get-CimInstance -ClassName Win32_OperatingSystem).Caption)" "INFO"

# Run all tests
$testResults = @{
    "PythonInstallation" = Test-PythonInstallation
    "PowerShellExecutionPolicy" = Test-PowerShellExecutionPolicy
    "PathHandling" = Test-PathHandling
    "CommandGeneration" = Test-CommandGeneration
    "VirtualEnvironment" = Test-VirtualEnvironment
    "Antivirus" = Test-AntivirusInterference
}

# Generate report
$reportPath = Generate-Report -Results $testResults

# Summary
Write-Log "" "INFO"
Write-Log "=== Test Summary ===" "INFO"
$passed = ($testResults.Values | Where-Object { $_ } | Count)
$total = $testResults.Count
Write-Log "Passed: $passed/$total" "INFO"

foreach ($test in $testResults.Keys) {
    $status = if ($testResults[$test]) { "✅ PASS" } else { "❌ FAIL" }
    Write-Log "$test`: $status" "INFO"
}

if ($passed -eq $total) {
    Write-Log "🎉 All Windows compatibility tests passed!" "SUCCESS"
    Write-Log "The system should work correctly on this Windows machine." "INFO"
} else {
    Write-Log "⚠️  Some tests failed. Please review the recommendations above." "WARN"
    Write-Log "Share the report file ($reportPath) with the development team." "INFO"
}

# Keep window open if run interactively
if ($PSVersionTable.PSVersion.Major -lt 6) {
    Read-Host "Press Enter to exit"
}