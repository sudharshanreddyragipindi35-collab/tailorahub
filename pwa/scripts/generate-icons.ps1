param(
  [string]$FrontendPublicPath = ""
)

if (-not $FrontendPublicPath) {
  $FrontendPublicPath = Join-Path $PSScriptRoot "..\..\frontend\public"
}

$iconsDir = Join-Path $FrontendPublicPath "icons"
New-Item -ItemType Directory -Force -Path $iconsDir | Out-Null

Add-Type -AssemblyName System.Drawing

function New-TailoraIcon {
  param(
    [int]$Size,
    [string]$Path,
    [bool]$Maskable = $false
  )

  $bitmap = New-Object System.Drawing.Bitmap $Size, $Size
  $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
  $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
  $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit

  $rect = New-Object System.Drawing.Rectangle 0, 0, $Size, $Size
  $bg = New-Object System.Drawing.Drawing2D.LinearGradientBrush $rect, ([System.Drawing.Color]::FromArgb(255, 5, 6, 6)), ([System.Drawing.Color]::FromArgb(255, 27, 30, 31)), 45
  $graphics.FillRectangle($bg, $rect)

  $gold = [System.Drawing.Color]::FromArgb(255, 245, 209, 93)
  $bronze = [System.Drawing.Color]::FromArgb(255, 177, 126, 24)
  $ringWidth = [Math]::Max(6, [int]($Size * 0.035))
  $padding = if ($Maskable) { [int]($Size * 0.20) } else { [int]($Size * 0.12) }
  $ringRect = New-Object System.Drawing.Rectangle $padding, $padding, ($Size - ($padding * 2)), ($Size - ($padding * 2))
  $ringPen = New-Object System.Drawing.Pen $gold, $ringWidth
  $graphics.DrawEllipse($ringPen, $ringRect)

  $innerPen = New-Object System.Drawing.Pen $bronze, ([Math]::Max(2, [int]($Size * 0.01)))
  $innerPadding = $padding + [int]($Size * 0.055)
  $innerRect = New-Object System.Drawing.Rectangle $innerPadding, $innerPadding, ($Size - ($innerPadding * 2)), ($Size - ($innerPadding * 2))
  $graphics.DrawEllipse($innerPen, $innerRect)

  $fontSize = [int]($Size * 0.23)
  $font = New-Object System.Drawing.Font "Arial", $fontSize, ([System.Drawing.FontStyle]::Bold), ([System.Drawing.GraphicsUnit]::Pixel)
  $brush = New-Object System.Drawing.SolidBrush $gold
  $format = New-Object System.Drawing.StringFormat
  $format.Alignment = [System.Drawing.StringAlignment]::Center
  $format.LineAlignment = [System.Drawing.StringAlignment]::Center
  $textRect = New-Object System.Drawing.RectangleF 0, 0, $Size, $Size
  $graphics.DrawString("TH", $font, $brush, $textRect, $format)

  $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)

  $format.Dispose()
  $brush.Dispose()
  $font.Dispose()
  $innerPen.Dispose()
  $ringPen.Dispose()
  $bg.Dispose()
  $graphics.Dispose()
  $bitmap.Dispose()
}

New-TailoraIcon -Size 192 -Path (Join-Path $iconsDir "icon-192.png") -Maskable $false
New-TailoraIcon -Size 512 -Path (Join-Path $iconsDir "icon-512.png") -Maskable $false
New-TailoraIcon -Size 512 -Path (Join-Path $iconsDir "maskable-512.png") -Maskable $true

Write-Host "Generated TailoraHub PWA icons in $iconsDir"
