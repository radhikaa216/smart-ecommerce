$ErrorActionPreference = "Stop"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is required. Install and start Docker Desktop, then run this script again."
}

$workspace = Resolve-Path (Join-Path $PSScriptRoot "..")
$envFile = Join-Path $workspace ".env"
$exampleFile = Join-Path $workspace ".env.example"

if (-not (Test-Path -LiteralPath $envFile)) {
    Copy-Item -LiteralPath $exampleFile -Destination $envFile
    Write-Host "Created .env from .env.example."
}

Set-Location $workspace
docker compose up --build
