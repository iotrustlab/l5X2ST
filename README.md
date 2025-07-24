# L5X-ST Compiler

A modern Python 3 implementation for converting between L5X files (Allen Bradley/Rockwell Automation) and Structured Text (ST) format. This project builds upon the original L5X parser and provides a clean, modular, and testable codebase with **complete round-trip conversion**, **IR validation**, and **L5K overlay support**.

## Features

### L5X to Structured Text (L5X2ST)
- Convert single L5X files to ST format
- Convert entire directories of L5X files to consolidated ST
- Handle multiple PLCs with proper variable renaming
- Support for Function Block Diagrams (FBD)
- Support for Ladder Logic (RLL)
- Automatic type conversion and reserved word handling
- Message instruction handling
- Timer function block support
- **IR validation mode** with guardrails
- **L5K overlay support** for enhanced project context

### Structured Text to L5X (ST2L5X)
- Convert ST files back to L5X format
- Generate proper L5X XML structure
- Support for variable declarations
- Support for function declarations
- Support for struct declarations
- **IR validation mode** with fidelity scoring

### L5K Overlay System
- **Enhanced Project Context**: Extract missing project-level information from L5K files
- **Global and Controller Tags**: Complete tag definitions with data types and initial values
- **Task and Program Mapping**: Execution order and program-to-task bindings
- **Module Configurations**: Hardware module settings and I/O configurations
- **User-Defined Data Types**: Complete UDT definitions with nested structures
- **Initial Tag Values**: Default values for all tags in the project

### Advanced Features
- **Complete Round-Trip Conversion**: L5X ↔ ST ↔ L5X with validation
- **Intermediate Representation (IR)**: Internal data model for validation
- **Fidelity Scoring**: Quantitative measurement of conversion quality
- **Guardrail Validation**: Optional `--use-ir` flag for enhanced validation
- **Industrial-Grade Reliability**: Handles complex Rockwell automation projects
- **Metadata Comparison**: Tools to analyze differences between overlay and non-overlay conversions
- **IR Export and Analysis**: Export IR components to JSON for downstream processing
- **Interactive Querying API**: Programmatic access to IR components with search and analysis
- **Control Flow Analysis**: Extract and analyze control flow structures from routines
- **Cross-Program Interaction Detection**: Identify dependencies between programs and controllers

## Installation

### Prerequisites
- Python 3.8 or higher
- pip

### Install from source
```bash
git clone <repository-url>
cd l5x2ST
pip install -e .
```

### Install dependencies
```bash
pip install -r requirements.txt
```

## Usage

### Command Line Interface

#### Convert L5X to ST
```bash
# Convert single file
python -m l5x_st_compiler.cli l5x2st -i project.L5X -o output.st

# With IR validation (recommended)
python -m l5x_st_compiler.cli l5x2st -i project.L5X -o output.st --use-ir

# With verbose output
python -m l5x_st_compiler.cli l5x2st -i project.L5X -o output.st -v
```

#### Convert L5X to ST with L5K Overlay
```bash
# Convert with L5K overlay for enhanced context
python -m l5x_st_compiler.cli l5x2st -i project.L5X -o output.st --l5k-overlay project.L5K

# With IR validation and L5K overlay
python -m l5x_st_compiler.cli l5x2st -i project.L5X -o output.st --l5k-overlay project.L5K --use-ir

# With verbose output and overlay
python -m l5x_st_compiler.cli l5x2st -i project.L5X -o output.st --l5k-overlay project.L5K -v
```

#### Validate L5K Overlay Differences
```bash
# Compare IR with and without L5K overlay
python examples/validate_l5k_overlay_diff.py -i project.L5X -l project.L5K

# Generate JSON report
python examples/validate_l5k_overlay_diff.py -i project.L5X -l project.L5K --json

# Compare multiple projects
python examples/validate_l5k_overlay_diff.py -i project1.L5X -l project1.L5K -i project2.L5X -l project2.L5K
```

#### Convert ST to L5X
```bash
# Convert single file
python -m l5x_st_compiler.cli st2l5x -i program.st -o output.L5X

# With IR validation (recommended)
python -m l5x_st_compiler.cli st2l5x -i program.st -o output.L5X --use-ir

# With verbose output
python -m l5x_st_compiler.cli st2l5x -i program.st -o output.L5X -v
```

#### Export IR Components
```bash
# Export basic IR components (tags and control flow)
python -m l5x_st_compiler.cli export-ir -i P1.L5X -o out/ir_dump.json --include tags,control_flow

# Export all IR components
python -m l5x_st_compiler.cli export-ir -i P1.L5X -o out/ir_full.json --include tags,control_flow,data_types,function_blocks,interactions,routines,programs

# Export with verbose output
python -m l5x_st_compiler.cli export-ir -i P1.L5X -o out/ir_dump.json --include tags,control_flow -v

# Export specific components only
python -m l5x_st_compiler.cli export-ir -i P1.L5X -o out/tags_only.json --include tags
```

### Python API

#### L5X to ST Conversion
```python
from l5x_st_compiler import L5X2STConverter

converter = L5X2STConverter()

# Convert single file
converter.convert_file("project.L5X", "output.st")

# Parse and get STFile object
st_file = converter.parse_l5x_file("project.L5X")
print(str(st_file))
```

#### L5K Overlay Integration
```python
from l5x_st_compiler import L5X2STConverter
from l5x_st_compiler.l5k_overlay import L5KOverlay

# Load L5K overlay for enhanced context
overlay = L5KOverlay()
overlay.load_l5k_file("project.L5K")

# Convert with overlay
converter = L5X2STConverter()
st_file = converter.parse_l5x_file("project.L5X", overlay=overlay)
print(str(st_file))
```

#### IR Validation and Round-Trip
```python
from l5x_st_compiler.ir_converter import IRConverter
from l5x_st_compiler import L5X2STConverter, ST2L5XConverter

# Load and validate L5X
ir_converter = IRConverter()
l5x2st = L5X2STConverter()
st2l5x = ST2L5XConverter()

# Round-trip with validation
original_project = l5x2st.parse_l5x_file("project.L5X")
original_ir = ir_converter.l5x_to_ir(original_project)

# Convert to ST and back
st_content = str(original_project)
final_l5x = st2l5x.convert_st_to_l5x(st_content, "")
final_project = l5x2st.parse_l5x_file("final.L5X")
final_ir = ir_converter.l5x_to_ir(final_project)

# Calculate fidelity score
fidelity_score = ir_converter.calculate_fidelity_score(original_ir, final_ir)
print(f"Round-trip fidelity: {fidelity_score:.2%}")
```

#### IR Comparison and Analysis
```python
from l5x_st_compiler.ir_converter import IRConverter
from l5x_st_compiler.l5k_overlay import L5KOverlay

# Compare IR with and without overlay
ir_converter = IRConverter()
overlay = L5KOverlay()
overlay.load_l5k_file("project.L5K")

# Generate IR without overlay
ir_without = ir_converter.l5x_to_ir("project.L5X")

# Generate IR with overlay
ir_with = ir_converter.l5x_to_ir("project.L5X", overlay=overlay)

# Analyze differences
diff_report = ir_converter.compare_ir(ir_without, ir_with)
print(f"Tags added: {diff_report['tags_added']}")
print(f"Tasks added: {diff_report['tasks_added']}")
print(f"Modules added: {diff_report['modules_added']}")
```

#### IR Export and Querying
```python
from l5x_st_compiler import IRConverter, export_ir_to_json, InteractiveIRQuery
import l5x

# Load L5X project and convert to IR
project = l5x.Project("project.L5X")
ir_converter = IRConverter()
ir_project = ir_converter.l5x_to_ir(project)

# Export IR components to JSON
export_data = export_ir_to_json(
    ir_project=ir_project,
    output_path="ir_export.json",
    include=["tags", "control_flow", "data_types", "interactions"],
    pretty_print=True
)

# Interactive querying
query = InteractiveIRQuery(ir_project)

# Find tags by prefix
lit_tags = query.find_tags_by_prefix("LIT")
print(f"Found {len(lit_tags)} tags with prefix 'LIT'")

# Get control flow for a routine
control_flow = query.get_control_flow("MainRoutine", "MainProgram")
if control_flow:
    print(f"Control flow type: {control_flow['type']}")

# Get tag dependencies
dependencies = query.get_dependencies("P101")
print(f"Tag P101 referenced by: {dependencies['referenced_by']}")

# Get project summary
summary = query.get_project_summary()
print(f"Project has {summary['tags']['total_tags']} total tags")
```

## Project Structure

```
l5x2ST/
├── l5x_st_compiler/          # Main package
│   ├── __init__.py           # Package initialization
│   ├── constants.py          # Constants and configurations
│   ├── models.py             # Data models and IR classes
│   ├── utils.py              # Utility functions
│   ├── instructions.py       # Instruction processors
│   ├── ladder_logic.py       # Ladder logic translator
│   ├── fbd_translator.py     # FBD to ST translator
│   ├── ir_converter.py       # IR conversion system
│   ├── l5k_overlay.py        # L5K file parser and overlay system
│   ├── l5x2st.py            # L5X to ST converter
│   ├── st2l5x.py            # ST to L5X converter
│   └── cli.py               # Command-line interface
├── examples/                 # Example scripts
│   ├── basic_usage.py       # Basic usage examples
│   ├── complex_st_example.py # Complex ST example
│   ├── ir_roundtrip_test.py # IR round-trip testing
│   ├── l5x_compare.py       # L5X comparison tool
│   ├── l5x_roundtrip_test.py # L5X round-trip testing
│   ├── l5k_overlay_example.py # L5K overlay usage examples
│   ├── validate_l5k_overlay_diff.py # Overlay difference analysis
│   └── validation_test.py   # Comprehensive validation
├── tests/                    # Test suite
│   ├── __init__.py
│   ├── test_l5x2st.py       # Tests for L5X2ST converter
│   └── test_l5k_overlay.py  # Tests for L5K overlay system
├── requirements.txt          # Python dependencies
├── setup.py                  # Package setup
├── pytest.ini               # Pytest configuration
└── README.md                # This file
```

## Development

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=l5x_st_compiler

# Run specific test file
pytest tests/test_l5x2st.py

# Run with verbose output
pytest -v

# Run L5K overlay tests
pytest tests/test_l5k_overlay.py

# Run validation test suite
python examples/validation_test.py

# Test L5K overlay functionality
python examples/l5k_overlay_example.py

# Validate overlay differences
python examples/validate_l5k_overlay_diff.py -i sampledata/swatfiles/P1.L5X -l sampledata/swatfiles/P1.L5K
```

### Code Quality
```bash
# Format code with black
black l5x_st_compiler/

# Lint with flake8
flake8 l5x_st_compiler/

# Type checking with mypy
mypy l5x_st_compiler/
```

### Building and Installing
```bash
# Install in development mode
pip install -e .

# Build distribution
python setup.py sdist bdist_wheel

# Install from distribution
pip install dist/l5x-st-compiler-2.0.0.tar.gz
```

## Key Improvements Over Original

### Code Quality
- **Python 3 Support**: Full Python 3.8+ compatibility
- **Type Hints**: Comprehensive type annotations
- **Modular Design**: Clean separation of concerns
- **Error Handling**: Proper exception handling and user feedback
- **Documentation**: Comprehensive docstrings and comments

### Architecture
- **Object-Oriented**: Proper class-based design
- **State Management**: Centralized compiler state
- **Configuration**: Externalized constants and settings
- **Extensibility**: Easy to add new features and processors
- **IR System**: Intermediate representation for validation

### Testing
- **Unit Tests**: Comprehensive test coverage
- **Mock Support**: Proper mocking for external dependencies
- **Test Configuration**: Pytest configuration and markers
- **CI/CD Ready**: Structured for continuous integration
- **Validation Suite**: Comprehensive round-trip testing

### Features
- **Bidirectional Conversion**: Both L5X→ST and ST→L5X
- **CLI Interface**: User-friendly command-line tools with IR validation
- **API Support**: Programmatic access to converters
- **IR Validation**: Guardrail system for conversion quality
- **Fidelity Scoring**: Quantitative measurement of round-trip accuracy
- **L5K Overlay**: Enhanced project context from L5K files
- **Metadata Analysis**: Tools for comparing conversion differences

## L5K Overlay System

The L5K overlay system enhances L5X to ST conversion by extracting additional project context from L5K files. This provides:

### Enhanced Context
- **Global Tags**: Controller-scoped tags with complete definitions
- **Task Definitions**: Execution order and timing information
- **Program Mappings**: Which programs run in which tasks
- **Module Configurations**: Hardware I/O settings and configurations
- **User-Defined Data Types**: Complete UDT definitions with nested structures
- **Initial Values**: Default values for all tags in the project

### Benefits
- **More Complete ST Output**: Includes system-level context and configurations
- **Better Round-Trip Fidelity**: Preserves more project metadata
- **Enhanced Debugging**: Complete tag definitions with initial values
- **System Integration**: Task and program execution information
- **Hardware Context**: Module configurations and I/O settings

### Usage Examples
```bash
# Basic overlay usage
python -m l5x_st_compiler.cli l5x2st -i project.L5X -o output.st --l5k-overlay project.L5K

# Compare with and without overlay
python examples/validate_l5k_overlay_diff.py -i project.L5X -l project.L5K
```

## Supported Instructions

### Currently Supported Categories
- **Bit Instructions**: XIC, XIO, OTE, OTL, OTU, ONS, OSR, OSF, OSRI, OSFI
- **Timer Instructions**: TON, TONR, TOF, TOFR, RTO, RTOR
- **Counter Instructions**: CTU, CTD, CTUD, RES
- **Compare Instructions**: EQ, NE, GT, GE, LT, LE, CMP, LIMIT, MEQ
- **Math Instructions**: ADD, SUB, MUL, DIV, MOD, SQR, SQRT, ABS, NEG
- **Data Conversion**: TOD, FRD, DTD, DTR, ROUND, TRUNC
- **Control Instructions**: JMP, JSR, RET, FOR, NEXT, WHILE, REPEAT, IF, CASE
- **Message Instructions**: MSG
- **System Instructions**: GSV, SSV

## Dependencies

### Core Dependencies
- `l5x>=0.1.0`: L5X file parser
- `ordered-set>=4.0.0`: Ordered set implementation
- `lxml>=4.6.0`: XML processing
- `click>=8.0.0`: CLI framework

### Development Dependencies
- `pytest>=6.0.0`: Testing framework
- `pytest-cov>=2.10.0`: Coverage reporting
- `black>=21.0.0`: Code formatting
- `flake8>=3.8.0`: Code linting
- `mypy>=0.800`: Type checking

## Limitations and TODOs

### Current Limitations
- Some complex FBD structures may not convert perfectly
- Message instruction handling is simplified
- Limited support for advanced motion instructions

### Planned Improvements
- [ ] Enhanced FBD processing with more complex structures
- [ ] Better message instruction handling
- [ ] Support for more advanced motion instructions
- [ ] Performance optimizations for large projects
- [ ] Better error reporting and diagnostics
- [ ] Integration with OpenPLC for ST validation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Original L5X parser and converter code
- Rockwell Automation for L5X format and instruction documentation
- IEC 61131-3 standard for Structured Text specification

## Support

For issues, questions, or contributions, please use the project's issue tracker or contact the maintainers.