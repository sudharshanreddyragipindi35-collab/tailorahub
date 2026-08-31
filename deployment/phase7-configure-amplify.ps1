param(
    [string]$Profile = "tailorahub-prod",
    [string]$Region = "eu-north-1",
    [string]$AppId = "djnngsaytw9uq",
    [string]$CustomHeadersFile = ""
)

$ErrorActionPreference = "Stop"

if (-not $CustomHeadersFile) {
    $CustomHeadersFile = Join-Path $PSScriptRoot "..\customHttp.yml"
}
$CustomHeadersFile = (Resolve-Path -LiteralPath $CustomHeadersFile).Path
$customHeaders = Get-Content -Raw -LiteralPath $CustomHeadersFile

$rules = @(
    [ordered]@{
        source = "</^[^.]+$|\.(?!(css|gif|ico|jpg|jpeg|js|png|svg|txt|webp|woff|woff2|json|xml|map)$)([^.]+$)/>"
        target = "/index.html"
        status = "200"
    }
)

$rulesPath = Join-Path $env:TEMP ("tailorahub-amplify-rules-{0}.json" -f [guid]::NewGuid().ToString("N"))
try {
    [System.IO.File]::WriteAllText(
        $rulesPath,
        ($rules | ConvertTo-Json -Depth 5 -Compress),
        (New-Object System.Text.UTF8Encoding($false))
    )

    aws amplify update-app `
        --profile $Profile `
        --region $Region `
        --app-id $AppId `
        --custom-rules ("file://" + $rulesPath) `
        --custom-headers $customHeaders `
        --output json

    if ($LASTEXITCODE -ne 0) {
        throw "Amplify SPA rewrite configuration failed."
    }
}
finally {
    Remove-Item -LiteralPath $rulesPath -Force -ErrorAction SilentlyContinue
}
