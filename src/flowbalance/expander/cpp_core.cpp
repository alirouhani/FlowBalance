#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <vector>
#include <string>
#include <tuple>
#include <map>

namespace py = pybind11;

// Pure Coordinate Arc: (from_location, from_time, to_location, to_time)
using TimeSpaceArc = std::tuple<std::string, int, std::string, int>;

// Source/Sink Identifier: (location, time, commodity_id)
using RhsKey = std::tuple<std::string, int, std::string>;

// 1. Unified Node-Arc Incidence Generator
std::vector<TimeSpaceArc> build_time_expanded_arcs_cpp(int horizon, const py::list& nodes, const py::list& edges) {
    std::vector<TimeSpaceArc> expanded_arcs;
    
    // Safety Guard: Return empty topology if the time horizon is invalid
    if (horizon <= 0) {
        return expanded_arcs;
    }

    // Pre-allocate contiguous memory to bypass dynamic resizing overhead
    expanded_arcs.reserve((nodes.size() * horizon) + (edges.size() * horizon));

    // Temporal Holding Arcs: ((i, t), (i, t+1))
    // Note: If horizon == 1, this loop is correctly bypassed entirely.
    for (int t = 0; t < horizon - 1; ++t) {
        for (auto item : nodes) {
            std::string node_id = py::str(item.attr("id"));
            expanded_arcs.emplace_back(node_id, t, node_id, t + 1);
        }
    }

    // Physical Transit Arcs: ((i, t), (j, t_bar))
    for (int t = 0; t < horizon; ++t) {
        for (auto item : edges) {
            int transit_time = item.attr("transit_time").cast<int>();
            int t_bar = t + transit_time;
            
            // Boundary Check: Ensure the arrival coordinate exists within the planned horizon.
            // This safely allows instantaneous transits (t_bar == t) when horizon = 1.
            if (t_bar < horizon) {
                std::string from_node = py::str(item.attr("from_node"));
                std::string to_node = py::str(item.attr("to_node"));
                
                // Prevent logical collision: Skip physical instantaneous self-loops.
                // A coordinate cannot jump to itself at the exact same time step.
                if (transit_time == 0 && from_node == to_node) {
                    continue;
                }
                
                expanded_arcs.emplace_back(from_node, t, to_node, t_bar);
            }
        }
    }

    return expanded_arcs;
}

// 2. Boundary Condition Compiler
std::map<RhsKey, double> compute_commodity_rhs_cpp(int horizon, const py::list& commodities) {
    std::map<RhsKey, double> b;

    if (horizon <= 0) {
        return b;
    }

    for (auto item : commodities) {
        std::string comm_id = py::str(item.attr("id"));
        std::string origin = py::str(item.attr("origin"));
        std::string destination = py::str(item.attr("destination"));
        
        // Extract the absolute physical demand volume (v^k)
        double volume = item.attr("volume").cast<double>();
        int t_s = item.attr("available_time").cast<int>(); 
        int t_e = item.attr("due_date").cast<int>();       

        // Inject volume at the start coordinate (s^k)
        if (t_s < horizon) {
            b[std::make_tuple(origin, t_s, comm_id)] += volume;
        }
        
        // Extract volume at the destination coordinate (e^k)
        if (t_e < horizon) {
            b[std::make_tuple(destination, t_e, comm_id)] -= volume;
        }
    }

    return b;
}

// 3. Python Extension Binding
PYBIND11_MODULE(_flowbalance_cpp, m) {
    m.doc() = "High-performance C++ topological expansion backend for flowbalance";
    
    m.def("build_arcs", &build_time_expanded_arcs_cpp, 
          "Constructs the unified ((i, t), (j, t_bar)) time-space arc vectors.");
          
    m.def("compute_rhs", &compute_commodity_rhs_cpp, 
          "Identifies s^k and e^k coordinates and compiles static volume constraints.");
}