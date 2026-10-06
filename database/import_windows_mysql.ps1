<#
.SYNOPSIS
Imports a Docker MySQL dump into a new database on the Windows MySQL Server.

.DESCRIPTION
This script refuses to use an existing target database. It does not delete or
replace Windows MySQL data. The selected Windows MySQL user needs CREATE
DATABASE and full privileges on the target database.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateScript({ Test-Path $_ -PathType Leaf })]
    [string]$DumpPath,

    [string]$Server = 'localhost',

    [ValidateRange(1, 65535)]
    [int]$Port = 3306,

    [Parameter(Mandatory)]
    [string]$Username,

    [ValidatePattern('^[A-Za-z0-9_]+$')]
    [string]$Database = 'smart_ecommerce',

    [string]$MySqlClientPath = 'mysql.exe',

    # Allows retrying only if a previous failed run left this target database empty.
    [switch]$ReplaceEmptyDatabase
)

$ErrorActionPreference = 'Stop'

function ConvertTo-PlainText([Security.SecureString]$SecureValue) {
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
}

function Invoke-MySql([string[]]$Arguments, [string]$Password, [string]$InputFile) {
    $startInfo = [Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $MySqlClientPath
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardInput = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.EnvironmentVariables['MYSQL_PWD'] = $Password
    $startInfo.Arguments = (($Arguments | ForEach-Object { '"' + ($_ -replace '"', '\\"') + '"' }) -join ' ')

    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    [void]$process.Start()
    if ($InputFile) {
        $file = [IO.File]::OpenRead($InputFile)
        try { $file.CopyTo($process.StandardInput.BaseStream) }
        finally { $file.Dispose(); $process.StandardInput.Close() }
    }
    $standardOutput = $process.StandardOutput.ReadToEnd()
    $standardError = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) {
        throw "mysql.exe failed with exit code $($process.ExitCode).`n$standardError"
    }
    return $standardOutput.Trim()
}

if (-not (Get-Command $MySqlClientPath -ErrorAction SilentlyContinue) -and -not (Test-Path $MySqlClientPath)) {
    throw "mysql.exe was not found. Add MySQL Server bin to PATH or pass -MySqlClientPath 'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe'."
}

$resolvedDump = (Resolve-Path $DumpPath).Path
$password = ConvertTo-PlainText (Read-Host "Windows MySQL password for '$Username'" -AsSecureString)
$baseArguments = @('--protocol=TCP', "--host=$Server", "--port=$Port", "--user=$Username")

try {
    $existingDatabase = Invoke-MySql ($baseArguments + @('--skip-column-names', '--batch', '--execute', "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '$Database';")) $password $null
    if ($existingDatabase -eq $Database) {
        $existingTableCount = Invoke-MySql ($baseArguments + @("--database=$Database", '--skip-column-names', '--batch', '--execute', 'SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE();')) $password $null
        if (-not $ReplaceEmptyDatabase -or [int]$existingTableCount -ne 0) {
            throw "Target database '$Database' already exists. This script will not overwrite it. It contains $existingTableCount table(s)."
        }
        Write-Host "Removing the empty database left by the previous failed import..." -ForegroundColor Yellow
        Invoke-MySql ($baseArguments + @('--execute', "DROP DATABASE ``$Database``;")) $password $null | Out-Null
    }

    Write-Host "Creating Windows MySQL database '$Database'..." -ForegroundColor Cyan
    Invoke-MySql ($baseArguments + @('--execute', "CREATE DATABASE ``$Database`` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;")) $password $null | Out-Null

    Write-Host "Importing '$resolvedDump'..." -ForegroundColor Cyan
    Invoke-MySql ($baseArguments + @("--database=$Database")) $password $resolvedDump | Out-Null

    $tables = Invoke-MySql ($baseArguments + @("--database=$Database", '--skip-column-names', '--batch', '--execute', 'SHOW TABLES;')) $password $null
    $tableCount = @($tables -split "`r?`n" | Where-Object { $_ }).Count
    $counts = Invoke-MySql ($baseArguments + @("--database=$Database", '--skip-column-names', '--batch', '--execute', 'SELECT (SELECT COUNT(*) FROM users), (SELECT COUNT(*) FROM products), (SELECT COUNT(*) FROM orders), (SELECT COUNT(*) FROM payments);')) $password $null

    Write-Host "Import complete: $tableCount tables created in '$Database'." -ForegroundColor Green
    Write-Host "Record counts (users, products, orders, payments): $counts"
}
catch {
    Write-Error "Import stopped. The database was not deleted automatically; it may be partially imported. Error: $($_.Exception.Message)"
    throw
}
finally {
    $password = $null
}
