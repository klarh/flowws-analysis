#!/usr/bin/env python

import os
from setuptools import setup

with open('flowws_analysis/version.py') as version_file:
    exec(version_file.read())

module_names = [
    'Colormap',
    'GTAR',
    'Plato',
    'Pyriodic',
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
      extras_require={},
      install_requires=['flowws'],
      license='MIT',
      packages=[
          'flowws_analysis',
      ],
      python_requires='>=3',
      version=__version__
      )
