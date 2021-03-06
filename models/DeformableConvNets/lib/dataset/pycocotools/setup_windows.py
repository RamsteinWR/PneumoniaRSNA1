from distutils.core import setup
from distutils.extension import Extension

import distutils.msvc9compiler
import numpy as np
from Cython.Build import cythonize

distutils.msvc9compiler.VERSION = 14.0

# To compile and install locally run "python setup.py build_ext --inplace"
# To install library to Python site-packages run "python setup.py build_ext install"

ext_modules = [
    Extension(
        '_mask',
        sources=['maskApi.c', '_mask.pyx'],
        include_dirs=[np.get_include()],
        extra_compile_args=[],
    )
]

setup(name='pycocotools',
      ext_modules=cythonize(ext_modules)
      )
