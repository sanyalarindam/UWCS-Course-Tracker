param([string]$Version = "0.2.0", [string]$Iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe")
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
python packaging/create_icon.py
if ($LASTEXITCODE -ne 0) { throw 'App icon generation failed.' }
python -m PyInstaller --noconfirm --clean --distpath dist --workpath .local-data/pyinstaller packaging/windows.spec
if ($LASTEXITCODE -ne 0) { throw 'Application packaging failed.' }
$smoke = Start-Process -FilePath '.\dist\CS Tracker\CS Tracker.exe' -ArgumentList '--smoke-test' -PassThru -Wait -WindowStyle Hidden
if ($smoke.ExitCode -ne 0) { throw 'Packaged application smoke test failed.' }
New-Item -ItemType Directory -Force .local-data/build-tools | Out-Null
Invoke-WebRequest 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' -OutFile .local-data/build-tools/MicrosoftEdgeWebview2Setup.exe
$signature = Get-AuthenticodeSignature .local-data/build-tools/MicrosoftEdgeWebview2Setup.exe
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Microsoft Corporation') { throw 'WebView2 bootstrapper signature verification failed.' }
& $Iscc "/DAppVersion=$Version" packaging/installer.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
Get-ChildItem dist/installer/*.exe | ForEach-Object { (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower() + '  ' + $_.Name } | Set-Content dist/installer/SHA256SUMS.txt -Encoding ascii
