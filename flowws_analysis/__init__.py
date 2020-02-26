from flowws import try_to_import

from .version import __version__

Colormap = try_to_import('.Colormap', 'Colormap', __name__)
Garnett = try_to_import('.Garnett', 'Garnett', __name__)
GTAR = try_to_import('.GTAR', 'GTAR', __name__)
Plato = try_to_import('.Plato', 'Plato', __name__)
Pyriodic = try_to_import('.Pyriodic', 'Pyriodic', __name__)
Save = try_to_import('.Save', 'Save', __name__)
ViewNotebook = try_to_import('.ViewNotebook', 'ViewNotebook', __name__)
ViewQt = try_to_import('.ViewQt', 'ViewQt', __name__)
