param(
    [int]$IntervalMinutes = 10,
    [string]$ApiBaseUrl = "http://127.0.0.1:8000/api/v1"
)

$ErrorActionPreference = "Stop"

if ($IntervalMinutes -lt 1) {
    Write-Error "IntervalMinutes must be 1 or greater."
    exit 1
}

if ([string]::IsNullOrWhiteSpace($ApiBaseUrl)) {
    Write-Error "ApiBaseUrl must not be empty."
    exit 1
}

$normalizedApiBaseUrl = $ApiBaseUrl.TrimEnd([char]"/")
$endpoint = "$normalizedApiBaseUrl/watchlist/refresh-prices"
$intervalSeconds = $IntervalMinutes * 60

Write-Host "Collecting price history via watchlist refresh."
Write-Host "Endpoint: $endpoint"
Write-Host "Interval: $IntervalMinutes minute(s)"
Write-Host "Stop: press Ctrl+C"
Write-Host ""

while ($true) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    try {
        $result = Invoke-RestMethod -Method Post -Uri $endpoint

        Write-Host "[$timestamp] total=$($result.total) updated=$($result.updated) failed=$($result.failed)"

        $failedItems = @($result.items | Where-Object { $_ -and -not $_.success })

        if ($failedItems.Count -gt 0) {
            foreach ($item in $failedItems) {
                $secid = if ($item.secid) { $item.secid } else { "UNKNOWN" }
                $errorText = if ($item.error) { $item.error } else { "unknown error" }

                Write-Warning "[$timestamp] failed: secid=$secid error=$errorText"
            }
        }
    } catch {
        Write-Warning "[$timestamp] Failed to refresh prices: $($_.Exception.Message)"
    }

    Start-Sleep -Seconds $intervalSeconds
}
