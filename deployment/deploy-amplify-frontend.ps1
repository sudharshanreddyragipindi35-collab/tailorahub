param(
    [Parameter(Mandatory = $true)]
    [string]$BuildDirectory,
    [string]$Profile = "tailorahub-prod",
    [string]$Region = "eu-north-1",
    [string]$AppId = "djnngsaytw9uq",
    [string]$BranchName = "production"
)

$ErrorActionPreference = "Stop"

$resolvedBuild = (Resolve-Path -LiteralPath $BuildDirectory).Path
$files = @(Get-ChildItem -LiteralPath $resolvedBuild -Recurse -File)
if ($files.Count -eq 0) {
    throw "The frontend build directory is empty."
}

$fileMap = [ordered]@{}
$pathsByKey = @{}
foreach ($file in $files) {
    $relativePath = $file.FullName.Substring($resolvedBuild.Length).TrimStart("\", "/") -replace "\\", "/"
    $fileMap[$relativePath] = (Get-FileHash -LiteralPath $file.FullName -Algorithm MD5).Hash.ToLowerInvariant()
    $pathsByKey[$relativePath] = $file.FullName
}

$mapPath = Join-Path $env:TEMP ("tailorahub-amplify-file-map-{0}.json" -f [guid]::NewGuid().ToString("N"))
try {
    $mapJson = $fileMap | ConvertTo-Json -Compress
    [System.IO.File]::WriteAllText($mapPath, $mapJson, (New-Object System.Text.UTF8Encoding($false)))

    $deploymentJson = aws amplify create-deployment `
        --profile $Profile `
        --region $Region `
        --app-id $AppId `
        --branch-name $BranchName `
        --file-map ("file://" + $mapPath) `
        --output json

    if ($LASTEXITCODE -ne 0) {
        throw "Amplify create-deployment failed."
    }

    $deployment = $deploymentJson | ConvertFrom-Json
    foreach ($property in $deployment.fileUploadUrls.psobject.Properties) {
        $relativePath = $property.Name
        & curl.exe --silent --show-error --fail --request PUT --upload-file $pathsByKey[$relativePath] $property.Value
        if ($LASTEXITCODE -ne 0) {
            throw "Amplify file upload failed for $relativePath."
        }
    }

    $startJson = aws amplify start-deployment `
        --profile $Profile `
        --region $Region `
        --app-id $AppId `
        --branch-name $BranchName `
        --job-id $deployment.jobId `
        --output json

    if ($LASTEXITCODE -ne 0) {
        throw "Amplify start-deployment failed."
    }

    $start = $startJson | ConvertFrom-Json
    [pscustomobject]@{
        JobId = $deployment.jobId
        Status = $start.jobSummary.status
        UploadedFiles = $files.Count
    } | ConvertTo-Json
}
finally {
    Remove-Item -LiteralPath $mapPath -Force -ErrorAction SilentlyContinue
}
