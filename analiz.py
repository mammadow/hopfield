"""
ALQORİTMİN ANALİZİ: eksperimental yoxlamalar
============================================

1) Dayanma teoremi:  hər çevirmədə Φ ≥ 1 artır  ⇒  addım sayı ≤ W = Σ|w_e|.
   Təsadüfi qraflarda üç seçim strategiyasını müqayisə edirik.

2) W sərhədi psevdo-polinomialdır: çəkilər böyüdükcə W xətti artır,
   real addım sayı isə demək olar ki, dəyişmir.

3) Maksimal kəsik (Max-Cut) əlaqəsi (KT §12.4): bütün çəkilər müsbət olanda
   yaxşı til = kəsikdən keçən til, Φ = kəsiyin çəkisi. Stabil konfiqurasiya
   lokal optimal kəsikdir və teoremə görə  w(A,B) ≥ ½·OPT.
   Kiçik qraflarda tam yoxlama ilə bunu təsdiqləyirik.

İşə salmaq:   python analiz.py
"""

import os
import random
import statistics
import sys
from itertools import product

from hopfield import HopfieldNetwork, state_flipping, STRATEGIES


def random_graph(n, p, max_w, rng, positive=False):
    edges = []
    for u in range(n):
        for v in range(u + 1, n):
            if rng.random() < p:
                w = rng.randint(1, max_w)
                if not positive and rng.random() < 0.5:
                    w = -w
                edges.append((u, v, w))
    return HopfieldNetwork(n, edges)


def random_state(n, rng):
    return [rng.choice((-1, 1)) for _ in range(n)]


# ---------------------------------------------------------------------------
# 1) Dayanma teoremi və strategiyaların müqayisəsi
# ---------------------------------------------------------------------------
def experiment_termination(sizes, trials=30, seed=1):
    rng = random.Random(seed)
    print("1) Dayanma teoremi: addım sayı ≤ W  (çəkilər ∈ [−10, 10], p = 0.3)\n")
    header = f"{'n':>4} | {'m (orta)':>8} | {'W (orta)':>9} |"
    header += "".join(f" {LABELS[name]:>8} |" for name in STRATEGIES) + " maks/W"
    print(header)
    print("-" * len(header))
    rows = []
    for n in sizes:
        flips = {name: [] for name in STRATEGIES}
        ms, Ws, worst_ratio = [], [], 0.0
        for _ in range(trials):
            net = random_graph(n, 0.3, 10, rng)
            s0 = random_state(n, rng)
            ms.append(len(net.edges))
            Ws.append(net.W)
            for name in STRATEGIES:
                res = state_flipping(net, s0, name, random.Random(rng.random()))
                # teoremin hər iki hissəsini yoxlayırıq
                assert net.is_stable(res.state)
                assert all(b - a >= 1 for a, b in zip(res.phi_history, res.phi_history[1:]))
                assert res.flips <= net.W
                flips[name].append(res.flips)
                worst_ratio = max(worst_ratio, res.flips / net.W)
        row = {"n": n, "m": statistics.mean(ms), "W": statistics.mean(Ws),
               **{k: statistics.mean(v) for k, v in flips.items()}}
        rows.append(row)
        line = f"{n:>4} | {row['m']:>8.0f} | {row['W']:>9.0f} |"
        line += "".join(f" {row[name]:>8.1f} |" for name in STRATEGIES)
        print(line + f" {worst_ratio:.3f}")
    print("\nBütün sınaqlarda: konfiqurasiya stabildir, Φ hər addımda ≥ 1 artır,"
          " addım sayı ≤ W  ✓")
    print("Cədvəldəki rəqəmlər orta çevirmə sayıdır. "
          "Acgöz strategiya adətən ən az addım tələb edir.\n")
    return rows


# ---------------------------------------------------------------------------
# 2) Çəkilərin böyüklüyü: psevdo-polinomial sərhəd
# ---------------------------------------------------------------------------
def experiment_weights(n=40, ranges=(1, 10, 100, 1000, 10000), trials=30, seed=2):
    rng = random.Random(seed)
    print(f"2) Çəki diapazonu artdıqca (n = {n}, p = 0.3, təsadüfi strategiya)\n")
    print(f"{'maks |w|':>9} | {'W (orta)':>11} | {'orta addım':>10} | {'maks addım':>10}")
    print("-" * 50)
    for R in ranges:
        Ws, fl = [], []
        for _ in range(trials):
            net = random_graph(n, 0.3, R, rng)
            res = state_flipping(net, random_state(n, rng), "random", rng)
            Ws.append(net.W)
            fl.append(res.flips)
        print(f"{R:>9} | {statistics.mean(Ws):>11.0f} | {statistics.mean(fl):>10.1f} | {max(fl):>10}")
    print("\nW çəkilərlə birlikdə xətti böyüyür (ədədin bit uzunluğuna görə isə eksponensial),")
    print("ona görə 'addım ≤ W' sərhədi PSEVDO-polinomialdır. Praktikada addım sayı")
    print("çox kiçik olur, lakin ümumi halda polinomial alqoritm məlum deyil (PLS-tam).\n")


# ---------------------------------------------------------------------------
# 3) Max-Cut: lokal optimum ≥ ½ · OPT
# ---------------------------------------------------------------------------
def cut_weight(net, s):
    return sum(w for u, v, w in net.edges if s[u] != s[v])


def max_cut_bruteforce(net):
    best = 0
    for bits in product((-1, 1), repeat=net.n - 1):    # 0-cı təpəni sabitləyirik
        best = max(best, cut_weight(net, (1,) + bits))
    return best


def experiment_maxcut(n=12, trials=100, seed=3):
    rng = random.Random(seed)
    print(f"3) Max-Cut: lokal axtarış vs optimal kəsik (n = {n}, çəkilər ∈ [1, 10], "
          f"{trials} qraf)\n")
    ratios = []
    for _ in range(trials):
        net = random_graph(n, 0.5, 10, rng, positive=True)
        res = state_flipping(net, random_state(n, rng), "random", rng)
        local = cut_weight(net, res.state)
        assert local == net.potential(res.state)          # Φ = kəsiyin çəkisi
        assert 2 * local >= net.W                         # w(A,B) ≥ W/2 ≥ OPT/2
        ratios.append(local / max_cut_bruteforce(net))
    print(f"  lokal / optimal nisbəti:  min = {min(ratios):.3f},  "
          f"orta = {statistics.mean(ratios):.3f},  maks = {max(ratios):.3f}")
    print(f"  tam optimal tapılan hallar: {sum(r == 1 for r in ratios)} / {trials}")
    print("  Teorem: nisbət həmişə ≥ 0.5  ✓  (praktikada daha yaxşıdır)\n")
    return ratios


# ---------------------------------------------------------------------------
# Qrafiklər
# ---------------------------------------------------------------------------
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, SURFACE, BASE = "#e1e0d9", "#fcfcfb", "#c3c2b7"
SERIES = {"first": "#2a78d6", "random": "#eb6834", "greedy": "#1baf7a"}
LABELS = {"first": "ardıcıl", "random": "təsadüfi", "greedy": "acgöz"}


def style_axes(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(BASE)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(True, color=GRID, linewidth=1)
    ax.set_axisbelow(True)


def save_figures(rows, ratios, outdir="neticeler"):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib tapılmadı – qrafiklər yaradılmadı.")
        return
    os.makedirs(outdir, exist_ok=True)
    plt.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans", "sans-serif"]

    # --- Addım sayı vs n (log miqyas), W sərhədi ilə birlikdə ----------------
    fig, ax = plt.subplots(figsize=(7.5, 4.2), facecolor=SURFACE)
    style_axes(ax)
    ns = [r["n"] for r in rows]
    ax.plot(ns, [r["W"] for r in rows], color=MUTED, linewidth=2, linestyle="--",
            label="sərhəd W = Σ|w|")
    for name in STRATEGIES:
        ax.plot(ns, [r[name] for r in rows], color=SERIES[name], linewidth=2,
                marker="o", markersize=7, markeredgecolor=SURFACE, markeredgewidth=2,
                label=LABELS[name])
    ax.set_yscale("log")
    ax.set_xlabel("neyron sayı n", color=INK2)
    ax.set_ylabel("çevirmə sayı (log miqyas)", color=INK2)
    ax.set_title("Real addım sayı nəzəri W sərhədindən çox-çox kiçikdir",
                 color=INK, fontsize=11)
    ax.legend(frameon=False, fontsize=9, labelcolor=INK2)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "analiz_addimlar.png"), dpi=150)
    plt.close(fig)

    # --- Max-Cut nisbətlərinin histoqramı ------------------------------------
    fig, ax = plt.subplots(figsize=(7.5, 4.2), facecolor=SURFACE)
    style_axes(ax)
    bins = [0.5 + 0.025 * i for i in range(21)]
    ax.hist(ratios, bins=bins, color="#2a78d6", edgecolor=SURFACE, linewidth=2)
    ax.axvline(0.5, color=INK2, linewidth=1)
    ax.annotate("zəmanət: ≥ 0.5·OPT", (0.5, 0.95), xycoords=("data", "axes fraction"),
                xytext=(6, 0), textcoords="offset points", color=INK2, fontsize=9)
    ax.set_xlim(0.48, 1.01)
    ax.set_xlabel("lokal kəsik / optimal kəsik", color=INK2)
    ax.set_ylabel("qraf sayı", color=INK2)
    ax.set_title("Max-Cut: lokal axtarışın keyfiyyəti", color=INK, fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "analiz_maxcut.png"), dpi=150)
    plt.close(fig)

    print(f"Qrafiklər saxlanıldı: {outdir}/analiz_addimlar.png, analiz_maxcut.png")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("=" * 64)
    print("  State-Flipping alqoritminin eksperimental analizi")
    print("=" * 64 + "\n")
    rows = experiment_termination([10, 20, 40, 80, 160])
    experiment_weights()
    ratios = experiment_maxcut()
    save_figures(rows, ratios)


if __name__ == "__main__":
    main()
