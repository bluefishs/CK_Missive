# 主要缺頁（majflt）基準 —— A127 的對照組

`majflt_baseline_20260909.json` 是 2026-09-09 06:0x（**平靜期**，最後一筆核心故障在
04:28:34、當時已安靜 100 分鐘）採的每個行程主要缺頁計數。

## 為什麼要它

A127 剩下的兩個候選變因裡，「同時換頁的行程數」只有在**跟平常比**的時候才有意義。
AaaP 的話：**有基準才知道爆發時的分佈跟平常不一樣在哪**；而「叢發持續時間」只能等下一次
自然爆發（被動），這一支現在就能建立。

## 怎麼再採一次（爆發當下）

```bash
docker run --rm --privileged --pid=host python:3.11-slim python -c "
import os,json
rows=[]
for pid in os.listdir('/proc'):
    if not pid.isdigit(): continue
    try:
        s=open('/proc/%s/stat'%pid).read(); i=s.rindex(')')
        comm=s[s.index('(')+1:i]; rest=s[i+2:].split()
        rows.append((int(rest[9]), int(rest[7]), comm, int(pid)))
    except Exception: pass
rows.sort(reverse=True)
print(json.dumps({'uptime_s':int(float(open('/proc/uptime').read().split()[0])),
  'total_majflt':sum(r[0] for r in rows),'n_proc':len(rows),
  'top':[{'majflt':r[0],'minflt':r[1],'comm':r[2],'pid':r[3]} for r in rows[:18]]},ensure_ascii=False))
"
```

⚠️ **`--pid=host` 不可省**：沒有它只看得到容器自己的 PID 命名空間，數字會是「幾乎沒有缺頁」
而看起來一切正常 —— 那是同一個晚上反覆出現的「量測工具在待測對象上失效」那一類。

## 怎麼讀

比較**兩次之間的差值**而不是絕對值（計數自開機累計）。要看的是：
1. 爆發期是不是**同一批行程**在換，還是換的行程數變多了
2. 有沒有某個行程的 majflt 突然佔掉大部分增量

## 這一份的內容（uptime 31,095s）

337 個行程、majflt 合計 131,357。前幾名：containerd 60,370／prometheus 14,334／
dockerd 8,314／hermes 7,350／grafana 5,017／loki 4,014。

⚠️ 前幾名幾乎都是**觀測棧與容器執行期**本身，不是業務服務 —— 這在爆發時是否改變，
正是這份基準要回答的問題。
