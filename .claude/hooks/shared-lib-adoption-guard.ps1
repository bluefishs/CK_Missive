# 共用層採用守門 (v1.0.0, 2026-08-30)
# PreToolUse: Write —— 新建的檢核腳本不得自己重造路徑／docker 推導
#
# 為什麼是 PreToolUse 而不是只靠 weekly 93：
#   weekly 93 一週才說一次話。下一個 session 可以連寫十支自造路徑的腳本，
#   而要到下次排程才被告知 —— 那時它已經走遠了，改起來也貴。
#   守門提前到「寫下去的當下」，才是 owner 說的「不要再發生各自創」。
#
# 刻意只擋 Write 不擋 Edit：
#   Edit 動到的是既有檔案，而既有 134 支自造路徑的腳本走 weekly 93 的基線
#   逐步清 —— 在這裡擋它們會讓人連「順手改一行」都做不到（L112 的反面教訓：
#   修一條沒生效的規則時，很容易順手把它放寬／收緊成另一個 bug）。

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch { }

$raw = ""
try { while ($line = [Console]::In.ReadLine()) { $raw += $line } } catch { }
if (-not $raw) { exit 0 }

try { $hook = $raw | ConvertFrom-Json } catch { exit 0 }
if ($hook.tool_name -ne "Write") { exit 0 }

$path = $hook.tool_input.file_path
$content = $hook.tool_input.content
if (-not $path -or -not $content) { exit 0 }

# ⚠️ 用 .Replace() 不用 -replace：後者吃正則，而反斜線在「寫檔的工具鏈」
#    與「PowerShell 的正則」之間要跳脫兩次。實測本檔第一版寫出去只剩一個
#    反斜線 ⇒ `-replace '\', '/'` 直接拋 InvalidRegularExpression，
#    **而 hook 拋例外的退出碼是 0 ⇒ 它整支形同不存在**（擋不了任何東西，
#    也不會有人知道）。[char]92 連反斜線字面都不用寫。
$norm = $path.Replace([char]92, '/')
# 只管檢核腳本 —— 這是共用層 lib/ 服務的範圍
if ($norm -notmatch '/scripts/checks/[^/]+\.py$') { exit 0 }
# lib/ 自己不受此限（它就是被引用的那一層）
if ($norm -match '/scripts/checks/lib/') { exit 0 }
# 覆寫既有檔案不擋（同 Edit 的理由）
if (Test-Path -LiteralPath $path) { exit 0 }

$problems = @()
if ($content -match 'Path\(__file__\)\.resolve\(\)\.parents\[') {
    if ($content -notmatch 'from lib\.paths import|from lib import paths') {
        $problems += "自己算專案根路徑（parents[N]）—— 改用 ``from lib.paths import repo_root``"
    }
}
if ($content -match '"docker"\s*,\s*"exec"' -or $content -match 'docker exec') {
    if ($content -notmatch 'from lib\.docker_exec import|from lib import docker_exec') {
        $problems += "自己拼 docker exec —— 改用 ``from lib.docker_exec import exec_in``"
    }
}

if ($problems.Count -eq 0) { exit 0 }

$msg = @()
$msg += "共用層採用守門：新建的檢核腳本不得自己重造既有能力。"
foreach ($p in $problems) { $msg += "  · $p" }
$msg += ""
$msg += "實測 182 支檢核裡 110 支自算路徑、39 支自開 docker exec，而共用層一直都在，"
$msg += "採用率只有 3.3% —— 不是沒有共用層，是共用層沒有成為預設路徑。"
$msg += "存量走 weekly 93 的基線逐步清；**新建的不放行**。"
$msg += "真有理由自造，請在檔頭寫明理由並改用 Edit 建立（本守門只擋新建的 Write）。"

[Console]::Error.WriteLine(($msg -join "`n"))
exit 2
