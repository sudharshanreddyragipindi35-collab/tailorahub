$ErrorActionPreference = "Stop"

$projectDirectory = $PSScriptRoot
$unsignedBundle = Join-Path $projectDirectory "Vastrivo-v5-release-unsigned.aab"
$signedBundle = Join-Path $projectDirectory "Vastrivo-v5-release.aab"
$keystore = Join-Path $projectDirectory "android.keystore"
$keyAlias = "android"

foreach ($requiredFile in @($unsignedBundle, $keystore)) {
    if (-not (Test-Path -LiteralPath $requiredFile)) {
        throw "Required file was not found: $requiredFile"
    }
}

if (Test-Path -LiteralPath $signedBundle) {
    throw "The signed output already exists: $signedBundle`nMove or rename it before running this script again."
}

if (-not (Get-Command jarsigner -ErrorAction SilentlyContinue)) {
    throw "jarsigner was not found. Install/use JDK 17 and make sure its bin directory is on PATH."
}

Write-Host "Signing Vastrivo version 5 with the existing Play Store upload key."
Write-Host "Enter your existing Android keystore password when jarsigner prompts you."
Write-Host "Do not paste that password into chat or save it in this project."

& jarsigner `
    -verbose `
    -sigalg SHA256withRSA `
    -digestalg SHA-256 `
    -keystore $keystore `
    -signedjar $signedBundle `
    $unsignedBundle `
    $keyAlias

if ($LASTEXITCODE -ne 0) {
    throw "Bundle signing failed. The unsigned bundle was not modified."
}

& jarsigner -verify $signedBundle
if ($LASTEXITCODE -ne 0) {
    throw "Signature verification failed for: $signedBundle"
}

$bundleHash = Get-FileHash -Algorithm SHA256 -LiteralPath $signedBundle

Write-Host ""
Write-Host "Signed Play Store bundle created successfully:"
Write-Host $signedBundle
Write-Host "SHA256: $($bundleHash.Hash)"
