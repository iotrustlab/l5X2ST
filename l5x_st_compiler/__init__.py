"""L5X-ST Compiler Package.

A modern Python 3 implementation for converting between L5X files and Structured Text.
"""

__version__ = "2.0.0"
__author__ = "Original Author + Modernization"

try:
    from .l5x2st import L5X2STConverter
    from .st2l5x import ST2L5XConverter
    from .ir_converter import IRConverter
    from .export_ir import export_ir_to_json
    from .query import InteractiveIRQuery
    __all__ = [
        "L5X2STConverter", 
        "ST2L5XConverter", 
        "IRConverter", 
        "export_ir_to_json", 
        "InteractiveIRQuery"
    ]
except ImportError as e:
    # Handle import errors gracefully for development
    __all__ = []
    print(f"Warning: Could not import converters: {e}") 