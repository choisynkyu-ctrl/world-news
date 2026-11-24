# GitHub Secrets 한 번에 등록 + 카카오 토큰 발급
# 실행: powershell -ExecutionPolicy Bypass -File scripts\setup_secrets.ps1
param([string]$RestKey)
$ErrorActionPreference = "Stop"
$gh = "C:\Program Files\GitHub CLI\gh.exe"
$RedirectUri = "https://localhost:5000"
$Repo = & $gh repo view --json nameWithOwner -q .nameWithOwner

function Read-Secret($prompt) {
  $s = Read-Host $prompt -AsSecureString
  [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s))
}
function Set-Secret($name, $value) {
  & $gh secret set $name --repo $Repo --body $value | Out-Null
  Write-Host "  [OK] $name 등록" -ForegroundColor Green
}

Write-Host "=== 저장소: $Repo ===" -ForegroundColor Cyan
Write-Host "입력한 값은 화면에 표시되지 않습니다.`n"

# 1) Gemini
$ak = Read-Secret "1) Gemini API 키 (AIza...)"
Set-Secret "GEMINI_API_KEY" $ak

# 2) Kakao 키
$rk = if ($RestKey) { $RestKey } else { Read-Secret "2) 카카오 REST API 키" }
Set-Secret "KAKAO_REST_API_KEY" $rk
$cs = Read-Secret "3) 카카오 클라이언트 시크릿 코드 (REST API 키 수정 화면의 '카카오 로그인' 코드)"
if ($cs) { Set-Secret "KAKAO_CLIENT_SECRET" $cs }

# 3) 카카오 로그인 → refresh token
Write-Host "`n4) 브라우저에서 카카오 로그인 후 '동의하고 계속하기'를 누르세요."
Write-Host "   '사이트에 연결할 수 없음' 페이지가 뜨면 정상입니다. 그 주소창 URL 전체를 복사해 오세요."
Start-Process "https://kauth.kakao.com/oauth/authorize?client_id=$rk&redirect_uri=$([uri]::EscapeDataString($RedirectUri))&response_type=code&scope=talk_message"
$url = Read-Host "   복사한 URL 붙여넣기"
if ($url -notmatch "[?&]code=([^&]+)") { throw "URL에서 code를 찾지 못했습니다." }
$body = @{ grant_type = "authorization_code"; client_id = $rk; redirect_uri = $RedirectUri; code = $Matches[1] }
if ($cs) { $body.client_secret = $cs }
$tok = Invoke-RestMethod -Method Post -Uri "https://kauth.kakao.com/oauth/token" -Body $body
Set-Secret "KAKAO_REFRESH_TOKEN" $tok.refresh_token

$tpl = '{"object_type":"text","text":"News digest setup OK","link":{"web_url":"https://developers.kakao.com","mobile_web_url":"https://developers.kakao.com"}}'
Invoke-RestMethod -Method Post -Uri "https://kapi.kakao.com/v2/api/talk/memo/default/send" `
  -Headers @{ Authorization = "Bearer $($tok.access_token)" } -Body @{ template_object = $tpl } | Out-Null
Write-Host "  [OK] 카카오톡 '나와의 채팅'으로 테스트 메시지 전송" -ForegroundColor Green

# 4) 카카오 토큰 자동 갱신용 GH_PAT
Write-Host "`n5) 카카오 토큰은 2개월마다 만료됩니다. 자동 갱신하려면 GitHub 토큰을 GH_PAT로 저장해야 합니다."
Write-Host "   (현재 gh 로그인 토큰을 사용합니다. 이 저장소의 워크플로만 읽을 수 있습니다.)"
$yn = Read-Host "   자동 갱신을 켤까요? (Y/n)"
if ($yn -ne "n") { Set-Secret "GH_PAT" (& $gh auth token) }

Write-Host "`n완료! 이 창을 닫고 Claude에게 '끝났어'라고 알려주세요." -ForegroundColor Cyan
