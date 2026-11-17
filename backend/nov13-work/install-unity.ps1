$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$assetsRoot = [System.IO.Path]::GetFullPath('C:/Users/good6/WarfrontMVP/Assets')
$stageRoot = Join-Path $taskRoot 'unity'
$backupRoot = Join-Path $taskRoot ('installed-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
foreach ($folder in @('script', 'Editor')) {
    foreach ($file in Get-ChildItem -LiteralPath (Join-Path $stageRoot $folder) -Filter '*.cs' -File) {
        $destination = [System.IO.Path]::GetFullPath((Join-Path (Join-Path $assetsRoot $folder) $file.Name))
        if (-not $destination.StartsWith($assetsRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Destination escaped Assets' }
        if (Test-Path -LiteralPath $destination) {
            $backupFolder = Join-Path $backupRoot $folder
            New-Item -ItemType Directory -Path $backupFolder -Force | Out-Null
            Copy-Item -LiteralPath $destination -Destination (Join-Path $backupFolder $file.Name)
        }
        Copy-Item -LiteralPath $file.FullName -Destination $destination
    }
}
Set-Content -LiteralPath (Join-Path $env:TEMP 'warfront-november.request') -Value 'run' -Encoding UTF8
Write-Output ('Unity scripts installed; previous files backed up in ' + $backupRoot)
