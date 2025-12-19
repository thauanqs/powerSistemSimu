import matplotlib.pyplot as plt
import os
import math

from matplotlib.transforms import blended_transform_factory

from reports.styles import voltage_color, V_MIN, V_MAX


# ============================================================
# ZOOM (rodinha do mouse)
# ============================================================
def zoom_factory(ax, base_scale=1.2):
    def zoom(event):
        if event.xdata is None or event.ydata is None:
            return

        cur_xlim = ax.get_xlim()
        cur_ylim = ax.get_ylim()

        xdata = event.xdata
        ydata = event.ydata

        if event.button == 'up':
            scale_factor = 1 / base_scale
        elif event.button == 'down':
            scale_factor = base_scale
        else:
            return

        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor

        relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])

        ax.set_xlim([
            xdata - new_width * (1 - relx),
            xdata + new_width * relx
        ])
        ax.set_ylim([
            ydata - new_height * (1 - rely),
            ydata + new_height * rely
        ])

        ax.figure.canvas.draw_idle()

    return zoom


# ============================================================
# PAN (botão esquerdo + arrastar)
# ============================================================
def pan_factory(ax):
    press = {"x": None, "y": None, "xlim": None, "ylim": None}

    def on_press(event):
        if event.inaxes != ax or event.button != 1:
            return
        press["x"] = event.xdata
        press["y"] = event.ydata
        press["xlim"] = ax.get_xlim()
        press["ylim"] = ax.get_ylim()

    def on_motion(event):
        if press["x"] is None or event.inaxes != ax:
            return

        dx = event.xdata - press["x"]
        dy = event.ydata - press["y"]

        ax.set_xlim(
            press["xlim"][0] - dx,
            press["xlim"][1] - dx
        )
        ax.set_ylim(
            press["ylim"][0] - dy,
            press["ylim"][1] - dy
        )

        ax.figure.canvas.draw_idle()

    def on_release(event):
        press["x"] = None
        press["y"] = None

    ax.figure.canvas.mpl_connect("button_press_event", on_press)
    ax.figure.canvas.mpl_connect("motion_notify_event", on_motion)
    ax.figure.canvas.mpl_connect("button_release_event", on_release)


# ============================================================
# VISUALIZAÇÃO INTERATIVA (UI)
# ============================================================
def show_voltage_profile(buses, voltages, save_path=None):
    n = len(buses)

    fig_height = max(6, 0.3 * n)
    colors = [voltage_color(v) for v in voltages]

    fig, ax = plt.subplots(figsize=(10, fig_height))

    ax.barh(range(n), voltages, color=colors)

    ax.axvline(V_MIN, linestyle="--", linewidth=1)
    ax.axvline(V_MAX, linestyle="--", linewidth=1)

    ax.set_xlabel("Tensão (pu)")
    ax.set_ylabel("Barra")
    ax.set_title("Perfil de Tensão do Sistema")

    ax.set_yticks(range(n))
    ax.set_yticklabels([])  # remove ticks automáticos
    ax.invert_yaxis()

    ax.grid(True, axis="x", linestyle="--", alpha=0.5)

    x_max = max(voltages)
    offset = 0.02 * x_max

    # 🔹 valores de tensão (direita)
    for y, v in enumerate(voltages):
        ax.text(
            v + offset,
            y,
            f"{v:.3f}",
            va="center",
            fontsize=8
        )

    ax.set_xlim(0, x_max + 5 * offset)

    # 🔹 números das barras (esquerda) → acompanham zoom/pan
    transform = blended_transform_factory(ax.transAxes, ax.transData)

    for y, bus in enumerate(buses):
        ax.text(
            -0.02,
            y,
            str(bus),
            va="center",
            ha="right",
            fontsize=9,
            transform=transform
        )

    # 🔥 ZOOM
    fig.canvas.mpl_connect("scroll_event", zoom_factory(ax))

    # 🔥 PAN
    pan_factory(ax)

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")

    plt.show()


# ============================================================
# EXPORTAÇÃO PARA PDF (EM PARTES)
# ============================================================
def save_voltage_profile_chunks(
    buses,
    voltages,
    output_dir,
    bars_per_image=20
):
    """
    Gera múltiplas imagens do perfil de tensão,
    com no máximo `bars_per_image` barras por imagem.
    Retorna lista de caminhos das imagens.
    """

    os.makedirs(output_dir, exist_ok=True)

    total = len(buses)
    num_pages = math.ceil(total / bars_per_image)

    image_paths = []

    for i in range(num_pages):
        start = i * bars_per_image
        end = min(start + bars_per_image, total)

        b = buses[start:end]
        v = voltages[start:end]
        colors = [voltage_color(x) for x in v]

        fig_height = max(6, 0.4 * len(b))
        fig, ax = plt.subplots(figsize=(10, fig_height))

        ax.barh(range(len(b)), v, color=colors)

        ax.axvline(V_MIN, linestyle="--", linewidth=1)
        ax.axvline(V_MAX, linestyle="--", linewidth=1)

        ax.set_xlabel("Tensão (pu)")
        ax.set_ylabel("Barra")
        ax.set_title(
            f"Perfil de Tensão – Barras {b[0]} a {b[-1]}"
        )

        ax.set_yticks(range(len(b)))
        ax.set_yticklabels([])
        ax.invert_yaxis()
        ax.grid(True, axis="x", linestyle="--", alpha=0.5)

        x_max = max(v)
        ax.set_xlim(0, x_max * 1.08)

        # valores dentro da barra
        for y, val in enumerate(v):
            ax.text(
                val - 0.01 * x_max,
                y,
                f"{val:.3f}",
                va="center",
                ha="right",
                fontsize=8,
                color="white",
                clip_on=True
            )

        # números das barras (fixos à esquerda)
        transform = blended_transform_factory(ax.transAxes, ax.transData)
        for y, bus in enumerate(b):
            ax.text(
                -0.02,
                y,
                str(bus),
                va="center",
                ha="right",
                fontsize=9,
                transform=transform
            )

        path = os.path.join(output_dir, f"perfil_tensao_{i + 1}.png")
        plt.tight_layout()
        plt.savefig(path, dpi=300)
        plt.close()

        image_paths.append(path)

    return image_paths
