
## Introduction

`flowws-analysis` is an in-development set of modules to create reusable
analysis pipelines for scientific simulations.

`flowws-analysis` is being developed in conjunction with
[flowws](https://github.com/klarh/flowws).

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

## Documentation

Browse more detailed documentation
[online](https://flowws-analysis.readthedocs.io) or build the sphinx
documentation from source:

```
git clone https://github.com/klarh/flowws-analysis
cd flowws-analysis/doc
pip install -r requirements.txt
make html
```
