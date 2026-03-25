param(
  [ValidateSet('list-targets','eval','navigate')]
  [string]$Mode = 'list-targets',
  [int]$Port = 19223,
  [string]$TargetUrlSubstring = 'new.web.cafe/messages',
  [string]$Expression,
  [string]$NavigateUrl
)

$ProgressPreference = 'SilentlyContinue'

function Get-Json($url) {
  Invoke-RestMethod -Uri $url -TimeoutSec 5
}

function Get-Target {
  $targets = Get-Json("http://127.0.0.1:$Port/json/list")
  if ($Mode -eq 'list-targets') {
    return $targets
  }
  $target = $targets | Where-Object { $_.type -eq 'page' -and $_.url -like "*$TargetUrlSubstring*" } | Select-Object -First 1
  if (-not $target) {
    throw "No matching target for substring: $TargetUrlSubstring"
  }
  return $target
}

function New-CdpSession([string]$wsUrl) {
  $ws = [System.Net.WebSockets.ClientWebSocket]::new()
  $cts = [System.Threading.CancellationTokenSource]::new()
  $uri = [Uri]$wsUrl
  $ws.ConnectAsync($uri, $cts.Token).GetAwaiter().GetResult() | Out-Null
  $state = [ordered]@{
    ws = $ws
    cts = $cts
    nextId = 1
    events = New-Object System.Collections.Generic.List[object]
  }
  return $state
}

function Send-Cdp($session, [string]$method, $params = $null) {
  $id = [int]$session.nextId
  $session.nextId = $id + 1
  $payload = [ordered]@{ id = $id; method = $method }
  if ($null -ne $params) { $payload.params = $params }
  $json = $payload | ConvertTo-Json -Compress -Depth 50
  $bytes = [Text.Encoding]::UTF8.GetBytes($json)
  $seg = [ArraySegment[byte]]::new($bytes)
  $session.ws.SendAsync($seg, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $session.cts.Token).GetAwaiter().GetResult() | Out-Null
  return $id
}

function Receive-Until($session, [scriptblock]$matcher, [int]$timeoutMs = 15000) {
  $buffer = New-Object byte[] 262144
  $ms = New-Object System.IO.MemoryStream
  while ($true) {
    $seg = [ArraySegment[byte]]::new($buffer)
    $res = $session.ws.ReceiveAsync($seg, $session.cts.Token).GetAwaiter().GetResult()
    if ($res.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) {
      throw 'WebSocket closed unexpectedly'
    }
    $ms.Write($buffer, 0, $res.Count)
    if (-not $res.EndOfMessage) { continue }
    $text = [Text.Encoding]::UTF8.GetString($ms.ToArray())
    $ms.SetLength(0)
    try {
      $obj = $text | ConvertFrom-Json -Depth 100
    } catch {
      continue
    }
    if ($obj.method) {
      $session.events.Add($obj) | Out-Null
    }
    $match = & $matcher $obj
    if ($match) { return $obj }
  }
}

function Invoke-Cdp($session, [string]$method, $params = $null, [int]$timeoutMs = 15000) {
  $id = Send-Cdp $session $method $params
  return Receive-Until $session { param($obj) $obj.id -eq $id } $timeoutMs
}

if ($Mode -eq 'list-targets') {
  Get-Target | ConvertTo-Json -Depth 20
  exit 0
}

$target = Get-Target
$session = New-CdpSession $target.webSocketDebuggerUrl

try {
  switch ($Mode) {
    'eval' {
      if (-not $Expression) { throw 'Expression is required for eval mode' }
      $null = Invoke-Cdp $session 'Runtime.enable'
      $res = Invoke-Cdp $session 'Runtime.evaluate' @{ expression = $Expression; returnByValue = $true; awaitPromise = $true }
      $res.result.result.value | ConvertTo-Json -Depth 50
    }
    'navigate' {
      if (-not $NavigateUrl) { throw 'NavigateUrl is required for navigate mode' }
      $null = Invoke-Cdp $session 'Page.enable'
      $null = Invoke-Cdp $session 'Page.navigate' @{ url = $NavigateUrl }
      Start-Sleep -Seconds 2
      $state = Invoke-Cdp $session 'Runtime.evaluate' @{ expression = '({href: location.href, title: document.title})'; returnByValue = $true }
      $state.result.result.value | ConvertTo-Json -Depth 20
    }
  }
}
finally {
  $session.ws.Dispose()
  $session.cts.Dispose()
}
