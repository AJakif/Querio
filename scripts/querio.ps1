param(
    [Parameter(Position = 0)]
    [ValidateSet("up", "down", "stop", "reset", "logs", "ps", "help")]
    [string]$Action = "up",

    [switch]$Detached
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$composeArgs = @("compose")

function Invoke-Compose {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    Push-Location $repoRoot
    try {
        & docker @composeArgs @Arguments
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
    finally {
        Pop-Location
    }
}

function Show-Help {
    Write-Host "Querio local stack helper"
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\scripts\querio.ps1 up        # start the full stack"
    Write-Host "  .\scripts\querio.ps1 down      # stop and remove containers"
    Write-Host "  .\scripts\querio.ps1 reset     # stop everything and delete volumes"
    Write-Host "  .\scripts\querio.ps1 logs      # stream logs"
    Write-Host "  .\scripts\querio.ps1 ps        # show container status"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Detached                      # start in background"
}

switch ($Action) {
    "help" {
        Show-Help
    }
    default {
        try {
            $null = & docker compose version 2>$null
        }
        catch {
            Write-Error "Docker Compose is not available. Install Docker Desktop and make sure 'docker compose' works first."
            exit 1
        }
    }
}

switch ($Action) {
    "up" {
        $args = @("up")
        if ($Detached) {
            $args += "-d"
        }

        Invoke-Compose -Arguments $args

        if ($Detached) {
            Write-Host ""
            Write-Host "Querio is starting in the background."
        }

        Write-Host "Frontend: http://localhost:3000"
        Write-Host "Backend:  http://localhost:8000/docs"
        Write-Host "Airflow:  http://localhost:8081"
    }
    "down" {
        Invoke-Compose -Arguments @("down")
    }
    "stop" {
        Invoke-Compose -Arguments @("down")
    }
    "reset" {
        Invoke-Compose -Arguments @("down", "--volumes")
    }
    "logs" {
        Invoke-Compose -Arguments @("logs", "-f")
    }
    "ps" {
        Invoke-Compose -Arguments @("ps")
    }
    "help" { }
}
