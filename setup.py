#!/usr/bin/env python

import os
from setuptools import setup

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

version_fname = os.path.join(THIS_DIR, 'flowws_analysis', 'version.py')
with open(version_fname) as version_file:
    exec(version_file.read())

readme_fname = os.path.join(THIS_DIR, 'README.md')
with open(readme_fname) as readme_file:
    long_description = readme_file.read()

module_names = [
    'Center',
    'Colormap',
    'Diffraction',
    'Garnett',
    'GTAR',
    'Plato',
    'Pyriodic',
    'Save',
    'SaveGarnett',
    'Selection',
    'ViewNotebook',
    'ViewQt',
]

flowws_modules = []
for name in module_names:
    flowws_modules.append('{0} = flowws_analysis.{0}:{0}'.format(name))
    flowws_modules.append(
        'flowws_analysis.{0} = flowws_analysis.{0}:{0}'.format(name))

setup(name='flowws-analysis',
      author='Matthew Spellings',
      author_email='matthew.p.spellings@gmail.com',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3',
      ],
      description='Stage-based scientific workflows for system analysis',
      entry_points={
          'flowws_modules': flowws_modules,
      },
      extras_require={
          'garnett': ['garnett', 'gsd', 'gtar', 'pycifrw'],
          'gtar': ['gtar'],
          'notebook': ['ipython', 'ipywidgets'],
          'plato': ['plato-draw >= 1.8'],
          'pyriodic': ['pyriodic-structures'],
          'qt': ['qt.py', 'pyside2'],
      },
      install_requires=['flowws >= 0.2.2'],
      license='MIT',
      long_description=long_description,
      long_description_content_type='text/markdown',
      packages=[
          'flowws_analysis',
      ],
      python_requires='>=3',
      version=__version__
      )
