# package_lambda.ps1
# ------------------------------------
# 在 Windows PowerShell 里运行：
#   ./package_lambda.ps1
#
# 会把整个 tiny_universe 包 + requirements.txt
# 打成一个 lambda.zip 到 infra/build/lambda.zip

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildDir = Join-Path $root "infra\build"
$zipPath = Join-Path $buildDir "lambda.zip"

Write-Host "Root directory: $root"

if (!(Test-Path $buildDir)) {
    New-Item -ItemType Directory -Path $buildDir | Out-Null
}

if (Test-Path $zipPath) {
    Remove-Item $zipPath
}

Write-Host "Creating virtual env (if needed) and installing deps (optional)..."
# 如果你想连依赖一起打包，可以在这里用 pip install -t 等；
# 暂时我们先只打代码，依赖放在 layer 以后再说。

Write-Host "Zipping tiny_universe package to $zipPath ..."

# 把 tiny_universe 整个文件夹打包
Push-Location $root
Compress-Archive -Path "tiny_universe", "requirements.txt" -DestinationPath $zipPath
Pop-Location

Write-Host "Done. Lambda package at $zipPath"
