$ErrorActionPreference='Stop'
$targetAssets=[System.IO.Path]::GetFullPath('C:/Users/good6/WarfrontMVP/Assets')
$backup=Join-Path $PSScriptRoot ('backup-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
foreach($folder in @('script','Editor')) {
    foreach($file in Get-ChildItem -LiteralPath (Join-Path (Join-Path $PSScriptRoot 'unity') $folder) -Filter '*.cs' -File) {
        $destination=[System.IO.Path]::GetFullPath((Join-Path (Join-Path $targetAssets $folder) $file.Name))
        if(-not $destination.StartsWith($targetAssets+[System.IO.Path]::DirectorySeparatorChar,[System.StringComparison]::OrdinalIgnoreCase)){throw 'Invalid destination'}
        if(Test-Path -LiteralPath $destination){
            $backupFolder=Join-Path $backup $folder
            New-Item -ItemType Directory -Path $backupFolder -Force | Out-Null
            Copy-Item -LiteralPath $destination -Destination (Join-Path $backupFolder $file.Name)
        }
        Copy-Item -LiteralPath $file.FullName -Destination $destination
    }
}
Set-Content -LiteralPath (Join-Path $env:TEMP 'warfront-town-panel-return.request') -Value 'run' -Encoding UTF8
Write-Output 'Installed town panel return changes with backups.'
