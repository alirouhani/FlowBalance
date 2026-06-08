# 🌊 flowbalance

**High-Performance Time-Space Network Optimization and Routing Engine**

`flowbalance` is a fast, flexible, and mathematically rigorous Python package designed to solve dynamic Multi-Commodity Network Flow and Fixed-Charge Network Design (MCFND) problems.

Powered by **dual C++ cores** (for topological expansion and high-speed dynamic pricing) and the **Google OR-Tools** engine, `flowbalance` utilizes exact Dantzig-Wolfe decomposition to solve massive routing problems. It allows data scientists and operations researchers to model complex asset routing over time, manage shared bottleneck capacities, and extract clean, pandas-ready operational analytics.

---

## 🧠 The Core Concept: Everything is a Network

At its heart, `flowbalance` doesn't just route trucks between cities. It uses a **Time-Space Coordinate Expansion**, meaning it treats the world as abstract mathematical states and transitions. If you have "criteria" or "assets" that need to move from State A to State B over **T** time, you can model it:

* **Logistics & Freight:** Nodes are cities, edges are highways, and transit time is driving duration.
* **Supply Chain & Inventory:** Nodes are warehouses, edges are internal transfers, and holding costs are storage fees.
* **Production Planning:** Nodes are assembly machines, edges are processing actions, and transit time is machine cycle time.
* **Finance & Treasury:** Nodes are corporate bank accounts, edges are wire transfers, and transit time is the banking clearing period.

Whether you are running a multi-period dynamic simulation (**T=30**) or evaluating a classical single-period static network (**T=1**, instantaneous transits), `flowbalance` safely compiles the topology and calculates the most cost-effective mass-balance flows.

---

## 🚀 Installation

`flowbalance` utilizes compiled C++ backend extensions (`pybind11`) for maximum speed. Ensure your system has a working C++17 compiler installed (e.g., GCC for Linux, Clang/Xcode for macOS, or MSVC for Windows).

### Production Setup (Direct from GitHub)

To install the package directly into your environment for use in your own projects:

```bash
pip install git+https://github.com/alirouhani/flowbalance.git

```

### Development Setup (For Contributors)

If you want to modify the source code, tweak the C++ memory allocation, or run the test suite:

```bash
git clone https://github.com/alirouhani/flowbalance.git
cd flowbalance

# Install in editable mode to instantly track local Python/C++ changes
pip install -e ".[dev]"

```

---

## ⚡ Quick Start: The 4-Step Pipeline

`flowbalance` is designed for modern data stacks, ingesting standard Pandas DataFrames and outputting clean tabular reports.

```python
import pandas as pd
import flowbalance as fb

# 1. DEFINE DATA
df_nodes = pd.DataFrame([
    {"id": "Factory", "capacity_limit": 1000.0, "holding_costs": "{}"},
    {"id": "Retail", "capacity_limit": 500.0, "holding_costs": "{}"}
])

df_edges = pd.DataFrame([
    {"from_node": "Factory", "to_node": "Retail", "transit_time": 1, 
     "shared_capacity_limit": 100.0, "costs_per_unit": "{'STANDARD': 10.0}"}
])

df_commodities = pd.DataFrame([
    {"id": "Order_01", "asset_type": "STANDARD", "origin": "Factory", 
     "destination": "Retail", "volume": 50.0, "available_time": 0, "due_date": 2, "consumption_factor": 1.0}
])

# 2. LOAD NETWORK
network = fb.PandasLoader(df_nodes, df_edges, df_commodities).load_network()

# 3. SOLVE VIA COLUMN GENERATION
solver = fb.ColumnGenerationSolver()
results = solver.solve(network, horizon=3, max_iterations=200)

# 4. EXPORT ANALYTICS
exporter = fb.SolutionExporter(results)
print(exporter.to_flow_dataframe())

```

---

## 📂 Real-World Examples

To see how adaptable the engine is across different industries, check out the `examples/` directory in this repository. You will find ready-to-run scripts demonstrating:

1. **`01_logistics_routing.py`**: Multi-modal freight routing prioritizing cheap rail vs. fast air-freight under strict deadlines.
2. **`02_inventory_management.py`**: Balancing high factory storage costs against multi-echelon distribution center transfers.
3. **`03_production_planning.py`**: Managing Work-In-Progress (WIP) queues across sequential milling and assembly machines.
4. **`04_finance_liquidity.py`**: Minimizing opportunity costs while routing cash transfers across international subsidiaries to meet payroll.

---

## ⚙️ Architecture Highlights

* **Dantzig-Wolfe Column Generation:** Bypasses the memory limits of massive time-space network arrays. The Python Master Problem manages shared capacities, while a C++ pricing engine dynamically evaluates exact reduced costs to generate optimal paths on the fly.
* **Cycle-Robust Pricing Search:** Safely navigates zero-cost temporal holding cycles using a heavily optimized Dijkstra priority queue, scaling perfectly with asset volumes and consumption factors.
* **Pricing Filter Optimization:** Implements advanced dual-variable heuristics to filter the pricing pool, drastically reducing the number of necessary shortest-path searches per iteration without sacrificing mathematical optimality.
* **Pydantic Data Validation:** Strict input schemas prevent timeline violations (e.g., negative transit times or illogical due dates) and enforce strict relational integrity before any matrices are built.

---

## 🤝 Contributing

Pull requests are welcome! For major algorithmic changes, please open an issue first to discuss what you would like to change. Ensure you run the complete test suite (`pytest tests/ -v`) to verify the structural integrity and objective scaling before submitting your code.