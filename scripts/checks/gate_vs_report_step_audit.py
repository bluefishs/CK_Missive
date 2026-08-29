#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""weekly 的每一步都必須能紅，否則要在步驟名裡講明它只是報告。

## 為什麼有這一支

2026-08-29 同日連續兩次踩到同一個形狀 **「檢查做了、記錄了，但不影響判定」**：

  · `/api/health/detailed` 六項檢查**只有兩項會改頂層 status**，
    AI 服務整個 exception 而訊息字面上寫著「All systems operational」
  · CK_AaaP 同日回報他們的 `all_healthy: True` 是寫死的初始值

⇒ 一般化的問題是：**weekly 的 88 個步驟裡，有沒有哪一步永遠不可能紅？**

實查：193 支檢核腳本中 20 支沒有任何非 0 退出路徑，
而其中**只有 1 支**（`facade_adoption_audit`）被 runner 當成 `run_step`。
它的檔頭明文寫著「informational only — 不入 strict fail」⇒ **那是有意的設計**。

**問題不在腳本，在顯示**：它的綠燈與其他 87 個真守門長得一模一樣，
讀輸出的人會合理地以為「這件事被檢查了而且沒問題」。
⇒ 修法是把它標成「（僅報告·不判紅）」，而不是逼它去紅。

## ⚠️ 判準的窄度是這支的全部價值

我的第一版判準是**掃檔頭有沒有 informational／不判紅／never fails 等字樣**，
命中 7 支 —— **其中 6 支是誤報**。那些字樣出現在「存量列 baseline 不判紅」
這類**局部豁免的散文**裡，而腳本整體是會紅的（step 61 與 64 在同日的
weekly 裡確實是紅的）。

⇒ 判準改為**看程式碼有沒有非 0 退出路徑**，不看它怎麼描述自己。
這與本 repo 反覆記過的「判準命中的是散文不是程式碼」是同一件事。

## 判準

對 `run_fitness_weekly.sh` 的每一個 `run_step`：

  RED  腳本**沒有任何非 0 退出路徑**（＝永遠不可能紅），
       而步驟名裡**沒有**標明它只是報告
  ok   能紅的步驟；或已標明「僅報告」的步驟

⚠️ 剝掉註解再判：`# return 1` 不算一條退出路徑。

## 誰跑它

weekly step 89（`run_fitness_weekly.sh`）。
"""
import ast
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "checks" / "run_fitness_weekly.sh"

#: 步驟名裡出現任一個就視為已標明「這只是報告」
_MARKED = re.compile(r"僅報告|不判紅|informational|report[- ]only", re.I)

#: shell 用的非 0 退出（Python 那邊改走 AST，見 `_py_can_fail`）
_SH_NONZERO = re.compile(r"\bexit\s+[1-9]")

_STEP = re.compile(r'run_step\s+"(\d+)"\s+"([^"]*)"\s+"([^"]+)"')


def _py_can_fail(text: str):
    """Python 檔：用 **AST** 判斷有沒有非 0 退出路徑。

    ⚠️ 2026-08-29 改用 AST（首版是手寫剝除註解＋正則）。五個案例實測，
    手寫版**誤判 1/5**：

        print("如果失敗請 return 1")     ← 被算成一條退出路徑

    一般字串裡的 `return 1` 剝不掉 —— 剝得掉的只有註解與 docstring。
    本 repo 當日已為同一件事把前端判準改用 TypeScript parser。

    CK_AaaP 同日的說法更準：**字串比對的預設誤用率就是高的**，
    一天用幾十次就一定有幾次落在散文上
    ⇒ **預設用 AST，讓字串比對成為需要理由的選項。**

    回傳 None＝語法錯誤（無法判定；呼叫端當成比「不會紅」更嚴重）。
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None

    #: 模組層定義的函式 —— 供 `sys.exit(main())` 追進去看它的 return
    _local_funcs = {
        n.name: n for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    def _nonzero_int(node) -> bool:
        return (isinstance(node, ast.Constant) and isinstance(node.value, int)
                and not isinstance(node.value, bool) and node.value != 0)

    def _may_be_nonzero(node) -> bool:
        """這個運算式**有沒有可能**是非 0。

        ⚠️ 2026-08-29：首版只認 `ast.Constant`，於是**漏判 5 支真守門**：

            return 1 if ci else 0     ← ast.IfExp，不是 Constant
            sys.exit(main())          ← 引數是 Call，不是 Constant

        那 5 支被報成「永遠不可能紅」—— **相反方向的錯誤，而且更糟**：
        它會叫人把真守門標成「僅報告」。
        ⇒ 判準變嚴格之後，要驗它**新增的命中**是真的，
          不能因為它更嚴格就相信它。

        **保守原則**：算不出來的一律當成「可能非 0」。
        漏報（把真守門標成報告）比誤報（多問一句）嚴重得多。
        """
        if node is None:
            return False
        if _nonzero_int(node):
            return True
        if isinstance(node, ast.IfExp):               # a if cond else b
            return _may_be_nonzero(node.body) or _may_be_nonzero(node.orelse)
        if isinstance(node, ast.BoolOp):              # a or b / a and b
            return any(_may_be_nonzero(v) for v in node.values)
        if isinstance(node, ast.Constant):            # 明確的 0 / None / 字串
            return False
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            # ⚠️ `sys.exit(main())` —— 幾乎每支腳本都這樣結尾。
            # 把它當成不透明的 Call 而「保守視為可能非 0」，會讓本檢核的
            # **偵測力歸零**（實測：連唯一的真實案例 step 12 都不再被抓到）。
            # ⇒ 追進那個函式，看它自己的 return —— **那才是退出碼的來源**。
            #
            # 這是本日第二次修正同一個判準：先漏判（只認 Constant），
            # 再過度保守（把 Call 一律當成可能非 0）。
            # **兩次都不是「更嚴格／更寬鬆」的問題，是判準沒有對準對象。**
            fn = _local_funcs.get(node.func.id)
            if fn is not None:
                return any(_may_be_nonzero(r.value)
                           for r in ast.walk(fn) if isinstance(r, ast.Return))
        # 其餘（屬性呼叫／BinOp／Subscript…）值要執行才知道，保守視為可能非 0
        return True

    # ⚠️ 2026-08-29 第三次修正這個判準，而這次改的是**對象**不是鬆緊。
    #
    # 首版：掃「檔案裡任何一個 `return 非0`」。那是錯的 ——
    # `count_importers` 的 `return len(files)` 是**輔助函式的回傳值**，
    # 與退出碼無關，卻讓 `facade_adoption_audit` 被判成「會紅」。
    #
    # **決定退出碼的只有 `sys.exit()` 與 `raise SystemExit()`。**
    # 一支從不呼叫它們的腳本，退出碼永遠是 0，不管內部 return 什麼。
    # ⇒ 只看這兩者（並在引數是本地函式時追進去看它的 return）。
    #
    # 三次修正：漏判（只認 Constant）→ 過度保守（Call 一律算可能非 0）
    # → **對錯了對象**（掃所有 return）。前兩次我以為問題在鬆緊，
    # 而真正的問題是**我沒有先問「退出碼是從哪裡來的」**。
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            name = f.attr if isinstance(f, ast.Attribute) else (
                f.id if isinstance(f, ast.Name) else "")
            if name in ("exit", "_exit", "SystemExit"):
                if any(_may_be_nonzero(a) for a in node.args):
                    return True
        # `raise SystemExit(<運算式>)` —— 值可能是函式回傳，保守視為可失敗
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            f = node.exc.func
            if ((isinstance(f, ast.Name) and f.id == "SystemExit")
                    or (isinstance(f, ast.Attribute) and f.attr == "SystemExit")):
                return True
    return False


def _sh_can_fail(text: str) -> bool:
    """Shell 檔：沒有標準 parser，仍用文字比對但先剝註解。

    ⚠️ 這一半**明知較弱**，寫出來以免有人以為整支都用 AST。
    shell 的 `exit 1` 幾乎不會出現在字串裡，誤判風險遠低於 Python。
    """
    code = "\n".join(ln.split("#", 1)[0] for ln in text.splitlines())
    return bool(_SH_NONZERO.search(code))


def main() -> int:
    if not RUNNER.is_file():
        print(f"✗ 找不到 {RUNNER} —— 無法判定（不視為通過）")
        return 2

    steps = _STEP.findall(RUNNER.read_text(encoding="utf-8", errors="replace"))
    if not steps:
        print("✗ 解析不到任何 run_step —— 判定不可信，不視為通過")
        return 2

    reds, marked, missing, broken = [], [], [], []
    for no, label, path in steps:
        script = ROOT / path.split()[0]
        if not script.is_file():
            missing.append((no, label, path))
            continue
        raw = script.read_text(encoding="utf-8", errors="replace")
        if script.suffix == ".py":
            verdict = _py_can_fail(raw)
            if verdict is None:
                # 語法錯比「不會紅」嚴重 —— 它根本跑不起來（同 L99）
                broken.append((no, label, script.name))
                continue
            can_fail = verdict
        else:
            can_fail = _sh_can_fail(raw)
        is_marked = bool(_MARKED.search(label))
        if can_fail:
            continue
        (marked if is_marked else reds).append((no, label, script.name))

    print(f"weekly 共 {len(steps)} 步｜永遠不可能紅但**已標明**的 {len(marked)} 步")
    for no, label, name in marked:
        print(f"    step {no}: {label}  ({name})")

    if broken:
        print(f"\n✗ {len(broken)} 步的腳本**有語法錯誤**（比不會紅嚴重：它跑不起來）")
        for no, label, name in broken:
            print(f"    step {no}: {label}  ({name})")
        return 2

    if missing:
        print(f"\n✗ {len(missing)} 步的腳本檔不存在：")
        for no, label, path in missing:
            print(f"    step {no}: {label} → {path}")
        return 2

    if not reds:
        print("✓ 每一步不是能紅、就是已標明只是報告")
        return 0

    print(f"\n✗ {len(reds)} 步**永遠不可能紅，而步驟名沒有說**")
    for no, label, name in reds:
        print(f"    step {no}: {label}  ({name})")
    print("\n  它的綠燈與真守門長得一樣，讀輸出的人會以為這件事被檢查過了。")
    print("  二選一：讓它在該紅的時候回非 0，或在步驟名加「（僅報告·不判紅）」。")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
