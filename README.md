[![ReadTheDocs](https://img.shields.io/readthedocs/flowws-analysis.svg?style=flat)](https://flowws-analysis.readthedocs.io/en/latest/)

# Introduction

`flowws-analysis` is an in-development set of
[flowws](https://flowws.readthedocs.io) modules to create reusable
analysis pipelines for scientific simulations. Although it is
currently mostly useful for analyzing structures found in molecular
simulation (together with
[flowws-freud](https://github.com/klarh/flowws-freud)), the framework
can be used as a base for analysis and visualization in jupyter
notebooks or a standalone GUI for other application domains.

## Installation

Install `flowws-analysis` from PyPI (note that most modules require
dependencies; use the second `pip install` command below to install
those) :

```
# this installs flowws-analysis without any prerequisites
pip install flowws-analysis

# optional prerequisites can be installed via extras, for example:
pip install flowws-analysis[garnett,gtar,notebook,plato,pyriodic,qt]
```

Alternatively, install from source:

```
pip install git+https://github.com/klarh/flowws-analysis.git#egg=flowws-analysis
```

## Examples

Consult the
[flowws-examples](https://github.com/klarh/flowws-examples) project
for examples using `flowws-analysis` modules.

## API Documentation

Browse more detailed documentation
[online](https://flowws-analysis.readthedocs.io) or build the sphinx
documentation from source:

```
git clone https://github.com/klarh/flowws-analysis
cd flowws-analysis/doc
pip install -r requirements.txt
make html
```
