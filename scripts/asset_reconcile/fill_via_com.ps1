param(
    [string]$DataPath
)
$ErrorActionPreference = "Stop"

# 用 .NET 显式按 UTF-8 读取，避免中文/换行乱码（不依赖 BOM）
$json = [System.IO.File]::ReadAllText($DataPath, [System.Text.Encoding]::UTF8)
$cfg = $json | ConvertFrom-Json

$src = $cfg.src
$out = $cfg.out
$rows = $cfg.rows

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
$wb = $null

try {
    $wb = $excel.Workbooks.Open($src)
    $n = 0
    foreach ($item in $rows) {
        $ws = $wb.Worksheets.Item([string]$item.sheet)
        $cell = $ws.Cells.Item([int]$item.row, [int]$item.col)
        $cell.Value2 = [string]$item.text
        $cell.WrapText = $true
        $cell.VerticalAlignment = -4160   # xlTop
        $n++
    }
    # 51 = xlOpenXMLWorkbook (.xlsx)
    $wb.SaveAs($out, 51)
    $wb.Close($false)
    Write-Output ("OK 已写入 " + $n + " 行 -> " + $out)
}
finally {
    if ($wb -ne $null) { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($wb) }
    $excel.Quit()
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel)
}
