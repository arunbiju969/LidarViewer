import numpy as np

from layers.layer_db import LayerManager, VALUE_COLORMAP_OPTION


def test_prepare_layer_coloring_value_colors():
    manager = LayerManager()
    layer = {
        'points': np.zeros((3, 3), dtype=float),
        'las': {'Class': np.array([1, 2, 1], dtype=np.int32)},
        'visible': True,
        'actor': None
    }
    settings = {
        'colormap': VALUE_COLORMAP_OPTION,
        'dimension': 'Class'
    }

    scalars, cmap = manager._prepare_layer_coloring(layer, settings)

    assert cmap is None
    assert scalars is not None
    assert scalars.shape == (3, 3)
    # Ensure identical values receive identical colors while differing values differ
    assert np.allclose(scalars[0], scalars[2])
    assert not np.allclose(scalars[0], scalars[1])
