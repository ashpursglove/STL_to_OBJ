
#!/usr/bin/env python3
"""
Ash's STL → OBJ Converter
===========================

A local-only desktop tool to convert STL files to OBJ using trimesh.

Features:
- Dark navy + orange theme
- Drag & drop STL files (and folders)
- Batch conversion in a background thread (UI stays responsive)
- Options:
  - Merge (weld) vertices
  - Validate & cleanup mesh (version-safe across older/newer trimesh)
  - Scale factor + presets
  - Center to origin
  - Swap Y/Z + flip axes
- Selected file stats (verts/faces/bounds/extents) with bounds/extents shown to 2dp
- Output naming modes:
  - Same name as STL
  - Add suffix
  - Custom base name (auto-numbered for batch and collision-safe)

Dependencies:
    pip install pyqt5 trimesh numpy
"""

from __future__ import annotations

import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import trimesh
from PyQt5 import QtCore, QtGui, QtWidgets


# -----------------------------
# Theme (dark navy + orange)
# -----------------------------
NAVY_BG = "#0b1320"
NAVY_PANEL = "#0f1b2e"
NAVY_PANEL_2 = "#101f36"
TEXT = "#e9eef7"
MUTED = "#b7c0cf"
ORANGE = "#ff8c00"
RED = "#ff4d4d"


def apply_dark_orange_theme(app: QtWidgets.QApplication) -> None:
    """Apply a consistent dark navy + orange theme via palette + QSS."""
    palette = QtGui.QPalette()

    palette.setColor(QtGui.QPalette.Window, QtGui.QColor(NAVY_BG))
    palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(TEXT))
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor(NAVY_PANEL))
    palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(NAVY_PANEL_2))
    palette.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor(TEXT))
    palette.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor(NAVY_BG))
    palette.setColor(QtGui.QPalette.Text, QtGui.QColor(TEXT))
    palette.setColor(QtGui.QPalette.Button, QtGui.QColor(NAVY_PANEL_2))
    palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(TEXT))
    palette.setColor(QtGui.QPalette.BrightText, QtGui.QColor(RED))
    palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(ORANGE))
    palette.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor(NAVY_BG))

    app.setPalette(palette)

    app.setStyleSheet(f"""
        QWidget {{
            font-size: 10.5pt;
            color: {TEXT};
            background-color: {NAVY_BG};
        }}

        QGroupBox {{
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 10px;
            margin-top: 10px;
            padding: 10px;
            background-color: {NAVY_PANEL};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 6px;
            color: {TEXT};
            font-weight: 600;
        }}

        QLineEdit, QPlainTextEdit, QTextEdit {{
            background-color: {NAVY_PANEL_2};
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 8px;
            padding: 6px;
            selection-background-color: {ORANGE};
            selection-color: {NAVY_BG};
        }}

        QListWidget {{
            background-color: {NAVY_PANEL_2};
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 8px;
            padding: 4px;
        }}
        QListWidget::item {{
            padding: 6px;
            border-radius: 6px;
        }}
        QListWidget::item:selected {{
            background-color: rgba(255, 140, 0, 0.25);
            border: 1px solid rgba(255, 140, 0, 0.55);
        }}

        QPushButton {{
            background-color: {NAVY_PANEL_2};
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 10px;
            padding: 8px 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            border: 1px solid rgba(255, 140, 0, 0.7);
        }}
        QPushButton:pressed {{
            background-color: rgba(255, 140, 0, 0.20);
            border: 1px solid rgba(255, 140, 0, 0.9);
        }}
        QPushButton#primaryButton {{
            background-color: rgba(255, 140, 0, 0.18);
            border: 1px solid rgba(255, 140, 0, 0.85);
        }}
        QPushButton#dangerButton {{
            background-color: rgba(255, 77, 77, 0.12);
            border: 1px solid rgba(255, 77, 77, 0.75);
        }}

        QCheckBox {{
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 1px solid rgba(255,255,255,0.18);
            background-color: {NAVY_PANEL_2};
        }}
        QCheckBox::indicator:checked {{
            background-color: rgba(255, 140, 0, 0.85);
            border: 1px solid rgba(255, 140, 0, 1.0);
        }}

        QProgressBar {{
            border: 1px solid rgba(255,255,255,0.14);
            border-radius: 8px;
            background-color: {NAVY_PANEL_2};
            text-align: center;
            padding: 2px;
        }}
        QProgressBar::chunk {{
            background-color: rgba(255, 140, 0, 0.85);
            border-radius: 6px;
        }}

        QSpinBox, QDoubleSpinBox, QComboBox {{
            background-color: {NAVY_PANEL_2};
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 8px;
            padding: 4px 6px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {NAVY_PANEL};
            selection-background-color: rgba(255, 140, 0, 0.25);
        }}

        QLabel#muted {{
            color: {MUTED};
        }}
    """)


# -----------------------------
# Conversion config & helpers
# -----------------------------
@dataclass
class ConvertOptions:
    merge_vertices: bool
    validate_cleanup: bool
    scale_factor: float
    center_to_origin: bool
    swap_yz: bool
    flip_x: bool
    flip_y: bool
    flip_z: bool


@dataclass
class MeshStats:
    vertices: int
    faces: int
    bounds_min: Tuple[float, float, float]
    bounds_max: Tuple[float, float, float]
    extents: Tuple[float, float, float]


def safe_mesh_stats(mesh: trimesh.Trimesh) -> MeshStats:
    bounds = mesh.bounds  # shape (2, 3)
    bmin = tuple(float(x) for x in bounds[0])
    bmax = tuple(float(x) for x in bounds[1])
    ext = tuple(float(x) for x in (bounds[1] - bounds[0]))
    return MeshStats(
        vertices=int(len(mesh.vertices)),
        faces=int(len(mesh.faces)),
        bounds_min=bmin,
        bounds_max=bmax,
        extents=ext,
    )


def load_stl_as_mesh(input_path: Path) -> trimesh.Trimesh:
    """Load STL robustly. If trimesh returns a Scene, concatenate into one Trimesh."""
    loaded = trimesh.load(str(input_path), force="mesh")

    if isinstance(loaded, trimesh.Scene):
        if not loaded.geometry:
            raise ValueError("STL loaded as a Scene but contains no geometry.")
        meshes = [g for g in loaded.geometry.values() if isinstance(g, trimesh.Trimesh)]
        if not meshes:
            raise ValueError("No mesh geometry found in the loaded scene.")
        return trimesh.util.concatenate(meshes)

    if not isinstance(loaded, trimesh.Trimesh):
        raise TypeError(f"Unsupported loaded type: {type(loaded)}")

    return loaded


def cleanup_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """
    Cleanup pass that works across a wide range of trimesh versions.

    We do feature-detection because some installs (especially older ones)
    do not have methods like remove_degenerate_faces / remove_duplicate_faces.

    What we try to accomplish:
    - Remove degenerate faces (zero area / repeated vertices)
    - Remove duplicate faces (exact duplicates, regardless of winding)
    - Remove NaN/inf vertices
    - Remove unreferenced vertices
    - Fix normals if possible
    """
    m = mesh.copy()

    # ------------------------------------------------------------
    # 1) Remove non-finite values (if available)
    # ------------------------------------------------------------
    if hasattr(m, "remove_infinite_values"):
        try:
            m.remove_infinite_values()
        except Exception:
            pass
    else:
        # Fallback: filter vertices that are finite, then drop faces referencing removed verts
        try:
            v = np.asarray(m.vertices)
            finite_mask = np.isfinite(v).all(axis=1)
            if not finite_mask.all():
                new_index = -np.ones(len(finite_mask), dtype=np.int64)
                new_index[finite_mask] = np.arange(int(finite_mask.sum()), dtype=np.int64)

                faces = np.asarray(m.faces, dtype=np.int64)
                face_mask = finite_mask[faces].all(axis=1)
                faces = faces[face_mask]
                faces = new_index[faces]

                m.vertices = v[finite_mask]
                m.faces = faces
        except Exception:
            pass

    # ------------------------------------------------------------
    # 2) Remove degenerate faces
    # ------------------------------------------------------------
    try:
        if hasattr(m, "remove_degenerate_faces"):
            m.remove_degenerate_faces()
        elif hasattr(m, "nondegenerate_faces"):
            keep = m.nondegenerate_faces()
            if keep is not None:
                keep = np.asarray(keep)
                if keep.dtype == bool:
                    face_mask = keep
                else:
                    face_mask = np.zeros(len(m.faces), dtype=bool)
                    face_mask[keep] = True
                m.update_faces(face_mask)
        else:
            # Last resort: remove faces with repeated vertex indices
            f = np.asarray(m.faces)
            face_mask = np.logical_and.reduce([
                f[:, 0] != f[:, 1],
                f[:, 1] != f[:, 2],
                f[:, 0] != f[:, 2],
            ])
            m.update_faces(face_mask)
    except Exception:
        pass

    # ------------------------------------------------------------
    # 3) Remove duplicate faces
    # ------------------------------------------------------------
    try:
        if hasattr(m, "remove_duplicate_faces"):
            m.remove_duplicate_faces()
        else:
            faces = np.asarray(m.faces, dtype=np.int64)
            if len(faces) > 0:
                canonical = np.sort(faces, axis=1)
                canonical_view = np.ascontiguousarray(canonical).view(
                    np.dtype((np.void, canonical.dtype.itemsize * canonical.shape[1]))
                )
                _, unique_idx = np.unique(canonical_view, return_index=True)
                face_mask = np.zeros(len(faces), dtype=bool)
                face_mask[unique_idx] = True
                m.update_faces(face_mask)
    except Exception:
        pass

    # ------------------------------------------------------------
    # 4) Remove unreferenced vertices
    # ------------------------------------------------------------
    try:
        if hasattr(m, "remove_unreferenced_vertices"):
            m.remove_unreferenced_vertices()
        else:
            faces = np.asarray(m.faces, dtype=np.int64)
            used = np.unique(faces.reshape(-1))
            new_index = -np.ones(len(m.vertices), dtype=np.int64)
            new_index[used] = np.arange(len(used), dtype=np.int64)

            m.vertices = np.asarray(m.vertices)[used]
            m.faces = new_index[faces]
    except Exception:
        pass

    # ------------------------------------------------------------
    # 5) Normals (best effort)
    # ------------------------------------------------------------
    try:
        if hasattr(m, "fix_normals"):
            m.fix_normals()
    except Exception:
        pass

    return m


def apply_transforms(mesh: trimesh.Trimesh, opt: ConvertOptions) -> trimesh.Trimesh:
    """
    Applies transforms in a predictable order:
    1) axis swaps/flips
    2) scaling
    3) centering
    """
    m = mesh.copy()
    V = np.asarray(m.vertices).copy()

    if opt.swap_yz:
        V = V[:, [0, 2, 1]]

    if opt.flip_x:
        V[:, 0] *= -1.0
    if opt.flip_y:
        V[:, 1] *= -1.0
    if opt.flip_z:
        V[:, 2] *= -1.0

    if opt.scale_factor != 1.0:
        V *= float(opt.scale_factor)

    m.vertices = V

    if opt.center_to_origin:
        b = m.bounds
        center = (b[0] + b[1]) * 0.5
        m.apply_translation(-center)

    return m


def convert_one(input_path: Path, output_path: Path, opt: ConvertOptions) -> MeshStats:
    """Convert a single STL to OBJ and return exported mesh stats."""
    mesh = load_stl_as_mesh(input_path)

    if opt.merge_vertices:
        mesh.merge_vertices()

    mesh = apply_transforms(mesh, opt)

    if opt.validate_cleanup:
        mesh = cleanup_mesh(mesh)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(str(output_path))

    return safe_mesh_stats(mesh)


# -----------------------------
# Worker thread (UI stays alive)
# -----------------------------
class ConvertWorker(QtCore.QThread):
    log = QtCore.pyqtSignal(str)
    progress = QtCore.pyqtSignal(int)        # 0..100
    done = QtCore.pyqtSignal(bool, str)      # success, message

    def __init__(self, items: List[Tuple[Path, Path]], opt: ConvertOptions):
        super().__init__()
        self._items = items
        self._opt = opt
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            n = len(self._items)
            if n == 0:
                self.done.emit(False, "No files to convert.")
                return

            self.log.emit(f"Starting conversion of {n} file(s)...")
            self.progress.emit(0)

            for i, (inp, outp) in enumerate(self._items, start=1):
                if self._cancel:
                    self.log.emit("Cancelled.")
                    self.done.emit(False, "Cancelled by user.")
                    return

                self.log.emit(f"\n[{i}/{n}] Loading: {inp.name}")
                stats = convert_one(inp, outp, self._opt)
                self.log.emit(
                    f"Exported: {outp.name}\n"
                    f"  Verts: {stats.vertices:,} | Faces: {stats.faces:,}\n"
                    f"  Bounds min: {tuple(round(x, 2) for x in stats.bounds_min)}\n"
                    f"  Bounds max: {tuple(round(x, 2) for x in stats.bounds_max)}\n"
                    f"  Extents:   {tuple(round(x, 2) for x in stats.extents)}"
                )

                self.progress.emit(int((i / n) * 100))

            self.done.emit(True, f"Converted {n} file(s) successfully.")

        except Exception as e:
            tb = traceback.format_exc()
            self.log.emit("\n❌ Error:\n" + tb)
            self.done.emit(False, f"Failed: {e}")


# -----------------------------
# Drag/drop list widget
# -----------------------------
class DropListWidget(QtWidgets.QListWidget):
    """List widget that accepts STL file/folder drops and emits filesDropped(paths)."""
    filesDropped = QtCore.pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        if not event.mimeData().hasUrls():
            super().dropEvent(event)
            return

        paths: List[str] = []
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.is_dir():
                paths.extend([str(x) for x in p.glob("*.stl")])
                paths.extend([str(x) for x in p.glob("*.STL")])
            else:
                paths.append(str(p))

        self.filesDropped.emit(paths)
        event.acceptProposedAction()


# -----------------------------
# Main window
# -----------------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ash's STL → OBJ Converter")
        self.resize(1100, 720)

        self._worker: Optional[ConvertWorker] = None

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        root = QtWidgets.QHBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(14)

        # -------- Left panel (files + output + convert) --------
        left = QtWidgets.QVBoxLayout()
        left.setSpacing(12)

        files_group = QtWidgets.QGroupBox("Input STL files")
        files_layout = QtWidgets.QVBoxLayout(files_group)

        self.file_list = DropListWidget()
        self.file_list.filesDropped.connect(self._on_files_dropped)

        hint = QtWidgets.QLabel("Drop STL files or folders here, or click Add Files.")
        hint.setObjectName("muted")

        btn_row = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton("Add Files")
        self.btn_add.clicked.connect(self._add_files)

        self.btn_remove = QtWidgets.QPushButton("Remove Selected")
        self.btn_remove.setObjectName("dangerButton")
        self.btn_remove.clicked.connect(self._remove_selected)

        self.btn_clear = QtWidgets.QPushButton("Clear")
        self.btn_clear.setObjectName("dangerButton")
        self.btn_clear.clicked.connect(self._clear_list)

        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_remove)
        btn_row.addWidget(self.btn_clear)

        files_layout.addWidget(hint)
        files_layout.addWidget(self.file_list, 1)
        files_layout.addLayout(btn_row)

        left.addWidget(files_group, 2)

        # Output settings
        out_group = QtWidgets.QGroupBox("Output")
        out_layout = QtWidgets.QFormLayout(out_group)
        out_layout.setLabelAlignment(QtCore.Qt.AlignLeft)
        out_layout.setFormAlignment(QtCore.Qt.AlignTop)
        out_layout.setHorizontalSpacing(12)
        out_layout.setVerticalSpacing(10)

        self.out_dir = QtWidgets.QLineEdit()
        self.out_dir.setPlaceholderText("Select output folder (defaults to each file's folder)")
        self.btn_out_dir = QtWidgets.QPushButton("Browse…")
        self.btn_out_dir.clicked.connect(self._choose_out_dir)

        out_dir_row = QtWidgets.QHBoxLayout()
        out_dir_row.addWidget(self.out_dir, 1)
        out_dir_row.addWidget(self.btn_out_dir)

        out_layout.addRow("Output folder:", out_dir_row)

        self.naming_mode = QtWidgets.QComboBox()
        self.naming_mode.addItems([
            "Same name as STL (file.obj)",
            "Add suffix (file_converted.obj)",
            "Custom name",
        ])
        self.naming_mode.currentIndexChanged.connect(self._on_naming_mode_changed)

        self.custom_name = QtWidgets.QLineEdit()
        self.custom_name.setPlaceholderText("Enter custom base name (e.g. motor_export)")
        self.custom_name.setEnabled(False)

        out_layout.addRow("Naming:", self.naming_mode)
        out_layout.addRow("Custom name:", self.custom_name)

        left.addWidget(out_group, 0)

        # Convert controls
        convert_group = QtWidgets.QGroupBox("Convert")
        convert_layout = QtWidgets.QVBoxLayout(convert_group)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        convert_btn_row = QtWidgets.QHBoxLayout()
        self.btn_convert = QtWidgets.QPushButton("Convert Selected (or All)")
        self.btn_convert.setObjectName("primaryButton")
        self.btn_convert.clicked.connect(self._start_conversion)

        self.btn_cancel = QtWidgets.QPushButton("Cancel")
        self.btn_cancel.setObjectName("dangerButton")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_conversion)

        convert_btn_row.addWidget(self.btn_convert, 1)
        convert_btn_row.addWidget(self.btn_cancel)

        convert_layout.addWidget(self.progress)
        convert_layout.addLayout(convert_btn_row)

        left.addWidget(convert_group, 0)

        root.addLayout(left, 2)

        # -------- Right panel (options + stats + log) --------
        right = QtWidgets.QVBoxLayout()
        right.setSpacing(12)

        options_group = QtWidgets.QGroupBox("Options")
        options_layout = QtWidgets.QGridLayout(options_group)
        options_layout.setHorizontalSpacing(14)
        options_layout.setVerticalSpacing(10)

        self.chk_merge = QtWidgets.QCheckBox("Merge (weld) duplicate vertices")
        self.chk_merge.setChecked(True)

        self.chk_validate = QtWidgets.QCheckBox("Validate & cleanup mesh")
        self.chk_validate.setChecked(False)

        self.chk_center = QtWidgets.QCheckBox("Center mesh to origin")
        self.chk_center.setChecked(True)

        self.chk_swap_yz = QtWidgets.QCheckBox("Swap Y/Z axes")
        self.chk_swap_yz.setChecked(False)

        self.chk_flip_x = QtWidgets.QCheckBox("Flip X")
        self.chk_flip_y = QtWidgets.QCheckBox("Flip Y")
        self.chk_flip_z = QtWidgets.QCheckBox("Flip Z")

        self.scale = QtWidgets.QDoubleSpinBox()
        self.scale.setRange(1e-9, 1e9)
        self.scale.setDecimals(9)
        self.scale.setSingleStep(0.1)
        self.scale.setValue(1.0)
        self.scale.setToolTip("Scale factor applied to vertices (e.g., STL in mm -> meters = 0.001).")

        self.scale_presets = QtWidgets.QComboBox()
        self.scale_presets.addItems([
            "Custom",
            "mm → m (0.001)",
            "cm → m (0.01)",
            "m → mm (1000)",
            "inch → mm (25.4)",
        ])
        self.scale_presets.currentIndexChanged.connect(self._apply_scale_preset)

        options_layout.addWidget(self.chk_merge, 0, 0, 1, 2)
        options_layout.addWidget(self.chk_validate, 1, 0, 1, 2)
        options_layout.addWidget(self.chk_center, 2, 0, 1, 2)
        options_layout.addWidget(self.chk_swap_yz, 3, 0, 1, 2)

        options_layout.addWidget(QtWidgets.QLabel("Scale:"), 4, 0)
        options_layout.addWidget(self.scale, 4, 1)
        options_layout.addWidget(QtWidgets.QLabel("Scale preset:"), 5, 0)
        options_layout.addWidget(self.scale_presets, 5, 1)

        flip_box = QtWidgets.QHBoxLayout()
        flip_box.addWidget(self.chk_flip_x)
        flip_box.addWidget(self.chk_flip_y)
        flip_box.addWidget(self.chk_flip_z)
        flip_wrap = QtWidgets.QWidget()
        flip_wrap.setLayout(flip_box)
        options_layout.addWidget(QtWidgets.QLabel("Axis flips:"), 6, 0)
        options_layout.addWidget(flip_wrap, 6, 1)

        right.addWidget(options_group, 0)

        stats_group = QtWidgets.QGroupBox("Selected file stats")
        stats_layout = QtWidgets.QFormLayout(stats_group)
        stats_layout.setHorizontalSpacing(12)
        stats_layout.setVerticalSpacing(10)

        self.lbl_file = QtWidgets.QLabel("None")
        self.lbl_file.setObjectName("muted")
        self.lbl_verts = QtWidgets.QLabel("—")
        self.lbl_faces = QtWidgets.QLabel("—")
        self.lbl_bounds = QtWidgets.QLabel("—")
        self.lbl_extents = QtWidgets.QLabel("—")

        stats_layout.addRow("File:", self.lbl_file)
        stats_layout.addRow("Vertices:", self.lbl_verts)
        stats_layout.addRow("Faces:", self.lbl_faces)
        stats_layout.addRow("Bounds (min/max):", self.lbl_bounds)
        stats_layout.addRow("Extents:", self.lbl_extents)

        right.addWidget(stats_group, 0)

        log_group = QtWidgets.QGroupBox("Log")
        log_layout = QtWidgets.QVBoxLayout(log_group)

        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Conversion logs will appear here…")

        log_layout.addWidget(self.log, 1)
        right.addWidget(log_group, 1)

        root.addLayout(right, 3)

        # Selection updates stats preview
        self.file_list.itemSelectionChanged.connect(self._update_stats_preview)
        self.file_list.itemDoubleClicked.connect(lambda *_: self._update_stats_preview())

        # Status bar
        self.status = self.statusBar()
        self.status.showMessage("Ready. Drop STL files to begin.")

        # Make main window accept drops too
        self.setAcceptDrops(True)

    # ---------- Formatting helpers for stats (2dp) ----------
    def _fmt_vec2(self, v) -> str:
        """Format a 3D vector/tuple to 2dp: (x, y, z)."""
        return f"({v[0]:.2f}, {v[1]:.2f}, {v[2]:.2f})"

    def _fmt_bounds2(self, bmin, bmax) -> str:
        """Format bounds min/max nicely to 2dp."""
        return f"{self._fmt_vec2(bmin)} → {self._fmt_vec2(bmax)}"

    # ---------- Drag-drop support on main window ----------
    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls()]
            self._on_files_dropped(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    # ---------- Naming mode handler ----------
    def _on_naming_mode_changed(self, index: int) -> None:
        """Enable/disable custom name input depending on naming mode."""
        self.custom_name.setEnabled(index == 2)

    # ---------- File list management ----------
    def _add_files(self) -> None:
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Select STL file(s)",
            "",
            "STL files (*.stl *.STL);;All files (*.*)",
        )
        if paths:
            self._on_files_dropped(paths)

    def _choose_out_dir(self) -> None:
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "Select output folder")
        if d:
            self.out_dir.setText(d)

    def _remove_selected(self) -> None:
        for item in self.file_list.selectedItems():
            row = self.file_list.row(item)
            self.file_list.takeItem(row)
        self._update_stats_preview()

    def _clear_list(self) -> None:
        self.file_list.clear()
        self._update_stats_preview()

    def _on_files_dropped(self, paths: List[str]) -> None:
        existing = set()
        for i in range(self.file_list.count()):
            existing.add(self.file_list.item(i).data(QtCore.Qt.UserRole))

        added = 0
        for p_str in paths:
            p = Path(p_str)
            if p.is_dir():
                candidates = list(p.glob("*.stl")) + list(p.glob("*.STL"))
                for c in candidates:
                    added += self._try_add_file(c, existing)
            else:
                added += self._try_add_file(p, existing)

        if added:
            self.status.showMessage(f"Added {added} STL file(s).")
            self._update_stats_preview()
        else:
            self.status.showMessage("No new STL files added (or duplicates).")

    def _try_add_file(self, p: Path, existing: set) -> int:
        if not p.exists() or p.suffix.lower() != ".stl":
            return 0

        key = str(p.resolve())
        if key in existing:
            return 0

        item = QtWidgets.QListWidgetItem(p.name)
        item.setToolTip(str(p))
        item.setData(QtCore.Qt.UserRole, key)
        self.file_list.addItem(item)
        existing.add(key)
        return 1

    # ---------- Options ----------
    def _apply_scale_preset(self, idx: int) -> None:
        text = self.scale_presets.currentText()
        presets = {
            "mm → m (0.001)": 0.001,
            "cm → m (0.01)": 0.01,
            "m → mm (1000)": 1000.0,
            "inch → mm (25.4)": 25.4,
        }
        if text in presets:
            self.scale.setValue(presets[text])

    def _gather_options(self) -> ConvertOptions:
        return ConvertOptions(
            merge_vertices=self.chk_merge.isChecked(),
            validate_cleanup=self.chk_validate.isChecked(),
            scale_factor=float(self.scale.value()),
            center_to_origin=self.chk_center.isChecked(),
            swap_yz=self.chk_swap_yz.isChecked(),
            flip_x=self.chk_flip_x.isChecked(),
            flip_y=self.chk_flip_y.isChecked(),
            flip_z=self.chk_flip_z.isChecked(),
        )

    # ---------- Stats preview ----------
    def _update_stats_preview(self) -> None:
        selected = self.file_list.selectedItems()
        if not selected:
            if self.file_list.count() == 0:
                self.lbl_file.setText("None")
                self.lbl_verts.setText("—")
                self.lbl_faces.setText("—")
                self.lbl_bounds.setText("—")
                self.lbl_extents.setText("—")
                return
            item = self.file_list.item(0)
        else:
            item = selected[0]

        path_str = item.data(QtCore.Qt.UserRole)
        p = Path(path_str)
        self.lbl_file.setText(p.name)

        try:
            mesh = load_stl_as_mesh(p)
            opt = self._gather_options()

            # Make preview reflect key geometry options
            if opt.merge_vertices:
                mesh.merge_vertices()
            mesh = apply_transforms(mesh, opt)

            stats = safe_mesh_stats(mesh)

            self.lbl_verts.setText(f"{stats.vertices:,}")
            self.lbl_faces.setText(f"{stats.faces:,}")
            self.lbl_bounds.setText(self._fmt_bounds2(stats.bounds_min, stats.bounds_max))
            self.lbl_extents.setText(self._fmt_vec2(stats.extents))

        except Exception as e:
            self.lbl_verts.setText("—")
            self.lbl_faces.setText("—")
            self.lbl_bounds.setText("—")
            self.lbl_extents.setText("—")
            self._append_log(f"Stats preview failed for {p.name}: {e}")

    # ---------- Conversion ----------
    def _build_conversion_list(self) -> List[Tuple[Path, Path]]:
        """
        Build (input, output) pairs.
        If selection exists: convert selection, else convert all.

        Naming modes:
        - 0: same name as STL
        - 1: add suffix
        - 2: custom base name (auto-number if batch)
        """
        selected = self.file_list.selectedItems()
        use_items = selected if selected else [self.file_list.item(i) for i in range(self.file_list.count())]

        if not use_items:
            return []

        out_base = self.out_dir.text().strip()
        out_dir = Path(out_base) if out_base else None

        suffix_mode = self.naming_mode.currentIndex()
        custom_base = self.custom_name.text().strip()

        pairs: List[Tuple[Path, Path]] = []
        used_names = set()

        for idx, item in enumerate(use_items, start=1):
            inp = Path(item.data(QtCore.Qt.UserRole))
            out_folder = out_dir if out_dir is not None else inp.parent

            if suffix_mode == 0:
                out_name = inp.stem
            elif suffix_mode == 1:
                out_name = f"{inp.stem}_converted"
            else:
                if not custom_base:
                    raise ValueError("Custom name selected but no name provided.")
                out_name = custom_base

                # If batch, make them distinct and readable
                if len(use_items) > 1:
                    out_name = f"{out_name}_{idx:02d}"

            final_name = f"{out_name}.obj"

            # Collision safety: avoid overwriting existing files and duplicates in this run
            counter = 1
            candidate = final_name
            while candidate.lower() in used_names or (out_folder / candidate).exists():
                candidate = f"{out_name}_{counter}.obj"
                counter += 1

            used_names.add(candidate.lower())
            pairs.append((inp, out_folder / candidate))

        return pairs

    def _start_conversion(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self.status.showMessage("Already converting. Cancel first if you want.")
            return

        try:
            pairs = self._build_conversion_list()
        except ValueError as e:
            QtWidgets.QMessageBox.warning(self, "Naming error", str(e))
            return

        if not pairs:
            QtWidgets.QMessageBox.warning(self, "Nothing to convert", "Add STL files first.")
            return

        opt = self._gather_options()

        self.progress.setValue(0)
        self._append_log("============================================================")
        self._append_log("Conversion started.")
        self._append_log(f"Options: {opt}")

        self._set_ui_busy(True)

        self._worker = ConvertWorker(pairs, opt)
        self._worker.log.connect(self._append_log)
        self._worker.progress.connect(self.progress.setValue)
        self._worker.done.connect(self._on_worker_done)
        self._worker.start()

    def _cancel_conversion(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._append_log("Cancel requested…")
            self._worker.cancel()

    def _on_worker_done(self, success: bool, message: str) -> None:
        self._set_ui_busy(False)
        self.status.showMessage(message)
        self._append_log(f"\n{'✅' if success else '❌'} {message}")

    def _set_ui_busy(self, busy: bool) -> None:
        self.btn_convert.setEnabled(not busy)
        self.btn_cancel.setEnabled(busy)
        self.btn_add.setEnabled(not busy)
        self.btn_remove.setEnabled(not busy)
        self.btn_clear.setEnabled(not busy)
        self.btn_out_dir.setEnabled(not busy)

        for w in [
            self.chk_merge, self.chk_validate, self.chk_center, self.chk_swap_yz,
            self.chk_flip_x, self.chk_flip_y, self.chk_flip_z,
            self.scale, self.scale_presets,
            self.naming_mode, self.custom_name, self.out_dir
        ]:
            w.setEnabled(not busy)

    def _append_log(self, text: str) -> None:
        self.log.appendPlainText(text)
        sb = self.log.verticalScrollBar()
        sb.setValue(sb.maximum())


# -----------------------------
# Main entry
# -----------------------------
def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    apply_dark_orange_theme(app)

    win = MainWindow()
    win.show()

    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
