# Build backend/win-ca-bundle.pem from the Windows root trust store.
# Needed when a TLS-intercepting AV/proxy (e.g. Avast Web Shield) re-signs HTTPS
# with a private root: curl_cffi (yfinance) reads this bundle via CURL_CA_BUNDLE,
# and truststore handles the OpenSSL libs. Re-run if the interceptor's CA rotates.
#   powershell -ExecutionPolicy Bypass -File backend/scripts/build_ca_bundle.ps1
$out = Join-Path $PSScriptRoot "..\win-ca-bundle.pem" | Resolve-Path -ErrorAction SilentlyContinue
if (-not $out) { $out = Join-Path $PSScriptRoot "..\win-ca-bundle.pem" }
$certs = foreach ($s in @('Cert:\LocalMachine\Root','Cert:\CurrentUser\Root')) { try { Get-ChildItem $s -ErrorAction Stop } catch {} }
$certs = $certs | Sort-Object Thumbprint -Unique
$sb = New-Object System.Text.StringBuilder
$kept = 0
foreach ($c in $certs) {
  # Keep only valid CA trust anchors; a non-CA cert in the bundle makes OpenSSL
  # reject the whole chain ("Basic Constraints of CA cert not matched").
  $bcExt = $c.Extensions | Where-Object { $_.Oid.Value -eq '2.5.29.19' }
  $isCA = $true
  if ($bcExt) { $isCA = ([System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]$bcExt).CertificateAuthority }
  if (-not $isCA) { continue }
  $kept++
  [void]$sb.AppendLine("# $($c.Subject)")
  [void]$sb.AppendLine("-----BEGIN CERTIFICATE-----")
  [void]$sb.AppendLine([System.Convert]::ToBase64String($c.RawData,'InsertLineBreaks'))
  [void]$sb.AppendLine("-----END CERTIFICATE-----")
}
[System.IO.File]::WriteAllText($out, $sb.ToString(), (New-Object System.Text.ASCIIEncoding))
Write-Host "Wrote $kept CA trust anchors to $out"
