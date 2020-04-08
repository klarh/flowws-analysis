
.. toctree::
   :maxdepth: 2
   :caption: Contents:

.. mdinclude:: ../../README.md

Analysis Workflow Design
========================

.. py:currentmodule:: flowws_analysis

In general, consider the flow of data when considering the order of
the workflow steps you would like to perform: place modules that
generate or load data first (such as :py:class:`Garnett` and
:py:class:`Pyriodic`), followed by modules that modify or compute
quantities (such as :py:class:`Center`). Finally, use visualization or
rendering modules, such as :py:class:`ViewNotebook` or
:py:class:`Save`. Modules are presented below in approximately this
order.

Modules
=======

Data Loading and Generation
---------------------------

.. autoclass:: Garnett

.. autoclass:: GTAR

.. autoclass:: Pyriodic

Calculation and Analysis
------------------------

.. autoclass:: Center

.. autoclass:: Colormap

.. autoclass:: Selection

Visualization and Rendering
---------------------------

.. autoclass:: Plato

.. autoclass:: ViewNotebook

.. autoclass:: ViewQt

.. autoclass:: Save

.. autoclass:: SaveGarnett

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
