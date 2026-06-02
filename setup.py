from setuptools import setup, Extension
import pybind11

# Define the C++ extension module
ext_modules = [
    Extension(
        "_flowbalance_cpp",  # The name Python will use to import the compiled binary
        ["src/flowbalance/expander/cpp_core.cpp"], # Path to your C++ file
        include_dirs=[pybind11.get_include()],
        language="c++",
        # -O3 applies maximum execution speed optimizations during compilation
        extra_compile_args=["-std=c++11", "-O3"],
    ),
]

setup(
    ext_modules=ext_modules,
)