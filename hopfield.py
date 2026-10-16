"""
Hopfild neyron şəbəkələrində lokal axtarış
==========================================

Mənbə: J. Kleinberg, É. Tardos, "Algorithm Design", §12.3
       ("An Application of Local Search to Hopfield Neural Networks").

Model
-----
* Yönləndirilməmiş qraf G = (V, E). Hər təpə bir neyrondur.
* Hər tilin tam ədəd çəkisi var: w_e (müsbət və ya mənfi ola bilər).
* Konfiqurasiya S – hər neyrona bir vəziyyət verir: s_u ∈ {-1, +1}.
* e = (u, v) tili YAXŞIDIR, əgər  w_e · s_u · s_v < 0,  əks halda PİSDİR.
    - w_e < 0  →  u və v EYNİ vəziyyətdə olmaq "istəyir";
    - w_e > 0  →  u və v FƏRQLİ vəziyyətdə olmaq "istəyir".
* u təpəsi RAZIDIR (satisfied), əgər ona bitişik yaxşı tillərin çəkiləri cəmi
  pis tillərin çəkiləri cəmindən kiçik deyilsə:

        Σ_{v ~ u}  w_uv · s_u · s_v  ≤  0

* Bütün təpələr razıdırsa, konfiqurasiya STABİLDİR.

Lokal axtarış: "State-Flipping" alqoritmi
----------------------------------------
    while konfiqurasiya stabil deyil:
        razı olmayan istənilən u təpəsini seç
        s_u := -s_u                       # vəziyyəti çevir (flip)
    return S

Potensial funksiya:  Φ(S) = Σ_{e yaxşı} |w_e|.
Razı olmayan təpəni çevirəndə Φ ən azı 1 artır, Φ isə 0 ≤ Φ ≤ W = Σ|w_e|
aralığındadır. Deməli alqoritm ən çox W addımdan sonra dayanır.

Bu faylı birbaşa işə saldıqda kiçik nümunə üzərində alqoritm addım-addım
göstərilir:   python hopfield.py
"""

import random
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Şəbəkə (qraf)
# ---------------------------------------------------------------------------
class HopfieldNetwork:
    """Çəkili yönləndirilməmiş qraf kimi Hopfild şəbəkəsi."""

    def __init__(self, n, edges):
        """
        n     – neyronların sayı (təpələr 0, 1, ..., n-1)
        edges – (u, v, w) üçlüklərinin siyahısı, w – tam ədəd çəki
        """
        self.n = n
        self.edges = []
        self.neighbors = [[] for _ in range(n)]   # qonşuluq siyahısı: (v, w)
        for u, v, w in edges:
            if u == v:
                raise ValueError("Özünə bağlı til (u = v) ola bilməz")
            if w == 0:
                continue                           # 0 çəkili til heç nəyə təsir etmir
            if not isinstance(w, int):
                raise TypeError("Çəkilər tam ədəd olmalıdır (W sərhədi üçün vacibdir)")
            self.edges.append((u, v, w))
            self.neighbors[u].append((v, w))
            self.neighbors[v].append((u, w))
        self.W = sum(abs(w) for _, _, w in self.edges)

    # --- yerli kəmiyyətlər --------------------------------------------------
    def local_field(self, s, u):
        """h_u = Σ_v w_uv · s_v   (neyrona qonşulardan gələn "sahə")."""
        return sum(w * s[v] for v, w in self.neighbors[u])

    def good_bad(self, s, u):
        """u təpəsinə bitişik yaxşı və pis tillərin çəki cəmləri: (g_u, b_u)."""
        good = bad = 0
        for v, w in self.neighbors[u]:
            if w * s[u] * s[v] < 0:
                good += abs(w)
            else:
                bad += abs(w)
        return good, bad

    def is_satisfied(self, s, u):
        """u razıdır  ⇔  s_u · h_u ≤ 0  ⇔  g_u ≥ b_u."""
        return s[u] * self.local_field(s, u) <= 0

    def is_stable(self, s):
        return all(self.is_satisfied(s, u) for u in range(self.n))

    # --- qlobal kəmiyyətlər -------------------------------------------------
    def potential(self, s):
        """Φ(S) = yaxşı tillərin çəkiləri cəmi."""
        return sum(abs(w) for u, v, w in self.edges if w * s[u] * s[v] < 0)

    def energy(self, s):
        """E(S) = Σ_e w_e · s_u · s_v.   Əlaqə: Φ = (W − E) / 2."""
        return sum(w * s[u] * s[v] for u, v, w in self.edges)


# ---------------------------------------------------------------------------
# Lokal axtarış: State-Flipping alqoritmi
# ---------------------------------------------------------------------------
@dataclass
class Step:
    node: int          # çevrilən neyron
    good: int          # çevrilmədən əvvəl g_u
    bad: int           # çevrilmədən əvvəl b_u
    phi_before: int
    phi_after: int


@dataclass
class Result:
    state: list                      # tapılan stabil konfiqurasiya
    steps: list = field(default_factory=list)
    phi_history: list = field(default_factory=list)

    @property
    def flips(self):
        return len(self.steps)


STRATEGIES = {
    "first":  "ardıcıl – ən kiçik nömrəli razı olmayan neyron",
    "random": "təsadüfi – razı olmayanlardan təsadüfi biri",
    "greedy": "acgöz – Φ-ni ən çox artıran neyron (b_u − g_u maksimum)",
}


def state_flipping(net, s0, strategy="random", rng=None, max_steps=None):
    """
    Kleinberg–Tardos State-Flipping alqoritmi.

    Səmərəli versiya: hər neyron üçün h_u = Σ w_uv s_v saxlanılır və
    razı olmayan neyronlar çoxluğu (U) yenilənir. Beləliklə bir çevirmə
    O(deg(u)) vaxt aparır (seçim strategiyasından asılı olaraq + O(|U|)).

    Qaytarır: Result (stabil konfiqurasiya, addımlar, Φ tarixçəsi).
    """
    if strategy not in STRATEGIES:
        raise ValueError(f"Naməlum strategiya: {strategy}")
    rng = rng or random.Random()
    s = list(s0)
    h = [net.local_field(s, u) for u in range(net.n)]
    unsatisfied = {u for u in range(net.n) if s[u] * h[u] > 0}
    phi = net.potential(s)
    result = Result(state=s, phi_history=[phi])

    while unsatisfied:                                 # stabil deyilsə...
        if max_steps is not None and result.flips >= max_steps:
            break

        # 1) Razı olmayan bir u neyronunu seç
        if strategy == "first":
            u = min(unsatisfied)
        elif strategy == "random":
            u = rng.choice(sorted(unsatisfied))
        else:  # greedy
            u = max(unsatisfied, key=lambda x: (s[x] * h[x], -x))

        # s_u · h_u = b_u − g_u  >  0  (razı deyil). Çəkilər tam olduğuna görə ≥ 1.
        gain = s[u] * h[u]
        g = (sum(abs(w) for _, w in net.neighbors[u]) - gain) // 2
        b = g + gain

        # 2) Vəziyyəti çevir: yaxşı tillər pis olur, pis tillər yaxşı.
        s[u] = -s[u]
        phi_new = phi - g + b                          # = phi + gain ≥ phi + 1
        assert phi_new >= phi + 1, "Teorem pozuldu: Φ ən azı 1 artmalıdır"

        # 3) Qonşuların sahəsini və razılıq vəziyyətini yenilə
        unsatisfied.discard(u)                         # indi s_u·h_u = −gain < 0
        for v, w in net.neighbors[u]:
            h[v] += 2 * w * s[u]
            if s[v] * h[v] > 0:
                unsatisfied.add(v)
            else:
                unsatisfied.discard(v)

        result.steps.append(Step(u, g, b, phi, phi_new))
        result.phi_history.append(phi_new)
        phi = phi_new

    assert result.flips <= net.W, "Teorem pozuldu: addım sayı W-dən çox ola bilməz"
    return result


# ---------------------------------------------------------------------------
# Kiçik nümayiş
# ---------------------------------------------------------------------------
EXAMPLE_EDGES = [
    # (u, v, w)
    (0, 1, 6), (0, 2, 4), (0, 3, 5), (0, 5, -8),
    (1, 4, -7), (1, 5, 4),
    (2, 3, 6),
    (3, 4, 9), (3, 5, -4),
]


def fmt_state(s):
    return "[" + " ".join("+" if x > 0 else "−" for x in s) + "]"


def demo():
    net = HopfieldNetwork(6, EXAMPLE_EDGES)
    s0 = [+1] * net.n

    print("=" * 66)
    print("  Hopfild şəbəkəsi – State-Flipping lokal axtarış alqoritmi")
    print("=" * 66)
    print(f"Neyron sayı n = {net.n},  til sayı m = {len(net.edges)}")
    print("Tillər (u, v, w):", ", ".join(f"({u},{v},{w:+d})" for u, v, w in net.edges))
    print(f"W = Σ|w_e| = {net.W}   →   alqoritm ən çox {net.W} addımda dayanmalıdır\n")

    print(f"Başlanğıc konfiqurasiya  S0 = {fmt_state(s0)}")
    print(f"Φ(S0) = {net.potential(s0)},  E(S0) = {net.energy(s0)}")
    print("Razı olmayan neyronlar:",
          [u for u in range(net.n) if not net.is_satisfied(s0, u)], "\n")

    res = state_flipping(net, s0, strategy="first")

    s = list(s0)
    print(f"{'addım':>5} | {'neyron':>6} | {'g_u':>4} | {'b_u':>4} | {'Φ':>9} | konfiqurasiya")
    print("-" * 66)
    for i, st in enumerate(res.steps, 1):
        s[st.node] = -s[st.node]
        print(f"{i:>5} | {st.node:>6} | {st.good:>4} | {st.bad:>4} | "
              f"{st.phi_before:>3} → {st.phi_after:<3} | {fmt_state(s)}")
    print("-" * 66)

    print(f"\nNəticə: {res.flips} çevirmədən sonra stabil konfiqurasiya tapıldı.")
    print(f"S* = {fmt_state(res.state)},  Φ(S*) = {net.potential(res.state)},"
          f"  E(S*) = {net.energy(res.state)}")
    print(f"Stabildirmi? {net.is_stable(res.state)}")
    print(f"Yoxlama: addım sayı {res.flips} ≤ W = {net.W}  ✓")
    print(f"Yoxlama: Φ = (W − E)/2 = ({net.W} − ({net.energy(res.state)}))/2 = "
          f"{(net.W - net.energy(res.state)) // 2}  ✓\n")

    print("Hər neyron üçün yekun yoxlama (g_u ≥ b_u olmalıdır):")
    for u in range(net.n):
        g, b = net.good_bad(res.state, u)
        print(f"  neyron {u}: s={res.state[u]:+d}  yaxşı={g:>2}  pis={b:>2}  "
              f"{'razı ✓' if g >= b else 'RAZI DEYİL ✗'}")

    # Lokal optimum ≠ qlobal optimum: bütün 2^n konfiqurasiyanı yoxlayaq
    from itertools import product
    best = max((list(c) for c in product([-1, 1], repeat=net.n)), key=net.potential)
    print(f"\nMüqayisə üçün tam yoxlama (2^{net.n} = {2 ** net.n} konfiqurasiya):")
    print(f"  qlobal maksimum Φ = {net.potential(best)}  (S = {fmt_state(best)})")
    print(f"  lokal axtarışın tapdığı Φ = {net.potential(res.state)}")
    print("  → Stabil konfiqurasiya LOKAL optimumdur: heç bir tək neyronu çevirmək Φ-ni\n"
          "    artırmır, lakin qlobal optimum olmaya da bilər.")


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    demo()
