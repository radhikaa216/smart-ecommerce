<#
.SYNOPSIS
Exports the current Docker MySQL smart_ecommerce database to a dated SQL dump.

.DESCRIPTION
The dump is copied byte-for-byte from the MySQL container, so PowerShell does
not change its encoding. Passwords are prompted for and are never written to disk.
#>
[CmdletBinding()]
param(
    [ValidatePattern('^[A-Za-z0-9_]+$')]
    [string]$Database = 'smart_ecommerce',

    [ValidatePattern('^[A-Za-z0-9_]+$')]
    [string]$DatabaseUser,

    [string]$OutputDirectory = (Join-Path $PSScriptRoot '..\backups')
)

$ErrorActionPreference = 'Stop'

function ConvertTo-PlainText([Security.SecureString]$SecureValue) {
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
}

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$databasePasswordFromEnv = $null
$envFile = Join-Path $projectRoot '.env'
if (Test-Path $envFile) {
    $environmentValues = @{}
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.*)$') { $environmentValues[$matches[1].Trim()] = $matches[2].Trim() }
    }
    if (-not $DatabaseUser) { $DatabaseUser = $environmentValues['DB_USER'] }
    $databasePasswordFromEnv = $environmentValues['DB_PASSWORD']
}
if (-not $DatabaseUser) { throw 'Database user is required. Pass -DatabaseUser or set DB_USER in .env.' }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker Desktop/Docker CLI was not found. Start Docker Desktop and try again.'
}

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$outputDirectoryPath = (Resolve-Path $OutputDirectory).Path
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$fileName = "$Database-docker-export-$timestamp.sql"
$dumpPath = Join-Path $outputDirectoryPath $fileName
$containerDumpPath = "/tmp/$fileName"
if ($databasePasswordFromEnv) {
    $databasePassword = $databasePasswordFromEnv
    Write-Host "Using the application database credentials configured in .env." -ForegroundColor DarkGray
} else {
    $databasePassword = ConvertTo-PlainText (Read-Host "Docker MySQL password for application user '$DatabaseUser'" -AsSecureString)
}

Push-Location $projectRoot
try {
    Write-Host "Exporting Docker MySQL database '$Database'..." -ForegroundColor Cyan
    & docker compose exec -T -e "MYSQL_PWD=$databasePassword" mysql sh -c "mysqldump --single-transaction --routines --triggers --events --set-gtid-purged=OFF --no-tablespaces -u'$DatabaseUser' '$Database' > '$containerDumpPath'"
    if ($LASTEXITCODE -ne 0) { throw "mysqldump failed with exit code $LASTEXITCODE." }

    & docker compose cp "mysql:$containerDumpPath" $dumpPath
    if ($LASTEXITCODE -ne 0) { throw "Could not copy the dump from the MySQL container (exit code $LASTEXITCODE)." }

    & docker compose exec -T mysql rm -f $containerDumpPath
    if ($LASTEXITCODE -ne 0) { Write-Warning "The temporary container dump could not be removed: $containerDumpPath" }
}
finally {
    Pop-Location
    $rootPassword = $null
}

if (-not (Test-Path $dumpPath) -or (Get-Item $dumpPath).Length -eq 0) {
    throw 'Export did not create a non-empty dump file.'
}

Write-Host "Export complete: $dumpPath" -ForegroundColor Green
Write-Host ("File size: {0:N2} MB" -f ((Get-Item $dumpPath).Length / 1MB))
