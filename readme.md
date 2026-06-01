# FlowBalance: A Multi-Commodity Time-Space Network Optimization Engine

FlowBalance is a high-performance Python package designed to model, expand, and optimize complex network flows across discrete temporal horizons. Featuring a streamlined, unified data architecture, FlowBalance is engineered for industrial use cases across **logistics** (reusable asset repositioning, container routing) and **finance** (multi-ledger corporate cash and liquidity management).

By modeling shipments and asset characteristics within a singular, highly intuitive class structure, FlowBalance simplifies data ingestion while enforcing strict relational integrity at the schema boundary using Pydantic.

---

## Features

* **Unified 1-Class Data Contract:** Eliminates redundant data architecture. Shipments, time-windows, physical asset types, and volumetric metrics are bundled into a single entity.
* **Automated Graph Expansion:** Programmatically transforms static nodes, edges, and commodity tracks into a multi-period time-space network layer.
* **Strict Operational Isolation:** Differentiates between an order's delivery requirements (`volume`) and its physical vehicle footprint (`consumption_factor`).
* **Robust Data Ingestion:** Production-ready repository interfaces for flat-file data processing (`PandasLoader`) and live relational database streaming (`SQLLoader`).

---

## Directory Layout

```text
flowbalance_project/
├── pyproject.toml             # Package metadata, build-systems, and dependencies
├── README.md                  # Project documentation
├── src/
│   └── flowbalance/
│       ├── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   └── entities.py    # Core Pydantic data schemas and relational validation
│       ├── expander/
│       │   ├── __init__.py
│       │   └── time_space.py  # Time-expanded graph algorithms and RHS compilers
│       └── loaders/
│           ├── __init__.py
│           ├── base.py        # Abstract Base Class interfaces (ABC)
│           ├── pandas_io.py   # Tabular Dataframe repository pipeline
│           └── sql_io.py      # SQLAlchemy relational database pipeline
└── tests/
    └── __init__.py