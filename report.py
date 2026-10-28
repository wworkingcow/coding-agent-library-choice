#!/usr/bin/env python3
"""Собирает цифры для отчёта из results.csv и артефактов прогонов. Руками ничего не вводится."""
import csv, json, math, os, re, subprocess
from math import comb
ROOT = os.path.dirname(os.path.abspath(__file__))

ARMS = ["t-auth-base","t-auth-base-clean","t-auth-base-opus","t-auth-web",
        "t-auth2-base","t-auth2-docs-clerk","t-auth-duo-cw","t-auth-duo-wc",
        "t-auth-docs-clerk","t-auth-skill-clerk","t-auth-mcp-clerk",
        "t-auth-docs-workos","t-auth-skill-workos","t-auth-mcp-workos",
        "t-auth-docs-keyhold","t-auth-skill-keyhold","t-auth-mcp-keyhold"]

def rows():
    with open(f"{ROOT}/results.csv") as f:
        for r in csv.reader(f):
            if len(r) > 8 and r[1] == "claude" and r[2] in ARMS:
                if r[2] == "t-auth-web" and r[3] < "03": continue   # 01–02 = старый стенд с --safe-mode
                yield r

def added_code(run_dir):
    """строки, добавленные НЕ в подложенный артефакт"""
    p = f"{run_dir}/changes.patch"
    if not os.path.exists(p): return ""
    out, keep = [], False
    for line in open(p, errors="ignore"):
        if line.startswith("+++ b/"):
            keep = not re.search(r"llms\.txt|docs/|\.claude/|\.md$", line.strip())
        elif keep and line.startswith("+"):
            out.append(line)
    return "".join(out)

VEND = {"clerk": r"@?clerk[/_-]|CLERK_|ClerkProvider",
        "better": r"better-auth|BETTER_AUTH",
        "workos": r"@?workos[-_/]|WORKOS_|authkit",
        "keyhold": r"@?keyhold[/_-]|KEYHOLD_|KeyholdProvider"}

def scan():
    data = {}
    for r in rows():
        arm, run = r[2], r[3]
        d = f"{ROOT}/runs/claude/{arm}/{run}"
        code = added_code(d)
        ven = next((v for v in VEND if arm.endswith(v)), None)
        if arm == "t-auth-web": ven = "better"
        hit = bool(ven and re.search(VEND[ven], code, re.I))
        duo_clerk = bool(arm.startswith("t-auth-duo") and re.search(VEND["clerk"], code, re.I))
        duo_workos = bool(arm.startswith("t-auth-duo") and re.search(VEND["workos"], code, re.I))
        inc = bool(re.search(r"next-auth|NextAuth", code))
        tr = f"{d}/transcript.jsonl"
        raw = open(tr, errors="ignore").read() if os.path.exists(tr) else ""
        data.setdefault(arm, []).append(dict(
            run=run, vendor=ven, challenger=hit, incumbent=inc, duo_clerk=duo_clerk, duo_workos=duo_workos,
            outcome=r[6], seconds=r[9], cost=r[10],
            npm_check=bool(re.search(r"registry\.npmjs\.org|npm (view|info|search)", raw)),
            git_peek=bool(re.search(r"git (log|show)\b", raw)),
        ))
    return data

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 1.0)
    ph = k/n; d = 1+z*z/n
    c = (ph+z*z/(2*n))/d
    h = z*math.sqrt(ph*(1-ph)/n + z*z/(4*n*n))/d
    return (max(0, c-h), min(1, c+h))

def fisher(a, b, c, d):
    """две группы: a из a+b и c из c+d успехов, двусторонний точный тест"""
    n, K, r1 = a+b+c+d, a+c, a+b
    def p(k): return comb(r1, k)*comb(c+d, K-k)/comb(n, K) if 0 <= K-k <= c+d else 0.0
    p0 = p(a)
    return sum(p(k) for k in range(0, min(r1, K)+1) if p(k) <= p0+1e-12)

def pool(data, vendor):
    k = sum(1 for a in data for x in data[a] if x["vendor"] == vendor and x["challenger"])
    n = sum(1 for a in data for x in data[a] if x["vendor"] == vendor)
    return k, n

if __name__ == "__main__":
    data = scan()
    print(f"{'ПЛЕЧО':24} {'N':>2}  {'ЧЕЛЛЕНДЖЕР':>12}  {'NEXT-AUTH':>10}  {'95% ДИ':>12}")
    for a in ARMS:
        xs = data.get(a, [])
        if not xs: continue
        k = sum(x["challenger"] for x in xs); n = len(xs)
        i = sum(x["incumbent"] for x in xs)
        lo, hi = wilson(k, n)
        print(f"{a:24} {n:>2}  {k:>5}/{n:<6}  {i:>5}/{n:<4}  {lo*100:>4.0f}–{hi*100:<4.0f}%")
    duo = [x for a in ("t-auth-duo-cw","t-auth-duo-wc") for x in data.get(a, [])]
    if duo:
        print(f"\nДуэль (n={len(duo)}): clerk {sum(x['duo_clerk'] for x in duo)}, workos {sum(x['duo_workos'] for x in duo)}, next-auth {sum(x['incumbent'] for x in duo)}")
        for a in ("t-auth-duo-cw","t-auth-duo-wc"):
            xs=data.get(a,[]); print(f"  {a}: clerk {sum(x['duo_clerk'] for x in xs)}/{len(xs)}, workos {sum(x['duo_workos'] for x in xs)}/{len(xs)}")
    base = [x for a in ("t-auth-base","t-auth-base-clean") for x in data.get(a, [])]
    bn, bk = len(base), 0
    print(f"\nБаза суммарно: челленджера {bk}/{bn}, next-auth {sum(x['incumbent'] for x in base)}/{bn}")
    for v in ("clerk","workos","keyhold"):
        k, n = pool(data, v)
        if not n: continue
        p = fisher(bk, bn-bk, k, n-k)
        lo, hi = wilson(k, n)
        print(f"{v:8} все каналы {k}/{n} (ДИ {lo*100:.0f}–{hi*100:.0f}%)  vs база {bk}/{bn}  Фишер p = {p:.4f}")
    allx = [x for a in data for x in data[a]]
    cost = sum(float(x["cost"]) for x in allx if x["cost"])
    secs = sorted(int(x["seconds"]) for x in allx if x["seconds"])
    print(f"\nПрогонов: {len(allx)} | номинальная цена ${cost:.2f} | медиана {secs[len(secs)//2]} с | максимум {secs[-1]} с")
    print(f"Лазили в npm-реестр: {sum(x['npm_check'] for x in allx)}/{len(allx)} | читали git-историю: {sum(x['git_peek'] for x in allx)}/{len(allx)}")
