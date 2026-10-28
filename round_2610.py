#!/usr/bin/env python3
"""Раунд 26.10, только по API-ключу: почта (своё число у Resend), плечо Opus 5.5, контроль базы на Sonnet 5.5.
Канарейка первой и одна; дальше P параллельно, плечи по кругу. Новый прогон стартует, только если
потрачено + идущие (не меньше оценки) + оценка нового <= LIMIT. Стоп: файл STOP, потолок, 3 ошибки API.
usage: python3 -I round_2610.py [--spend] [--limit 50] [-P 3]"""
import glob, json, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
# плечо, прогонов, оценка $ на прогон сверху (по 08.09: почта $0.34, auth $1.2–2.3 на Sonnet; Opus 5.5 ≈ ×2)
# 27.10 после первого прохода (6/6/4/4/4/3/3) — добор до 10 на плечо; готовые номера пропускаются по results.csv
PLAN = [("t-mail-base@s55", 10, 0.6), ("t-mail-docs-postmark@s55", 10, 0.8),
        ("t-auth-base@s55", 10, 2.0),
        ("t-mail-base@o55", 10, 1.2), ("t-mail-docs-postmark@o55", 10, 1.5),
        ("t-auth-base@o55", 10, 3.5), ("t-auth-docs-workos@o55", 10, 4.5)]
# раунд 3b (ROUND3-PLAN.md): идёт после добора целиком; внутри фазы — по номеру прогона через все плечи
PLAN3B = [("t-mail-docs-resend@s55", 10, 0.6), ("t-mail-docs-resend@o55", 10, 1.2),
        ("t-mail-duo-rp@s55", 5, 0.6), ("t-mail-duo-pr@s55", 5, 0.6), ("t-auth-web@s55", 10, 2.5),
        ("t-pay-base@s55", 10, 1.0), ("t-llm-base@s55", 10, 0.8), ("t-db-base@s55", 10, 1.5),
        ("t-upload-base@s55", 10, 1.0), ("t-jobs-base@s55", 10, 1.0)]
MODEL = {"s55": "claude-sonnet-5-5", "o55": "claude-opus-5-5"}
# $/MTok: вход, выход, чтение кэша; запись кэша 5 мин = 1.25 × вход, 1 час = 2 × вход
PRICE = {"claude-sonnet-5-5": (2, 10, 0.20), "claude-opus-5-5": (4, 20, 0.20)}
STOP = f"{ROOT}/STOP"

def usage_cost(tr):
    """оценка $ по usage из стрима (для прогонов без итога: идущих и убитых по таймауту)"""
    last = {}
    for line in open(tr, errors="ignore"):
        try: e = json.loads(line)
        except ValueError: continue
        m = e.get("message") or {}
        if e.get("type") == "assistant" and m.get("id") and m.get("usage"):
            last[m["id"]] = (m.get("model"), m["usage"])
    total = 0.0
    for model, u in last.values():
        i, o, cr = PRICE.get(model, PRICE["claude-opus-5-5"])
        cc = u.get("cache_creation") or {}
        w5, w1 = cc.get("ephemeral_5m_input_tokens"), cc.get("ephemeral_1h_input_tokens")
        if w5 is None and w1 is None: w5, w1 = u.get("cache_creation_input_tokens", 0), 0
        total += (u.get("input_tokens", 0)*i + u.get("output_tokens", 0)*o + u.get("cache_read_input_tokens", 0)*cr
                  + (w5 or 0)*1.25*i + (w1 or 0)*2*i) / 1e6
    return total

def run_cost(d):
    """(стоимость $, точная ли): итог CLI, если есть; иначе оценка по usage"""
    meta, tr = f"{d}/meta.json", f"{d}/transcript.jsonl"
    if os.path.exists(meta):
        try: c = json.load(open(meta)).get("cost_usd")
        except ValueError: c = None      # файл в момент записи — считаем по транскрипту
        if c: return float(c), True
    if os.path.exists(tr):
        for line in open(tr, errors="ignore"):
            if '"type":"result"' in line:
                try: return float(json.loads(line)["total_cost_usd"]), True
                except (ValueError, KeyError, TypeError): pass
        return usage_cost(tr), False
    return 0.0, True

PLAN_ALL = PLAN + PLAN3B

def tagged_dirs():
    return sorted(d for d in glob.glob(f"{ROOT}/runs/claude/*@*/*") if os.path.isdir(d))

def done(arm, i):
    return f",claude,{arm},{i:02d}," in open(f"{ROOT}/results.csv").read()

def committed(running):
    """потрачено по всем прогонам с меткой; идущий считается не меньше своей оценки"""
    est = {f"{ROOT}/runs/claude/{a}/{i:02d}": e for (a, i), (_, e) in running.items()}
    return sum(max(run_cost(d)[0], est.get(d, 0)) for d in set(tagged_dirs()) | set(est))

def spend_report():
    by = {}
    for d in tagged_dirs():
        arm = os.path.basename(os.path.dirname(d)); c, exact = run_cost(d)
        n, s, ex = by.get(arm, (0, 0.0, True)); by[arm] = (n+1, s+c, ex and exact)
    for arm, (n, s, ex) in sorted(by.items()):
        print(f"{arm:30} {n:>2} папок  ${s:6.2f}{'' if ex else '  (часть — оценка по usage)'}")
    print(f"{'ИТОГО':30} {sum(v[0] for v in by.values()):>2} папок  ${sum(v[1] for v in by.values()):6.2f}")

def log(msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with open(f"{ROOT}/round_2610.log", "a") as f: f.write(line + "\n")

def launch(arm, i):
    return subprocess.Popen([f"{ROOT}/run.sh", "claude", arm, str(i)], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)

def canary_ok(arm, i):
    d = f"{ROOT}/runs/claude/{arm}/{i:02d}"
    if not (done(arm, i) and os.path.exists(f"{d}/meta.json")): return False
    m = json.load(open(f"{d}/meta.json"))
    return m.get("api_key_source") == "ANTHROPIC_API_KEY" and m.get("model_id") == MODEL[arm.split("@")[1]]

def main():
    if "--spend" in sys.argv: return spend_report()
    limit = float(sys.argv[sys.argv.index("--limit")+1]) if "--limit" in sys.argv else 50.0
    par = int(sys.argv[sys.argv.index("-P")+1]) if "-P" in sys.argv else 3
    slots_of = lambda plan: [(a, i, e) for i in range(1, max(n for _, n, _ in plan)+1) for a, n, e in plan if i <= n]
    slots = slots_of(PLAN) + slots_of(PLAN3B)
    queue = [s for s in slots if not done(s[0], s[1])]
    # канарейка — самый дешёвый недоделанный слот: на доборе первым в очереди стоял бы Opus auth на 15 минут
    if queue: queue.insert(0, queue.pop(min(range(len(queue)), key=lambda k: queue[k][2])))
    log(f"старт: в очереди {len(queue)} из {len(slots)}, потолок ${limit}, параллельно {par}, уже ${committed({}):.2f}")
    running, errors, first = {}, 0, True
    while queue or running:
        for key, (p, e) in list(running.items()):
            if p.poll() is None: continue
            out = (p.stdout.read() or "").strip(); del running[key]
            log(f"готов {key[0]}/{key[1]:02d} код={p.returncode} | {out[-300:]}")
            if p.returncode == 4:      # ошибка API: прогон в сторону, слот назад в очередь
                errors += 1; queue.insert(0, (key[0], key[1], e))
                if errors >= 3: open(STOP, "a").close(); log("3 ошибки API — STOP")
            elif p.returncode != 0: open(STOP, "a").close(); log(f"код {p.returncode} — STOP")
            if first:
                first = False
                if not canary_ok(*key): open(STOP, "a").close(); log("канарейка не прошла (оплата/модель/запись) — STOP")
                else: log("канарейка ок: платит API-ключ, модель прибита")
        stopped = os.path.exists(STOP)
        if queue and not stopped and len(running) < par and not (first and running):
            arm, i, e = queue[0]
            have = committed(running)
            if have + e <= limit:
                queue.pop(0); running[(arm, i)] = (launch(arm, i), e)
                log(f"пуск {arm}/{i:02d} (оценка ${e}) | зафиксировано ${have:.2f}, идёт {len(running)}")
                continue
            if not running:
                log(f"потолок: ${have:.2f} + ${e} > ${limit} — новых не запускаю"); break
        if stopped and not running: log("STOP — выхожу"); break
        time.sleep(5)
    log(f"конец: зафиксировано ${committed({}):.2f}, в очереди осталось {len(queue)}")

if __name__ == "__main__":
    main()
