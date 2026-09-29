param(
    [Parameter(Mandatory=$true)][string]$File,
    [Parameter(Mandatory=$true)]
    [ValidateSet("gpx","habu_log","capture_db","gis","other")]
    [string]$Kind,
    [string]$Source = "local-bridge",
    [string]$SourceRef = "",
    [string]$ExpectedSha256 = "",
    [switch]$Promote
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ArgsList = @(
    "$PSScriptRoot\ingest_attachment.py",
    "--file", $File,
    "--repo-root", $RepoRoot,
    "--kind", $Kind,
    "--source", $Source
)
if ($SourceRef) { $ArgsList += @("--source-ref", $SourceRef) }
if ($ExpectedSha256) { $ArgsList += @("--expected-sha256", $ExpectedSha256) }
if ($Promote) { $ArgsList += "--promote" }

python @ArgsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
