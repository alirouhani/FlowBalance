#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <vector>
#include <queue>
#include <algorithm>
#include <limits>

namespace py = pybind11;

constexpr double INF = std::numeric_limits<double>::infinity();
constexpr double EPSILON = 1e-6;

struct TimeSpaceArc {
    int id;
    int from_idx;
    int to_idx;
    double cost;

    // Explicit constructor required by py::init
    TimeSpaceArc(int _id, int _from, int _to, double _cost)
        : id(_id), from_idx(_from), to_idx(_to), cost(_cost) {}
};

struct CommodityCore {
    int id;
    int origin;
    int destination;

    // Explicit constructor required by py::init
    CommodityCore(int _id, int _origin, int _dest)
        : id(_id), origin(_origin), destination(_dest) {}
};

struct GeneratedColumn {
    int commodity_id;
    std::vector<int> arc_ids;
    double reduced_cost;
};

class PricingEngine {
private:
    int num_nodes;
    std::vector<TimeSpaceArc> arcs;
    std::vector<std::vector<int>> adjacency_list;
    std::vector<int> topological_order;

    void compute_topological_sort() {
        std::vector<int> in_degree(num_nodes, 0);
        for (const auto& arc : arcs) {
            in_degree[arc.to_idx]++;
        }

        std::queue<int> q;
        for (int i = 0; i < num_nodes; ++i) {
            if (in_degree[i] == 0) q.push(i);
        }

        topological_order.clear();
        while (!q.empty()) {
            int u = q.front();
            q.pop();
            topological_order.push_back(u);

            for (int arc_idx : adjacency_list[u]) {
                int v = arcs[arc_idx].to_idx;
                if (--in_degree[v] == 0) {
                    q.push(v);
                }
            }
        }
    }

public:
    PricingEngine(int n_nodes, const std::vector<TimeSpaceArc>& ts_arcs) 
        : num_nodes(n_nodes), arcs(ts_arcs) {
        adjacency_list.resize(num_nodes);
        for (size_t i = 0; i < arcs.size(); ++i) {
            adjacency_list[arcs[i].from_idx].push_back(i);
        }
        compute_topological_sort();
    }

    std::vector<GeneratedColumn> find_columns(
        const std::vector<CommodityCore>& commodities,
        const std::vector<double>& dual_pi,
        const std::vector<double>& dual_mu) 
    {
        std::vector<GeneratedColumn> new_columns;

        for (const auto& comm : commodities) {
            std::vector<double> dist(num_nodes, INF);
            std::vector<int> parent_arc(num_nodes, -1);
            std::vector<int> parent_node(num_nodes, -1);

            if (comm.origin >= num_nodes || comm.destination >= num_nodes) {
                continue;
            }

            dist[comm.origin] = 0.0;

            for (int u : topological_order) {
                if (dist[u] == INF) continue;

                for (int arc_idx : adjacency_list[u]) {
                    const auto& arc = arcs[arc_idx];
                    int v = arc.to_idx;

                    double reduced_cost = arc.cost - dual_pi[arc.id];
                    
                    if (dist[u] + reduced_cost < dist[v]) {
                        dist[v] = dist[u] + reduced_cost;
                        parent_arc[v] = arc.id;
                        parent_node[v] = u;
                    }
                }
            }

            if (comm.id >= static_cast<int>(dual_mu.size())) {
                continue;
            }

            double final_reduced_cost = dist[comm.destination] - dual_mu[comm.id];

            if (final_reduced_cost < -EPSILON && dist[comm.destination] != INF) {
                GeneratedColumn col;
                col.commodity_id = comm.id;
                col.reduced_cost = final_reduced_cost;

                int curr = comm.destination;
                bool valid_path = true;
                while (curr != comm.origin) {
                    int a_id = parent_arc[curr];
                    if (a_id == -1) {
                        valid_path = false;
                        break;
                    }
                    col.arc_ids.push_back(a_id);
                    curr = parent_node[curr];
                }
                
                if (valid_path) {
                    std::reverse(col.arc_ids.begin(), col.arc_ids.end());
                    new_columns.push_back(col);
                }
            }
        }
        return new_columns;
    }
};

PYBIND11_MODULE(_flowbalance_pricing, m) {
    py::class_<TimeSpaceArc>(m, "TimeSpaceArc")
        .def(py::init<int, int, int, double>(), 
             py::arg("id"), py::arg("from_idx"), py::arg("to_idx"), py::arg("cost"))
        .def_readwrite("id", &TimeSpaceArc::id)
        .def_readwrite("from_idx", &TimeSpaceArc::from_idx)
        .def_readwrite("to_idx", &TimeSpaceArc::to_idx)
        .def_readwrite("cost", &TimeSpaceArc::cost);

    py::class_<CommodityCore>(m, "CommodityCore")
        .def(py::init<int, int, int>(), 
             py::arg("id"), py::arg("origin"), py::arg("destination"))
        .def_readwrite("id", &CommodityCore::id)
        .def_readwrite("origin", &CommodityCore::origin)
        .def_readwrite("destination", &CommodityCore::destination);

    py::class_<GeneratedColumn>(m, "GeneratedColumn")
        .def_readonly("commodity_id", &GeneratedColumn::commodity_id)
        .def_readonly("arc_ids", &GeneratedColumn::arc_ids)
        .def_readonly("reduced_cost", &GeneratedColumn::reduced_cost);

    py::class_<PricingEngine>(m, "PricingEngine")
        .def(py::init<int, const std::vector<TimeSpaceArc>&>(), 
             py::arg("num_nodes"), py::arg("ts_arcs"))
        .def("find_columns", &PricingEngine::find_columns, py::call_guard<py::gil_scoped_release>());
}