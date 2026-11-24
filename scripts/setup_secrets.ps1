# GitHub Secrets 한 번에 등록 + 카카오 토큰 발급
# 실행: powershell -ExecutionPolicy Bypass -File scripts\setup_secrets.ps1 -RestKey <REST API 키>
param([string]$RestKey)
$ErrorActionPreference = "Stop"
$gh = "C:\Program Files\GitHub CLI\gh.exe"
$RedirectUri = "https://localhost:5000"
$Repo = & $gh repo view --json nameWithOwner -q .nameWithOwner
$Existing = (& $gh secret list --repo $Repo) | ForEach-Object { ($_ -split "\s+")[0] }

function Read-Secret($prompt) {
  $s = Read-Host $prompt -AsSecureString
  ([Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s))).Trim()
}
function Set-Secret($name, $value) {
  & $gh secret set $name --repo $Repo --body $value | Out-Null
  Write-Host "  [OK] $name 등록" -ForegroundColor Green
}
function Already($name) {
  if ($Existing -contains $name) {
    $a = Read-Host "  $name 은(는) 이미 등록돼 있습니다. 다시 입력할까요? (y/N)"
    return ($a -ne "y")
  }
  return $false
}
function Invoke-Kakao($uri, $body, $headers = @{}) {
  try { return Invoke-RestMethod -Method Post -Uri $uri -Body $body -Headers $headers }
  catch {
    $msg = ""
    if ($_.Exception.Response) {
      $msg = (New-Object IO.StreamReader($_.Exception.Response.GetResponseStream())).ReadToEnd()
    }
    Write-Host "`n카카오 오류: $msg" -ForegroundColor Red
    if ($msg -match "KOE010|invalid_client") {
      Write-Host "→ 클라이언트 시크릿 코드가 틀렸습니다. 'REST API 키 수정' 화면의 '카카오 로그인' 줄 코드(비즈니스 인증 줄 아님)를 다시 복사해 이 스크립트를 다시 실행하세요." -ForegroundColor Yellow
    } elseif ($msg -match "KOE320|invalid_grant") {
      Write-Host "→ 로그인 코드가 만료됐거나 이미 사용됐습니다. 스크립트를 다시 실행해 로그인부터 다시 하세요." -ForegroundColor Yellow
    } elseif ($msg -match "KOE006|redirect") {
      Write-Host "→ Redirect URI 설정 문제입니다. Claude에게 알려주세요." -ForegroundColor Yellow
    }
    exit 1
  }
}

Write-Host "=== 저장소: $Repo ===" -ForegroundColor Cyan
Write-Host "입력한 값은 화면에 표시되지 않습니다. 붙여넣고 Enter만 누르면 됩니다.`n"

# 1) Gemini
if (-not (Already "GEMINI_API_KEY")) {
  Set-Secret "GEMINI_API_KEY" (Read-Secret "1) Gemini API 키")
}

# 2) Kakao 키
$rk = if ($RestKey) { $RestKey } else { Read-Secret "2) 카카오 REST API 키" }
if ($Existing -notcontains "KAKAO_REST_API_KEY" -or $RestKey) { Set-Secret "KAKAO_REST_API_KEY" $rk }

# 3) 클라이언트 시크릿 (토큰 발급에 바로 쓰므로 항상 입력)
$cs = Read-Secret "3) 카카오 클라이언트 시크릿 코드 (REST API 키 수정 화면 > 클라이언트 시크릿 > '카카오 로그인' 줄)"

# 4) 카카오 로그인 → refresh token
Write-Host "`n4) 브라우저에서 카카오 로그인 후 '동의하고 계속하기'를 누르세요."
Write-Host "   '사이트에 연결할 수 없음' 페이지가 뜨면 정상입니다. 그 주소창 URL 전체를 복사해 오세요."
Start-Process "https://kauth.kakao.com/oauth/authorize?client_id=$rk&redirect_uri=$([uri]::EscapeDataString($RedirectUri))&response_type=code&scope=talk_message&prompt=login"
$url = (Read-Host "   복사한 URL 붙여넣기").Trim()
if ($url -notmatch "[?&]code=([^&]+)") { Write-Host "URL에서 code를 찾지 못했습니다." -ForegroundColor Red; exit 1 }
$body = @{ grant_type = "authorization_code"; client_id = $rk; redirect_uri = $RedirectUri; code = $Matches[1] }
if ($cs) { $body.client_secret = $cs }
$tok = Invoke-Kakao "https://kauth.kakao.com/oauth/token" $body

# 토큰이 성공했으니 시크릿도 확정 등록
if ($cs) { Set-Secret "KAKAO_CLIENT_SECRET" $cs }
Set-Secret "KAKAO_REFRESH_TOKEN" $tok.refresh_token

$tpl = '{"object_type":"text","text":"News digest setup OK","link":{"web_url":"https://developers.kakao.com","mobile_web_url":"https://developers.kakao.com"}}'
Invoke-Kakao "https://kapi.kakao.com/v2/api/talk/memo/default/send" @{ template_object = $tpl } @{ Authorization = "Bearer $($tok.access_token)" } | Out-Null
Write-Host "  [OK] 카카오톡 '나와의 채팅'으로 테스트 메시지 전송" -ForegroundColor Green

# 5) 카카오 토큰 자동 갱신용 GH_PAT
Write-Host "`n5) 카카오 토큰은 2개월마다 만료됩니다. 자동 갱신하려면 GitHub 토큰을 GH_PAT로 저장해야 합니다."
Write-Host "   (현재 gh 로그인 토큰을 사용합니다. 이 토큰은 다른 저장소에도 접근 권한이 있습니다.)"
$yn = Read-Host "   자동 갱신을 켤까요? (Y/n)"
if ($yn -ne "n") { Set-Secret "GH_PAT" (& $gh auth token) }

Write-Host "`n완료! Claude에게 '끝났어'라고 알려주세요." -ForegroundColor Cyan
