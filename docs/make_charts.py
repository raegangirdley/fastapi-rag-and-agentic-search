from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path("docs/images") if Path("docs").exists() else Path("images")
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": ["Inter", "DejaVu Sans"],
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#8a8f98",
    "axes.labelcolor": "#2b2f36",
    "xtick.color": "#2b2f36",
    "ytick.color": "#2b2f36",
})

COLORS = {"Correct": "#2a9d8f", "Partial": "#e9c46a", "Wrong": "#e76f51"}
SYSTEMS = ["RAG", "No retrieval\n(control)", "Agentic search"]

# Manual answer grades on 14 answerable questions: correct / partial / wrong
GRADES = {"RAG": (11, 3, 0), "No retrieval\n(control)": (4, 4, 6),
          "Agentic search": (2, 8, 4)}
# Citation support on answerable questions (out of 14)
CITES = {"RAG": 12, "No retrieval\n(control)": 0, "Agentic search": 1}
# Average tokens per question and average latency (completed answers)
TOKENS = {"RAG": 3806, "No retrieval\n(control)": 112, "Agentic search": 8653}
LATENCY = {"RAG": 5.86, "No retrieval\n(control)": 1.28, "Agentic search": 10.50}


def save(fig, name):
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", OUT / name)


# Chart 2
fig, (ax1, ax2) = plt.subplots(
    1, 2, figsize=(11, 3.9), gridspec_kw={"width_ratios": [1.7, 1]})

labels = list(reversed(SYSTEMS))
left = [0] * len(labels)
for i, kind in enumerate(["Correct", "Partial", "Wrong"]):
    vals = [GRADES[s][i] for s in labels]
    bars = ax1.barh(labels, vals, left=left, color=COLORS[kind], label=kind,
                    height=0.55, edgecolor="white", linewidth=1.2)
    for bar, v, l in zip(bars, vals, left):
        if v:
            ax1.text(l + v / 2, bar.get_y() + bar.get_height() / 2, str(v),
                     ha="center", va="center", fontsize=11, fontweight="bold",
                     color="white" if kind != "Partial" else "#3d3200")
    left = [a + b for a, b in zip(left, vals)]
ax1.set_xlim(0, 14)
ax1.set_xlabel("Answerable questions (n = 14)")
ax1.set_title("Manual answer grades", loc="left", fontweight="bold", fontsize=12)
ax1.legend(ncol=3, frameon=False, loc="lower right",
           bbox_to_anchor=(1.0, 1.0), fontsize=9)

vals = [CITES[s] for s in labels]
bars = ax2.barh(labels, vals, color="#264653", height=0.55)
ax2.set_xlim(0, 14)
ax2.set_yticklabels([])
ax2.set_xlabel("Answers whose citations support the claims (of 14)")
ax2.set_title("Citation support", loc="left", fontweight="bold", fontsize=12)
for bar, v in zip(bars, vals):
    ax2.text(v + 0.3, bar.get_y() + bar.get_height() / 2, f"{v}/14",
             va="center", fontsize=11, fontweight="bold", color="#264653")

fig.suptitle("llama3.1:8b on 17 FastAPI-docs questions: RAG vs. agentic search",
             x=0.01, ha="left", fontsize=13, fontweight="bold", y=1.03)
fig.text(0.01, -0.07,
         "One human reviewer; small development evaluation, not a benchmark. "
         "Questions share vocabulary with the docs.",
         fontsize=8.5, color="#5b616b")
save(fig, "results-quality.png")

# Chart 2
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 3.2))
labels = SYSTEMS
palette = ["#2a9d8f", "#9aa0a6", "#6d597a"]

bars = ax1.bar(labels, [TOKENS[s] for s in labels], color=palette, width=0.55)
ax1.set_title("Average tokens per question", loc="left", fontweight="bold",
              fontsize=12)
for bar, s in zip(bars, labels):
    ax1.text(bar.get_x() + bar.get_width() / 2, TOKENS[s] + 120,
             f"{TOKENS[s]:,}", ha="center", fontsize=10, fontweight="bold")
ax1.set_ylim(0, max(TOKENS.values()) * 1.18)

bars = ax2.bar(labels, [LATENCY[s] for s in labels], color=palette, width=0.55)
ax2.set_title("Average latency per answer (s)", loc="left", fontweight="bold",
              fontsize=12)
for bar, s in zip(bars, labels):
    ax2.text(bar.get_x() + bar.get_width() / 2, LATENCY[s] + 0.25,
             f"{LATENCY[s]:.1f}", ha="center", fontsize=10, fontweight="bold")
ax2.set_ylim(0, max(LATENCY.values()) * 1.2)

fig.text(0.01, -0.13,
         "Completed answers only (the agent's one 305 s timeout is excluded). "
         "RAG latency excludes the one-time index build.",
         fontsize=8.5, color="#5b616b")
save(fig, "results.png")