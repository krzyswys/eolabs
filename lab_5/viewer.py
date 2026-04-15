#!/usr/bin/env python3
"""
Hyperspectral BSQ Viewer
------------------------
Browse ENVI/BSQ hyperspectral data cubes.
Click any pixel in the RGB preview to display its full spectral signature.
Export the selected spectrum to CSV.

Usage:
    python viewer.py [path/to/file.hdr]

If no path is given the tool searches data/images/ for .hdr files.
Requires Python 3.10+  (uses X | Y union type hints)
"""

import sys
import csv
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

try:
    import spectral.io.envi as envi
except ImportError:
    sys.exit(
        "The 'spectral' library is missing.\n"
        "Install it with:  pip install spectral"
    )

# ── Configuration ─────────────────────────────────────────────────────────────

# Default search directory (relative to this script)
DATA_DIR = Path(__file__).parent / "Obrazy lotnicze"

# Fallback RGB band indices (0-based) when the header has no default_bands
FALLBACK_RGB = (30, 20, 10)

# Land-cover classes used in the lab guide
LAND_COVER_CLASSES = (
    ("water", "deepskyblue"),
    ("vegetation", "limegreen"),
    ("soil", "saddlebrown"),
    ("urban", "dimgray"),
)

# ── ENVI header helpers ───────────────────────────────────────────────────────

def find_hdr_files(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.hdr"))


def parse_wavelengths(meta: dict) -> np.ndarray | None:
    """Return wavelength array from ENVI metadata, or None if absent."""
    wl = meta.get("wavelength")
    if wl:
        return np.array([float(w) for w in wl])
    return None


def get_rgb_bands(meta: dict) -> tuple[int, int, int]:
    """
    Read default_bands from the ENVI header.
    Header values are 1-based floats, so we subtract 1.
    Falls back to FALLBACK_RGB if the key is missing.
    """
    db = meta.get("default bands")
    if db and len(db) >= 3:
        return tuple(int(float(v)) - 1 for v in db[:3])
    return FALLBACK_RGB


def get_ignore_value(meta: dict) -> float | None:
    """Return the no-data / ignore value declared in the ENVI header."""
    raw = meta.get("data ignore value")
    if raw:
        try:
            return float(str(raw).strip())
        except ValueError:
            pass
    return None


# ── Image I/O ─────────────────────────────────────────────────────────────────

def load_image(hdr_path: Path):
    """
    Open an ENVI image via spectral (memory-mapped — no full load into RAM).
    The companion .bsq file is located automatically next to the .hdr.
    """
    return envi.open(str(hdr_path))


def read_rgb(img, r: int, g: int, b: int, ignore_value: float | None) -> np.ndarray:
    """
    Read three bands and return a float32 RGB array (values 0–1) for display.
    No-data pixels and negative values are masked before the stretch.
    Applies a per-channel 2–98 % percentile stretch.
    """
    # shape: (lines, samples, 3) — reads only 3 bands from disk
    rgb = img.read_bands([r, g, b]).astype(np.float32)

    if ignore_value is not None:
        rgb[rgb >= ignore_value] = np.nan
    rgb[rgb < 0] = np.nan

    for c in range(3):
        ch = rgb[:, :, c]
        p2, p98 = np.nanpercentile(ch, [2, 98])
        rgb[:, :, c] = np.clip((ch - p2) / max(p98 - p2, 1e-6), 0, 1)

    return np.nan_to_num(rgb, nan=0.0)


def read_spectrum(img, row: int, col: int, ignore_value: float | None) -> np.ndarray:
    """
    Read the full spectrum (all bands) for a single pixel.
    BSQ layout makes this efficient: one seek per band.
    Bad / no-data values are replaced with NaN so the plot shows gaps.
    """
    spec = img.read_pixel(row, col).astype(np.float64)
    if ignore_value is not None:
        spec[spec >= ignore_value] = np.nan
    spec[spec < 0] = np.nan
    return spec


# ── Application ───────────────────────────────────────────────────────────────

class HyperspectralViewer:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Hyperspectral BSQ Viewer")
        self.root.geometry("1300x720")

        # state
        self.img = None
        self.wavelengths: np.ndarray | None = None
        self.ignore_value: float | None = None
        self.rgb_display: np.ndarray | None = None   # float32 (lines, samples, 3)
        self.active_class = tk.StringVar(value=LAND_COVER_CLASSES[0][0])
        self.class_points: dict[str, tuple[int, int]] = {}
        self.class_spectra: dict[str, np.ndarray] = {}

        self._build_ui()
        self._auto_load()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # top toolbar
        bar = tk.Frame(self.root, bd=1, relief=tk.RAISED)
        bar.pack(side=tk.TOP, fill=tk.X)

        tk.Button(bar, text="Open file…", command=self._open_file).pack(
            side=tk.LEFT, padx=4, pady=3
        )
        tk.Button(bar, text="Export active class CSV…", command=self._export_csv).pack(
            side=tk.LEFT, padx=4, pady=3
        )
        tk.Button(bar, text="Export all class CSVs…", command=self._export_all_csv).pack(
            side=tk.LEFT, padx=4, pady=3
        )
        tk.Button(bar, text="Remove active mark", command=self._remove_active_mark).pack(
            side=tk.LEFT, padx=4, pady=3
        )
        self.status_var = tk.StringVar(value="No file loaded.")
        tk.Label(bar, textvariable=self.status_var, anchor=tk.W, fg="#444").pack(
            side=tk.LEFT, padx=12
        )

        class_bar = tk.Frame(self.root, bd=1, relief=tk.GROOVE)
        class_bar.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(2, 0))
        tk.Label(
            class_bar,
            text="Active class for next click:",
            anchor=tk.W,
        ).pack(side=tk.LEFT, padx=6, pady=4)
        for class_name, color in LAND_COVER_CLASSES:
            tk.Radiobutton(
                class_bar,
                text=class_name,
                value=class_name,
                variable=self.active_class,
                fg=color,
            ).pack(side=tk.LEFT, padx=5)

        # matplotlib figure embedded inside the tkinter window
        self.fig = Figure(figsize=(14, 6.5))
        self.ax_rgb = self.fig.add_subplot(1, 2, 1)
        self.ax_spec = self.fig.add_subplot(1, 2, 2)
        self.fig.tight_layout(pad=2.5)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        NavigationToolbar2Tk(self.canvas, self.root)  # adds zoom/pan/save toolbar
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # left-click to inspect a pixel
        self.canvas.mpl_connect("button_press_event", self._on_click)

    # ── File loading ──────────────────────────────────────────────────────────

    def _auto_load(self):
        """
        Called at startup. Loads a file from DATA_DIR automatically if
        exactly one .hdr is present, otherwise shows a picker dialog.
        A path can also be passed as a command-line argument.
        """
        if len(sys.argv) > 1:
            self._load(Path(sys.argv[1]))
            return

        if not DATA_DIR.exists():
            self.status_var.set(f"Data directory not found: {DATA_DIR}")
            return

        hdrs = find_hdr_files(DATA_DIR)
        if not hdrs:
            self.status_var.set(f"No .hdr files found in {DATA_DIR}")
            return
        if len(hdrs) == 1:
            self._load(hdrs[0])
        else:
            self._pick_file(hdrs)

    def _pick_file(self, hdrs: list[Path]):
        """Small modal dialog when multiple datasets are available."""
        dlg = tk.Toplevel(self.root)
        dlg.title("Select dataset")
        dlg.grab_set()
        tk.Label(dlg, text="Multiple datasets found — select one to open:").pack(
            padx=12, pady=8
        )
        lb = tk.Listbox(dlg, width=72, height=min(len(hdrs), 10))
        lb.pack(padx=12, pady=4)
        for h in hdrs:
            lb.insert(tk.END, h.name)
        lb.selection_set(0)

        def on_ok():
            idx = lb.curselection()
            dlg.destroy()
            self._load(hdrs[idx[0]])

        tk.Button(dlg, text="Open", command=on_ok, width=12).pack(pady=8)
        dlg.wait_window()

    def _open_file(self):
        path = filedialog.askopenfilename(
            title="Open ENVI header (.hdr)",
            initialdir=DATA_DIR if DATA_DIR.exists() else Path.home(),
            filetypes=[("ENVI header", "*.hdr"), ("All files", "*.*")],
        )
        if path:
            self._load(Path(path))

    def _load(self, hdr_path: Path):
        self.status_var.set(f"Loading RGB bands from  {hdr_path.name} …")
        self.root.update_idletasks()
        try:
            self.img = load_image(hdr_path)
            meta = self.img.metadata
            self.wavelengths = parse_wavelengths(meta)
            self.ignore_value = get_ignore_value(meta)
            r, g, b = get_rgb_bands(meta)
            self.rgb_display = read_rgb(self.img, r, g, b, self.ignore_value)
            self.class_points = {}
            self.class_spectra = {}
            self._refresh_plots()
            self.status_var.set(
                f"{hdr_path.name}  |  "
                f"{self.img.nrows} lines × {self.img.ncols} samples × "
                f"{self.img.nbands} bands  |  "
                "Select class -> click RGB. Max 4 marks (one per class)."
            )
        except Exception as exc:
            messagebox.showerror("Error loading file", str(exc))
            self.status_var.set("Load failed.")

    # ── Plotting ──────────────────────────────────────────────────────────────

    def _refresh_plots(self):
        # ── left: RGB image ──
        self.ax_rgb.clear()
        if self.rgb_display is not None:
            self.ax_rgb.imshow(
                self.rgb_display, interpolation="bilinear", aspect="auto"
            )
            for class_name, color in LAND_COVER_CLASSES:
                if class_name not in self.class_points:
                    continue
                row, col = self.class_points[class_name]
                self.ax_rgb.plot(
                    col,
                    row,
                    marker="o",
                    markersize=8,
                    markeredgewidth=1.5,
                    markeredgecolor="white",
                    color=color,
                    label=class_name,
                )
            if self.class_points:
                self.ax_rgb.legend(loc="lower right", fontsize=8, framealpha=0.8)
        self.ax_rgb.set_title(
            f"RGB preview — active class: {self.active_class.get()} "
            "(left click to add, right click near mark to remove)"
        )
        self.ax_rgb.axis("off")

        # ── right: spectral signature ──
        self.ax_spec.clear()
        if self.class_spectra:
            any_spectrum = next(iter(self.class_spectra.values()))
            x = (
                self.wavelengths
                if self.wavelengths is not None
                else np.arange(len(any_spectrum))
            )
            xlabel = "Wavelength (nm)" if self.wavelengths is not None else "Band index"

            for class_name, color in LAND_COVER_CLASSES:
                if class_name not in self.class_spectra:
                    continue
                linewidth = 2.2 if class_name == self.active_class.get() else 1.4
                row, col = self.class_points[class_name]
                self.ax_spec.plot(
                    x,
                    self.class_spectra[class_name],
                    linewidth=linewidth,
                    color=color,
                    label=f"{class_name} ({row}, {col})",
                )

            self.ax_spec.set_title("Collected spectral signatures (up to 4)")
            self.ax_spec.set_xlabel(xlabel)
            self.ax_spec.set_ylabel("Reflectance (× 10⁻⁴)")
            self.ax_spec.grid(True, alpha=0.3)
            self.ax_spec.legend(loc="best", fontsize=8)
        else:
            self.ax_spec.set_title("Spectral signatures")
            self.ax_spec.text(
                0.5, 0.5,
                "Select a class and click the RGB image.\nOne click per class (max 4 total).",
                ha="center", va="center",
                transform=self.ax_spec.transAxes,
                color="gray", fontsize=12,
            )

        self.fig.tight_layout(pad=2.5)
        self.canvas.draw()

    # ── Mouse click handler ───────────────────────────────────────────────────

    def _on_click(self, event):
        if event.inaxes is not self.ax_rgb or self.img is None:
            return
        if event.xdata is None or event.ydata is None:
            return
        col = int(round(event.xdata))
        row = int(round(event.ydata))
        if not (0 <= row < self.img.nrows and 0 <= col < self.img.ncols):
            return

        if event.button == 3:
            self._remove_nearest_mark(row, col)
            return

        if event.button != 1:
            return

        class_name = self.active_class.get()
        if class_name in self.class_points:
            messagebox.showinfo(
                "Class already set",
                f"'{class_name}' already has a mark.\n"
                "Remove it first if you want to choose another pixel.",
            )
            return

        if len(self.class_points) >= len(LAND_COVER_CLASSES):
            messagebox.showinfo(
                "Limit reached",
                "You already placed 4 marks (one per class).",
            )
            return

        self.class_points[class_name] = (row, col)
        self.class_spectra[class_name] = read_spectrum(
            self.img, row, col, self.ignore_value
        )
        self._refresh_plots()
        remaining = len(LAND_COVER_CLASSES) - len(self.class_points)
        self.status_var.set(
            f"Saved {class_name} at ({row}, {col})  |  "
            f"Remaining classes: {remaining}."
        )

    # ── CSV export ────────────────────────────────────────────────────────────

    def _write_spectrum_csv(self, path: str, spectrum: np.ndarray):
        x = (
            self.wavelengths
            if self.wavelengths is not None
            else np.arange(len(spectrum))
        )
        col_header = "wavelength_nm" if self.wavelengths is not None else "band"

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([col_header, "value"])
            for xi, vi in zip(x, spectrum):
                writer.writerow([float(xi), "" if np.isnan(vi) else float(vi)])

    def _export_csv(self):
        class_name = self.active_class.get()
        if class_name not in self.class_spectra:
            messagebox.showinfo("Nothing to export", "Click on a pixel first.")
            return

        row, col = self.class_points[class_name]
        default_name = f"{class_name}.csv"
        path = filedialog.asksaveasfilename(
            title=f"Save '{class_name}' spectrum as CSV",
            initialfile=default_name,
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return

        self._write_spectrum_csv(path, self.class_spectra[class_name])
        self.status_var.set(f"Saved {class_name} -> {path}")
        messagebox.showinfo(
            "Saved",
            f"Exported '{class_name}' from pixel ({row}, {col}) to:\n{path}",
        )

    def _export_all_csv(self):
        if not self.class_spectra:
            messagebox.showinfo(
                "Nothing to export",
                "No classes are collected yet. Add marks first.",
            )
            return

        output_dir = filedialog.askdirectory(title="Select folder for class CSV files")
        if not output_dir:
            return

        saved_files = []
        for class_name, _ in LAND_COVER_CLASSES:
            spectrum = self.class_spectra.get(class_name)
            if spectrum is None:
                continue
            out_path = str(Path(output_dir) / f"{class_name}.csv")
            self._write_spectrum_csv(out_path, spectrum)
            saved_files.append(out_path)

        self.status_var.set(
            f"Exported {len(saved_files)} class file(s) to {output_dir}"
        )
        messagebox.showinfo(
            "Export complete",
            "Saved files:\n" + "\n".join(saved_files),
        )

    def _remove_active_mark(self):
        class_name = self.active_class.get()
        if class_name not in self.class_points:
            messagebox.showinfo("Nothing to remove", f"No mark for '{class_name}'.")
            return
        self.class_points.pop(class_name, None)
        self.class_spectra.pop(class_name, None)
        self._refresh_plots()
        self.status_var.set(f"Removed mark for '{class_name}'.")

    def _remove_nearest_mark(self, row: int, col: int):
        if not self.class_points:
            return

        nearest_class = None
        nearest_dist2 = None
        for class_name, (r, c) in self.class_points.items():
            dist2 = (r - row) ** 2 + (c - col) ** 2
            if nearest_dist2 is None or dist2 < nearest_dist2:
                nearest_class = class_name
                nearest_dist2 = dist2

        if nearest_class is None or nearest_dist2 is None or nearest_dist2 > 36:
            return

        self.class_points.pop(nearest_class, None)
        self.class_spectra.pop(nearest_class, None)
        self.active_class.set(nearest_class)
        self._refresh_plots()
        self.status_var.set(f"Removed mark for '{nearest_class}' via right click.")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    HyperspectralViewer(root)
    root.mainloop()
