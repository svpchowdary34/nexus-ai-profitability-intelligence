# NEXUS AI — Cross-Functional Profitability Intelligence | ONE Google Colab cell
# Connect the dots. Find the profit leak.
import subprocess, sys, os, re, zipfile, html, math, itertools, warnings
warnings.filterwarnings("ignore")
try:
    import gradio, plotly, sklearn, scipy
    assert int(gradio.__version__.split(".")[0]) in (4, 5)
except Exception:
    subprocess.call([sys.executable, "-m", "pip", "install", "-q", "gradio>=4.44,<6", "plotly", "scikit-learn>=1.2", "scipy", "pandas", "numpy"])
import numpy as np, pandas as pd, plotly.graph_objects as go, gradio as gr
from scipy import stats
from sklearn.linear_model import Ridge

C = dict(mid="#202D39", sl="#344650", sg="#B8E3C7", go="#D7B878", iv="#F3F2EC", li="#C9B8F0", co="#E58C83", st="#AAB9C0")
G = {}; TESTS = []; _D = {}; BL = ["", "nan", "none", "n/a", "na", "-", "null", "nat"]
esc = lambda x: html.escape(str(x)); nul = lambda v: v is None or (not isinstance(v, str) and bool(pd.isna(v)))
nf = lambda v, d=0: "—" if nul(v) else format(v, ",." + str(d) + "f"); pc = lambda v, d=1: "—" if nul(v) else format(v, "." + str(d) + "%"); sg = lambda v: "—" if nul(v) else "%+.1f%%" % (100 * v)
kk = lambda v: "—" if nul(v) else ("-" if v < 0 else "") + "₹" + format(abs(v), ",.0f") + "k"; ch = lambda a, b: np.nan if (nul(a) or nul(b) or b == 0) else (a - b) / abs(b)
def note(t, k="info"): return "<div class='note' style='border-left:4px solid %s'>%s</div>" % ({"info": C["st"], "ok": C["sg"], "warn": C["go"], "err": C["co"], "ai": C["li"]}[k], t)
def card(l, v, d, c=C["mid"]): return "<div class='kc'><div class='kl'>%s</div><div class='kv' style='color:%s'>%s</div><div class='kd'>%s</div></div>" % (l, c, v, d)
SEC = lambda t: "<div class='sec'>%s</div>" % t
def pill(s):
    c = C["co"] if s.startswith(("Not met", "Missed", "Unfav")) else (C["sg"] if s.startswith(("Strong", "Met", "Fav", "Reconciled")) else C["go"]); return "<span class='pill' style='background:%s'>%s</span>" % (c, esc(s))
def tbl(d, cols, fmt=None):
    fmt = fmt or {}; h = "<div class='tw'><table><tr>" + "".join("<th>%s</th>" % n for _, n in cols) + "</tr>"
    for _, r in d.iterrows(): h += "<tr>" + "".join("<td>%s</td>" % (fmt[k](r[k]) if k in fmt else ("—" if nul(r[k]) else esc(r[k]))) for k, _n in cols) + "</tr>"
    return h + "</table></div>"
def sty(f, h=340, t=""):
    f.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=C["mid"]), height=h, title=dict(text=t, x=.02), margin=dict(l=55, r=25, t=50, b=45), legend=dict(orientation="h", y=-.25), colorway=[C["mid"], C["go"], C["li"], C["co"], C["st"]]); return f
def empty(m):
    f = go.Figure(); f.add_annotation(text=m, showarrow=False, font=dict(color=C["st"], size=14)); f.update_xaxes(visible=False); f.update_yaxes(visible=False); return sty(f, 280)
def banner(): return note("<b>Illustrative synthetic data.</b> Fictional company with planted demonstration mechanisms (discounting, product mix, overtime, rework); not a real business.", "warn") if G.get("demo") else ""
def safe(n):
    def deco(fn):
        def w(*a):
            def out(m): return m if n == 1 else (m,) + (None,) * (n - 1)
            if "D" not in G: return out(note("Load data first."))
            try: return fn(*a)
            except Exception as e: return out(note("Could not render this page: " + esc(e), "err"))
        return w
    return deco
nm_ = lambda s: re.sub(r"\W+", "_", str(s).strip().lower()).strip("_")
def clean_str(s): t = s.astype(str).str.strip(); return t.where(~(s.isna() | t.str.lower().isin(BL)), np.nan)
def to_num(s): return s.astype(float) if pd.api.types.is_numeric_dtype(s) else pd.to_numeric(s.astype(str).str.replace(r"[₹$,%\s]", "", regex=True), errors="coerce")
def to_dt(s):
    if pd.api.types.is_datetime64_any_dtype(s): return s
    try: return pd.to_datetime(s, errors="coerce", format="mixed")
    except Exception: return pd.to_datetime(s, errors="coerce")
def read_csv_any(f):
    p = f if isinstance(f, str) else getattr(f, "name", f)
    try: d = pd.read_csv(p)
    except Exception: d = pd.read_csv(p, sep=None, engine="python", encoding_errors="replace")
    if d.empty: raise ValueError("A file contains no rows.")
    return d

# ------------------------------ FICTIONAL synthetic enterprise (fixed seed, documented mechanisms) ------------------------------
COST = ["marketing_expense", "payroll", "overtime_cost", "recruit_train_cost", "ops_cost", "other_opex"]; FINC = ["revenue", "cogs", "gross_profit"] + COST + ["operating_profit"]
BUD = ["budget_" + c for c in ["revenue", "cogs"] + COST] + ["budget_operating_profit"]; SEGS = ["Online", "Stores"]; PER = pd.date_range("2023-10-01", periods=36, freq="MS")
ADD = FINC + BUD + ["orders", "gross_sales", "new_customers", "overtime_hours"]; RATE = ["conversion_rate", "turnover_rate", "absence_rate", "capacity_util", "rework_rate", "return_rate", "on_time_pct", "email_ctr", "engagement_score", "low_margin_mix_share"]
def make_data(seed=11):
    r = np.random.default_rng(seed); T = 36; t = np.arange(T); ramp = np.clip((t - 26) / 9, 0, 1); sea = np.sin(2 * np.pi * (PER.month.values - 2) / 12); z = lambda s: r.normal(0, s, T); F, Mk, H, O = [], [], [], []
    for g, sc in zip(SEGS, [1.0, .6]):
        orders = np.round(20000 * sc * (1 + .008 * t) * (1 + .02 * sea) * (1 + z(.012))); mix = np.clip(.25 + .25 * ramp + z(.012), 0, 1); disc = .10 + .04 * ramp + z(.003); L = 920 - 50 * mix + z(2.0); c = 380 + 130 * mix + z(2.0)
        gross = orders * L / 1000; rev = gross * (1 - disc); cogs = orders * c / 1000; head = np.round(sc * (180 + .6 * t)); oth = sc * (500 + 800 * ramp) * (1 + z(.05)); turn = 1.2 + 1.0 * ramp + z(.1); rew = 3 + 3 * ramp + z(.2); ret = 4 + 2 * ramp + z(.2); cpo = 52 + 1.5 * rew + 1.2 * ret
        f = dict(revenue=rev, cogs=cogs, marketing_expense=1500 * sc * (1 + .008 * t) * (1 + .08 * ramp) * (1 + z(.02)), payroll=head * 9.5 * (1 + z(.01)), overtime_cost=oth * .4, recruit_train_cost=head * turn / 100 * 45, ops_cost=orders * cpo / 1000, other_opex=600 * sc * (1 + .004 * t) * (1 + z(.02)))
        f["gross_profit"] = rev - cogs; f["operating_profit"] = f["gross_profit"] - sum(f[k] for k in COST); b = {"budget_revenue": rev * (.97 + z(.004)), "budget_cogs": cogs * (1.03 + z(.004))}
        for k in COST: b["budget_" + k] = f[k] * (1.04 + z(.004))
        b["budget_operating_profit"] = b["budget_revenue"] - b["budget_cogs"] - sum(b["budget_" + k] for k in COST); base = dict(period=PER, segment=g)
        F.append(pd.DataFrame({**base, **{k: np.round(v, 4) for k, v in {**f, **b}.items()}})); Mk.append(pd.DataFrame({**base, "gross_sales": np.round(gross, 4), "new_customers": np.round(orders * .045 * (1 + z(.02))), "conversion_rate": np.round(2.6 + .008 * t + z(.05), 3), "low_margin_mix_share": np.round(mix * 100, 2), "email_ctr": np.round(2 + z(.15), 3)}))
        H.append(pd.DataFrame({**base, "headcount": head, "overtime_hours": np.round(oth, 1), "turnover_rate": np.round(turn, 3), "absence_rate": np.round(3 + .3 * ramp + z(.25), 3), "engagement_score": np.round(72 - 4 * ramp + z(1.5), 2)})); O.append(pd.DataFrame({**base, "orders": orders, "capacity_util": np.round(78 + 14 * ramp + z(1.0), 2), "rework_rate": np.round(rew, 3), "return_rate": np.round(ret, 3), "on_time_pct": np.round(95 + z(.8), 2)}))
    kpi = pd.DataFrame([("New customers per month", "Marketing", "new_customers", 1200, "up"), ("Conversion rate (%)", "Marketing", "conversion_rate", 2.4, "up"), ("Headcount", "HR", "headcount", 340, "down"), ("Employee engagement", "HR", "engagement_score", 65, "up"), ("Orders per month", "Operations", "orders", 28000, "up"), ("Capacity utilisation (%)", "Operations", "capacity_util", 95, "down"),
                        ("On-time delivery (%)", "Operations", "on_time_pct", 93, "up"), ("Operating costs vs budget (%)", "Finance", "cost_vs_budget_pct", 0, "down"), ("Revenue vs budget (%)", "Finance", "revenue_vs_budget_pct", 0, "up")], columns=["kpi", "department", "column", "target", "direction"])
    return dict(fin=pd.concat(F, ignore_index=True), mkt=pd.concat(Mk, ignore_index=True), hr=pd.concat(H, ignore_index=True), ops=pd.concat(O, ignore_index=True), kpi=kpi)
def demo_raw(seed=11):
    if ("r", seed) not in _D: _D[("r", seed)] = make_data(seed)
    return _D[("r", seed)]
def demo_D(seed=11):
    if ("d", seed) not in _D: _D[("d", seed)] = load_all(demo_raw(seed))
    return _D[("d", seed)]

# ------------------------------ ingestion, validation, reconciliation ------------------------------
SP = dict(fin=[("period", 1, ["month", "date"]), ("segment", 0, ["region", "business_unit"])] + [(c, 1, []) for c in ["revenue", "cogs"] + COST] + [(c, 0, []) for c in ["gross_profit", "operating_profit"] + BUD],
          mkt=[("period", 1, ["month", "date"]), ("segment", 0, ["region"]), ("gross_sales", 1, ["list_sales"]), ("new_customers", 1, ["customers"]), ("conversion_rate", 1, ["conversion"]), ("low_margin_mix_share", 0, []), ("email_ctr", 0, [])],
          hr=[("period", 1, ["month", "date"]), ("segment", 0, ["region"]), ("headcount", 1, ["fte"]), ("overtime_hours", 1, ["overtime"]), ("turnover_rate", 1, ["attrition_rate"]), ("absence_rate", 0, []), ("engagement_score", 0, [])],
          ops=[("period", 1, ["month", "date"]), ("segment", 0, ["region"]), ("orders", 1, ["units"]), ("capacity_util", 1, ["utilisation"]), ("rework_rate", 1, []), ("return_rate", 1, []), ("on_time_pct", 0, ["otd"])], kpi=[(c, 1, []) for c in ["kpi", "department", "column", "target", "direction"]])
TN = dict(fin="financials", mkt="marketing", hr="hr", ops="operations", kpi="departmental_kpis")
def parse_map(text):
    ov = {}
    for p in re.split(r"[,;\n]", text or ""):
        if "=" in p: k, v = p.split("=", 1); ov[nm_(k)] = nm_(v)
    return ov
def cmap(raw, t, ov, iss):
    d = raw.copy(); d.columns = [nm_(c) for c in d.columns]; ren = {}
    for f, req, al in SP[t]:
        c = ov.get(f); c = c if c in d.columns else next((a for a in [f] + [nm_(x) for x in al] if a in d.columns and a not in ren), None)
        if c is None or c in ren:
            if req: iss.append(("error", "%s: required field '%s' not found. Columns found: %s. Use the mapping box, e.g. %s=your_column." % (TN[t], f, ", ".join(map(str, raw.columns[:12])), f)))
            continue
        ren[c] = f
    d = d.rename(columns=ren); return d.loc[:, ~d.columns.duplicated()]
def load_all(raw, mapping=""):
    iss, ex, ov, out = [], [], parse_map(mapping), {}
    for t in ("fin", "mkt", "hr", "ops"):
        if raw.get(t) is None: raise ValueError("Missing required table: " + TN[t])
    T = {t: cmap(raw[t], t, ov, iss) for t in TN if raw.get(t) is not None}; errs = [m for l, m in iss if l == "error"]
    if errs: raise ValueError(" | ".join(errs))
    rows_in = {t: len(raw[t]) for t in T}
    for t in ("fin", "mkt", "hr", "ops"):
        d = T[t].copy(); d["period"] = to_dt(d["period"]); d["segment"] = clean_str(d["segment"]).fillna("Company") if "segment" in d else "Company"; nums = [c for c, _, _ in SP[t] if c not in ("period", "segment") and c in d]
        for c in nums: d[c] = to_num(d[c])
        d["_row"] = np.arange(len(d)) + 2; bad = pd.Series(False, index=d.index); req = [c for c, rq, _ in SP[t] if rq and c not in ("period", "segment")]; nn = [c for c in nums if "profit" not in c]
        for why, m in [("invalid or missing period", d.period.isna()), ("missing or non-numeric required value", d[req].isna().any(axis=1)), ("negative amount, count or rate", (d[nn] < 0).any(axis=1))]:
            m = m & ~bad
            if m.any(): ex.append((TN[t], why, int(m.sum()))); iss.append(("warn", "%s: %d rows excluded: %s (rows %s)" % (TN[t], m.sum(), why, ", ".join(str(i) for i in d["_row"][m].values[:6])))); bad = bad | m
        d = d[~bad].copy()
        if len(d) and (d.period.dt.day != 1).mean() > .5: iss.append(("info", "%s: dates normalised to month start. Daily or weekly records must be aggregated to months before upload; grains are never mixed." % TN[t]))
        d["period"] = d.period.dt.to_period("M").dt.to_timestamp(); dp = d.duplicated(["period", "segment"], keep="first")
        if dp.any(): ex.append((TN[t], "duplicate period+segment", int(dp.sum()))); iss.append(("warn", "%s: %d duplicate period/segment rows ignored (first kept)." % (TN[t], dp.sum())))
        out[t] = d[~dp].drop(columns="_row")
    P = out["fin"]
    for t in ("mkt", "hr", "ops"): P = P.merge(out[t], on=["period", "segment"], how="left")
    ms = int(P[["gross_sales", "headcount", "orders"]].isna().any(axis=1).sum())
    if ms: iss.append(("warn", "%d financial rows have no matching marketing, HR or operations row (values left missing, never filled)." % ms))
    for col, rhs, nm in (("gross_profit", P.revenue - P.cogs, "gross profit = revenue − COGS"), ("operating_profit", P.revenue - P.cogs - P[COST].sum(axis=1), "operating profit = revenue − COGS − operating costs")):
        if col not in P or P[col].isna().all(): P[col] = rhs; iss.append(("info", "%s not supplied: derived from %s." % (col, nm)))
        else:
            e = ((P[col] - rhs).abs() > .005 * P.revenue.abs() + .01) & P[col].notna()
            if e.any(): iss.append(("warn", "Reconciliation failed for %d rows: %s (tolerance 0.5%% of revenue). Values kept as supplied, not corrected, so the profit bridge may not reconcile." % (e.sum(), nm)))
    if "budget_operating_profit" not in P or P.budget_operating_profit.isna().all():
        if all(c in P for c in BUD[:-1]) and P[BUD[:-1]].notna().all().all(): P["budget_operating_profit"] = P.budget_revenue - P.budget_cogs - P[["budget_" + c for c in COST]].sum(axis=1); iss.append(("info", "budget_operating_profit derived from budget components."))
    K = T["kpi"].copy() if "kpi" in T else pd.DataFrame(columns=["kpi", "department", "column", "target", "direction"]); K["target"] = to_num(K["target"]); K["direction"] = K["direction"].astype(str).str.lower().map(lambda s: "down" if re.search("down|low|max|<", s) else "up")
    for s, g in P.groupby("segment"):
        gap = len(pd.date_range(g.period.min(), g.period.max(), freq="MS")) - g.period.nunique()
        if gap: iss.append(("warn", "Segment %s is missing %d months (never filled; incomplete quarters are excluded)." % (s, gap)))
    if P.period.nunique() < 24: iss.append(("warn", "Only %d months: relationship and model results are unreliable (24+ recommended)." % P.period.nunique()))
    return dict(P=P.reset_index(drop=True), K=K, issues=iss, excluded=ex, rows_in=rows_in, segs=sorted(P.segment.unique()), pers=sorted(P.period.unique()))

# ------------------------------ aggregation (documented rules: sums add; rates are order-weighted means) ------------------------------
def derive(M):
    M = M.copy(); o = M.orders.replace(0, np.nan); g = M.gross_sales.replace(0, np.nan); rv = M.revenue.replace(0, np.nan)
    M["discount_rate"] = 100 * (1 - M.revenue / g); M["list_price"] = M.gross_sales * 1000 / o; M["unit_cost"] = M.cogs * 1000 / o; M["cac"] = M.marketing_expense * 1000 / M.new_customers.replace(0, np.nan); M["cost_per_order"] = M.ops_cost * 1000 / o
    M["total_costs"] = M[COST].sum(axis=1, min_count=len(COST)); M["labour_cost"] = M.payroll + M.overtime_cost + M.recruit_train_cost; M["gross_margin_pct"] = 100 * M.gross_profit / rv; M["op_margin_pct"] = 100 * M.operating_profit / rv
    M["contribution_margin"] = M.gross_profit - M.ops_cost - M.marketing_expense; M["cost_to_revenue"] = 100 * M.total_costs / rv
    bc = ["budget_" + c for c in COST]
    if all(c in M for c in bc): M["budget_total_costs"] = M[bc].sum(axis=1, min_count=len(bc)); M["cost_vs_budget_pct"] = 100 * (M.total_costs / M.budget_total_costs.replace(0, np.nan) - 1)
    if "budget_revenue" in M: M["revenue_vs_budget_pct"] = 100 * (M.revenue / M.budget_revenue.replace(0, np.nan) - 1)
    return M.replace([np.inf, -np.inf], np.nan)
def monthly(P, seg):
    d = P if seg == "All" else P[P.segment == seg]; add = [c for c in ADD if c in d]; M = d.groupby("period")[add].sum(min_count=1)
    if "headcount" in d: M["headcount"] = d.groupby("period").headcount.sum(min_count=1)
    w = d.orders
    for c in RATE:
        if c in d and d[c].notna().any(): M[c] = (d[c] * w).groupby(d.period).sum(min_count=1) / w.groupby(d.period).sum(min_count=1)
    return derive(M)
def quarterly(M):
    q = M.index.to_period("Q"); n = M.groupby(q).size(); add = [c for c in ADD if c in M]; Q = M.groupby(q)[add].sum(min_count=1)
    if "headcount" in M: Q["headcount"] = M.groupby(q).headcount.mean()
    for c in RATE:
        if c in M: Q[c] = (M[c] * M.orders).groupby(q).sum(min_count=1) / M.orders.groupby(q).sum(min_count=1)
    Q = Q[n.reindex(Q.index) == 3]; Q.index = [str(p) for p in Q.index]; return derive(Q)

# ------------------------------ profit bridge and Shapley attribution ------------------------------
def drv(q): return dict(O=q.orders, L=q.list_price, d=q.discount_rate / 100, c=q.unit_cost, Mk=q.marketing_expense, Lab=q.labour_cost, Ops=q.ops_cost, Oth=q.other_opex)
def opf(x): return x["O"] * (x["L"] * (1 - x["d"]) - x["c"]) / 1000 - x["Mk"] - x["Lab"] - x["Ops"] - x["Oth"]
def bridge(q0, q1):
    a, b = drv(q0), drv(q1)
    rows = [("Volume (orders)", (b["O"] - a["O"]) * (a["L"] * (1 - a["d"]) - a["c"]) / 1000), ("List price / list-price mix", b["O"] * (b["L"] - a["L"]) * (1 - a["d"]) / 1000), ("Discounting", -b["O"] * b["L"] * (b["d"] - a["d"]) / 1000), ("Unit cost of goods (incl. product mix)", -b["O"] * (b["c"] - a["c"]) / 1000),
            ("Marketing spend", -(b["Mk"] - a["Mk"])), ("Payroll", -(q1.payroll - q0.payroll)), ("Overtime cost", -(q1.overtime_cost - q0.overtime_cost)), ("Recruitment and training", -(q1.recruit_train_cost - q0.recruit_train_cost)), ("Operations / fulfilment cost", -(b["Ops"] - a["Ops"])), ("Other operating expenses", -(b["Oth"] - a["Oth"]))]
    tot = sum(v for _, v in rows); act = q1.operating_profit - q0.operating_profit; tol = max(.5, .001 * abs(act)); return dict(rows=rows, total=tot, actual=act, diff=tot - act, tol=tol, ok=bool(abs(tot - act) <= tol))
def shapley(a, b):
    P = list(a); n = len(P); v = lambda S: opf({k: (b[k] if k in S else a[k]) for k in P}); phi = {}
    for i in P:
        rest = [k for k in P if k != i]; s = 0.0
        for m in range(n):
            for S in itertools.combinations(rest, m): s += math.factorial(m) * math.factorial(n - m - 1) / math.factorial(n) * (v(set(S) | {i}) - v(set(S)))
        phi[i] = s
    return phi, v(set(P)) - v(set())
SH = dict(O="Volume", L="List price", d="Discount rate", c="Unit cost / product mix", Mk="Marketing spend", Lab="Labour (payroll + overtime + recruitment)", Ops="Operations cost", Oth="Other operating expenses")
def streak(Q, i):
    s = 0; v = Q.operating_profit.values
    while i - s > 0 and v[i - s] < v[i - s - 1]: s += 1
    return s

# ------------------------------ relationships (trend and season removed, lags, FDR) ------------------------------
def bh(p):
    p = np.asarray(p, float); n = len(p); o = np.argsort(p); q = np.empty(n); prev = 1.0
    for i in range(n - 1, -1, -1): j = o[i]; prev = min(prev, p[j] * n / (i + 1)); q[j] = prev
    return q
def resid(df, cols):
    n = len(df); X = np.c_[np.ones(n), np.arange(n), pd.get_dummies(pd.Series(df.index.month), drop_first=True).values.astype(float)]; o = {}
    for c in cols:
        y = df[c].values.astype(float); m = np.isfinite(y)
        if m.sum() < X.shape[1] + 4 or np.nanstd(y) == 0: o[c] = np.full(n, np.nan); continue
        b = np.linalg.lstsq(X[m], y[m], rcond=None)[0]; r = np.full(n, np.nan); r[m] = y[m] - X[m] @ b; o[c] = r
    return pd.DataFrame(o, index=df.index)
def pairs(Rs, o, d, L):
    x = np.concatenate([R[d].shift(L).values for R in Rs]); y = np.concatenate([R[o].values for R in Rs]); m = np.isfinite(x) & np.isfinite(y); return x[m], y[m]
def prep_R(D, cols, det, segs):
    fr = [monthly(D["P"], g) for g in segs]; cols = [c for c in cols if all(c in f for f in fr)]; return [resid(f, cols) if det else f[cols] for f in fr], cols
DRV = ["discount_rate", "cac", "conversion_rate", "marketing_expense", "low_margin_mix_share", "overtime_hours", "turnover_rate", "absence_rate", "headcount", "capacity_util", "rework_rate", "return_rate", "cost_per_order", "on_time_pct", "email_ctr", "engagement_score", "other_opex", "orders"]; ACC = {"discount_rate", "cost_per_order", "unit_cost", "list_price"}
RC = ["driver", "lag", "n", "pearson", "spearman", "p", "lo", "hi", "q", "strength", "acc"]
def rel_table(D, o, drv_, maxlag, det, segs):
    Rs, cols = prep_R(D, [o] + list(drv_), det, segs); rows = []
    if o not in cols: return pd.DataFrame(columns=RC)
    for d in cols[1:]:
        for L in range(int(maxlag) + 1):
            x, y = pairs(Rs, o, d, L); n = len(x); r = dict(driver=d, lag=L, n=n, pearson=np.nan, spearman=np.nan, p=np.nan, lo=np.nan, hi=np.nan)
            if n >= 24 and np.std(x) > 0 and np.std(y) > 0:
                r["pearson"] = stats.pearsonr(x, y)[0]; s = stats.spearmanr(x, y); r["spearman"], r["p"] = s[0], s[1]; z_ = np.arctanh(np.clip(r["spearman"], -.999, .999)); se = 1.06 / math.sqrt(max(n - 3, 1)); r["lo"], r["hi"] = math.tanh(z_ - 1.96 * se), math.tanh(z_ + 1.96 * se)
            rows.append(r)
    T = pd.DataFrame(rows, columns=RC[:8]); T["q"] = np.nan; ok = T.p.notna()
    if ok.any(): T.loc[ok, "q"] = bh(T.p[ok].values)
    T["strength"] = ["insufficient data" if nul(p) else ("supported" if (q < .05 and abs(s) >= .3 and n >= 24) else ("tentative" if p < .05 else "not supported")) for p, q, s, n in zip(T.p, T.q, T.spearman, T.n)]; T["acc"] = T.driver.isin(ACC); return T

# ------------------------------ chronological driver model ------------------------------
def reg_model(D, segs, o="op_margin_pct"):
    parts = []
    for g in segs:
        f = monthly(D["P"], g); X = pd.DataFrame({d: f[d].shift(1) for d in DRV if d in f}); X["prev"] = f[o].shift(1); X["y"] = f[o]; X["seg"] = g; parts.append(X)
    A = pd.concat(parts).dropna(axis=1, how="all").dropna(); per = sorted(A.index.unique())
    if len(per) < 18: return dict(ok=False, why="needs at least 18 monthly periods with complete lagged drivers (found %d): descriptive and correlation analysis only." % len(per))
    cut = per[int(len(per) * .7)]; tr, te = A[A.index < cut], A[A.index >= cut]; cols = [c for c in A.columns if c not in ("y", "seg")]; mu = tr[cols].mean(); sd = tr[cols].std(ddof=0).replace(0, np.nan); Z = lambda d: ((d[cols] - mu) / sd).fillna(0)
    m = Ridge(alpha=5.0).fit(Z(tr), tr.y); pr = m.predict(Z(te)); nv = te["prev"].values; mae = lambda p: float(np.mean(np.abs(te.y.values - p))); perf = pd.DataFrame([dict(model="Naive: previous month's margin", mae=mae(nv)), dict(model="Ridge: lagged drivers + previous margin", mae=mae(pr))]); perf["skill"] = 1 - perf.mae / perf.mae.iloc[0]
    coef = pd.DataFrame(dict(driver=cols, beta=m.coef_)).assign(a=lambda d: d.beta.abs()).sort_values("a", ascending=False).drop(columns="a").head(8); return dict(ok=True, split=(tr.index.max(), te.index.min()), n_tr=len(tr), n_te=len(te), perf=perf, coef=coef)

# ------------------------------ root-cause hypotheses, KPI paradox, actions ------------------------------
HYP = [("disc", "Discounting and acquisition cost erode contribution margin", ["Discounting"], ["discount_rate", "cac"], "discount_rate", "Promotions may defend share against competitors; discount depth may be temporary; volume gained from discounts is not measured here.", "Compare margin and repeat purchase of discounted vs full-price cohorts; test a discount cap in one channel.", "Marketing / Sales"),
       ("mix", "Less favourable product or customer mix raises unit cost", ["Unit cost of goods (incl. product mix)", "List price / list-price mix"], ["low_margin_mix_share", "unit_cost"], "low_margin_mix_share", "Supplier cost inflation or currency effects could explain unit cost; mix is visible only through the reported share.", "Split unit cost into purchase price vs mix at SKU level (price-volume-mix on transaction data).", "Marketing / Finance"),
       ("lab", "Labour cost: overtime, turnover and recruitment outpace output", ["Overtime cost", "Recruitment and training", "Payroll"], ["overtime_hours", "turnover_rate", "capacity_util"], "overtime_hours", "Overtime may reflect volume peaks, not poor planning; turnover may follow labour-market conditions.", "Map overtime to shifts and capacity use; compare turnover cost with the cost of retention measures.", "HR / Operations"),
       ("ops", "Operations inefficiency: rework, returns and cost per order", ["Operations / fulfilment cost"], ["rework_rate", "return_rate", "cost_per_order"], "rework_rate", "Cost per order may rise through carrier tariffs or product size, not only rework.", "Root-cause rework and returns by product and shift; cost expedited shipping separately.", "Operations"),
       ("mkt", "Marketing spend grows faster than its profit payoff", ["Marketing spend"], ["marketing_expense", "cac", "new_customers"], "cac", "Spend may build brand effects beyond the period; attributed customers are not proven incremental.", "Run geo or holdout tests to measure incremental revenue before raising spend further.", "Marketing / Finance"),
       ("oth", "Shared and other costs creep up across cost centres", ["Other operating expenses"], ["other_opex"], "other_opex", "Allocation keys may move shared cost between departments without changing the total.", "Audit allocation keys and recurring items in each cost centre.", "Finance"),
       ("vol", "Volume or list-price headwind", ["Volume (orders)"], ["orders"], "orders", "Seasonality or channel shifts may explain volume changes.", "Compare volume by channel and segment against plan.", "Sales / Finance")]
def hyps(br, REL, q0, mat):
    bd = dict(br["rows"]); bm = mat * abs(q0.operating_profit); rows = []
    for key, title, bk, ind, dv, alt, nxt, dept in HYP:
        amt = sum(bd.get(k, 0) for k in bk); t = REL[(REL.driver == dv) & REL.p.notna()] if len(REL) else REL; b = t.loc[t.spearman.abs().idxmax()] if len(t) else None; st = b.strength if b is not None else "insufficient data"
        lab = ("Strong: accounting + statistical" if st == "supported" else "Moderate: accounting + tentative statistical" if st == "tentative" else "Moderate: accounting only") if amt < -bm else ("Favourable contributor" if amt > bm else "Not material")
        ev = "Bridge: %s (%s). " % (kk(amt), ", ".join(bk)) + (("Relationship of %s with operating margin (monthly changes, trend and season removed): rho %+.2f at lag %d, n=%d, q=%.3f (%s)." % (dv.replace("_", " "), b.spearman, b.lag, b.n, b.q, st)) if b is not None else "No testable relationship (insufficient data).")
        rows.append(dict(key=key, title=title, amount=amt, dept=dept, ind=", ".join(ind), ev=ev, alt=alt, nxt=nxt, label=lab))
    return pd.DataFrame(rows).sort_values("amount").reset_index(drop=True)
def kpi_eval(D, M, ql):
    K = D["K"]; mo = M[M.index.to_period("Q").astype(str) == ql]; rows = []
    for r in K.itertuples():
        v = mo[r.column].mean() if r.column in mo else np.nan; ok = np.nan if nul(v) else bool(v >= r.target if r.direction == "up" else v <= r.target); rows.append(dict(kpi=r.kpi, dept=r.department, value=v, target=r.target, dirn=r.direction, met=ok, label="Met" if ok is True else ("Not met" if ok is False else "n/a")))
    return pd.DataFrame(rows, columns=["kpi", "dept", "value", "target", "dirn", "met", "label"])
ACT = dict(disc=("Introduce discount guardrails (cap depth, margin sign-off) and review the promotion calendar", .3, "Volume may fall if discounts are cut; competitors may respond", "Discount rate, contribution margin per order"), mix=("Review assortment and pricing of low-margin products; add margin targets to sales incentives", .5, "Fewer low-margin sales may reduce traffic", "Low-margin mix share, unit cost, gross margin"),
           lab=("Rebalance shifts and workforce plan to cut overtime; target retention in high-turnover roles", .5, "Hiring adds fixed cost; retention measures may not work", "Overtime hours, turnover rate, labour cost per order"), ops=("Root-cause rework and returns; reduce expedited shipping", .6, "Quality controls can slow throughput", "Rework rate, return rate, cost per order"),
           mkt=("Shift spend to channels with better margin; test incrementality with holdouts", .4, "Lower spend may reduce reach", "CAC, incremental revenue, contribution margin"), oth=("Audit shared-cost allocation and recurring items", .3, "Cuts may move cost between departments", "Other opex as % of revenue"), vol=("Investigate the volume shortfall against plan by channel", .4, "Chasing volume can add discounts", "Orders, revenue vs budget"))
def actions(R):
    h = R["hy"][R["hy"].label.str.startswith(("Strong", "Moderate"))]; rows = []; mx = max(h.amount.abs().max(), 1e-9) if len(h) else 1
    for r in h.itertuples():
        a = ACT[r.key]; es = 1.0 if r.label.startswith("Strong") else (.7 if "tentative" in r.label else .5); rows.append(dict(problem=r.title, evidence=r.ev, action=a[0], dept=r.dept, impact=r.amount, effort=a[1], evid_s=es, label=r.label, risks=a[2], kpi=a[3], review="Next quarter", score=100 * (.5 * abs(r.amount) / mx + .3 * es + .2 * (1 - a[1]))))
    return pd.DataFrame(rows, columns=["problem", "evidence", "action", "dept", "impact", "effort", "evid_s", "label", "risks", "kpi", "review", "score"]).sort_values("score", ascending=False).reset_index(drop=True)
def getR(seg, cur, base, thr):
    key = (seg, str(cur), str(base), float(thr), G["ver"])
    if key in G["_c"]: return G["_c"][key]
    D = G["D"]; M = monthly(D["P"], seg); Q = quarterly(M)
    if len(Q) < 5: raise ValueError("Need at least 5 complete quarters (found %d)." % len(Q))
    ql = list(Q.index); cur = cur if cur in ql else ql[-1]; i = ql.index(cur); base = base if (base in ql and base != cur) else ql[max(i - 1, 0)]; q1, q0 = Q.loc[cur], Q.loc[base]; segs = D["segs"] if seg == "All" else [seg]
    REL = rel_table(D, "op_margin_pct", DRV, 2, True, segs); br = bridge(q0, q1); sh, tot = shapley(drv(q0), drv(q1)); R = dict(M=M, Q=Q, cur=cur, base=base, i=i, q1=q1, q0=q0, prev=Q.iloc[i - 1] if i > 0 else None, py=Q.iloc[i - 4] if i >= 4 else None, br=br, sh=sh, shtot=tot, rel=REL, thr=thr / 100, segs=segs, kp=kpi_eval(D, M, cur), streak=streak(Q, i))
    R["hy"] = hyps(br, REL, q0, thr / 100); R["act"] = actions(R); G["_c"][key] = R; return R

# ------------------------------ scenario model (joint, interaction-aware) ------------------------------
def scen(x, lev, f, el):
    d = x["d"] - lev["disc"] * f / 100; O = x["O"] * (1 - el * lev["disc"] * f / 100) * (1 + lev["mel"] * lev["mkt"] * f / 100); y = dict(O=O, L=x["L"], d=d, c=x["c"], Mk=x["Mk"] * (1 + lev["mkt"] * f / 100), Lab=x["Lab"] - x["ot"] * lev["ot"] * f / 100, Ops=x["Ops"] * (1 - lev["ops"] * f / 100) * O / x["O"], Oth=x["Oth"] * (1 + lev["oth"] * f / 100))
    rev = O * x["L"] * (1 - d) / 1000; op = opf(y); return dict(rev=rev, op=op, om=100 * op / rev if rev else np.nan)

# ------------------------------ analyst narrative (deterministic) ------------------------------
def report(R):
    q1, q0, Q, i = R["q1"], R["q0"], R["Q"], R["i"]; br = R["br"]; rows = sorted(br["rows"], key=lambda t: t[1]); kp = R["kp"]; hy = R["hy"]; sp = R["rel"][R["rel"].strength == "supported"].assign(a=lambda d: d.spearman.abs()).sort_values("a", ascending=False).head(3) if len(R["rel"]) else R["rel"]; A = R["act"]
    rg, og = ch(q1.revenue, q0.revenue), ch(q1.operating_profit, q0.operating_profit); met = int((kp.met == True).sum()) if len(kp) else 0; n = int(kp.met.notna().sum()) if len(kp) else 0
    s1 = "In %s operating profit was %s (margin %s) versus %s in %s: %s. It has fallen for %d consecutive quarter(s). Revenue changed %s over the same comparison, so %s. %s" % (R["cur"], kk(q1.operating_profit), nf(q1.op_margin_pct, 1) + "%", kk(q0.operating_profit), R["base"], sg(og), R["streak"], sg(rg), "growth was not profitable growth" if (not nul(rg) and rg > 0 and not nul(og) and og < 0) else "revenue and profit moved together", ("Departmental KPIs: %d of %d are on target, yet company profit fell, so targets are not capturing the interactions." % (met, n)) if n else "No departmental KPI table was supplied.")
    s2 = "Bridge from %s to %s (reconciles to the actual change within ₹%sk: %s): " % (R["base"], R["cur"], nf(br["tol"], 1), "yes" if br["ok"] else "NO, difference %s" % kk(br["diff"])) + "; ".join("%s %s" % (a, kk(b)) for a, b in rows[:4]) + ". Shapley attribution (shares interactions fairly): " + "; ".join("%s %s" % (SH[k], kk(v)) for k, v in sorted(R["sh"].items(), key=lambda t: t[1])[:3]) + "."
    s3 = ("Relationships that survive trend/season removal and multiple-testing control (q<0.05): " + "; ".join("%s ↔ operating margin (lag %d, rho %+.2f, n=%d, q=%.3f)" % (r.driver.replace("_", " "), r.lag, r.spearman, r.n, r.q) for r in sp.itertuples()) + ". Several of these drivers moved together, so correlation cannot separate them; use the accounting bridge for magnitudes. These are associations, not causes.") if len(sp) else "No relationship passed the multiple-testing screen: treat patterns as tentative."
    s4 = " | ".join("%s — %s [%s]" % (r.title, r.ev, r.label) for r in hy.head(4).itertuples()); s5 = "; ".join("%s (%s)" % (r.title, r.label) for r in hy.itertuples() if r.label.startswith("Moderate")) or "All material hypotheses have statistical support, but every one still needs causal validation."; s5 += " Alternatives to check: " + " ".join(r.alt for r in hy.head(2).itertuples())
    s6 = "; ".join("#%d %s: %s (departments: %s)" % (k + 1, r.problem, r.action, r.dept) for k, r in enumerate(A.head(3).itertuples())) or "No material adverse driver was found."; s7 = "Track weekly or monthly for two quarters: operating margin, contribution margin, " + "; ".join(sorted(set(k for r in A.head(3).itertuples() for k in [r.kpi]))) + ". Success = margin recovery without losing agreed volume; confirm with a holdout or phased rollout."
    return [("1. What happened to profitability?", s1), ("2. Which financial components explain the decline?", s2), ("3. Which cross-functional relationships deserve attention?", s3), ("4. What evidence supports each finding?", s4), ("5. Which hypotheses remain unverified?", s5), ("6. What should management investigate or change?", s6), ("7. How should success be measured?", s7)]
def ask(q, _=None):
    if "D" not in G: return "Load data first."
    f = G.get("f") or ("All", None, None, 2); R = getR(*f); rp = report(R); q = (q or "").strip() or "What happened to profitability?"; ql = q.lower(); idx = []
    for pat, ks in ((r"happen|profit|declin|summary|why", [0, 1]), (r"component|bridge|explain|driver", [1]), (r"relationship|correl|associat|cross", [2]), (r"evidence|support", [3]), (r"unverified|uncertain|limit|caveat|trust", [4]), (r"should|action|recommend|change|investigate", [5]), (r"measure|success|kpi|track", [6])):
        if re.search(pat, ql): idx += ks
    idx = list(dict.fromkeys(idx)) or [0, 5]; return "### Answer (deterministic, computed from the loaded data)\n" + "\n".join("- **%s**: %s" % (rp[k][0], rp[k][1]) for k in idx) + "\n\n*Every figure is computed from the active dataset; associations are not causes; scenarios are hypothetical; management judgement is required.*"

# ------------------------------ pages ------------------------------
def wf(vals, labels, title):
    f = go.Figure(go.Waterfall(x=list(labels) + ["Total"], measure=["relative"] * len(vals) + ["total"], y=list(vals) + [0], increasing=dict(marker=dict(color=C["sg"])), decreasing=dict(marker=dict(color=C["co"])), totals=dict(marker=dict(color=C["mid"])), connector=dict(line=dict(color=C["st"])))); return sty(f, 360, title)
@safe(4)
def render_cc(seg, cur, base, thr):
    R = getR(seg, cur, base, thr); G["f"] = (seg, cur, base, thr); Q, q, p, i = R["Q"], R["q1"], R["prev"], R["i"]; g = lambda a, c: sg(ch(a, c)); pq = p if p is not None else q
    h = banner() + "<div class='kg'>" + card("Revenue", kk(q.revenue), "QoQ " + g(q.revenue, pq.revenue)) + card("Gross profit", kk(q.gross_profit), "margin %s%% · QoQ %s" % (nf(q.gross_margin_pct, 1), g(q.gross_profit, pq.gross_profit))) + card("Operating costs", kk(q.total_costs), "%s%% of revenue · QoQ %s" % (nf(q.cost_to_revenue, 1), g(q.total_costs, pq.total_costs)), C["co"]) + card("Operating profit", kk(q.operating_profit), "margin %s%% · QoQ %s" % (nf(q.op_margin_pct, 1), g(q.operating_profit, pq.operating_profit)), C["co"]) + \
        card("Marketing spend", kk(q.marketing_expense), "CAC ₹%s · QoQ spend %s" % (nf(q.cac), g(q.marketing_expense, pq.marketing_expense))) + card("Labour cost", kk(q.labour_cost), "payroll %s · overtime %s · recruit %s" % (kk(q.payroll), kk(q.overtime_cost), kk(q.recruit_train_cost))) + card("Operations cost per order", "₹" + nf(q.cost_per_order, 1), "QoQ " + g(q.cost_per_order, pq.cost_per_order)) + card("Operating profit vs budget", sg(ch(q.operating_profit, q.get("budget_operating_profit"))), "budget %s" % kk(q.get("budget_operating_profit"))) + card("Consecutive declining quarters", str(R["streak"]), "operating profit, ending " + R["cur"], C["co"]) + "</div>"
    rp = report(R); h += note("Facts are measured from the data; relationships are statistical associations; bridges are accounting arithmetic; scenarios are hypothetical.", "info") + "".join("<div class='note' style='border-left:4px solid %s'><b>%s</b><br>%s</div>" % (C["go"], a, esc(b)) for a, b in (rp[0], rp[1], rp[5]))
    Z = Q.tail(12); col = [C["co"] if (k > 0 and Z.operating_profit.iloc[k] < Z.operating_profit.iloc[k - 1]) else C["mid"] for k in range(len(Z))]; f1 = go.Figure([go.Bar(x=Z.index, y=Z.operating_profit, marker_color=col, name="Operating profit (coral = declined vs prior quarter)")] + ([go.Scatter(x=Z.index, y=Z.budget_operating_profit, name="Budget", line=dict(color=C["go"], dash="dot", width=3))] if "budget_operating_profit" in Z else [])); f1 = sty(f1, 340, "Quarterly operating profit vs budget (₹k)")
    ix = Z[["revenue", "operating_profit"]] / Z[["revenue", "operating_profit"]].iloc[0] * 100; f2 = sty(go.Figure([go.Scatter(x=ix.index, y=ix[c], name=n, line=dict(width=3)) for c, n in (("revenue", "Revenue"), ("operating_profit", "Operating profit"))]), 320, "Revenue growth vs profitable growth (index, first quarter shown = 100)")
    f3 = go.Figure([go.Bar(x=Z.index, y=100 * Z[c] / Z.revenue, name=n) for c, n in (("cogs", "COGS"), ("marketing_expense", "Marketing"), ("labour_cost", "Labour"), ("ops_cost", "Operations"), ("other_opex", "Other"))]); f3.update_layout(barmode="stack"); f3 = sty(f3, 340, "Cost structure as % of revenue"); return h, f1, f2, f3
@safe(3)
def render_inv(seg, cur, base, thr):
    R = getR(seg, cur, base, thr); q1, q0, br = R["q1"], R["q0"], R["br"]; bud = None
    if "budget_operating_profit" in q1 and not nul(q1.get("budget_operating_profit")): bud = pd.Series(dict(operating_profit=q1.budget_operating_profit, revenue=q1.budget_revenue, op_margin_pct=100 * q1.budget_operating_profit / q1.budget_revenue))
    def cmpr(lab, a, b):
        return None if (b is None or nul(b.get("operating_profit"))) else dict(vs=lab, o0=b.operating_profit, o1=a.operating_profit, d=a.operating_profit - b.operating_profit, dp=ch(a.operating_profit, b.operating_profit), m0=b.op_margin_pct, m1=a.op_margin_pct, dm=a.op_margin_pct - b.op_margin_pct, dr=ch(a.revenue, b.revenue))
    cs = [x for x in [cmpr("Previous quarter", q1, R["prev"]), cmpr("Same quarter last year", q1, R["py"]), cmpr("Budget", q1, bud), cmpr("Baseline (%s)" % R["base"], q1, q0)] if x]
    h = banner() + note("<b>Current quarter %s.</b> Absolute profit change (₹k) and margin change (percentage points) are shown separately: a margin can fall while profit rises, and revenue can grow while profit falls (<b>revenue growth ≠ profitable growth</b>)." % R["cur"], "info") + tbl(pd.DataFrame(cs), [("vs", "Compared with"), ("o0", "Operating profit then"), ("o1", "Operating profit now"), ("d", "Change ₹k"), ("dp", "Change %"), ("m0", "Margin then %"), ("m1", "Margin now %"), ("dm", "Margin change (pts)"), ("dr", "Revenue change")], dict(o0=kk, o1=kk, d=kk, dp=sg, m0=lambda v: nf(v, 1), m1=lambda v: nf(v, 1), dm=lambda v: "%+.1f" % v, dr=sg))
    rows = pd.DataFrame(br["rows"], columns=["c", "v"]); rows["sh"] = rows.v / br["actual"] if br["actual"] else np.nan; ok = br["ok"]
    h += SEC("Operating-profit bridge: %s → %s" % (R["base"], R["cur"])) + tbl(rows, [("c", "Component"), ("v", "Impact ₹k"), ("sh", "Share of change")], dict(v=kk, sh=lambda v: pc(v, 0))) + note("%s Bridge total %s vs actual change %s (difference %s; tolerance ₹%sk). Formula: OP = orders × (list price × (1 − discount) − unit cost) − marketing − labour − operations − other; each line is exact and sums to the change. Missing months or unreconciled P&L rows would show up as a difference." % (pill("Reconciled" if ok else "Not reconciled"), kk(br["total"]), kk(br["actual"]), kk(br["diff"]), nf(br["tol"], 1)), "ok" if ok else "err")
    cost_g = ch(q1.total_costs, q0.total_costs); h += note("Revenue %s vs costs %s: %s." % (sg(ch(q1.revenue, q0.revenue)), sg(cost_g), "cost growth outpaced revenue growth" if (not nul(cost_g) and cost_g > ch(q1.revenue, q0.revenue)) else "cost growth did not outpace revenue"), "info")
    Z = R["Q"].tail(8); h += SEC("Last 8 quarters") + tbl(Z.reset_index().rename(columns={"index": "q"}), [("q", "Quarter"), ("revenue", "Revenue"), ("gross_margin_pct", "Gross margin %"), ("total_costs", "Operating costs"), ("operating_profit", "Operating profit"), ("op_margin_pct", "Operating margin %")], dict(revenue=kk, gross_margin_pct=lambda v: nf(v, 1), total_costs=kk, operating_profit=kk, op_margin_pct=lambda v: nf(v, 1)))
    f1 = wf([v for _, v in br["rows"]], [c for c, _ in br["rows"]], "Profit bridge (₹k)"); f1.update_xaxes(tickangle=-30); f2 = sty(go.Figure(go.Bar(x=Z.index, y=Z.op_margin_pct, marker_color=C["li"])), 300, "Operating margin by quarter (%)"); f3 = sty(go.Figure(go.Bar(x=Z.index, y=Z.gross_margin_pct, marker_color=C["sg"])), 300, "Gross margin by quarter (%)"); return h, f1, f2, f3
@safe(4)
def render_rel(seg, cur, base, thr, o, ml, det, sel):
    R = getR(seg, cur, base, thr); D = G["D"]; o = o or "op_margin_pct"; T = rel_table(D, o, DRV, ml, bool(det), R["segs"]); ok = T[T.p.notna()]
    h = banner() + note("<b>Outcome:</b> %s. Monthly data, aligned by month and segment (grains are never mixed). %s A lag of L means the driver is taken L months earlier. %d tests: p-values are corrected with Benjamini–Hochberg (q). <b>Correlation is not causation</b>: marketing spend rising with revenue may only reflect growth, which is why trend and season are removed first." % (o.replace("_", " "), "Linear trend and calendar-month effects are removed from every series (per segment)." if det else "<b>Raw levels are used: shared trends can create false correlations.</b>", len(ok)), "info")
    tp = ok.assign(a=ok.spearman.abs()).sort_values("a", ascending=False).head(25); h += tbl(tp, [("driver", "Driver"), ("lag", "Lag (mo)"), ("n", "n"), ("pearson", "Pearson"), ("spearman", "Spearman"), ("lo", "95% low"), ("hi", "95% high"), ("p", "p"), ("q", "q (FDR)"), ("strength", "Evidence"), ("acc", "Part of the margin arithmetic")], dict(pearson=lambda v: nf(v, 2), spearman=lambda v: nf(v, 2), lo=lambda v: nf(v, 2), hi=lambda v: nf(v, 2), p=lambda v: nf(v, 4), q=lambda v: nf(v, 4), acc=lambda v: "yes" if v else ""))
    Rs, cols = prep_R(D, [o] + DRV, bool(det), R["segs"]); top = tp.driver.drop_duplicates().head(8).tolist()
    if len(top) > 1: C_ = pd.concat([r[top] for r in Rs]).corr(); pr = [(a, b, C_.loc[a, b]) for k, a in enumerate(top) for b in top[k + 1:] if abs(C_.loc[a, b]) > .85]; h += note("Multicollinearity among top drivers (|r| > 0.85): " + ("; ".join("%s ~ %s (%.2f)" % t for t in pr) if pr else "none") + ". Drivers that move together cannot be told apart by correlation; they share the same evidence.", "warn" if pr else "info")
    hm = ok.pivot_table(index="driver", columns="lag", values="spearman"); order = hm.abs().max(axis=1).sort_values(ascending=False).head(15).index; f1 = go.Figure(go.Heatmap(z=hm.loc[order].values, x=["lag %d" % c for c in hm.columns], y=list(order), zmin=-1, zmax=1, colorscale=[[0, C["co"]], [.5, "#ffffff"], [1, C["mid"]]])) if len(hm) else empty("Not enough data"); f1 = sty(f1, 420, "Spearman heatmap: top 15 drivers by lag")
    sel = sel if sel in cols else (tp.driver.iloc[0] if len(tp) else None); f2 = f3 = empty("No driver")
    if sel:
        L = int(tp[tp.driver == sel].lag.iloc[0]) if (tp.driver == sel).any() else 0; x, y = pairs(Rs, o, sel, L)
        if len(x) > 5: cf = np.polyfit(x, y, 1); xs = np.linspace(x.min(), x.max(), 20); f2 = sty(go.Figure([go.Scatter(x=x, y=y, mode="markers", marker=dict(color=C["mid"], size=7), name="Segment-months"), go.Scatter(x=xs, y=cf[0] * xs + cf[1], line=dict(color=C["go"], width=3), name="Linear trend")]), 340, "%s (lag %d) vs %s%s, n=%d" % (sel, L, o, " (detrended residuals)" if det else "", len(x)))
        fr = monthly(D["P"], R["segs"][0] if len(R["segs"]) == 1 else "All"); f3 = sty(go.Figure([go.Scatter(x=fr.index, y=fr[c] / fr[c].dropna().iloc[0] * 100, name=c, line=dict(width=3)) for c in (sel, "op_margin_pct") if c in fr and fr[c].notna().any()]), 320, "Levels indexed to 100 at the first month (context only)")
    return h, f1, f2, f3
@safe(3)
def render_rc(seg, cur, base, thr):
    R = getR(seg, cur, base, thr); hy = R["hy"]; kp = R["kp"]; met = int((kp.met == True).sum()) if len(kp) else 0; n = int(kp.met.notna().sum()) if len(kp) else 0
    h = banner() + note("<b>Hypotheses are templates; the amounts and statistics come from the data.</b> Strength: <i>Strong</i> = material adverse bridge amount (≥ %s of baseline profit) plus a relationship that survives FDR control; <i>Moderate</i> = accounting evidence with weaker or no statistical support. Accounting reconciliation, statistical association and causal proof are different things: nothing here proves causation." % pc(R["thr"], 0), "info")
    h += (note("<b>Departmental paradox:</b> %d of %d departmental KPIs are on target in %s, yet operating profit fell %s versus %s." % (met, n, R["cur"], sg(ch(R["q1"].operating_profit, R["q0"].operating_profit)), R["base"]), "warn") if n else "") + SEC("Ranked cross-department hypotheses (most adverse first)")
    for r in hy.itertuples(): h += "<div class='tw'><table><tr><th colspan='2'>%s &nbsp; %s</th></tr>" % (esc(r.title), pill(r.label)) + "".join("<tr><td style='width:230px'><b>%s</b></td><td>%s</td></tr>" % (a, esc(b)) for a, b in [("Observed deterioration (bridge, %s → %s)" % (R["base"], R["cur"]), kk(r.amount)), ("Related departmental indicators", r.ind), ("Departments", r.dept), ("Periods", "%s vs %s; segment: %s" % (R["cur"], R["base"], R["segs"][0] if len(R["segs"]) == 1 else "all")), ("Supporting evidence", r.ev), ("Alternative explanations", r.alt), ("Next analysis or validation step", r.nxt)]) + "</table></div>"
    if len(kp): h += SEC("Departmental KPIs vs targets, %s (monthly averages)" % R["cur"]) + tbl(kp, [("kpi", "KPI"), ("dept", "Department"), ("value", "Value"), ("target", "Target"), ("dirn", "Better when"), ("label", "Status")], dict(value=lambda v: nf(v, 1), target=lambda v: nf(v, 1), label=pill))
    f1 = go.Figure(go.Bar(y=hy.title, x=hy.amount, orientation="h", marker_color=[C["co"] if v < 0 else C["sg"] for v in hy.amount])); f1 = sty(f1, 360, "Bridge impact by hypothesis (₹k; negative = adverse)"); f1.update_yaxes(autorange="reversed"); f2 = empty("No KPI table")
    if len(kp): f2 = sty(go.Figure(go.Bar(x=kp.kpi, y=kp.label.map({"Met": 1, "Not met": 0}).fillna(.5), marker_color=[C["sg"] if l == "Met" else C["co"] for l in kp.label])), 300, "Departmental KPI status (1 = met)"); f2.update_xaxes(tickangle=-25)
    return h, f1, f2
@safe(3)
def render_attr(seg, cur, base, thr):
    R = getR(seg, cur, base, thr); br = dict(R["br"]["rows"]); seq = dict(O=br["Volume (orders)"], L=br["List price / list-price mix"], d=br["Discounting"], c=br["Unit cost of goods (incl. product mix)"], Mk=br["Marketing spend"], Lab=br["Payroll"] + br["Overtime cost"] + br["Recruitment and training"], Ops=br["Operations / fulfilment cost"], Oth=br["Other operating expenses"])
    T = pd.DataFrame([dict(driver=SH[k], seq=seq[k], shap=R["sh"][k], inter=R["sh"][k] - seq[k]) for k in SH]); act = R["br"]["actual"]
    h = banner() + note("<b>Two accounting allocations of the same change</b> (%s → %s). The sequential bridge is order-dependent (volume is valued at old margins). The <b>Shapley allocation</b> averages over all 8! orderings, so interactions (for example a larger volume at a lower price) are shared fairly. Both sum exactly to the actual change %s (Shapley total %s). They are <b>explanatory allocations, not causal effects</b>, and each expense appears once (no double counting)." % (R["base"], R["cur"], kk(act), kk(R["shtot"])), "info") + tbl(T, [("driver", "Driver"), ("seq", "Sequential bridge ₹k"), ("shap", "Shapley ₹k"), ("inter", "Interaction share ₹k")], dict(seq=kk, shap=kk, inter=kk))
    m = reg_model(G["D"], R["segs"]); h += SEC("Predictive check: can last month's indicators predict this month's operating margin?")
    if not m["ok"]: h += note("Driver model disabled: " + esc(m["why"]), "warn")
    else: h += note("Chronological split: train months before %s (%d rows, latest %s), test from %s (%d rows). Drivers are lagged one month and standardised with <b>training months only</b>; no random split. Skill = 1 − MAE ÷ MAE of the naive previous-month forecast; a model that does not beat the naive baseline adds no predictive value. Coefficients show model reliance, <b>not causal impact</b>." % (m["split"][1].strftime("%b %Y"), m["n_tr"], m["split"][0].strftime("%b %Y"), m["split"][1].strftime("%b %Y"), m["n_te"]), "ai") + tbl(m["perf"], [("model", "Model (held-out test)"), ("mae", "MAE (margin pts)"), ("skill", "Skill vs naive")], dict(mae=lambda v: nf(v, 2), skill=sg)) + tbl(m["coef"], [("driver", "Feature (standardised)"), ("beta", "Ridge coefficient")], dict(beta=lambda v: nf(v, 3)))
    f1 = wf(list(T.shap), list(T.driver), "Shapley attribution of the operating-profit change (₹k)"); f1.update_xaxes(tickangle=-30); f2 = go.Figure([go.Bar(x=T.driver, y=T.seq, name="Sequential bridge", marker_color=C["st"]), go.Bar(x=T.driver, y=T.shap, name="Shapley", marker_color=C["mid"])]); f2.update_layout(barmode="group"); f2 = sty(f2, 340, "Sequential vs Shapley allocation (₹k)"); f2.update_xaxes(tickangle=-30); return h, f1, f2
@safe(4)
def render_dept(seg, cur, base, thr):
    R = getR(seg, cur, base, thr); Q = R["Q"].tail(8)
    def sect(title, cols, fm, txt):
        c = [(k, n) for k, n in cols if k in Q]; return SEC(title) + note(txt, "info") + tbl(Q.reset_index().rename(columns={"index": "q"}), [("q", "Quarter")] + c, {k: fm.get(k, lambda v: nf(v, 1)) for k, _ in c})
    Q = Q.assign(disc_cost=Q.gross_sales * Q.discount_rate / 100, labour_pct=100 * Q.labour_cost / Q.revenue, ops_pct=100 * Q.ops_cost / Q.revenue, mkt_pct=100 * Q.marketing_expense / Q.revenue, cm_pct=100 * Q.contribution_margin / Q.revenue)
    h = banner() + sect("Marketing profitability", [("marketing_expense", "Spend ₹k"), ("budget_marketing_expense", "Budget ₹k"), ("mkt_pct", "Spend % revenue"), ("cac", "CAC ₹"), ("new_customers", "New customers"), ("conversion_rate", "Conversion %"), ("discount_rate", "Discount %"), ("disc_cost", "Discount cost ₹k"), ("low_margin_mix_share", "Low-margin mix %"), ("cm_pct", "Contribution margin %")], dict(marketing_expense=kk, budget_marketing_expense=kk, disc_cost=kk, new_customers=lambda v: nf(v)), "Attributed customers are not proven incremental, and a lower CAC does not mean more profitable customers. Channel and campaign data were not supplied, so channel-level margin and incrementality are unavailable.")
    h += sect("HR cost and workforce", [("payroll", "Payroll ₹k"), ("overtime_cost", "Overtime ₹k"), ("recruit_train_cost", "Recruit + train ₹k"), ("labour_pct", "Labour % revenue"), ("headcount", "Headcount"), ("overtime_hours", "Overtime hours"), ("turnover_rate", "Turnover %/mo"), ("absence_rate", "Absence %"), ("engagement_score", "Engagement")], dict(payroll=kk, overtime_cost=kk, recruit_train_cost=kk, headcount=lambda v: nf(v), overtime_hours=lambda v: nf(v)), "The full labour cost includes overtime, turnover and recruitment, not payroll alone. Findings concern workforce conditions, not individual employees; output per labour hour needs labour-hours data that was not supplied.")
    h += sect("Operations cost and efficiency", [("orders", "Orders"), ("ops_cost", "Ops cost ₹k"), ("ops_pct", "Ops % revenue"), ("cost_per_order", "Cost / order ₹"), ("capacity_util", "Capacity use %"), ("rework_rate", "Rework %"), ("return_rate", "Returns %"), ("on_time_pct", "On-time %")], dict(orders=lambda v: nf(v), ops_cost=kk), "Cost growth is split in the bridge into volume (orders) and unit cost; the rework and return rates are associated with cost per order, not proven causes.")
    f1 = go.Figure([go.Scatter(x=Q.index, y=Q.discount_rate, name="Discount %", line=dict(width=3)), go.Scatter(x=Q.index, y=Q.low_margin_mix_share, name="Low-margin mix %", line=dict(width=3))]); f1 = sty(f1, 320, "Discounting and product mix")
    f2 = sty(go.Figure([go.Bar(x=Q.index, y=Q.labour_pct, name="Labour % revenue", marker_color=C["li"]), go.Bar(x=Q.index, y=Q.ops_pct, name="Operations % revenue", marker_color=C["go"])]), 320, "Labour and operations cost as % of revenue"); f3 = sty(go.Figure([go.Scatter(x=Q.index, y=Q.cac, name="CAC ₹", line=dict(width=3, color=C["mid"]))]), 300, "Customer acquisition cost"); f4 = sty(go.Figure([go.Scatter(x=Q.index, y=Q.rework_rate, name="Rework %", line=dict(width=3)), go.Scatter(x=Q.index, y=Q.capacity_util / 10, name="Capacity use % ÷ 10", line=dict(width=3, dash="dot"))]), 300, "Rework and capacity use"); return h, f1, f2, f3, f4
@safe(2)
def render_fin(seg, cur, base, thr):
    R = getR(seg, cur, base, thr); D = G["D"]; P = D["P"]; q = R["q1"]; g = (P.gross_profit - (P.revenue - P.cogs)).abs().max(); o = (P.operating_profit - (P.revenue - P.cogs - P[COST].sum(axis=1))).abs().max()
    ck = pd.DataFrame([("Gross profit = revenue − COGS (largest monthly difference)", g, g < .01 * P.revenue.mean()), ("Operating profit = gross profit − operating costs (largest monthly difference)", o, o < .01 * P.revenue.mean()), ("Profit bridge reconciles to actual change (difference)", R["br"]["diff"], R["br"]["ok"])], columns=["c", "v", "ok"])
    h = banner() + note("Finance integrity is checked <b>before</b> any recommendation: an accounting discrepancy is not an operational driver. Tolerances: 1% of mean monthly revenue for identities; the bridge uses ₹%sk." % nf(R["br"]["tol"], 1), "info") + tbl(ck.assign(s=ck.ok.map({True: "Reconciled", False: "Not reconciled"})), [("c", "Check"), ("v", "Difference ₹k"), ("s", "Result")], dict(v=lambda v: nf(v, 3), s=pill))
    L = pd.DataFrame([dict(line=c.replace("_", " "), act=q[c], bud=q.get("budget_" + c, np.nan)) for c in ["cogs"] + COST]); L["var"] = L.act - L.bud; L["varp"] = L["var"] / L.bud.abs(); n_over = int((L["var"] > 0).sum())
    h += SEC("Actual vs budget by cost line, %s" % R["cur"]) + tbl(L, [("line", "Line"), ("act", "Actual ₹k"), ("bud", "Budget ₹k"), ("var", "Variance ₹k (+ = over budget)"), ("varp", "Variance %")], dict(act=kk, bud=kk, var=kk, varp=sg)) + note("%d of %d lines are over budget. When every cost centre is individually within budget while profit falls, the budgets are not capturing cross-department interactions (shared drivers such as discounting, mix and overtime)." % (n_over, len(L)), "warn" if n_over else "info")
    h += SEC("Data-quality log") + ("".join(note(esc(m), "err" if l == "error" else "warn" if l == "warn" else "info") for l, m in D["issues"]) or note("No validation issues.", "ok")) + (tbl(pd.DataFrame(D["excluded"], columns=["t", "w", "c"]), [("t", "Table"), ("w", "Reason"), ("c", "Rows")]) if D["excluded"] else "") + note("Definitions: operating costs = marketing + payroll + overtime + recruitment/training + operations + other. Shared-cost allocation keys and account mappings are assumed consistent across the uploaded tables; verify them with Finance.", "info")
    f = go.Figure(go.Bar(x=L.line, y=L.varp * 100, marker_color=[C["co"] if v > 0 else C["sg"] for v in L.varp])); return h, sty(f, 320, "Cost-line variance vs budget (%)")
@safe(3)
def render_ana(seg, cur, base, thr):
    R = getR(seg, cur, base, thr); rp = report(R); h = banner() + note("<b>Investigation report</b> generated from the computed results (no LLM). Each statement quotes the data fields behind it; associations and accounting facts are labelled separately.", "ai") + "".join("<div class='note' style='border-left:4px solid %s'><b>%s</b><br>%s</div>" % (C["go"], a, esc(b)) for a, b in rp)
    h += SEC("Evidence references") + note("Dataset fields: financials (revenue, cogs, %s), marketing (gross_sales, new_customers, conversion_rate, low_margin_mix_share), hr (headcount, overtime_hours, turnover_rate), operations (orders, capacity_util, rework_rate, return_rate). Periods: %s vs %s. Calculations: profit bridge, Shapley attribution, trend-and-season-adjusted Spearman with BH FDR, chronological Ridge check." % (", ".join(COST), R["cur"], R["base"]), "info"); return h, None, None
@safe(3)
def render_act(seg, cur, base, thr, ds, ot, ops, mk, mel, oc, el):
    R = getR(seg, cur, base, thr); A = R["act"]; q = R["q1"]; x = dict(drv(q), ot=q.overtime_cost); lev = dict(disc=float(ds or 0), ot=float(ot or 0), ops=float(ops or 0), mkt=float(mk or 0), mel=float(mel or 0), oth=float(oc or 0)); el = float(el or 0); G["A"] = A
    h = banner() + SEC("Corrective action register (proposed; human review required)") + (tbl(A, [("problem", "Problem"), ("evidence", "Supporting evidence"), ("action", "Proposed intervention"), ("dept", "Departments"), ("impact", "Measured adverse movement ₹k"), ("effort", "Effort (0-1)"), ("label", "Evidence strength"), ("risks", "Risks and trade-offs"), ("kpi", "Success metrics"), ("review", "Review"), ("score", "Priority")], dict(impact=kk, effort=lambda v: nf(v, 1), label=pill, score=lambda v: nf(v, 0))) if len(A) else note("No material adverse driver found.", "ok")) + note("Priority = 100 × (0.5 × impact share + 0.3 × evidence strength + 0.2 × (1 − effort)). It ranks attention and is <b>not a probability of success</b>. 'Impact' is the measured adverse bridge movement, not a promised saving; effort values are heuristic defaults.", "info")
    runs = {"Base (no change)": (0, 1), "Downside (50% of levers realised, volume loss ×2)": (.5, 2), "Scenario (levers as entered)": (1, 1), "Upside (125% realised, volume loss ×0.5)": (1.25, .5)}; S = {k: scen(x, lev, f, el * m) for k, (f, m) in runs.items()}; b0 = S["Base (no change)"]["op"]
    h += SEC("Scenario lab: joint model on %s run-rate (hypothetical)" % R["cur"]) + note("<b>Assumption-based illustration, not a forecast and not realised savings.</b> All levers are applied <b>together in one model</b>: orders respond to discount cuts (%.1f%% fewer orders per point cut, your assumption) and to marketing changes (%.2f%% orders per 1%% spend); operations cost scales with orders; COGS follows volume. Benefits therefore interact instead of being added." % (el, lev["mel"]), "warn")
    h += tbl(pd.DataFrame([[n, s["rev"], s["op"], s["om"], s["op"] - b0] for n, s in S.items()], columns=["n", "r", "o", "m", "d"]), [("n", "Scenario"), ("r", "Revenue ₹k"), ("o", "Operating profit ₹k"), ("m", "Margin %"), ("d", "Change vs base ₹k")], dict(r=kk, o=kk, m=lambda v: nf(v, 1), d=kk))
    one = [(n, scen(x, {**{k: 0 for k in lev}, "mel": lev["mel"], k_: lev[k_]}, 1, el)["op"] - b0) for n, k_ in (("Discount cut alone", "disc"), ("Overtime reduction alone", "ot"), ("Rework / operations fix alone", "ops"), ("Marketing change alone", "mkt"), ("Other-cost change alone", "oth"))]; joint = S["Scenario (levers as entered)"]["op"] - b0; sm = sum(v for _, v in one)
    h += SEC("Double-counting check") + tbl(pd.DataFrame(one + [("Sum of independent effects", sm), ("Joint model effect", joint), ("Interaction (joint − sum)", joint - sm)], columns=["n", "v"]), [("n", "Lever"), ("v", "Effect on operating profit ₹k")], dict(v=kk)) + note("Adding independent estimates would give %s; the joint model gives %s, so the difference of %s is the overlap and interaction that simple addition would double count or miss." % (kk(sm), kk(joint), kk(joint - sm)), "info")
    f1 = sty(go.Figure(go.Bar(x=[n.split(" (")[0] for n in S], y=[s["op"] for s in S.values()], marker_color=[C["st"], C["co"], C["mid"], C["sg"]])), 320, "Quarterly operating profit by scenario (₹k, hypothetical)"); f2 = wf([v for _, v in one], [n.replace(" alone", "") for n, _ in one], "Independent lever effects (₹k, before interactions)"); G["scn"] = pd.DataFrame([dict(scenario=n, revenue=s["rev"], operating_profit=s["op"], margin_pct=s["om"]) for n, s in S.items()]); return h, f1, f2
def export_all(seg, cur, base, thr):
    if "D" not in G: return None, note("Load data first.")
    R = getR(seg, cur, base, thr); out = []
    def w(df, fn):
        df.to_csv(fn, index=False)
        if os.path.exists(fn): out.append(fn)
    w(R["Q"].reset_index().rename(columns={"index": "quarter"}), "nexus_quarterly.csv"); w(pd.DataFrame(R["br"]["rows"] + [("Total of bridge", R["br"]["total"]), ("Actual change", R["br"]["actual"])], columns=["component", "impact_k"]), "nexus_profit_bridge.csv"); w(pd.DataFrame([dict(driver=SH[k], shapley_k=v) for k, v in R["sh"].items()]), "nexus_shapley.csv"); w(R["rel"], "nexus_relationships.csv")
    w(R["hy"], "nexus_root_causes.csv"); w(R["act"], "nexus_actions.csv"); w(R["kp"], "nexus_kpi_check.csv"); w(G.get("scn", pd.DataFrame([dict(note="run the scenario lab first")])), "nexus_scenarios.csv"); open("nexus_investigation_report.md", "w", encoding="utf-8").write("# NEXUS AI — Investigation report (%s, %s vs %s)\n\n%s\n\n" % (seg, R["cur"], R["base"], "_Synthetic demo data._" if G.get("demo") else "") + "\n\n".join("## %s\n%s" % (a, b) for a, b in report(R))); out.append("nexus_investigation_report.md")
    return [f for f in out if os.path.exists(f)], note("Generated %d files for %s, %s vs %s (reproducible with the same inputs)." % (len(out), seg, R["cur"], R["base"]), "ok")
@safe(2)
def render_dq():
    D = G["D"]; h = banner() + note("Rows read: " + ", ".join("%s %s" % (TN[k], nf(v)) for k, v in D["rows_in"].items()) + ". Raw uploads stay unchanged; a validated copy is analysed. Excluded rows: <b>%d</b> (nothing is dropped or imputed silently). Grain: monthly; quarters need all 3 months. Rule: amounts add, rates are order-weighted means." % sum(c for _, _, c in D["excluded"]), "ok")
    h += "".join(note(esc(m), "err" if l == "error" else "warn" if l == "warn" else "info") for l, m in D["issues"]) or note("No validation issues.", "ok"); return h, SEC("Self-test results (run at start-up)") + "".join(note(("PASS " if ok else "FAIL ") + esc(g + ": " + n) + " — " + esc(d), "ok" if ok else "err") for g, n, ok, d in TESTS)

# ------------------------------ self-tests ------------------------------
def setG(D, demo=True): _D["ver"] = _D.get("ver", 0) + 1; G.clear(); G.update(D=D, demo=demo, ver=_D["ver"], _c={})
def mkq(O, L, d, c, Mk, pay, ot, rec, Ops, Oth):
    gs = O * L / 1000; rev = gs * (1 - d / 100); lab = pay + ot + rec; return pd.Series(dict(orders=O, list_price=L, discount_rate=d, unit_cost=c, marketing_expense=Mk, labour_cost=lab, payroll=pay, overtime_cost=ot, recruit_train_cost=rec, ops_cost=Ops, other_opex=Oth, revenue=rev, operating_profit=rev - O * c / 1000 - Mk - lab - Ops - Oth))
def run_selftests(verbose=True):
    if TESTS: return TESTS
    Tt = []; saved = dict(G)
    def chk(g, n, fn):
        try: ok, d = fn(); Tt.append((g, n, bool(ok), d))
        except Exception as e: Tt.append((g, n, False, type(e).__name__ + ": " + str(e)[:90]))
    def t1():
        r = {k: v.copy() for k, v in demo_raw().items()}; r["fin"] = r["fin"].drop(columns=["payroll"])
        try: load_all(r); return False, "no error"
        except ValueError as e: return "payroll" in str(e), "missing column reported with guidance"
    def t2():
        r = {k: v.copy() for k, v in demo_raw().items()}; f = r["fin"]; r["fin"] = pd.concat([f, f.iloc[[0]]], ignore_index=True); r["fin"].loc[5, "operating_profit"] += 500; r["fin"].loc[6, "revenue"] = -3.0; D = load_all(r); w = " | ".join(m for _, m in D["issues"]); return "duplicate" in w and "Reconciliation failed" in w and "negative" in w, "duplicate row, negative revenue and a corrupted profit identity are reported (kept as supplied, not corrected)"
    def t3(): M = derive(pd.DataFrame(dict(revenue=[100.0, 0.0], cogs=[60.0, 0.0], gross_profit=[40.0, 0.0], marketing_expense=[5.0] * 2, payroll=[10.0] * 2, overtime_cost=[2.0] * 2, recruit_train_cost=[1.0] * 2, ops_cost=[8.0] * 2, other_opex=[4.0] * 2, operating_profit=[10.0, -30.0], orders=[10.0, 0.0], gross_sales=[110.0, 0.0], new_customers=[5.0, 0.0]))); return abs(M.gross_margin_pct[0] - 40) < 1e-9 and abs(M.op_margin_pct[0] - 10) < 1e-9 and abs(M.discount_rate[0] - 100 * (1 - 100 / 110)) < 1e-9 and np.isnan(M.gross_margin_pct[1]) and np.isnan(M.cac[1]), "margins and discount formulas correct; zero revenue/orders give n/a, not infinity"
    def t4(): a = mkq(1000, 100, 10, 50, 10, 10, 5, 5, 5, 5); b = mkq(1100, 98, 14, 55, 12, 10, 8, 6, 6, 5); br = bridge(a, b); return abs(a.operating_profit) < 1e-9 and abs(br["diff"]) < 1e-9 and br["ok"], "bridge sums exactly to the actual change %s (difference %.1e)" % (kk(br["actual"]), br["diff"])
    def t5():
        a = mkq(1000, 100, 10, 50, 10, 10, 5, 5, 5, 5); b = mkq(1100, 98, 14, 55, 12, 10, 8, 6, 6, 5); phi, tot = shapley(drv(a), drv(b)); c = mkq(1000, 100, 10, 50, 12, 10, 5, 5, 5, 5); p2, t2_ = shapley(drv(a), drv(c)); return abs(sum(phi.values()) - (b.operating_profit - a.operating_profit)) < 1e-9 and abs(p2["Mk"] + 2) < 1e-9 and abs(p2["O"]) < 1e-9, "Shapley values sum to the change; a lone marketing increase of 2 gets exactly −2 and the others 0"
    def t6(): D = demo_D(); Q = quarterly(monthly(D["P"], "All")); v = Q.operating_profit.values; kp = kpi_eval(D, monthly(D["P"], "All"), Q.index[-1]); return len(Q) == 12 and v[-1] < v[-2] < v[-3] < v[-4] and streak(Q, len(Q) - 1) >= 3 and (kp.met == True).all(), "operating profit falls %s → %s → %s → %s over three quarters while all %d departmental KPIs are met" % (kk(v[-4]), kk(v[-3]), kk(v[-2]), kk(v[-1]), len(kp))
    def t7():
        r = np.random.default_rng(3); n = 60; idx = pd.date_range("2021-01-01", periods=n, freq="MS"); x = pd.DataFrame({"x": np.arange(n) * .5 + r.normal(0, 1, n), "y": np.arange(n) * .3 + r.normal(0, 1, n)}, index=idx); raw = np.corrcoef(x.x, x.y)[0, 1]; R_ = resid(x, ["x", "y"]); rr = np.corrcoef(R_.x, R_.y)[0, 1]
        s = r.normal(0, 1, n); y = pd.Series(s).shift(2).values + .05 * r.normal(0, 1, n); Rs = [pd.DataFrame({"x": s, "y": y}, index=idx)]; c = {L: (lambda a, b: np.corrcoef(a, b)[0, 1])(*pairs(Rs, "y", "x", L)) for L in range(4)}; return raw > .8 and abs(rr) < .35 and max(c, key=lambda k: abs(c[k])) == 2, "shared trend: raw r=%.2f falls to %.2f after detrending; a series built from x two months earlier peaks at lag 2 (r=%.2f)" % (raw, rr, c[2])
    def t8(): Rs = [pd.DataFrame({"x": np.ones(40), "y": np.arange(40.0)})]; x, y = pairs(Rs, "y", "x", 0); T = rel_table(demo_D(), "op_margin_pct", ["discount_rate"], 0, True, ["Online"]); return np.std(x) == 0 and len(T) == 1 and T.p.notna().all() and abs(bh(np.array([.01]))[0] - .01) < 1e-12, "constant series has zero variance (no correlation computed); FDR on a single test equals the p-value"
    def t9(): m = reg_model(demo_D(), SEGS); return m["ok"] and m["split"][0] < m["split"][1], "training ends %s before testing starts %s; standardisation uses training months only; Ridge skill vs naive %s" % (m["split"][0].strftime("%b %Y"), m["split"][1].strftime("%b %Y"), sg(m["perf"].skill.iloc[1]))
    def t10(): setG(demo_D()); R = getR("All", "2026Q3", "2025Q4", 2); top = list(R["hy"].key[:3]); sup = R["rel"][(R["rel"].driver == "discount_rate")].strength.eq("supported").any(); G.clear(); G.update(saved); return len(set(top) & {"disc", "mix", "lab"}) >= 2 and sup, "planted mechanisms found in the top 3 by bridge impact: %s; discounting relationship statistically supported" % top
    def t11(): x = dict(drv(mkq(1000, 100, 10, 50, 10, 10, 5, 5, 5, 5)), ot=5.0); z = dict(disc=0, ot=0, ops=0, mkt=0, mel=.05, oth=0); b = scen(x, z, 1, 1.5)["op"]; u = scen(x, dict(z, disc=2, ot=20, ops=10), 1, 1.5)["op"]; s = sum(scen(x, dict(z, **{k: v}), 1, 1.5)["op"] - b for k, v in (("disc", 2), ("ot", 20), ("ops", 10))); return abs(b - opf(x)) < 1e-9 and abs((u - b) - s) > 1e-6, "no levers reproduce the base (%s); joint effect %s differs from the sum of separate effects %s (interaction)" % (kk(b), kk(u - b), kk(s))
    def t12(): setG(demo_D()); f, _ = export_all("All", "2026Q3", "2025Q4", 2); n = len(pd.read_csv("nexus_root_causes.csv")); R = getR("All", "2026Q3", "2025Q4", 2); G.clear(); G.update(saved); return n == len(R["hy"]) and "nexus_investigation_report.md" in f, "%d files written; root-cause export has %d rows matching the analysis" % (len(f), n)
    def t13(): setG(demo_D()); G["f"] = ("All", "2026Q3", "2025Q4", 2); R = getR(*G["f"]); a = ask("What happened to profitability?"); ok = "deterministic" in a and kk(R["q1"].operating_profit) in a; G.clear(); G.update(saved); return ok, "report answers without any API and quotes the computed operating profit"
    for g, n, f in [("data", "missing column", t1), ("data", "duplicates, negatives, reconciliation", t2), ("formula", "profit, margin and discount formulas", t3), ("bridge", "profit bridge reconciles", t4), ("bridge", "Shapley efficiency", t5), ("decline", "three-quarter decline, KPIs on target", t6), ("relationship", "trend removal and lag detection", t7), ("relationship", "edge cases and FDR", t8), ("model", "chronological split, no leakage", t9), ("rootcause", "planted mechanisms discovered", t10), ("scenario", "joint scenario and interactions", t11), ("reporting", "CSV export consistency", t12), ("reporting", "grounded analyst report", t13)]: chk(g, n, f)
    G.clear(); G.update(saved); TESTS[:] = Tt
    if verbose:
        for g, n, ok, d in Tt: print(("PASS " if ok else "FAIL ") + g + ": " + n + " :: " + d)
        print("Result: %d of %d self-tests passed." % (sum(1 for t in Tt if t[2]), len(Tt)))
    return TESTS

# ------------------------------ project export ------------------------------
ALGO = """## How NEXUS AI works: the 10-step algorithm
1. **Ingest and map.** Load the four departmental tables (financials, marketing, HR, operations) plus optional KPI targets, or the synthetic demo. Map your column names to the schema and keep raw data unchanged.
2. **Validate and reconcile.** Check required fields, dates, negatives, duplicates, missing months and the P&L identities *gross profit = revenue − COGS* and *operating profit = gross profit − operating costs*. Problems are listed with row references; nothing is dropped or imputed silently.
3. **Align the grain.** Normalise everything to months, then to complete quarters. Amounts add; rates are order-weighted means; ratios such as discount, CAC and cost per order are recomputed from sums, never averaged.
4. **Establish the decline.** Compare the current quarter with the previous quarter, the same quarter last year, budget and a configurable baseline; separate absolute profit change from margin change; count consecutive declining quarters.
5. **Reconcile the profit bridge.** Decompose the profit change exactly into volume, list price, discounting, unit cost and mix, marketing, payroll, overtime, recruitment, operations and other costs, and verify it equals the actual change within a stated tolerance.
6. **Attribute fairly.** Compute exact Shapley values over eight drivers so interactions (such as volume times price) are shared, and compare them with the order-dependent sequential bridge. Each cost or revenue effect is counted once.
7. **Screen cross-functional relationships.** Remove trend and calendar-month effects, align by month and segment, test lags 0–2 with Pearson and Spearman, control false discoveries (Benjamini–Hochberg), flag multicollinearity, and run a chronological Ridge check against a naive baseline. Association only.
8. **Test root-cause hypotheses.** Score seven cross-department hypotheses by their bridge amount plus statistical evidence, list alternative explanations and the next validation step, and show the departmental-KPI paradox (departments on target while profit falls).
9. **Prioritise corrective actions.** Rank actions by impact, evidence strength and effort, with owners, risks, success metrics and review period. The score is a ranking aid, not a probability of success.
10. **Stress-test, report and review.** Run base, downside and upside scenarios in one joint model (interactions included, double counting shown), generate the evidence-linked investigation report, export CSV and Markdown, and require human review before acting.
"""
METH = ALGO + """
### Notes
- Planted demonstration mechanisms in the synthetic data: from quarter 10 discounts rise, low-margin product mix rises, overtime, turnover, rework and returns rise, and marketing spend grows, while orders and revenue keep growing and each department's KPIs stay on target. Other indicators (email click-through, on-time delivery) are noise.
- Bridges and Shapley values are accounting allocations, not causal effects. Relationship p-values assume independent months and are optimistic.
- Scenarios are assumption-based. Elasticities are user assumptions, not estimates from the data.
- Not included: Streamlit (Gradio is used), PDF export, a hosted open-source LLM, transaction-level price-volume-mix, channel-level marketing analysis.
"""
LICENSE = "MIT License\n\nCopyright (c) 2026 NEXUS AI contributors\n\nPermission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the \"Software\"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:\n\nThe above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.\n\nTHE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.\n"
README = """# NEXUS AI — Cross-Functional Profitability Intelligence
Connect the dots. Find the profit leak.

Profit has declined for three straight quarters while Marketing, HR, Operations and Finance each report satisfactory results. NEXUS AI integrates their data, reconciles the profit decline, attributes it fairly, tests cross-functional hypotheses and proposes corrective actions. Bundled data is **fictional synthetic data** with documented planted mechanisms (36 months, 12 quarters, 2 segments, actual and budget).

""" + ALGO + """
## Architecture
@@@mermaid
flowchart LR
  A[CSV upload or synthetic data] --> B[Validation + P&L reconciliation]
  B --> C[Monthly and quarterly alignment]
  C --> D[Decline analysis + profit bridge]
  D --> E[Shapley attribution]
  C --> F[Trend-adjusted relationships + FDR]
  E --> G[Root-cause hypotheses]
  F --> G
  G --> H[Action register]
  H --> I[Joint scenario lab]
  H --> J[Analyst report + exports]
@@@

## Run
@@@
pip install -r requirements.txt
python app.py
@@@
In Google Colab paste `app.py` into one cell and run it. The `src/` modules in the brief are consolidated into `app.py`.

## Sample schemas
`financials.csv` (period, segment, revenue, cogs, marketing_expense, payroll, overtime_cost, recruit_train_cost, ops_cost, other_opex, gross_profit, operating_profit, budget_* columns); `marketing.csv` (period, segment, gross_sales, new_customers, conversion_rate, low_margin_mix_share, email_ctr); `hr.csv` (period, segment, headcount, overtime_hours, turnover_rate, absence_rate, engagement_score); `operations.csv` (period, segment, orders, capacity_util, rework_rate, return_rate, on_time_pct); `departmental_kpis.csv` (kpi, department, column, target, direction).

## Tests and limits
`pip install pytest && pytest tests` runs the built-in self-tests. Associations are not causes; scenarios are hypothetical; actions need human review. Add screenshots to `screenshots/` (none included).
""".replace("@@@", "`" * 3)
TFILE = "from app import run_selftests\n\n\ndef test_%s():\n    res = [r for r in run_selftests(verbose=False) if r[0] in %s]\n    assert res and all(r[2] for r in res), res\n"
def _src():
    try: return open(__file__, encoding="utf-8").read()
    except Exception: pass
    try:
        for s in list(get_ipython().user_ns.get("In") or [])[::-1]:
            if "NEXUS AI — Cross-Functional Profitability" in s and "def main" in s: return s
    except Exception: pass
    return None
def write_samples():
    raw = demo_raw(); os.makedirs("sample_data", exist_ok=True); out = []
    for k, n in TN.items(): p = "sample_data/%s.csv" % n; raw[k].to_csv(p, index=False); out.append(p)
    return out
def build_project(files):
    root = "nexus-ai-profitability-intelligence"
    for d in ["sample_data", "tests", "docs", "screenshots"]: os.makedirs(os.path.join(root, d), exist_ok=True)
    src = _src()
    if src: open(root + "/app.py", "w", encoding="utf-8").write(src)
    for f in files: open(os.path.join(root, f), "wb").write(open(f, "rb").read())
    W = {"requirements.txt": "gradio>=4.44,<6\nplotly\nscikit-learn\nscipy\npandas\nnumpy\n", "README.md": README, "LICENSE": LICENSE, ".gitignore": "__pycache__/\n.ipynb_checkpoints/\n*.zip\nnexus_*.csv\nnexus_*.md\n.env\n", "docs/methodology.md": METH, "docs/data_dictionary.md": "# Data dictionary\nSee README schemas. Amounts are in ₹ thousands per month; rates are percentages; segment defaults to 'Company'. All samples are synthetic.\n",
         "docs/assumptions_and_limitations.md": "# Assumptions and limitations\nSynthetic data with planted mechanisms. Monthly grain, complete quarters only. p-values assume independent months. Bridges and Shapley values are accounting allocations, not causal effects. Scenario elasticities are user assumptions. Action effort values are heuristic. Human review required.\n", "screenshots/README.md": "# Screenshots\nAdd your own screenshots here. None are included.\n"}
    for nm, g in [("financial_reconciliation", ("data", "formula")), ("profitability_analysis", ("bridge", "decline")), ("relationship_engine", ("relationship",)), ("driver_attribution", ("bridge", "model")), ("root_cause_engine", ("rootcause",)), ("scenarios", ("scenario", "reporting"))]: W["tests/test_%s.py" % nm] = TFILE % (nm, repr(g))
    for fn, tx in W.items(): open(os.path.join(root, fn), "w", encoding="utf-8").write(tx)
    z = "nexus_ai_project.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for dp, _, fs in os.walk(root):
            for f in fs: zf.write(os.path.join(dp, f))
    return z, bool(src)

# ------------------------------ UI ------------------------------
CSS = """
.gradio-container{background:#F3F2EC!important;color:#202D39!important;font-family:Inter,system-ui,-apple-system,sans-serif!important;max-width:1400px!important}
.hdr{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:14px;padding:24px 30px;border-radius:14px;background:#202D39;color:#F3F2EC;margin-bottom:12px}
.brand{display:flex;gap:16px;align-items:center}.logo{width:52px;height:52px;border-radius:12px;background:linear-gradient(135deg,#B8E3C7,#C9B8F0);color:#202D39;font-weight:800;font-size:22px;display:flex;align-items:center;justify-content:center}
.hdr h1{margin:0;font-size:28px;letter-spacing:3px;color:#F3F2EC}.hdr h1 span{color:#D7B878}.hdr p{margin:4px 0 0;color:#C9B8F0;font-style:italic}.badges span{display:inline-block;margin:3px;padding:4px 11px;border-radius:6px;background:#ffffff1a;color:#F3F2EC;font-size:12px}
button[role=tab]{background:#202D39!important;color:#F3F2EC!important;border-radius:8px 8px 0 0!important;margin-right:2px}button[role=tab][aria-selected=true]{background:#D7B878!important;color:#202D39!important;font-weight:700}
.kg{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:10px 0}.kc{background:#fff;border:1px solid #202D3926;border-radius:10px;padding:14px 16px}.kl{color:#5d6d78;font-size:11px;text-transform:uppercase;letter-spacing:1.1px}.kv{font-size:22px;font-weight:700;margin:6px 0 4px}.kd{color:#5d6d78;font-size:12px}
.note{background:#fff;padding:10px 14px;border-radius:8px;margin:8px 0;color:#202D39;font-size:14px;line-height:1.5;border:1px solid #202D3918}.sec{font-size:15px;font-weight:700;color:#202D39;margin:18px 0 6px;text-transform:uppercase;letter-spacing:1px}
.pill{display:inline-block;border-radius:99px;padding:2px 10px;font-size:11px;font-weight:700;color:#202D39;white-space:nowrap}.tw{overflow-x:auto;border-radius:8px;border:1px solid #202D3926;margin:8px 0;background:#fff}table{border-collapse:collapse;width:100%;font-size:13px}
th{background:#344650;color:#F3F2EC;text-align:left;padding:9px 10px;font-weight:600}td{padding:8px 10px;border-top:1px solid #202D3912;color:#202D39;vertical-align:top}tr:hover td{background:#B8E3C722}
button.primary{background:#202D39!important;color:#F3F2EC!important;border:none!important;font-weight:700!important}@media(max-width:640px){.hdr h1{font-size:21px}.kv{font-size:19px}}
"""
HEADER = "<div class='hdr'><div class='brand'><div class='logo'>NX</div><div><h1>NEXUS <span>AI</span></h1><p>Connect the dots. Find the profit leak.</p></div></div><div class='badges'><span>Associations, not causes</span><span>Scenarios are hypothetical</span><span>Priority ≠ probability</span><span>Human review required</span></div></div>"
def run_all(*a):
    try:
        files = a[:5]; mapping = a[5]; seed = int(a[6] or 11); demo = all(f is None for f in files)
        D = demo_D(seed) if (demo and not mapping) else load_all(demo_raw(seed) if demo else dict(zip(["fin", "mkt", "hr", "ops", "kpi"], [read_csv_any(f) if f is not None else None for f in files])), mapping); setG(D, demo); Q = quarterly(monthly(D["P"], "All"))
        return note(("Fictional demo company analysed. " if demo else "Your data analysed. ") + "%d segments, %d months, %d complete quarters (%s to %s)." % (len(D["segs"]), len(D["pers"]), len(Q), Q.index[0], Q.index[-1]), "ok")
    except Exception as e: return note("Could not complete the analysis: " + esc(e), "err")
def refresh():
    if "D" not in G: return tuple(gr.update() for _ in range(4))
    D = G["D"]; Q = quarterly(monthly(D["P"], "All")); ql = list(Q.index); pk = Q.operating_profit.iloc[:-1].idxmax(); R = [d for d in DRV if d in monthly(D["P"], "All")]
    return gr.update(choices=["All"] + D["segs"], value="All"), gr.update(choices=ql, value=ql[-1]), gr.update(choices=ql, value=pk), gr.update(choices=R, value=R[0])
def build_ui(zip_path, sfiles):
    with gr.Blocks(css=CSS, title="NEXUS AI", theme=gr.themes.Base(primary_hue="slate", neutral_hue="stone")) as demo:
        gr.HTML(HEADER)
        with gr.Accordion("Filters: segment, current quarter, baseline quarter, materiality (apply to every page)", open=True):
            with gr.Row():
                f_s = gr.Dropdown(["All"], value="All", label="Segment"); f_c = gr.Dropdown([], label="Current quarter"); f_b = gr.Dropdown([], label="Baseline quarter (default = pre-decline peak)"); f_t = gr.Slider(1, 10, 2, step=1, label="Materiality (% of baseline profit)"); ap_b = gr.Button("Apply filters", variant="primary")
        status = gr.HTML(note("Loading the fictional company, running the investigation and self-tests (about 1 minute)...", "info")); FI = [f_s, f_c, f_b, f_t]
        with gr.Tabs():
            with gr.Tab("Command Centre"):
                cc_h = gr.HTML()
                with gr.Row():
                    cc1 = gr.Plot(); cc2 = gr.Plot()
                cc3 = gr.Plot()
            with gr.Tab("Profitability Investigation"):
                iv_h = gr.HTML(); iv1 = gr.Plot()
                with gr.Row():
                    iv2 = gr.Plot(); iv3 = gr.Plot()
            with gr.Tab("Relationship Engine"):
                with gr.Row():
                    r_o = gr.Dropdown(["op_margin_pct", "gross_margin_pct", "operating_profit", "contribution_margin"], value="op_margin_pct", label="Outcome"); r_l = gr.Slider(0, 4, 2, step=1, label="Maximum lag (months)"); r_d = gr.Checkbox(True, label="Remove trend and season (recommended)"); r_s = gr.Dropdown([], label="Driver for scatter"); r_b = gr.Button("Analyse", variant="primary")
                r_h = gr.HTML(); r1 = gr.Plot()
                with gr.Row():
                    r2 = gr.Plot(); r3 = gr.Plot()
            with gr.Tab("Root-Cause Investigation"):
                rc_h = gr.HTML()
                with gr.Row():
                    rc1 = gr.Plot(); rc2 = gr.Plot()
            with gr.Tab("Driver Attribution"):
                at_h = gr.HTML()
                with gr.Row():
                    at1 = gr.Plot(); at2 = gr.Plot()
            with gr.Tab("Marketing, HR & Operations"):
                dp_h = gr.HTML()
                with gr.Row():
                    dp1 = gr.Plot(); dp2 = gr.Plot()
                with gr.Row():
                    dp3 = gr.Plot(); dp4 = gr.Plot()
            with gr.Tab("Finance Integrity"):
                fn_h = gr.HTML(); fn1 = gr.Plot()
            with gr.Tab("AI Business Analyst"):
                an_h = gr.HTML(); an1 = gr.Plot(visible=False); an2 = gr.Plot(visible=False)
                gr.Markdown("Ask: *What happened to profitability?* · *Which components explain the decline?* · *Which relationships deserve attention?* · *What is unverified?* · *What should management change?* · *How do we measure success?*")
                ag_q = gr.Textbox(label="Ask a question"); ag_b = gr.Button("Ask", variant="primary"); ag_o = gr.Markdown()
            with gr.Tab("Actions & Scenario Lab"):
                gr.Markdown("Assumption-based what-if. **Not a forecast and not realised savings.**")
                with gr.Row():
                    s1 = gr.Slider(0, 5, 1.5, step=.5, label="Discount cut (percentage points)"); s2 = gr.Slider(0, 50, 20, step=5, label="Overtime cost reduction (%)"); s3 = gr.Slider(0, 25, 8, step=1, label="Operations cost reduction from rework fix (%)"); s4 = gr.Slider(-20, 20, 0, step=1, label="Marketing spend change (%)")
                with gr.Row():
                    s5 = gr.Slider(0, .3, .05, step=.01, label="Orders change per 1% marketing change (%)"); s6 = gr.Slider(-10, 10, 0, step=1, label="Other cost change (%)"); s7 = gr.Slider(0, 5, 1.5, step=.5, label="Orders lost per point of discount cut (%)"); sc_b = gr.Button("Run scenario", variant="primary")
                ac_h = gr.HTML()
                with gr.Row():
                    ac1 = gr.Plot(); ac2 = gr.Plot()
            with gr.Tab("Data & Reports"):
                gr.Markdown("Upload CSVs: **financials, marketing, hr, operations** are required; **departmental_kpis** is optional. Leave empty for the fictional demo. Raw uploads are never modified.")
                up = []
                with gr.Row():
                    for k in TN: up.append(gr.File(label=TN[k] + ".csv" + (" (optional)" if k == "kpi" else ""), file_types=[".csv"]))
                mp = gr.Textbox(label="Column mapping (only if auto-detect fails)", placeholder="revenue=net_sales, orders=units", lines=2)
                with gr.Row():
                    seed = gr.Number(11, label="Demo seed"); ld_b = gr.Button("Validate and load", variant="primary"); rg_b = gr.Button("Regenerate demo")
                gr.File(value=sfiles, label="Sample CSVs (synthetic)", file_count="multiple", interactive=False); dq_h = gr.HTML(); t_h = gr.HTML()
                gr.Markdown("### Exports"); xp_b = gr.Button("Generate exports and investigation report", variant="primary"); xp_m = gr.HTML(); xp_f = gr.File(label="Exports", file_count="multiple", interactive=False); gr.File(value=zip_path, label="Download GitHub-ready project (ZIP)", interactive=False)
            with gr.Tab("Methodology"):
                gr.Markdown(METH)
        RUN = up + [mp, seed]; RI = FI + [r_o, r_l, r_d, r_s]; SI = FI + [s1, s2, s3, s4, s5, s6, s7]
        def pages(e):
            e = e.then(render_cc, FI, [cc_h, cc1, cc2, cc3]).then(render_inv, FI, [iv_h, iv1, iv2, iv3]).then(render_rel, RI, [r_h, r1, r2, r3]).then(render_rc, FI, [rc_h, rc1, rc2]).then(render_attr, FI, [at_h, at1, at2]).then(render_dept, FI, [dp_h, dp1, dp2, dp3, dp4])
            return e.then(render_fin, FI, [fn_h, fn1]).then(render_ana, FI, [an_h, an1, an2]).then(render_act, SI, [ac_h, ac1, ac2]).then(render_dq, None, [dq_h, t_h])
        def full(ev): return pages(ev.then(refresh, None, [f_s, f_c, f_b, r_s]))
        full(ld_b.click(run_all, RUN, [status], show_progress="full")); full(demo.load(run_all, RUN, [status])); full(rg_b.click(lambda s: (s or 11) + 1, seed, seed).then(run_all, RUN, [status], show_progress="full"))
        ap_b.click(render_cc, FI, [cc_h, cc1, cc2, cc3]).then(render_inv, FI, [iv_h, iv1, iv2, iv3]).then(render_rel, RI, [r_h, r1, r2, r3]).then(render_rc, FI, [rc_h, rc1, rc2]).then(render_attr, FI, [at_h, at1, at2]).then(render_dept, FI, [dp_h, dp1, dp2, dp3, dp4]).then(render_fin, FI, [fn_h, fn1]).then(render_ana, FI, [an_h, an1, an2]).then(render_act, SI, [ac_h, ac1, ac2])
        r_b.click(render_rel, RI, [r_h, r1, r2, r3]); sc_b.click(render_act, SI, [ac_h, ac1, ac2], show_progress="full"); xp_b.click(export_all, FI, [xp_f, xp_m], show_progress="full"); ag_b.click(ask, ag_q, ag_o); ag_q.submit(ask, ag_q, ag_o)
    return demo
def main():
    sf = write_samples(); zp, saved = build_project(sf)
    print("=" * 78); print("NEXUS AI starting. Demo data is FICTIONAL with planted mechanisms. No API key needed."); print("Running self-tests (about 1 minute):")
    demo_D(); run_selftests(verbose=True); demo = build_ui(zp, sf)
    print("Project ZIP:", zp, "| standalone app.py included:", "yes" if saved else "NO (create app.py yourself by pasting this cell into it)")
    print("Not included / not tested: Streamlit (Gradio used), PDF export, optional LLM, uploads of your own CSVs. The public Gradio link is open to anyone: do not load confidential data.")
    print("=" * 78); demo.queue().launch(debug=False, show_error=True)
if __name__ == "__main__" or "google.colab" in sys.modules:
    main()