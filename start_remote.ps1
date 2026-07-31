$ErrorActionPreference = "Stop"

Write-Host "Starting Relay Server..."
Start-Process -FilePath "python" -ArgumentList "system_mcp/relay_server.py" -WindowStyle Minimized
Start-Sleep -Seconds 2

Write-Host "Starting Localtunnel..."
# We run localtunnel and pipe its output to a file so we can read the URL
Start-Process -FilePath "cmd.exe" -ArgumentList "/c npx -y localtunnel --port 8765 > lt.log" -WindowStyle Minimized

Start-Sleep -Seconds 5
$ltOutput = Get-Content "lt.log" -Raw
if ($ltOutput -match "your url is: (https://.*)") {
    $publicUrl = $matches[1]
    $wsUrl = $publicUrl -replace "https://", "wss://"
    Write-Host "Public Relay URL: $wsUrl"
    
    Write-Host "Starting Python Host Agent..."
    $env:RELAY_URL = $wsUrl
    Start-Process -FilePath "python" -ArgumentList "mitchell_assistant.py --remote" -WindowStyle Normal
    Write-Host "Host Agent started successfully!"
} else {
    Write-Host "Failed to get localtunnel URL. Output was: $ltOutput"
}
