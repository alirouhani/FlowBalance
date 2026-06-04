from setuptools import setup, Extension, find_packages
import sys
import pybind11

# Define high-speed compiler optimization flags
extra_compile_args = ["-std=c++17", "-O3"]

# Apply explicit macOS target mapping to prevent linking warnings if compiling on Apple Silicon/Clang
if sys.platform == "darwin":
    extra_compile_args.append("-mmacosx-version-min=10.15")

# Define the dual C++ extension modules
ext_modules = [
    # 1. The Core Topological Time-Space Expander Module
    Extension(
        "_flowbalance_cpp",
        ["src/flowbalance/expander/cpp_core.cpp"],
        include_dirs=[pybind11.get_include()],
        language="c++",
        extra_compile_args=extra_compile_args,
    ),
    # 2. The Column Generation Pricing DAG Solver Module
    Extension(
        "_flowbalance_pricing",
        ["src/flowbalance/cg_solver/pricing_engine.cpp"],
        include_dirs=[pybind11.get_include()],
        language="c++",
        extra_compile_args=extra_compile_args,
    ),
]

setup(
    name="flowbalance",
    version="1.1.0",
    # Dynamically discovers all sub-packages in src/ (loader, analytics, core, cg_solver, etc.)
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    ext_modules=ext_modules,
    install_requires=[
        "ortools",
        "pandas",
        "pydantic"
    ]
)