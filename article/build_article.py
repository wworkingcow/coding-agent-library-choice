#!/usr/bin/env python3
"""Собирает ARTICLE.md из ARTICLE.template.md. Каждое число в статье — метка {{путь|формат}} из stats.json
(его пишет report_2610.py). Неизвестная метка — ошибка, руками число не впишешь.
Блок раунда 2: пока прогонов нет — берётся <!-- round2:pending -->, после — <!-- round2:done -->.
usage: python3 report_2610.py && python3 article/build_article.py"""
import datetime, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
S = json.load(open(f"{ROOT}/stats.json"))

def get(path):
    v = S
    for k in path.split("."):
        if not isinstance(v, dict) or k not in v: sys.exit(f"нет в stats.json: {path}")
        v = v[k]
    return v

def fmt(v, f):
    if v is None: return "n/a"
    if f == "ci": return f"{v['ci95'][0]}–{v['ci95'][1]}%"
    if f == "p": return "p < 0.0001" if v < 0.0001 else f"p = {v:.2g}"
    if f == "usd": return f"${v:,.2f}"
    if f == "pct": return f"{round(100*v['k']/v['n'])}%" if v["n"] else "n/a"
    if f in ("k", "n"): return str(v[f])
    if f == "picks": return ", ".join(f"{k} {c}/{v['n']}" for k, c in sorted(v["picks"].items(), key=lambda kv: -kv[1])) or "n/a"
    if isinstance(v, dict) and {"k", "n"} <= v.keys(): return f"{v['k']}/{v['n']}"
    if isinstance(v, list): return ", ".join(map(str, v))
    return str(v)

def fill(text):
    """блок раунда 2 по наличию прогонов, потом все метки {{путь|формат}}"""
    drop = "done" if get("round2.integrity.runs") == 0 else "pending"
    text = re.sub(rf"<!-- round2:{drop} -->.*?<!-- /round2:{drop} -->\n?", "", text, flags=re.S)
    text = re.sub(r"<!-- /?round2:\w+ -->\n?", "", text)
    return re.sub(r"\{\{([^}|]+)(?:\|(\w+))?\}\}", lambda m: fmt(get(m.group(1).strip()), m.group(2)), text)

if __name__ == "__main__":
    text = fill(open(f"{HERE}/ARTICLE.template.md").read())
    text += f"\n---\n*Every number above is filled in from `stats.json` by `article/build_article.py` ({datetime.date.today()}).*\n"
    open(f"{HERE}/ARTICLE.md", "w").write(text)
    print(f"ARTICLE.md: {len(text.split())} слов, раунд 2 = {'есть' if get('round2.integrity.runs') else 'нет прогонов'}")
