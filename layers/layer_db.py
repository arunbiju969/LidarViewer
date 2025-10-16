# LayerManager class to encapsulate layer state and management logic
import colorsys
import numpy as np
VALUE_COLORMAP_OPTION = "Value Colors"


class LayerManager:
    VALUE_COLORMAP_OPTION = VALUE_COLORMAP_OPTION

    def __init__(self):
        # uuid -> dict with file_path, points, las, visible, actor
        self.layers = {}
        self.current_layer_id = None
        self.current_file_path = None

    def plot_all_layers(self, viewer, sidebar):
        """Clear and redraw all visible layers in the plotter."""
        print("[PLOTTER] plot_all_layers: clearing plotter and redrawing all visible layers")
        if hasattr(viewer, 'plotter'):
            viewer.plotter.clear()

        total_original_points = 0
        total_rendered_points = 0
        last_lod_info = None

        for uuid, layer in self.layers.items():
            actor = layer.get('actor', None)
            if actor is not None and hasattr(viewer, 'plotter'):
                try:
                    viewer.plotter.remove_actor(actor)
                except Exception as e:
                    print(f"[WARN] Could not remove actor for layer {uuid}: {e}")

            if not layer.get('visible', False):
                self.layers[uuid]['actor'] = None
                continue

            settings = load_layer_settings(uuid)
            scalars, colormap = self._prepare_layer_coloring(layer, settings)

            result = viewer.display_point_cloud(
                layer['points'],
                scalars=scalars,
                cmap=colormap,
                return_actor=True,
                show_scalar_bar=False,
                return_lod_info=True
            )

            if isinstance(result, tuple):
                actor, lod_info = result
                last_lod_info = lod_info
                total_original_points += lod_info.get('original_count', 0)
                total_rendered_points += lod_info.get('final_count', 0)
            else:
                actor = result
                lod_info = None

            self.layers[uuid]['actor'] = actor

            point_size = settings.get('point_size') if settings else None
            if point_size is not None and hasattr(viewer, 'set_point_size'):
                viewer.set_point_size(point_size, actor=actor)

        if hasattr(sidebar, 'update_lod_status') and last_lod_info:
            combined_lod_info = {
                'level': last_lod_info.get('level', 'close'),
                'original_count': total_original_points,
                'final_count': total_rendered_points,
                'reduction_percent': ((total_original_points - total_rendered_points) / total_original_points * 100) if total_original_points > 0 else 0
            }
            sidebar.update_lod_status(combined_lod_info)

        if hasattr(viewer, 'plotter'):
            try:
                viewer.plotter.remove_scalar_bar()
            except Exception as e:
                print(f"[WARN] Could not remove scalar bar: {e}")
            viewer.plotter.update()
        actors_present = {uuid: l['actor'] is not None for uuid, l in self.layers.items()}
        print(f"[PLOTTER] Actors present after plot_all_layers: {actors_present}")

    def redraw_current_layer(self, viewer):
        current_layer_id = self.get_current_layer_id()
        if not (current_layer_id and current_layer_id in self.layers):
            print("[WARN] redraw_current_layer: No current layer to redraw.")
            return

        uuid = current_layer_id
        layer = self.layers[uuid]
        if hasattr(viewer, 'plotter'):
            actor = layer.get('actor', None)
            if actor is not None:
                try:
                    viewer.plotter.remove_actor(actor)
                except Exception as e:
                    print(f"[WARN] Could not remove actor for layer {uuid}: {e}")

        settings = load_layer_settings(uuid)
        scalars, colormap = self._prepare_layer_coloring(layer, settings)
        point_size = settings.get('point_size') if settings else None

        actor = viewer.display_point_cloud(
            layer['points'],
            scalars=scalars,
            cmap=colormap,
            return_actor=True,
            show_scalar_bar=False
        )

        self.layers[uuid]['actor'] = actor
        if point_size is not None and hasattr(viewer, 'set_point_size'):
            viewer.set_point_size(point_size, actor=actor)
        if hasattr(viewer, 'plotter'):
            viewer.plotter.update()

    def add_layer(self, uuid, file_path, points, las, visible=True, actor=None):
        self.layers[uuid] = {
            'file_path': file_path,
            'points': points,
            'las': las,
            'visible': visible,
            'actor': actor
        }
        self.current_layer_id = uuid
        self.current_file_path = file_path

    def remove_layer(self, uuid):
        if uuid in self.layers:
            del self.layers[uuid]
            if self.current_layer_id == uuid:
                self.current_layer_id = None
                self.current_file_path = None

    def set_layer_visible(self, uuid, visible):
        if uuid in self.layers:
            self.layers[uuid]['visible'] = visible

    def get_layer(self, uuid):
        return self.layers.get(uuid, None)

    def get_all_layers(self):
        return self.layers

    def set_current_layer(self, uuid):
        if uuid in self.layers:
            self.current_layer_id = uuid
            self.current_file_path = self.layers[uuid]['file_path']

    def get_current_layer(self):
        if self.current_layer_id:
            return self.layers.get(self.current_layer_id, None)
        return None

    def get_current_layer_id(self):
        return self.current_layer_id

    def get_current_file_path(self):
        return self.current_file_path

    def _prepare_layer_coloring(self, layer, settings):
        if not settings:
            return None, None

        colormap_choice = settings.get('colormap')
        dim_name = settings.get('dimension')
        las = layer.get('las')
        scalars = None
        cmap = colormap_choice

        if las is not None and dim_name and dim_name in las:
            if colormap_choice == self.VALUE_COLORMAP_OPTION:
                scalars = self._generate_value_color_scalars(las[dim_name])
                cmap = None
            else:
                from fileio.las_loader import get_normalized_scalars
                scalars = get_normalized_scalars(las, dim_name)

        if colormap_choice == "Custom":
            try:
                cmap = self._build_custom_colormap(settings)
            except Exception as e:
                print(f"[WARN] Failed to create custom colormap, falling back to 'viridis': {e}")
                cmap = 'viridis'
        elif colormap_choice == self.VALUE_COLORMAP_OPTION:
            cmap = None

        return scalars, cmap

    def _build_custom_colormap(self, settings):
        from matplotlib.colors import LinearSegmentedColormap

        safe_settings = settings or {}
        color_start = safe_settings.get('color_start', '#0000ff') or '#0000ff'
        color_mid = safe_settings.get('color_mid', '#00ff00') or '#00ff00'
        color_end = safe_settings.get('color_end', '#ff0000') or '#ff0000'
        return LinearSegmentedColormap.from_list('custom_cmap', [color_start, color_mid, color_end])

    def _generate_value_color_scalars(self, values):
        if values is None:
            return None

        np_values = np.asarray(values)
        if np_values.size == 0:
            return np.empty((0, 3), dtype=np.float32)

        unique_vals, inverse_indices = np.unique(np_values, return_inverse=True)
        if unique_vals.size == 0:
            return np.empty((0, 3), dtype=np.float32)

        if unique_vals.size > 512:
            print(f"[COLOR] Value Colors: {unique_vals.size} unique values detected; colors may repeat periodically.")
        palette = self._generate_value_color_palette(unique_vals.size)
        return palette[inverse_indices]

    def _generate_value_color_palette(self, count: int) -> np.ndarray:
        golden_ratio = 0.61803398875
        secondary_ratio = 0.38196601125
        tertiary_ratio = 0.70710678118
        colors = np.empty((count, 3), dtype=np.float32)

        for i in range(count):
            hue = (i * golden_ratio) % 1.0
            saturation = 0.65 + 0.30 * ((i * secondary_ratio) % 1.0)
            value = 0.70 + 0.25 * ((i * tertiary_ratio) % 1.0)
            if i % 2 == 1:
                value = max(0.45, value - 0.25)
            colors[i] = colorsys.hsv_to_rgb(hue, min(saturation, 0.95), min(value, 0.95))

        return colors
import sqlite3
import json
import os
import uuid

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'layers.db')

# Ensure the database and table exist
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS layers (
            uuid TEXT PRIMARY KEY,
            file_path TEXT,
            settings_json TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Save sidebar settings for a uuid (settings is a dict)
def save_layer_settings(uuid_val, file_path, settings):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    settings_json = json.dumps(settings)
    c.execute('''
        INSERT INTO layers (uuid, file_path, settings_json)
        VALUES (?, ?, ?)
        ON CONFLICT(uuid) DO UPDATE SET file_path=excluded.file_path, settings_json=excluded.settings_json
    ''', (uuid_val, file_path, settings_json))
    conn.commit()
    conn.close()

# Load sidebar settings for a uuid (returns dict or None)
def load_layer_settings(uuid_val):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT settings_json FROM layers WHERE uuid=?', (uuid_val,))
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None

# List all layers (uuid, file_path, settings)
def list_layers():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT uuid, file_path, settings_json FROM layers')
    rows = c.fetchall()
    conn.close()
    return [(uuid_val, fp, json.loads(js)) for uuid_val, fp, js in rows]

# Remove a layer by uuid
def remove_layer(uuid_val):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM layers WHERE uuid=?', (uuid_val,))
    conn.commit()
    conn.close()

# Generate a new unique layer id
def generate_layer_id():
    return str(uuid.uuid4())

# Call on startup to ensure DB exists
init_db()

# Call on startup to ensure DB exists
init_db()
