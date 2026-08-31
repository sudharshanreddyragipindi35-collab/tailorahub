[CmdletBinding()]
param(
    [ValidateSet('public-read', 'customer-read', 'tailor-read', 'admin-read', 'auth', 'booking', 'tailor-stage', 'notifications', 'media', 'websocket', 'payment')]
    [string]$Suite = 'public-read',

    [ValidateSet('smoke', 'baseline', 'normal', 'growth', 'release', 'high', 'spike', 'soak')]
    [string]$Profile = 'smoke',

    [string]$BaseUrl = 'http://127.0.0.1:8001/api',
    [switch]$AllowRemoteTarget,
    [switch]$AllowSyntheticWrites
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot 'load-tests\phase10.js'
$resultsDirectory = Join-Path $repoRoot 'load-test-results'
$k6 = Get-Command k6 -ErrorAction SilentlyContinue
if (-not $k6) {
    throw 'k6 is not installed. Install Grafana k6, then run this command again.'
}

$uri = [Uri]$BaseUrl
$localHosts = @('localhost', '127.0.0.1', '::1')
$isRemote = $localHosts -notcontains $uri.Host
if ($isRemote -and (-not $AllowRemoteTarget -or $env:PHASE10_REMOTE_APPROVAL -ne 'TAILORAHUB_APPROVED_LOAD_TEST')) {
    throw 'Remote targets require -AllowRemoteTarget and PHASE10_REMOTE_APPROVAL=TAILORAHUB_APPROVED_LOAD_TEST.'
}

$writeSuites = @('booking', 'tailor-stage', 'notifications', 'media', 'payment')
if ($writeSuites -contains $Suite) {
    if (-not $AllowSyntheticWrites -or $env:PHASE10_WRITE_APPROVAL -ne 'TAILORAHUB_APPROVED_SYNTHETIC_WRITES') {
        throw 'Write suites require -AllowSyntheticWrites and PHASE10_WRITE_APPROVAL=TAILORAHUB_APPROVED_SYNTHETIC_WRITES.'
    }
}

if ($Suite -eq 'payment') {
    if ($env:PAYMENT_PROVIDER_MODE -ne 'sandbox' -or $env:PHASE10_PAYMENT_APPROVAL -ne 'TAILORAHUB_APPROVED_SANDBOX_PAYMENTS') {
        throw 'Payment tests require PAYMENT_PROVIDER_MODE=sandbox and PHASE10_PAYMENT_APPROVAL=TAILORAHUB_APPROVED_SANDBOX_PAYMENTS.'
    }
}

New-Item -ItemType Directory -Path $resultsDirectory -Force | Out-Null
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$reportPath = ('load-test-results/phase10-{0}-{1}-{2}.json' -f $Suite, $Profile, $timestamp)

Write-Host ("Phase 10 suite={0} profile={1} target={2}" -f $Suite, $Profile, $BaseUrl)
& $k6.Source run `
    -e "BASE_URL=$BaseUrl" `
    -e "TEST_SUITE=$Suite" `
    -e "LOAD_PROFILE=$Profile" `
    -e "REPORT_PATH=$reportPath" `
    $scriptPath

if ($LASTEXITCODE -ne 0) {
    throw "The k6 run failed or an acceptance threshold was missed. Report: $reportPath"
}

Write-Host "Phase 10 thresholds passed. Report: $reportPath"
