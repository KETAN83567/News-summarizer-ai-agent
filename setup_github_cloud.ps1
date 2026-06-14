param(
    [Parameter(Mandatory = $true)]
    [string]$RepositoryUrl
)

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is not installed or not available on PATH."
}

if (-not (Test-Path -LiteralPath ".git")) {
    git init
    git branch -M main
}

$ExistingRemote = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0) {
    git remote set-url origin $RepositoryUrl
} else {
    git remote add origin $RepositoryUrl
}

git add .
git commit -m "Deploy personal morning intelligence agent"
if ($LASTEXITCODE -ne 0) {
    $Status = git status --porcelain
    if ($Status) {
        throw "Git commit failed. Review the output above."
    }
}

git push -u origin main
Write-Host "Project pushed. Add the required Actions secrets before enabling delivery."
