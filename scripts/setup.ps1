param(
    [switch]$Force,
    [switch]$SmallModel,
    [switch]$Help
)

# Querio first-run setup: generates .env / .env.secrets from the .example
# templates and auto-detects a local Ollama instance so a first query is
# reachable with zero external accounts or API keys (Epic 8, Slice 17).

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

# Overridable for tests / alternate layouts; not part of the normal CLI surface.
$outputDir = if ($env:QUERIO_SETUP_OUTPUT_DIR) { $env:QUERIO_SETUP_OUTPUT_DIR } else { $repoRoot }
$ollamaProbeUrl = if ($env:QUERIO_OLLAMA_PROBE_URL) { $env:QUERIO_OLLAMA_PROBE_URL } else { "http://localhost:11434" }

function Show-Help {
    Write-Host "Querio first-run setup"
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\scripts\setup.ps1 [-Force] [-Help]"
    Write-Host ""
    Write-Host "Generates .env and .env.secrets from the .env.example / .env.secrets.example"
    Write-Host "templates (skips any file that already exists, so it's safe to re-run)."
    Write-Host ""
    Write-Host "Probes for a local Ollama instance at http://localhost:11434. If found, the"
    Write-Host "generated .env defaults MODEL_PROVIDER=ollama with a working OLLAMA_BASE_URL"
    Write-Host "so you can ask your first question without any API key or account. If not"
    Write-Host "found, .env keeps the default (openai) provider - set an API key in"
    Write-Host ".env.secrets, or leave it blank to run against the built-in FakeSqlGenerator."
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Force        Overwrite existing .env / .env.secrets instead of skipping them."
    Write-Host "  -SmallModel   Apply conservative context-knob values suited for local models"
    Write-Host "                with an 8192-token context window (MAX_RESULT_ROWS=200,"
    Write-Host "                MAX_LLM_ROWS=20, SESSION_BRIEF_MAX_TOKENS=150). Always applied"
    Write-Host "                to .env when this flag is passed, even if .env already existed."
}

if ($Help) {
    Show-Help
    exit 0
}

# Detect a running local Ollama at the standard endpoint. Tries /api/tags
# first, falls back to /api/version - either confirms a live daemon.
function Test-Ollama {
    param([string]$Url)

    foreach ($path in @("/api/tags", "/api/version")) {
        try {
            $response = Invoke-WebRequest -Uri "$Url$path" -TimeoutSec 2 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                return $true
            }
        }
        catch {
            continue
        }
    }
    return $false
}

# Copies src -> dest unless dest exists and -Force wasn't passed. Returns
# $true if the file was (re)written, $false if it was left alone.
function Copy-IfNeeded {
    param([string]$Src, [string]$Dest)

    $destName = Split-Path -Leaf $Dest
    $srcName = Split-Path -Leaf $Src
    if ((Test-Path $Dest) -and -not $Force) {
        Write-Host "Skipping $destName - already exists (use -Force to overwrite)."
        return $false
    }
    Copy-Item -Path $Src -Destination $Dest -Force
    Write-Host "Created $destName from $srcName."
    return $true
}

# Sets KEY=VALUE in a dotenv-style file, replacing an existing line or
# appending a new one.
function Set-EnvVar {
    param([string]$FilePath, [string]$Key, [string]$Value)

    $lines = Get-Content -Path $FilePath
    $pattern = "^$Key=.*"
    if ($lines -match $pattern) {
        $lines = $lines -replace $pattern, "$Key=$Value"
    }
    else {
        $lines += "$Key=$Value"
    }
    Set-Content -Path $FilePath -Value $lines -Encoding utf8
}

$envExample = Join-Path $repoRoot ".env.example"
$secretsExample = Join-Path $repoRoot ".env.secrets.example"
$envFile = Join-Path $outputDir ".env"
$secretsFile = Join-Path $outputDir ".env.secrets"

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$envWritten = Copy-IfNeeded -Src $envExample -Dest $envFile
Copy-IfNeeded -Src $secretsExample -Dest $secretsFile | Out-Null

if (Test-Ollama -Url $ollamaProbeUrl) {
    Write-Host "Detected a local Ollama instance at $ollamaProbeUrl."
    if ($envWritten) {
        Set-EnvVar -FilePath $envFile -Key "MODEL_PROVIDER" -Value "ollama"
        Set-EnvVar -FilePath $envFile -Key "OLLAMA_BASE_URL" -Value "$ollamaProbeUrl/v1"
        Write-Host "Configured MODEL_PROVIDER=ollama in .env - no API key needed."
    }
    else {
        Write-Host ".env already existed and was left untouched. Set MODEL_PROVIDER=ollama yourself if you want to use it."
    }
}
else {
    Write-Host "No local Ollama instance detected at $ollamaProbeUrl."
    Write-Host "Falling back to existing behavior: add an OPENAI_API_KEY or ANTHROPIC_API_KEY to .env.secrets,"
    Write-Host "or leave both blank to run against the built-in FakeSqlGenerator."
}

if ($SmallModel) {
    # Conservative row/token caps for local models with <=8192-token context windows.
    # MAX_RESULT_ROWS=200  - limits raw DB result size; the default 1000 can overwhelm small models.
    # MAX_LLM_ROWS=20     - rows serialized into the LLM prompt; 20x~45 tokens ~= 900 tokens,
    #                       leaving headroom for system prompt + schema + question + response.
    # SESSION_BRIEF_MAX_TOKENS=150 - halves the default 300-token brief to save context space.
    Set-EnvVar -FilePath $envFile -Key "MAX_RESULT_ROWS" -Value "200"
    Set-EnvVar -FilePath $envFile -Key "MAX_LLM_ROWS" -Value "20"
    Set-EnvVar -FilePath $envFile -Key "SESSION_BRIEF_MAX_TOKENS" -Value "150"
    Write-Host "Applied small-model profile to .env (MAX_RESULT_ROWS=200, MAX_LLM_ROWS=20, SESSION_BRIEF_MAX_TOKENS=150)."
}

Write-Host ""
Write-Host "Setup complete. Next: docker compose up (or .\scripts\querio.ps1 up)."
