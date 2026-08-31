param(
    [string]$Profile = "tailorahub-prod",
    [string]$Region = "ap-south-1",
    [string]$RepositoryName = "tailorahub-backend",
    [string]$ImageTag = "",
    [string]$BackendDirectory = ""
)

$ErrorActionPreference = "Stop"

if (-not $BackendDirectory) {
    $BackendDirectory = Join-Path $PSScriptRoot "..\backend"
}
$BackendDirectory = (Resolve-Path -LiteralPath $BackendDirectory).Path

if (-not $ImageTag) {
    $ImageTag = (git -C (Join-Path $PSScriptRoot "..") rev-parse --short=12 HEAD).Trim()
}
if ($ImageTag -notmatch '^[A-Za-z0-9._-]{1,128}$') {
    throw "ImageTag contains characters that ECR does not accept."
}

$identity = aws sts get-caller-identity --profile $Profile --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) {
    throw "AWS identity check failed. Refresh the $Profile login first."
}

aws ecr describe-repositories --profile $Profile --region $Region --repository-names $RepositoryName --output json 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    aws ecr create-repository `
        --profile $Profile `
        --region $Region `
        --repository-name $RepositoryName `
        --image-tag-mutability IMMUTABLE `
        --image-scanning-configuration scanOnPush=true `
        --encryption-configuration encryptionType=AES256 `
        --output json | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "ECR repository creation failed."
    }
}

$registry = "$($identity.Account).dkr.ecr.$Region.amazonaws.com"
$password = aws ecr get-login-password --profile $Profile --region $Region
$password | docker login --username AWS --password-stdin $registry | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Docker login to ECR failed."
}

$imageUri = "$registry/$RepositoryName`:$ImageTag"
docker build --pull --tag $imageUri $BackendDirectory
if ($LASTEXITCODE -ne 0) {
    throw "Backend image build failed."
}

docker push $imageUri
if ($LASTEXITCODE -ne 0) {
    throw "Backend image push failed."
}

[pscustomobject]@{
    Account = $identity.Account
    Region = $Region
    Repository = $RepositoryName
    ImageUri = $imageUri
} | ConvertTo-Json
