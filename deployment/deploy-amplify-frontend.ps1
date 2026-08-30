param(
    [Parameter(Mandatory = $true)]
    [string]$ZipPath,
    [string]$Profile = "tailorahub-prod",
    [string]$Region = "eu-north-1",
    [string]$AppId = "djnngsaytw9uq",
    [string]$BranchName = "production"
)

$ErrorActionPreference = "Stop"

$resolvedZip = (Resolve-Path -LiteralPath $ZipPath).Path
$deploymentJson = aws amplify create-deployment `
    --profile $Profile `
    --region $Region `
    --app-id $AppId `
    --branch-name $BranchName `
    --output json

if ($LASTEXITCODE -ne 0) {
    throw "Amplify create-deployment failed."
}

$deployment = $deploymentJson | ConvertFrom-Json
& curl.exe --silent --show-error --fail --request PUT --upload-file $resolvedZip $deployment.zipUploadUrl

if ($LASTEXITCODE -ne 0) {
    throw "Amplify ZIP upload failed."
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
} | ConvertTo-Json
