from experiments import DataCollector
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import matplotlib
import numpy as np                # für np.arange (numerische Positionen)
from pathlib import Path
matplotlib.rcParams['text.usetex'] = True 
_BASE = Path(__file__).parent.parent  # src/ -> repo root
_DEFAULT_PATH = _BASE / "output/experiments/"
_DEFAULT_PATH.mkdir(parents=True, exist_ok=True)

def bar_chart_gesamt_absolute_inter_intra(title: str, data_set: dict, axes: plt.Axes):
    COLOR_INTRA  = "#7CB5F1DD"   # hellblau  – intra-axis Kanten
    COLOR_INTER  = "#0C3158"     # dunkelblau – inter-axis Kanten
    COLOR_NODES  = "#1B4D3E"     # dunkles Grün – Knoten

    BAR_WIDTH = 0.38
    x_values  = data_set["x"]
    n         = len(x_values)
    pos       = np.arange(n)

    lower_bar    = data_set["absoluter Anteil intra-axis Kanten"]
    upper_bar    = data_set["absoluter Anteil inter-axis Kanten"]
    total_kanten = [a + b for a, b in zip(lower_bar, upper_bar)]
    knoten       = data_set["Gesamtknoten"]

    # Kantenbalken (links, gestapelt)
    axes.bar(pos - BAR_WIDTH / 2, lower_bar, width=BAR_WIDTH,
             color=COLOR_INTRA, label="intra-axis Kanten")
    axes.bar(pos - BAR_WIDTH / 2, upper_bar, width=BAR_WIDTH,
             color=COLOR_INTER, label="inter-axis Kanten", bottom=lower_bar)

    # Knotenbalken (rechts)
    axes.bar(pos + BAR_WIDTH / 2, knoten, width=BAR_WIDTH,
             color=COLOR_NODES, label="Gesamtknoten")

    # Verhältnis-Annotation über Kantenbalken
    for x, k, e in zip(pos, knoten, total_kanten):
        ratio = k / e * 100
        axes.text(x + BAR_WIDTH / 2,
                k + max(total_kanten) * 0.015,
                rf"${ratio:.0f}\%$",
                ha="center", va="bottom", fontsize=6, color="#333333")

    axes.set(title=title, xlabel="Jahr", ylabel="Anteile")
    axes.legend(fontsize=8)
    axes.set_xticks(pos)
    axes.set_xticklabels(x_values, rotation=45, ha="right")

def bar_chart_gesamt_native_min_max(title: str, data_set: dict, axes: plt.Axes):
    COLOR_COMMUNITIES = "#4C78A8"   # blau – native Communities
    COLOR_RANGE_BASE  = "#A8C8E8"   # hellblau – min
    COLOR_RANGE_TOP   = "#0C3158"   # dunkelblau – max - min

    BAR_WIDTH  = 0.38
    x_values   = data_set["x"]
    pos        = np.arange(len(x_values))

    communities = data_set["Native Communities"]
    min_com     = data_set["kleinste Community"]
    max_com     = data_set["größte Community"]
    span        = [mx - mn for mx, mn in zip(max_com, min_com)]

    # Linker Balken: Anzahl Communities
    axes.bar(pos - BAR_WIDTH / 2, communities, width=BAR_WIDTH,
             color=COLOR_COMMUNITIES, label="Anzahl Communities")

    # Rechter Balken: Range (min als Basis, Span oben)
    axes.bar(pos + BAR_WIDTH / 2, min_com, width=BAR_WIDTH,
             color=COLOR_RANGE_BASE, label="kleinste Community")
    axes.bar(pos + BAR_WIDTH / 2, span, width=BAR_WIDTH,
             color=COLOR_RANGE_TOP, label="größte Community",
             bottom=min_com)

    # Max-Wert oben annotieren
    for x, c, mx in zip(pos, communities, max_com):
        axes.text(x - BAR_WIDTH / 2,
                c + max(communities) * 0.015,
                str(c),
                ha="center", va="bottom", fontsize=6)
        axes.text(x + BAR_WIDTH / 2,
                mx + max(max_com) * 0.015,
                str(mx),
                ha="center", va="bottom", fontsize=6)

    axes.set(title=title, xlabel="Jahr", ylabel="Anzahl Knoten")
    axes.legend(fontsize=8)
    axes.set_xticks(pos)
    axes.set_xticklabels(x_values, rotation=45, ha="right")

def boxplot_h_one(title, dsets, axes: plt.Axes):
    axes.boxplot(dsets, 
                      labels=[r"$\tau = 4$", r"$\tau = 6$", r"$\tau = 8$"],
                      patch_artist=True,           # Boxen füllbar
                      boxprops=dict(facecolor="lightblue", alpha=0.5),
                      medianprops=dict(color="red", linewidth=2))
    for i, d in enumerate(dsets, start=1):
        x = np.random.normal(i, 0.04, size=len(d))
        axes.scatter(x, d, alpha=0.4, s=8, color="steelblue", zorder=3)
    alle = [v for d in dsets for v in d]
    axes.set_ylim(min(alle) * 0.95, max(alle) * 1.05)
    axes.set_title(title)
    axes.set_xlabel(r"Schwellwert $\tau$")
    axes.set_ylabel("Laufzeit (s)")

def lineplot_h_one(title, dsets, axes: plt.Axes): # k5_lineplot_laufzeit_zu_tau
    taus  = [4, 6, 8]
    means = [np.mean(d) for d in dsets]
    stds  = [np.std(d)  for d in dsets]

    axes.errorbar(taus, means, yerr=stds,
                  marker="o", linewidth=2, capsize=5,
                  color="steelblue", markersize=6,
                  label="Mittelwert ± Standardabweichung")

    for tau, mean in zip(taus, means):
        if tau == 4:
            ha, offset = "left", (14, 4)    # links unten
        elif tau == 6:
            ha, offset = "left", (8, 4)    # mitte unten
        else:
            ha, offset = "right", (-8, 5)  # rechts unten

        axes.annotate(f"{mean:.2f}s",
                    xy=(tau, mean),
                    xytext=offset, textcoords="offset points",
                    fontsize=9, ha=ha, va="top",
                    clip_on=False)

    axes.set_xticks(taus)
    axes.set_xticklabels([r"$\tau = 4$", r"$\tau = 6$", r"$\tau = 8$"])
    axes.set_title(title)
    axes.set_xlabel(r"Schwellwert $\tau$")
    axes.set_ylabel("Laufzeit (s)")
    axes.legend()

def stacked_bar_partition_plot_h_one(title: str, collector: DataCollector, fig, ax):
    data = {
        "GD2000": [
            collector.data_sets["Laufzeiten und Kreuzungszahlen für tau = 4, GD2000"]["Kreuzungen ex"][0],
            collector.data_sets["Laufzeiten und Kreuzungszahlen für tau = 6, GD2000"]["Kreuzungen ex"][0],
            collector.data_sets["Laufzeiten und Kreuzungszahlen für tau = 8, GD2000"]["Kreuzungen ex"][0],
        ],
        "GD2008": [
            collector.data_sets["Laufzeiten und Kreuzungszahlen für tau = 4, GD2016"]["Kreuzungen ex"][0],
            collector.data_sets["Laufzeiten und Kreuzungszahlen für tau = 6, GD2016"]["Kreuzungen ex"][0],
            collector.data_sets["Laufzeiten und Kreuzungszahlen für tau = 8, GD2016"]["Kreuzungen ex"][0],
        ],
        "GD2024": [
            collector.data_sets["Laufzeiten und Kreuzungszahlen für tau = 4, GD2024"]["Kreuzungen ex"][0],
            collector.data_sets["Laufzeiten und Kreuzungszahlen für tau = 6, GD2024"]["Kreuzungen ex"][0],
            collector.data_sets["Laufzeiten und Kreuzungszahlen für tau = 8, GD2024"]["Kreuzungen ex"][0],
        ],
    }

    taus        = [r"$\tau = 4$", r"$\tau = 6$", r"$\tau = 8$"]
    bar_colors  = ["#4C78A8", "#72A0C1", "#A8C8E8"]
    trend_color = "#2d7a4f"
    years       = list(data.keys())
    x_labels    = [f"{year}\n{tau}" for year in years for tau in taus]
    values      = [data[year][i] for year in years for i in range(3)]
    colors      = bar_colors * 3

    bars = ax.bar(range(9), values, color=colors, edgecolor="white", linewidth=0.8)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(values) * 0.01,
                f"{val:,}", ha="center", va="bottom", fontsize=8)

    for x in [2.5, 5.5]:
        ax.axvline(x, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)

    ax.set_xticks(range(9))
    ax.set_xticklabels(x_labels, fontsize=9)
    ax.set_ylabel("Anzahl Kreuzungen")
    ax.set_title(title)

    # Trendlinie: prozentuale Abnahme relativ zu tau=4, Gefälle nach unten
    ax2 = ax.twinx()
    for i, year in enumerate(years):
        base  = data[year][0]
        pct   = [((v - base) / base) * 100 for v in data[year]]
        x_pos = [i * 3, i * 3 + 1, i * 3 + 2]
        ax2.plot(x_pos, pct, color=trend_color, marker="o",
                 linewidth=1.5, markersize=4,
                 label=r"Abnahme zu $\tau$=4" if i == 0 else "")
        for x, p in zip(x_pos[1:], pct[1:]):
            ax2.text(x, p - 1.5, f"{p:.1f}\%", ha="center", va="top",
                     fontsize=7, color=trend_color)

    ax2.set_ylabel(r"Abnahme zu $\tau$=4 (\%)", color=trend_color)
    ax2.tick_params(axis="y", labelcolor=trend_color)
    ax2.set_ylim(-50, 5)

    # Legende
    legend_elements = [Patch(facecolor=bar_colors[i], label=taus[i]) for i in range(3)]
    legend_elements.append(Line2D([0], [0], color=trend_color, marker="o",
                                  label=r"Abnahme zu $\tau$=4"))
    ax.legend(handles=legend_elements, title=r"Schwellwert $\tau$", fontsize=8)

def bar_chart_runtime_bary_ilp(title: str, data_set: dict, axes: plt.Axes):
    """
    Gestapeltes Balkendiagramm: Barycenter (blau) vs. 1L2S-ILP (grün).
    Drei Schichten: Achsenordnung (geteilt) | Kern-Pipeline | Rest.

    Erwartet data_set = collector.data_sets["Laufzeitenvergleich Bary/ILP"]
    """
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    C_BARY_ORD = "#00f76fce"   # dunkles Blau  – Achsenordnung Bary
    C_ILP_ORD  = "#0077ff99"   # helles Blau   – Achsenordnung ILP
    C_ILP_OPT  = "#0044ffe4"   # Grün          – IP-Modell-Pipeline
    C_REST     = "#a0a0a0"   # Grau          – Sonstige (beide Varianten)
    C_MED_BARY = "#e05c00"   # Orange        – Median Bary
    C_MED_ILP  = "#cc0000"   # Rot           – Median ILP

    x_values  = data_set["x"]
    n         = len(x_values)
    pos       = np.arange(n)
    BAR_WIDTH = 0.38

    # ── Daten ────────────────────────────────────────────────────────────
    b_ord  = data_set["step_ordering Bary t"]
    b_tot  = data_set["Barycenter gesamt t"]
    b_rest = [max(0.0, t - o) for t, o in zip(b_tot, b_ord)]

    i_ord  = data_set["step_ordering ILP t"]
    i_opt  = data_set["ip_model_pipeline t"]
    i_tot  = data_set["1L2S-ILP gesamt t"]
    i_rest = [max(0.0, t - o - c) for t, o, c in zip(i_tot, i_ord, i_opt)]

    bary_med = float(np.median(b_tot))
    ilp_med  = float(np.median(i_tot))

    # ── Balken ───────────────────────────────────────────────────────────
    axes.bar(pos - BAR_WIDTH/2, b_ord,  width=BAR_WIDTH, color=C_BARY_ORD)
    axes.bar(pos - BAR_WIDTH/2, b_rest, width=BAR_WIDTH, color=C_REST,
             bottom=b_ord)

    axes.bar(pos + BAR_WIDTH/2, i_ord,  width=BAR_WIDTH, color=C_ILP_ORD)
    axes.bar(pos + BAR_WIDTH/2, i_opt,  width=BAR_WIDTH, color=C_ILP_OPT,
             bottom=i_ord)
    axes.bar(pos + BAR_WIDTH/2, i_rest, width=BAR_WIDTH, color=C_REST,
             bottom=[o + c for o, c in zip(i_ord, i_opt)])

    # ── Medianlinien ─────────────────────────────────────────────────────
    axes.axhline(bary_med, color=C_MED_BARY, linewidth=2.2,
                 linestyle="--", zorder=5)
    axes.axhline(ilp_med,  color=C_MED_ILP,  linewidth=2.2,
                 linestyle="--", zorder=5)

    # ── Achsen ───────────────────────────────────────────────────────────
    axes.set_title(title)
    axes.set_xlabel("Jahre")
    axes.set_ylabel("Laufzeit (s)")
    axes.set_xticks(pos)
    axes.set_xticklabels(x_values)

    # ── Legende ──────────────────────────────────────────────────────────
    legend_elements = [
        Patch(facecolor=C_BARY_ORD, label=r"ip_ordering (Barycenter)"),
        Patch(facecolor=C_REST,     label=r"Sonstige"),
        Patch(facecolor=C_ILP_ORD,  label=r"ip_ordering (1L2S)"),
        Patch(facecolor=C_ILP_OPT,  label=r"ip_model_pipeline"),
        Line2D([0], [0], color=C_MED_BARY, linewidth=2.2, linestyle="--",
               label=rf"Median Bary: ${bary_med:.1f}$\,s"),
        Line2D([0], [0], color=C_MED_ILP,  linewidth=2.2, linestyle="--",
               label=rf"Median ILP: ${ilp_med:.1f}$\,s"),
    ]
    axes.legend(handles=legend_elements, fontsize=8, loc="upper left")

def plotter(title: str, file_name: str, data_set: str = None, mode: int = 0):
    collector = DataCollector()
    # fig, axes = plt.subplots() balkendiagramm1
    if mode == 0:
        fig, ax = plt.subplots(figsize=(14, 4))
        dset = collector.data_sets[data_set]
        bar_chart_gesamt_absolute_inter_intra(title, dset, ax)
    elif mode == 1:
        fig, axes = plt.subplots(1, 3, figsize=(14, 4))
        for axes, year in zip(ax, ["GD2000", "GD2016", "GD2024"]):
            dsets = [
                collector.data_sets[f"Laufzeiten und Kreuzungszahlen für tau = 4, {year}"]["Laufzeit ex"],
                collector.data_sets[f"Laufzeiten und Kreuzungszahlen für tau = 6, {year}"]["Laufzeit ex"],
                collector.data_sets[f"Laufzeiten und Kreuzungszahlen für tau = 8, {year}"]["Laufzeit ex"],
            ]
            lineplot_h_one(f"Laufzeiten in Abhängigkeit zu $\\tau$ - {year}", dsets, axes)
    elif mode == 2:
        fig, ax = plt.subplots(figsize=(10, 5))
        stacked_bar_partition_plot_h_one(title, collector, fig, ax)
    elif mode == 3:
        fig, ax = plt.subplots(figsize=(14, 4))
        dset = collector.data_sets[data_set]
        bar_chart_gesamt_native_min_max(title, dset, ax)
    elif mode == 4:
        fig, ax = plt.subplots(figsize=(18, 6))
        dset = collector.data_sets[data_set]
        bar_chart_runtime_bary_ilp(title, dset, ax)
    

    plt.tight_layout()
    fig.savefig(_DEFAULT_PATH / (file_name + ".pdf"), bbox_inches="tight")
    plt.close(fig)

if __name__ == "__main__":
    # plotter(r"Gesamtkanten/-knoten Vergleich über alle Jahre $\tau$ = 8", "k5_diagramm1_absolute_anteile", "Gesamtkanten und -anteile tau = 8", 0)
    # plotter(r" ", "k5_lineplot_laufzeit_zu_tau", mode = 1)
    # plotter(r"Kreuzungszahlen in Abhängigkeit zu $\tau$ - GD2000/2016/2024", "k5_balken_kreuzungen_zu_tau", mode = 2)
    # plotter(r"Native Communities und größte/kleinste Community Vergleich über alle Jahre $\tau = 0$", "k5_balken_nativ", "Gesamtkanten und -anteile tau = 8", mode = 3)
    plotter(r"Laufzeitvergleich Barycenter vs.\ 1L2S-ILP (GD 2000 bis 2024, $\tau = 8$)", data_set = "Laufzeitenvergleich Bary/ILP", file_name = "k5_gesamt_laufzeit_bary_ilp", mode = 4)