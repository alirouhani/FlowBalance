#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <vector>
#include <queue>
#include <algorithm>
#include <limits>

namespace py = pybind11;

constexpr double INF = std::numeric_limits<double>::infinity();
constexpr double EPSILON = 1e-6;

// Step 1: Define physical network transition structures
struct TimeSpaceArc {
    int id;
    int from_idx;
    int to_idx;
    double cost;

    TimeSpaceArc(int _id, int _from, int _to, double _cost)
        : id(_id), from_idx(_from), to_idx(_to), cost(_cost) {}
};

// Step 2: Define tracking bounds for multi-commodity assets
struct CommodityCore {
    int id;
    int origin;
    int destination;
    double volume;
    double consumption_factor;

    CommodityCore(int _id, int _origin, int _dest, double _vol, double _cons)
        : id(_id), origin(_origin), destination(_dest), volume(_vol), consumption_factor(_cons) {}
};

// Step 3: Define column layout matrices for RMP injection
struct GeneratedColumn {
    int commodity_id;
    std::vector<int> arc_ids;
    double reduced_cost;
};

// Step 4: Configure the sorting structures for min-heap exploration
struct State {
    int node;
    double dist;
    bool operator>(const State& other) const {
        return dist > other.dist;
    }
};

class PricingEngine {
private:
    int num_nodes;
    std::vector<TimeSpaceArc> arcs;
    std::vector<std::vector<int>> adjacency_list;

public:
    // Step 5: Construct forward-star representation graph maps
    PricingEngine(int n_nodes, const std::vector<TimeSpaceArc>& ts_arcs) 
        : num_nodes(n_nodes), arcs(ts_arcs) {
        adjacency_list.resize(num_nodes);
        for (size_t i = 0; i < arcs.size(); ++i) {
            adjacency_list[arcs[i].from_idx].push_back(i);
        }
    }

    std::vector<GeneratedColumn> find_columns(
        const std::vector<CommodityCore>& active_commodities,
        const std::vector<double>& dual_w, 
        const std::vector<double>& dual_alpha) 
    {
        std::vector<GeneratedColumn> new_columns;

        for (const auto& comm : active_commodities) {
            if (comm.origin >= num_nodes || comm.destination >= num_nodes) continue;

            std::vector<double> dist(num_nodes, INF);
            std::vector<int> parent_arc(num_nodes, -1);
            std::priority_queue<State, std::vector<State>, std::greater<State>> pq;

            dist[comm.origin] = 0.0;
            pq.push({comm.origin, 0.0});

            // Step 6: Execute cycle-robust shortest-path relaxation
            while (!pq.empty()) {
                State current = pq.top();
                pq.pop();

                // Step 7: Apply destination target early-exit triggers
                if (current.node == comm.destination) break; 
                if (current.dist > dist[current.node]) continue;

                for (int arc_idx : adjacency_list[current.node]) {
                    const auto& arc = arcs[arc_idx];
                    
                    // Step 8: Calculate scaled reduced-cost arc parameters
                    double reduced_cost = (arc.cost * comm.volume) - (dual_w[arc.id] * comm.volume * comm.consumption_factor);
                    
                    if (dist[current.node] + reduced_cost < dist[arc.to_idx] - EPSILON) {
                        dist[arc.to_idx] = dist[current.node] + reduced_cost;
                        parent_arc[arc.to_idx] = arc.id;
                        pq.push({arc.to_idx, dist[arc.to_idx]});
                    }
                }
            }

            if (comm.id >= static_cast<int>(dual_alpha.size())) continue;
            
            // Step 9: Process convexity dual bounds to isolate active columns
            double final_reduced_cost = dist[comm.destination] - dual_alpha[comm.id];

            if (final_reduced_cost < -EPSILON && dist[comm.destination] != INF) {
                GeneratedColumn col;
                col.commodity_id = comm.id;
                col.reduced_cost = final_reduced_cost;

                // Step 10: Backtrack paths and reverse chronological order
                int curr = comm.destination;
                bool valid = true;
                while (curr != comm.origin) {
                    int a_id = parent_arc[curr];
                    if (a_id == -1) { valid = false; break; }
                    col.arc_ids.push_back(a_id);
                    curr = arcs[a_id].from_idx;
                }
                
                if (valid) {
                    std::reverse(col.arc_ids.begin(), col.arc_ids.end());
                    new_columns.push_back(col);
                }
            }
        }
        return new_columns;
    }
};

// Step 11: Implement pybind11 module macros and drop the GIL
PYBIND11_MODULE(_flowbalance_pricing, m) {
    py::class_<TimeSpaceArc>(m, "TimeSpaceArc")
        .def(py::init<int, int, int, double>())
        .def_readwrite("id", &TimeSpaceArc::id)
        .def_readwrite("from_idx", &TimeSpaceArc::from_idx)
        .def_readwrite("to_idx", &TimeSpaceArc::to_idx)
        .def_readwrite("cost", &TimeSpaceArc::cost);

    py::class_<CommodityCore>(m, "CommodityCore")
        .def(py::init<int, int, int, double, double>())
        .def_readwrite("id", &CommodityCore::id)
        .def_readwrite("origin", &CommodityCore::origin)
        .def_readwrite("destination", &CommodityCore::destination)
        .def_readwrite("volume", &CommodityCore::volume)
        .def_readwrite("consumption_factor", &CommodityCore::consumption_factor);

    py::class_<GeneratedColumn>(m, "GeneratedColumn")
        .def_readonly("commodity_id", &GeneratedColumn::commodity_id)
        .def_readonly("arc_ids", &GeneratedColumn::arc_ids)
        .def_readonly("reduced_cost", &GeneratedColumn::reduced_cost);

    py::class_<PricingEngine>(m, "PricingEngine")
        .def(py::init<int, const std::vector<TimeSpaceArc>&>())
        .def("find_columns", &PricingEngine::find_columns, py::call_guard<py::gil_scoped_release>());
}