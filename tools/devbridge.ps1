<#
.SYNOPSIS
    Drive the game through the GSO DevTools DevBridge and print the resulting log lines.

.DESCRIPTION
    The DevBridge (src/GSODevTools/DevBridge.cs, deployed by build.ps1 -Deploy) polls <game>\GSODevTools\cmd.txt
    and runs each line in-game. This script writes those lines for you, waits between them, and returns
    the BepInEx log output they produced. See docs/DEVBRIDGE.md for the command reference.

    Getting into the world needs GSO Offline Server (the official servers are gone): -Enable also sets
    its AutoLogin/AutoCharacter so -Launch ends up in-game without touching the menus.

.EXAMPLE
    .\tools\devbridge.ps1 -Enable -Account Tester -Character Testguy   # bridge on + auto-login
    .\tools\devbridge.ps1 -Launch -Commands 'npcs 5' -Filter 'uid='
    .\tools\devbridge.ps1 -Commands 'client interactNpc 10018 $me','client sendDialogueOptionChoise $me 1' -Filter dialogue
    .\tools\devbridge.ps1 -Disable -ResetSaves -Account Tester -Character Testguy   # back to normal play
#>
[CmdletBinding()]
param(
    [string]$GameDir,
    [switch]$Enable,
    [string]$Account = 'Tester',
    [string]$Character = 'Testguy',
    [switch]$Disable,
    [switch]$ResetSaves,
    [switch]$Launch,
    [string[]]$Commands = @(),
    [double]$Wait = 2,
    [string]$Filter = ''
)

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot '..\build\GSOBuild.psm1') -Force
$GameDir = Resolve-GameDir $GameDir
$log = Join-Path $GameDir 'BepInEx\LogOutput.log'
$devCfg = Join-Path $GameDir 'BepInEx\config\gso.devtools.cfg'
$serverCfg = Join-Path $GameDir 'BepInEx\config\gso.offline.server.cfg'
$workDir = Join-Path $GameDir 'GSODevTools'
$cmdFile = Join-Path $workDir 'cmd.txt'

# Sets Key = Value in a BepInEx config. A missing file/key is created (BepInEx keeps it on next load).
function Set-ConfigValue([string]$Cfg, [string]$Section, [string]$Key, [string]$Value) {
    $lines = if (Test-Path $Cfg) { @(Get-Content $Cfg) } else { @() }
    if ($lines -match "^$Key\s*=") {
        $lines = $lines -replace "^$Key\s*=.*", "$Key = $Value"
    }
    else {
        $lines += @('', "[$Section]", "$Key = $Value")
    }
    $lines | Set-Content $Cfg
}

if ($Enable) {
    if (-not (Test-Path (Join-Path $GameDir 'BepInEx\plugins\GSODevTools\GSODevTools.dll'))) {
        throw 'GSODevTools.dll is not deployed. Run .\build.ps1 -Deploy in this repo first.'
    }
    Set-ConfigValue $devCfg 'General' 'Enabled' 'true'
    if (Test-Path $serverCfg) {
        Set-ConfigValue $serverCfg 'Convenience' 'AutoLogin' $Account
        Set-ConfigValue $serverCfg 'Convenience' 'AutoCharacter' $Character
        Write-Host "DevBridge enabled (auto-login $Account / $Character)."
    }
    else {
        Write-Warning "No $serverCfg, so no auto-login: GSO Offline Server must be installed and launched once."
    }
}
if ($Disable) {
    Get-Process GSO -ErrorAction SilentlyContinue | Stop-Process -Force
    if (Test-Path $devCfg) { Set-ConfigValue $devCfg 'General' 'Enabled' 'false' }
    if (Test-Path $serverCfg) {
        Set-ConfigValue $serverCfg 'Convenience' 'AutoLogin' ''
        Set-ConfigValue $serverCfg 'Convenience' 'AutoCharacter' ''
    }
    Write-Host 'DevBridge disabled; normal login restored.'
}
if ($ResetSaves) {
    # Only the test account/character, never other saves: real players' characters live here too.
    Get-Process GSO -ErrorAction SilentlyContinue | Stop-Process -Force
    foreach ($f in "accounts\$Account.json", "characters\$Character.json") {
        $p = Join-Path $GameDir "OfflineSaves\$f"
        if (Test-Path $p) { Remove-Item $p -Force; Write-Host "Deleted $p" }
    }
    if (Test-Path $workDir) { Remove-Item $workDir -Recurse -Force }
}

if ($Launch) {
    Get-Process GSO -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep 1
    # Remove the old log first, or the wait below would match the previous run.
    Remove-Item $log -ErrorAction SilentlyContinue
    Start-Process -FilePath (Join-Path $GameDir 'GSO.exe') -WorkingDirectory $GameDir
    $deadline = (Get-Date).AddSeconds(120)
    while ((Get-Date) -lt $deadline) {
        if ((Test-Path $log) -and (Select-String -Path $log -Pattern 'harvestables\.' -Quiet)) { break }
        Start-Sleep 2
    }
    if (-not ((Test-Path $log) -and (Select-String -Path $log -Pattern 'harvestables\.' -Quiet))) {
        throw 'The world did not load within 120 s (is auto-login enabled? see -Enable).'
    }
    Start-Sleep 3
}

if ($Commands.Count -eq 0 -and -not $Launch) { return }

$before = if ($Launch -or -not (Test-Path $log)) { 0 } else { (Get-Content $log).Count }
New-Item -ItemType Directory -Force $workDir | Out-Null
foreach ($c in $Commands) {
    # The bridge deletes the file once it has read it; wait so commands are not overwritten.
    $until = (Get-Date).AddSeconds(10)
    while ((Test-Path $cmdFile) -and (Get-Date) -lt $until) { Start-Sleep -Milliseconds 200 }
    Set-Content $cmdFile $c
    Start-Sleep -Seconds $Wait
}

$lines = Get-Content $log | Select-Object -Skip $before
if ($Filter) { $lines = $lines | Where-Object { $_ -match $Filter } }
$lines
