"""
TƏTBİQ: Hopfild şəbəkəsi ilə assosiativ yaddaş (obrazın bərpası)
================================================================

İdeya
-----
10×10 ölçülü hərf şəkli = 100 neyron, hər piksel bir neyrondur:
    qara piksel → s = +1,   ağ piksel → s = −1.

1) Öyrənmə (Hebb qaydası). Yadda saxlanılacaq ξ¹, ..., ξᴾ obrazları üçün
   çəkilər belə seçilir:

        w_ij = − Σ_p  ξᵖ_i · ξᵖ_j          (i ≠ j)

   Kleinberg–Tardos konvensiyasında MƏNFİ çəki "eyni vəziyyət" deməkdir.
   Obrazda eyni rəngli iki piksel arasında çəki mənfi olur (birlikdə olmaq
   istəyirlər), fərqli rənglilər arasında müsbət olur.
   Nəticədə yadda saxlanılan obrazlar Φ-nin lokal maksimumları, yəni
   STABİL konfiqurasiyalar olur.

2) Xatırlama = LOKAL AXTARIŞ. Küylü (pozulmuş) şəkildən başlayırıq və
   State-Flipping alqoritmini işə salırıq. Hər addımda razı olmayan bir
   piksel çevrilir, Φ artır və şəbəkə ən yaxın stabil konfiqurasiyaya,
   adətən orijinal hərfə "yuvarlanır".

İşə salmaq:   python assosiativ_yaddas.py
Qrafiklər `neticeler/` qovluğuna yazılır (matplotlib quraşdırılıbsa).
"""

import os
import random
import sys

from hopfield import HopfieldNetwork, state_flipping

SIZE = 10
N = SIZE * SIZE

PATTERNS = {
    "A": """
        ...####...
        ..######..
        .###..###.
        .##....##.
        .##....##.
        .########.
        .########.
        .##....##.
        .##....##.
        .##....##.
    """,
    "Ə": """
        ..######..
        .########.
        .##....##.
        .......##.
        .########.
        .########.
        .##....##.
        .###..###.
        ..######..
        ...####...
    """,
    "Z": """
        ##########
        ##########
        ......###.
        .....###..
        ....###...
        ...###....
        ..###.....
        .###......
        ##########
        ##########
    """,
    "X": """
        ##......##
        ###....###
        .###..###.
        ..######..
        ...####...
        ...####...
        ..######..
        .###..###.
        ###....###
        ##......##
    """,
}


# ---------------------------------------------------------------------------
# Köməkçi funksiyalar
# ---------------------------------------------------------------------------
def to_vector(text):
    """'#'/'.' şəklini ±1 vektoruna çevirir."""
    rows = [r.strip() for r in text.strip().splitlines()]
    assert len(rows) == SIZE and all(len(r) == SIZE for r in rows)
    return [1 if c == "#" else -1 for r in rows for c in r]


def hebb_network(patterns):
    """Hebb qaydası ilə çəkiləri hesablayır (KT konvensiyası: w = −Σ ξ_i ξ_j)."""
    edges = []
    for i in range(N):
        for j in range(i + 1, N):
            w = -sum(p[i] * p[j] for p in patterns)
            if w != 0:
                edges.append((i, j, w))
    return HopfieldNetwork(N, edges)


def add_noise(pattern, fraction, rng):
    """Təsadüfi seçilmiş fraction·N pikselin rəngini dəyişir."""
    s = list(pattern)
    for i in rng.sample(range(N), round(fraction * N)):
        s[i] = -s[i]
    return s


def hamming(a, b):
    return sum(x != y for x, y in zip(a, b))


def classify(state, vectors):
    """Nəticəni təsnif edir: hansı obrazdır (və ya onun inversiyası) / saxta hal."""
    for name, v in vectors.items():
        if state == v:
            return name
        if state == [-x for x in v]:
            return f"−{name} (inversiya)"
    return "saxta stabil hal"


def render_rows(state):
    return ["".join("█" if state[r * SIZE + c] > 0 else "·" for c in range(SIZE))
            for r in range(SIZE)]


def print_side_by_side(titles, states):
    blocks = [render_rows(s) for s in states]
    width = SIZE + 6
    print("".join(t.ljust(width) for t in titles))
    for r in range(SIZE):
        print("".join(b[r].ljust(width) for b in blocks))


# ---------------------------------------------------------------------------
# 1-ci hissə: hər hərfin küylü versiyasının bərpası
# ---------------------------------------------------------------------------
def recall_demo(net, vectors, noise=0.25, seed=7):
    rng = random.Random(seed)
    runs = {}
    print(f"\n1) Hər hərfə {noise:.0%} küy əlavə edib lokal axtarışla bərpa edirik\n")
    for name, v in vectors.items():
        noisy = add_noise(v, noise, rng)
        res = state_flipping(net, noisy, strategy="random", rng=rng)
        runs[name] = (noisy, res)

        print(f"── Hərf «{name}» " + "─" * 40)
        print_side_by_side(
            ["orijinal", f"küylü ({hamming(noisy, v)} xəta)", "bərpa olunmuş"],
            [v, noisy, res.state],
        )
        print(f"Çevirmə sayı: {res.flips}   (yuxarı sərhəd W = {net.W})")
        print(f"Φ: {res.phi_history[0]} → {res.phi_history[-1]}   "
              f"stabil: {net.is_stable(res.state)}   "
              f"nəticə: {classify(res.state, vectors)}\n")
    return runs


# ---------------------------------------------------------------------------
# 2-ci hissə: küy səviyyəsindən asılı olaraq bərpa faizi
# ---------------------------------------------------------------------------
def noise_experiment(net, vectors, levels, trials=40, seed=11):
    rng = random.Random(seed)
    table = []
    print("2) Küy səviyyəsi → düzgün bərpa faizi "
          f"(hər hərf üçün {trials} sınaq, cəmi {trials * len(vectors)})\n")
    print(f"{'küy':>5} | {'düzgün':>7} | {'inversiya':>9} | {'saxta':>6} | {'orta çevirmə':>12}")
    print("-" * 52)
    for level in levels:
        correct = inverse = spurious = flips = 0
        for name, v in vectors.items():
            for _ in range(trials):
                res = state_flipping(net, add_noise(v, level, rng), "random", rng)
                flips += res.flips
                if res.state == v:
                    correct += 1
                elif res.state == [-x for x in v]:
                    inverse += 1
                else:
                    spurious += 1
        total = trials * len(vectors)
        row = (level, correct / total, inverse / total, spurious / total, flips / total)
        table.append(row)
        print(f"{level:>5.0%} | {row[1]:>7.0%} | {row[2]:>9.0%} | {row[3]:>6.0%} | {row[4]:>12.1f}")
    print()
    return table


# ---------------------------------------------------------------------------
# Qrafiklər (matplotlib)
# ---------------------------------------------------------------------------
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, SURFACE = "#e1e0d9", "#fcfcfb"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]


def style_axes(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#c3c2b7")
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(True, color=GRID, linewidth=1)
    ax.set_axisbelow(True)


def save_figures(net, vectors, runs, table, outdir="neticeler"):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.colors import ListedColormap
    except ImportError:
        print("matplotlib tapılmadı – qrafiklər yaradılmadı.")
        return
    os.makedirs(outdir, exist_ok=True)
    cmap = ListedColormap(["#f0efec", "#184f95"])
    plt.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans", "sans-serif"]

    # --- Şəkil 1: orijinal / küylü / aralıq / bərpa ---------------------------
    names = list(vectors)
    fig, axes = plt.subplots(len(names), 4, figsize=(8, 2.1 * len(names)),
                             facecolor=SURFACE)
    for r, name in enumerate(names):
        noisy, res = runs[name]
        mid = list(noisy)
        for st in res.steps[: res.flips // 2]:
            mid[st.node] = -mid[st.node]
        panels = [
            (vectors[name], "orijinal"),
            (noisy, f"küylü ({hamming(noisy, vectors[name])} xəta)"),
            (mid, f"{res.flips // 2} çevirmədən sonra"),
            (res.state, f"bərpa ({res.flips} çevirmə)"),
        ]
        for c, (state, title) in enumerate(panels):
            ax = axes[r][c]
            ax.imshow([state[i * SIZE:(i + 1) * SIZE] for i in range(SIZE)],
                      cmap=cmap, vmin=-1, vmax=1)
            ax.set_xticks([]), ax.set_yticks([])
            for sp in ax.spines.values():
                sp.set_color(GRID)
            ax.set_title(title, fontsize=9, color=INK2)
    fig.suptitle("Assosiativ yaddaş: lokal axtarışla obrazın bərpası",
                 fontsize=12, color=INK)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "yaddas_berpa.png"), dpi=150)
    plt.close(fig)

    # --- Şəkil 2: hər addımda Φ ---------------------------------------------
    fig, ax = plt.subplots(figsize=(7.5, 4), facecolor=SURFACE)
    style_axes(ax)
    for k, name in enumerate(names):
        hist = runs[name][1].phi_history
        ax.plot(range(len(hist)), hist, color=SERIES[k], linewidth=2,
                solid_capstyle="round", label=f"«{name}»")
        ax.plot(len(hist) - 1, hist[-1], "o", color=SERIES[k], markersize=7,
                markeredgecolor=SURFACE, markeredgewidth=2)
    ax.set_xlabel("addım (çevirmə) nömrəsi", color=INK2)
    ax.set_ylabel("potensial Φ(S)", color=INK2)
    ax.set_title("Hər çevirmədə Φ ciddi artır (ən azı 1 vahid)", color=INK, fontsize=11)
    ax.legend(frameon=False, fontsize=9, labelcolor=INK2)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "yaddas_potensial.png"), dpi=150)
    plt.close(fig)

    # --- Şəkil 3: küy → bərpa faizi -----------------------------------------
    fig, ax = plt.subplots(figsize=(7.5, 4), facecolor=SURFACE)
    style_axes(ax)
    xs = [100 * row[0] for row in table]
    ys = [100 * row[1] for row in table]
    ax.plot(xs, ys, color=SERIES[0], linewidth=2, marker="o", markersize=7,
            markeredgecolor=SURFACE, markeredgewidth=2)
    ax.set_ylim(-3, 103)
    ax.set_xlabel("küy səviyyəsi (dəyişdirilmiş piksellərin faizi)", color=INK2)
    ax.set_ylabel("düzgün bərpa, %", color=INK2)
    ax.set_title("Küy artdıqca düzgün bərpa ehtimalı azalır", color=INK, fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "yaddas_kuy.png"), dpi=150)
    plt.close(fig)

    print(f"Qrafiklər saxlanıldı: {outdir}/yaddas_berpa.png, "
          f"yaddas_potensial.png, yaddas_kuy.png")


# ---------------------------------------------------------------------------
def main():
    sys.stdout.reconfigure(encoding="utf-8")
    vectors = {name: to_vector(t) for name, t in PATTERNS.items()}
    net = hebb_network(list(vectors.values()))

    print("=" * 60)
    print("  Assosiativ yaddaş – Hopfild şəbəkəsi + lokal axtarış")
    print("=" * 60)
    print(f"Neyron sayı: {N},  til sayı: {len(net.edges)},  W = Σ|w| = {net.W}")
    print("Yadda saxlanılan obrazlar:", ", ".join(f"«{k}»" for k in vectors))
    print("Hər obraz stabil konfiqurasiyadırmı?",
          all(net.is_stable(v) for v in vectors.values()))

    runs = recall_demo(net, vectors)
    table = noise_experiment(net, vectors, [0.0, 0.1, 0.2, 0.3, 0.35, 0.4, 0.45, 0.5])
    save_figures(net, vectors, runs, table)


if __name__ == "__main__":
    main()
