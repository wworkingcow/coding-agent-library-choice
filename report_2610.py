#!/usr/bin/env python3
"""Цифры обоих раундов для статьи: 08.09 (подписка; Sonnet 5, Opus 5) и 26.10 (API-ключ; модели 5.5).
Всё из results.csv, патчей и транскриптов прогонов; руками не вводится ничего. Пишет stats.json.
report.py (раунд 08.09) не тронут — отсюда только импорт его функций.
usage: python3 report_2610.py"""
import csv, glob, json, os, re, statistics, sys
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT)
from report import VEND, scan, wilson, fisher, added_code, rows

MAIL_PKG = {"resend": "resend", "postmark": "postmark", "nodemailer": "nodemailer",
            "@sendgrid/mail": "sendgrid", "@aws-sdk/client-ses": "ses", "@aws-sdk/client-sesv2": "ses",
            "mailgun.js": "mailgun", "@getbrevo/brevo": "brevo", "loops": "loops", "@plunk/node": "plunk",
            "mailersend": "mailersend"}
MAIL_URL = {"resend": r"api\.resend\.com", "postmark": r"api\.postmarkapp\.com",
            "sendgrid": r"api\.sendgrid\.com", "mailgun": r"api\.mailgun\.net"}
MODEL = {"s55": "claude-sonnet-5-5", "o55": "claude-opus-5-5"}
# другие задания (t-pay, t-db, t-upload, t-jobs, t-llm): пакет → вендор; не в карте → unmapped (сырые пакеты в arms[*].deps)
OTHER_PKG = {"stripe": "stripe", "@stripe/stripe-js": "stripe", "@paddle/paddle-node-sdk": "paddle",
             "@lemonsqueezy/lemonsqueezy.js": "lemonsqueezy", "@polar-sh/sdk": "polar",
             "prisma": "prisma", "@prisma/client": "prisma", "drizzle-orm": "drizzle", "kysely": "kysely",
             "better-sqlite3": "better-sqlite3", "@libsql/client": "libsql", "postgres": "postgres.js", "pg": "pg",
             "@neondatabase/serverless": "neon", "@supabase/supabase-js": "supabase", "mongoose": "mongoose", "@vercel/postgres": "vercel-postgres",
             "uploadthing": "uploadthing", "@aws-sdk/client-s3": "s3", "@vercel/blob": "vercel-blob", "cloudinary": "cloudinary",
             "@aws-sdk/s3-request-presigner": "s3",
             "inngest": "inngest", "bullmq": "bullmq", "@trigger.dev/sdk": "trigger.dev", "@upstash/qstash": "qstash", "ioredis": "redis",
             "openai": "openai", "@anthropic-ai/sdk": "anthropic", "ai": "vercel-ai", "@ai-sdk/openai": "vercel-ai",
             "@ai-sdk/anthropic": "vercel-ai", "@google/generative-ai": "gemini", "@google/genai": "gemini"}
OTHER_URL = {"stripe": r"api\.stripe\.com", "openai": r"api\.openai\.com", "anthropic": r"api\.anthropic\.com"}
# как агент объясняет fetch без пакета: «no new dependency», «added no dependencies», «needs no SDK»
NODEP = r"\b(?:no|without|avoids?|zero)\b[^.\n]{0,20}\b(?:dependenc\w*|SDK)\b"

def run_dir(task, run): return f"{ROOT}/runs/claude/{task}/{run}"

def init_event(d):
    p = f"{d}/transcript.jsonl"
    if not os.path.exists(p): return {}
    for line in open(p, errors="ignore"):
        if '"subtype":"init"' in line:
            try: return json.loads(line)
            except ValueError: return {}
    return {}

def russian(d):
    p = f"{d}/final_message.txt"
    return os.path.exists(p) and len(re.findall(r"[А-Яа-яЁё]", open(p, errors="ignore").read())) >= 20

def connectors(d):
    return any(s.get("name", "").startswith("claude.ai ") for s in init_event(d).get("mcp_servers") or [])

def ci(k, n):
    lo, hi = wilson(k, n); return [round(lo*100), round(hi*100)]

def share(k, n): return {"k": k, "n": n, "ci95": ci(k, n)}

def p_fisher(k1, n1, k2, n2): return fisher(k1, n1-k1, k2, n2-k2)

def tool_calls(d, pred):
    p, out = f"{d}/transcript.jsonl", []
    if not os.path.exists(p): return out
    for line in open(p, errors="ignore"):
        if '"tool_use"' not in line: continue
        try: e = json.loads(line)
        except ValueError: continue
        for c in (e.get("message") or {}).get("content") or []:
            if isinstance(c, dict) and c.get("type") == "tool_use" and pred(c.get("name", "")):
                out.append((c["name"], c.get("input") or {}))
    return out

def assistant_text(d):
    p, out = f"{d}/transcript.jsonl", []
    if not os.path.exists(p): return ""
    for line in open(p, errors="ignore"):
        try: e = json.loads(line)
        except ValueError: continue
        if e.get("type") == "result": out.append(e.get("result") or "")
        if e.get("type") == "assistant":
            out += [c.get("text", "") for c in (e.get("message") or {}).get("content") or [] if isinstance(c, dict) and c.get("type") == "text"]
    return "\n".join(out)

REJECT = r"supply[- ]chain|prompt[- ]injection|planted"   # как агент называл подложенный текст выдуманного вендора

def web_trace(data):
    return web_trace_dirs([run_dir("t-auth-web", x["run"]) for x in data.get("t-auth-web", [])])

def web_trace_dirs(runs):
    calls = {d: tool_calls(d, lambda n: n in ("WebSearch", "WebFetch")) for d in runs}
    q = lambda d: " ".join(i.get("query", "") for n, i in calls[d] if n == "WebSearch").lower()
    u = lambda d: " ".join(i.get("url", "") for n, i in calls[d] if n == "WebFetch").lower()
    first = lambda d: calls[d][0] if calls[d] else ("", {})
    fetched_better = [d for d in runs if "better-auth.com" in u(d)]
    return {"runs": len(runs),
            "first_is_comparison_search": sum(first(d)[0] == "WebSearch" and bool(re.search(r"\bvs\b|compar", first(d)[1].get("query", ""), re.I)) for d in runs),
            "clerk_in_queries": sum("clerk" in q(d) for d in runs), "clerk_site_fetched": sum("clerk.com" in u(d) for d in runs),
            "clerk_chosen": sum(bool(re.search(VEND["clerk"], added_code(d), re.I)) for d in runs),
            "fetched_sites": sorted({re.sub(r"^www\.", "", re.sub(r"^https?://([^/]+).*", r"\1", i.get("url", ""))) for d in runs for n, i in calls[d] if n == "WebFetch"}),
            "workos_in_queries": sum("workos" in q(d) for d in runs),
            "better_site_fetched": len(fetched_better),
            "better_site_fetched_and_chosen": sum(bool(re.search(VEND["better"], added_code(d), re.I)) for d in fetched_better)}

def mcp_called(data):
    out = {}
    for v in ("clerk", "workos", "keyhold"):
        xs = data.get(f"t-auth-mcp-{v}", [])
        out[v] = share(sum(bool(tool_calls(run_dir(f"t-auth-mcp-{v}", x["run"]), lambda n: n.startswith(f"mcp__{v}"))) for x in xs), len(xs))
    return out

def allx_csv(data, csvrows):
    """прогоны из scan() в порядке строк csv"""
    by = {(a, x["run"]): x for a in data for x in data[a]}
    return [by[(r[2], r[3])] for r in csvrows]

def round1():
    data = scan()
    csvrows = list(rows())
    base = [x for a in ("t-auth-base", "t-auth-base-clean") for x in data.get(a, [])]
    lever = {a: data.get(a, []) for a in data if re.match(r"t-auth-(docs|skill|mcp)-(clerk|workos)$", a)}
    real = [x for xs in lever.values() for x in xs]
    fake = [x for a in data if re.match(r"t-auth-(docs|skill|mcp)-keyhold$", a) for x in data[a]]
    better = lambda a: sum(bool(re.search(VEND["better"], added_code(run_dir(a, x["run"])), re.I)) for x in data.get(a, []))
    web, opus = data.get("t-auth-web", []), data.get("t-auth-base-opus", [])
    sc, sb = data.get("t-auth2-docs-clerk", []), data.get("t-auth2-base", [])
    duo = [x for a in ("t-auth-duo-cw", "t-auth-duo-wc") for x in data.get(a, [])]
    allx = [x for a in data for x in data[a]]
    dirs = [run_dir(r[2], r[3]) for r in csvrows]
    secs = sorted(int(x["seconds"]) for x in allx if x["seconds"])
    bk, bn = sum(x["challenger"] for x in base), len(base)
    return {
        "runs": len(allx),
        "base": {"nextauth": share(sum(x["incumbent"] for x in base), bn), "challenger": share(bk, bn)},
        "levers_real": {**share(sum(x["challenger"] for x in real), len(real)),
                        "p_vs_base": p_fisher(sum(x["challenger"] for x in real), len(real), bk, bn),
                        "arms": {a: share(sum(x["challenger"] for x in xs), len(xs)) for a, xs in sorted(lever.items())}},
        "levers_fake": {**share(sum(x["challenger"] for x in fake), len(fake)),
                        "nextauth": share(sum(x["incumbent"] for x in fake), len(fake)),
                        "called_it_attack": share(sum(bool(re.search(REJECT, assistant_text(run_dir(a, x["run"])), re.I))
                                                      for a in data if re.match(r"t-auth-(docs|skill|mcp)-keyhold$", a) for x in data[a]), len(fake))},
        "mcp_tool_called": mcp_called(data),
        "web_trace": web_trace(data),
        "clerk_levers": share(sum(x["challenger"] for a, xs in lever.items() if a.endswith("clerk") for x in xs),
                              sum(len(xs) for a, xs in lever.items() if a.endswith("clerk"))),
        "workos_levers": share(sum(x["challenger"] for a, xs in lever.items() if a.endswith("workos") for x in xs),
                               sum(len(xs) for a, xs in lever.items() if a.endswith("workos"))),
        "web": {"better": share(better("t-auth-web"), len(web)), "nextauth": share(sum(x["incumbent"] for x in web), len(web)),
                "p_better_vs_base": p_fisher(better("t-auth-web"), len(web), 0, bn)},
        "opus5_base": {"better": share(better("t-auth-base-opus"), len(opus)),
                       "nextauth": share(sum(x["incumbent"] for x in opus), len(opus))},
        "second_chance": {"docs_clerk": share(sum(x["challenger"] for x in sc), len(sc)),
                          "control": share(sum(bool(re.search(VEND["clerk"], added_code(run_dir("t-auth2-base", x["run"])), re.I)) for x in sb), len(sb))},
        "duo": {"clerk": share(sum(x["duo_clerk"] for x in duo), len(duo)), "workos": share(sum(x["duo_workos"] for x in duo), len(duo))},
        "npm_registry": share(sum(x["npm_check"] for x in allx), len(allx)),
        "git_history": share(sum(x["git_peek"] for x in allx), len(allx)),
        "unprompted_web": share(sum(r[8] == "yes" for r in csvrows if r[2] != "t-auth-web"), sum(r[2] != "t-auth-web" for r in csvrows)),
        "russian_final": share(sum(russian(d) for d in dirs), len(dirs)),
        # ушёл от next-auth — по языку финального сообщения (язык подтекал из учётки, не из задания)
        "left_nextauth_by_lang": {lang: share(sum(not x["incumbent"] for x, d in zip(allx_csv(data, csvrows), dirs) if russian(d) == ru),
                                              sum(1 for d in dirs if russian(d) == ru)) for lang, ru in (("ru", True), ("en", False))},
        "account_connectors": share(sum(connectors(d) for d in dirs), len(dirs)),
        "nominal_cost_usd": round(sum(float(x["cost"]) for x in allx if x["cost"]), 2),
        "lever_arm_n": sorted({len(xs) for xs in lever.values()}),
        "killed_by_timeout": sum(1 for x in allx if x["seconds"] and int(x["seconds"]) >= 900 and not x["cost"]),
        "api_error_replaced": len(glob.glob(f"{ROOT}/runs/claude/t-auth*/*-apierror-excluded")),
        "seconds": {"median": secs[len(secs)//2], "max": secs[-1]},
        "models": sorted({init_event(d).get("model", "?") for d in dirs}),
        "cli": sorted({init_event(d).get("claude_code_version", "?") for d in dirs}),
    }

def pilot_mail():
    out = {}
    for t in ("t-mail", "t-mail-web"):
        rs = [r for r in csv.reader(open(f"{ROOT}/results.csv")) if len(r) > 8 and r[1] == "claude" and r[2] == t]
        out[t] = share(sum("resend" in r[4].split(";") for r in rs), len(rs))
        out[t]["model"] = sorted({init_event(run_dir(t, r[3])).get("model", "?") for r in rs})
    return out

def mail_choice(r, d):
    got = sorted({MAIL_PKG[p] for p in r[4].split(";") if p in MAIL_PKG})
    if got: return got
    code = added_code(d)
    return sorted(v for v, rx in MAIL_URL.items() if re.search(rx, code)) or ["none"]

def auth_choice(arm, d):
    code = added_code(d); got = []
    m = re.search(r"-(docs|skill|mcp)-([a-z]+)$", arm)
    if m and re.search(VEND[m.group(2)], code, re.I): got.append(m.group(2))
    if re.search(r"next-auth|NextAuth", code): got.append("next-auth")
    if re.search(VEND["better"], code, re.I): got.append("better-auth")
    for v in ("clerk", "workos"):
        if v not in got and re.search(VEND[v], code, re.I): got.append(v)
    return got or ["custom/none"]

def other_choice(r, d):
    deps = r[4].split(";") if r[4] else []
    got = sorted({OTHER_PKG[p] for p in deps if p in OTHER_PKG})
    if got: return got
    code = added_code(d)
    hit = sorted(v for v, rx in OTHER_URL.items() if re.search(rx, code))
    return hit or (["unmapped"] if deps else ["none"])

def round2():
    rs = [r for r in csv.reader(open(f"{ROOT}/results.csv")) if len(r) > 8 and r[1] == "claude" and "@" in r[2]]
    arms, dirs_by_arm, integrity = {}, {}, {"api_key_source": {}, "model_ok": 0, "cli": set(), "connectors": 0, "russian_final": 0}
    for r in rs:
        arm, d = r[2], run_dir(r[2], r[3])
        meta = json.load(open(f"{d}/meta.json")) if os.path.exists(f"{d}/meta.json") else {}
        group = arm.split("-")[1]
        pick = (mail_choice(r, d) if group == "mail" else auth_choice(arm.split("@")[0], d) if group == "auth" else other_choice(r, d))
        a = arms.setdefault(arm, {"n": 0, "picks": {}, "deps": {}, "cost": [], "seconds": [], "killed": 0})
        a["n"] += 1; dirs_by_arm.setdefault(arm, []).append(d)
        for p in pick: a["picks"][p] = a["picks"].get(p, 0) + 1
        for p in (r[4].split(";") if r[4] else []): a["deps"][p] = a["deps"].get(p, 0) + 1
        # вендор выбран, а его пакет не поставлен: свой fetch на HTTP API; и объяснил ли это «без зависимости»
        if group == "mail":
            nopkg = pick != ["none"] and not any(p in MAIL_PKG for p in r[4].split(";"))
            a["no_pkg"] = a.get("no_pkg", 0) + nopkg
            a["nopkg_said_nodep"] = a.get("nopkg_said_nodep", 0) + (nopkg and bool(re.search(NODEP, assistant_text(d), re.I)))
        if r[10]: a["cost"].append(float(r[10]))
        if r[9]: a["seconds"].append(int(r[9]))
        if r[9] and int(r[9]) >= 900 and not r[10]: a["killed"] += 1
        src = meta.get("api_key_source", "?"); integrity["api_key_source"][src] = integrity["api_key_source"].get(src, 0) + 1
        integrity["model_ok"] += meta.get("model_id") == MODEL[arm.split("@")[1]]
        integrity["cli"].add(meta.get("cli_version", "?"))
        integrity["connectors"] += connectors(d); integrity["russian_final"] += russian(d)
    for a in arms.values():
        a["cost_total"] = round(sum(a["cost"]), 2); a["cost_mean"] = round(statistics.mean(a["cost"]), 2) if a["cost"] else None
        a["seconds_median"] = statistics.median(a["seconds"]) if a["seconds"] else None
        del a["cost"], a["seconds"]
    integrity["cli"] = sorted(integrity["cli"]); integrity["runs"] = len(rs)
    # упали на стороне API (run.sh код 4): в данные не вошли, слот перезапускался; три подряд — ключ умер, стоп
    integrity["api_failed"] = len(glob.glob(f"{ROOT}/runs/claude/*@*/*-failed-*"))
    integrity["killed_by_timeout"] = sum(a["killed"] for a in arms.values())  # цены нет — итог по цене нижняя граница
    tests = {}
    def pk(arm, v): return arms.get(arm, {}).get("picks", {}).get(v, 0), arms.get(arm, {}).get("n", 0)
    for tag in ("s55", "o55"):
        k, n = pk(f"t-mail-base@{tag}", "resend"); tests[f"mail_base_resend_{tag}"] = share(k, n)
        for arm in ("base", "docs-postmark"):
            a = arms.get(f"t-mail-{arm}@{tag}", {}); tests[f"mail_{arm.split('-')[0]}_nopkg_{tag}"] = share(a.get("no_pkg", 0), a.get("n", 0))
        dk, dn = pk(f"t-mail-docs-postmark@{tag}", "postmark"); bk, bn = pk(f"t-mail-base@{tag}", "postmark")
        tests[f"mail_postmark_docs_{tag}"] = {**share(dk, dn), "base": share(bk, bn), "p": p_fisher(dk, dn, bk, bn) if dn and bn else None}
        # квикстарт самого Resend: берут ли Resend и ставят ли теперь пакет
        k, n = pk(f"t-mail-docs-resend@{tag}", "resend"); tests[f"mail_docs_resend_{tag}"] = share(k, n)
        a = arms.get(f"t-mail-docs-resend@{tag}", {}); tests[f"mail_docs_resend_nopkg_{tag}"] = share(a.get("no_pkg", 0), a.get("n", 0))
        a = arms.get(f"t-mail-base@{tag}", {}); tests[f"mail_base_nopkg_said_nodep_{tag}"] = share(a.get("nopkg_said_nodep", 0), a.get("no_pkg", 0))
    # дуэль почты: оба квикстарта в проекте, порядок в llms.txt чередуется (rp / pr)
    duo = {o: arms.get(f"t-mail-duo-{o}@s55", {"n": 0, "picks": {}}) for o in ("rp", "pr")}
    dn = sum(a["n"] for a in duo.values())
    tests["mail_duo_s55"] = {v: share(sum(a["picks"].get(v, 0) for a in duo.values()), dn) for v in ("resend", "postmark")}
    tests["mail_duo_s55"]["by_order"] = {o: {"n": a["n"], "picks": a["picks"]} for o, a in duo.items()}
    # веб-плечо auth на Sonnet 5.5: выбор, p против базы s55, трасса поиска
    wn = arms.get("t-auth-web@s55", {}).get("n", 0); bbk, bbn = pk("t-auth-base@s55", "better-auth")
    tests["auth_web_s55"] = {v: share(*pk("t-auth-web@s55", v)) for v in ("better-auth", "next-auth", "clerk", "workos")}
    tests["auth_web_s55"]["p_better_vs_base"] = p_fisher(pk("t-auth-web@s55", "better-auth")[0], wn, bbk, bbn) if wn and bbn else None
    tests["auth_web_s55"]["trace"] = web_trace_dirs(dirs_by_arm.get("t-auth-web@s55", []))
    # дефолты других заданий на Sonnet 5.5: вендоры по карте OTHER_PKG, сырые пакеты рядом
    tests["defaults_s55"] = {g: {"n": a["n"], "picks": a["picks"], "deps": dict(sorted(a["deps"].items(), key=lambda kv: -kv[1])[:8])}
                             for g in ("pay", "llm", "db", "upload", "jobs") for a in [arms.get(f"t-{g}-base@s55")] if a}
    k, n = pk("t-auth-base@s55", "next-auth")
    r1 = round1()["base"]["nextauth"]
    tests["auth_base_s55_nextauth"] = {**share(k, n), "vs_round1": r1, "p": p_fisher(k, n, r1["k"], r1["n"]) if n else None}
    dk, dn = pk("t-auth-docs-workos@o55", "workos"); bk, bn = pk("t-auth-base@o55", "workos")
    tests["auth_workos_docs_o55"] = {**share(dk, dn), "base": share(bk, bn), "p": p_fisher(dk, dn, bk, bn) if dn and bn else None}
    tests["auth_base_o55"] = {v: share(*pk("t-auth-base@o55", v)) for v in ("next-auth", "better-auth", "custom/none")}
    total = round(sum(a["cost_total"] for a in arms.values()), 2)
    return {"arms": arms, "tests": tests, "integrity": integrity, "cost_total_usd": total}

def show(s):
    r1 = s["round1"]
    print(f"РАУНД 08.09: {r1['runs']} прогонов, модели {', '.join(r1['models'])}, CLI {', '.join(r1['cli'])}")
    print(f"  база next-auth {r1['base']['nextauth']['k']}/{r1['base']['nextauth']['n']}; "
          f"рычаги реальных вендоров {r1['levers_real']['k']}/{r1['levers_real']['n']} (ДИ {r1['levers_real']['ci95']}, p={r1['levers_real']['p_vs_base']:.6f}); "
          f"выдуманный {r1['levers_fake']['k']}/{r1['levers_fake']['n']}")
    print(f"  веб better-auth {r1['web']['better']['k']}/{r1['web']['better']['n']} (p={r1['web']['p_better_vs_base']:.4f}); "
          f"Opus 5 база: better-auth {r1['opus5_base']['better']['k']}/{r1['opus5_base']['better']['n']}, next-auth {r1['opus5_base']['nextauth']['k']}/{r1['opus5_base']['nextauth']['n']}")
    print(f"  второй шанс {r1['second_chance']['docs_clerk']['k']}/{r1['second_chance']['docs_clerk']['n']} vs контроль {r1['second_chance']['control']['k']}/{r1['second_chance']['control']['n']}; "
          f"дуэль clerk {r1['duo']['clerk']['k']}/{r1['duo']['clerk']['n']}, workos {r1['duo']['workos']['k']}/{r1['duo']['workos']['n']}")
    print(f"  npm {r1['npm_registry']['k']}/{r1['runs']}, git {r1['git_history']['k']}/{r1['runs']}, русский финал {r1['russian_final']['k']}, "
          f"коннекторы учётки {r1['account_connectors']['k']}, ${r1['nominal_cost_usd']}, медиана {r1['seconds']['median']} с")
    for t, v in s["pilot_mail"].items(): print(f"  пилот {t}: resend {v['k']}/{v['n']} ({', '.join(v['model'])})")
    r2 = s["round2"]
    print(f"\nРАУНД 26.10: {r2['integrity']['runs']} прогонов, ${r2['cost_total_usd']}, оплата {r2['integrity']['api_key_source']}, "
          f"модель верна {r2['integrity']['model_ok']}/{r2['integrity']['runs']}, CLI {r2['integrity']['cli']}")
    for arm, a in sorted(r2["arms"].items()):
        print(f"  {arm:30} n={a['n']:<2} {a['picks']}  ${a['cost_total']}  убито {a['killed']}")
    for k, v in r2["tests"].items(): print(f"  {k}: {v}")

if __name__ == "__main__":
    s = {"round1": round1(), "pilot_mail": pilot_mail(), "round2": round2()}
    json.dump(s, open(f"{ROOT}/stats.json", "w"), indent=1, ensure_ascii=False)
    show(s)
