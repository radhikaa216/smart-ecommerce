$ErrorActionPreference = "Stop"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is required to run the complete local test suite."
}

$workspace = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $workspace

docker compose run --rm fastapi pytest -q
docker compose run --rm django python manage.py test
docker compose run --rm frontend npm test -- --run
docker compose run --rm frontend npm run build
