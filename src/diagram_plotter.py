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

def bar_chart_gesamt_absolute_inter_intra(title: str, data_set: dict[str, str | int | float | None], axes: plt.Axes):
    colors = ["#0C3158", "#7CB5F1DD", "#4C78A8", "#4C78A8"]
    position = np.arange(len(data_set["x"]))
    x_values = data_set["x"]
    lower_bar = data_set["absoluter Anteil intra-axis Kanten"]
    upper_bar = data_set["absoluter Anteil inter-axis Kanten"]

    axes.bar(x_values, lower_bar, color = colors[1], width=0.5, label="intra-axis")
    axes.bar(x_values, upper_bar, color = colors[0], width=0.5, label="inter-axis", bottom = lower_bar)
    
    axes.set(title = title, xlabel = "Jahr", ylabel = "absoluter Anteil")
    axes.legend()

    axes.set_xticks(x_values)
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

def plotter(title: str, file_name: str, data_set: str = None, mode: int = 0):
    colors = ["#4C78A8", "#4C78A8", "#4C78A8", "#4C78A8"]
    collector = DataCollector()
    # fig, axes = plt.subplots() balkendiagramm1
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    if mode == 0:
        dset = collector.data_sets[data_set]
        bar_chart_gesamt_absolute_inter_intra(title, dset, ax)
    elif mode == 1:
        for ax, year in zip(axes, ["GD2000", "GD2016", "GD2024"]):
            dsets = [
                collector.data_sets[f"Laufzeiten und Kreuzungszahlen für tau = 4, {year}"]["Laufzeit ex"],
                collector.data_sets[f"Laufzeiten und Kreuzungszahlen für tau = 6, {year}"]["Laufzeit ex"],
                collector.data_sets[f"Laufzeiten und Kreuzungszahlen für tau = 8, {year}"]["Laufzeit ex"],
            ]
            lineplot_h_one(f"Laufzeiten in Abhängigkeit zu $\\tau$ - {year}", dsets, ax)
    elif mode == 2:
        fig, ax = plt.subplots(figsize=(10, 5))
        stacked_bar_partition_plot_h_one(title, collector, fig, ax)
    
    

    plt.tight_layout()
    fig.savefig(_DEFAULT_PATH / (file_name + ".pdf"), bbox_inches="tight")
    plt.close(fig)

if __name__ == "__main__":
    # plotter(r"Gesamtkanten und -anteile $\tau$ = 8", "k5_diagramm1_absolute_anteile", "Gesamtkanten und -anteile tau = 8", 0)
    plotter(r" ", "k5_lineplot_laufzeit_zu_tau", mode = 1)
    # plotter(r"Kreuzungszahlen in Abhängigkeit zu $\tau$ - GD2000/2016/2024", "k5_balken_kreuzungen_zu_tau", mode = 2)
    