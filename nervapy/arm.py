# This file is part of PeachPy package and is licensed under the Simplified BSD license.
#    See license.rst for the full text of the license.

import inspect
import string
import time

import nervapy.c
import nervapy.codegen
from nervapy import Constant, ConstantBucket, RegisterAllocationError

active_function = None
active_stream = None


