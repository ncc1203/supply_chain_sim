import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import numpy as np

# === CONFIGURABLE VARIABLES ===
FIGURE_SIZE = (5, 4)         # Width x Height in inches
TITLE_FONT_SIZE = 8
LABEL_FONT_SIZE = 6
TICK_FONT_SIZE = 5
LEGEND_FONT_SIZE = 5
MARKER_SIZE = 3
DROPDOWN_FONT = ("Arial", 9)
LINE_WIDTH = 1.5

# === RESULTS GUI CLASS ===
class ResultsGUI:
    def __init__(self, root, hospitals):
        self.hospitals = hospitals
        self.root = root
        self.root.title("Hospital Results Dashboard")

        # Dropdown menu
        self.selected_hospital = tk.StringVar()
        self.dropdown = ttk.Combobox(root, textvariable=self.selected_hospital, state="readonly", font=DROPDOWN_FONT)
        self.dropdown['values'] = [h.name for h in hospitals]
        self.dropdown.current(0)
        self.dropdown.bind("<<ComboboxSelected>>", self.update_plots)
        self.dropdown.pack(pady=5)

        # Figure and canvas
        self.fig, self.axes = plt.subplots(3, 1, figsize=FIGURE_SIZE)
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack()

        self.update_plots()

    def update_plots(self, event=None):
        hospital_name = self.selected_hospital.get() or self.hospitals[0].name
        hospital = next(h for h in self.hospitals if h.name == hospital_name)

        for ax in self.axes:
            ax.clear()

        # Plot Inventory
        self.axes[0].plot(hospital.h_inventory, linewidth=LINE_WIDTH, markersize=MARKER_SIZE)
        self.axes[0].set_title("Inventory", fontsize=TITLE_FONT_SIZE)
        self.axes[0].set_ylabel("Units", fontsize=LABEL_FONT_SIZE)
        self.axes[0].tick_params(labelsize=TICK_FONT_SIZE)

        # Plot Orders (transposed)
        if hospital.h_orders:
            orders_by_product = list(zip(*hospital.h_orders))
            for idx, order_series in enumerate(orders_by_product):
                self.axes[1].plot(order_series, label=f"Order {idx + 1}", linewidth=LINE_WIDTH, markersize=MARKER_SIZE)
            self.axes[1].set_title("Orders", fontsize=TITLE_FONT_SIZE)
            self.axes[1].legend(fontsize=LEGEND_FONT_SIZE)
            self.axes[1].tick_params(labelsize=TICK_FONT_SIZE)
        self.axes[1].set_ylabel("Units", fontsize=LABEL_FONT_SIZE)

        # Plot Backlog
        self.axes[2].plot(np.cumsum(hospital.h_unmet_demand), linewidth=LINE_WIDTH, markersize=MARKER_SIZE)
        self.axes[2].set_title("Cumulative Unmet Demand", fontsize=TITLE_FONT_SIZE)
        self.axes[2].set_xlabel("Time", fontsize=LABEL_FONT_SIZE)
        self.axes[2].set_ylabel("Units", fontsize=LABEL_FONT_SIZE)
        self.axes[2].tick_params(labelsize=TICK_FONT_SIZE)

        self.fig.tight_layout()
        self.canvas.draw()
