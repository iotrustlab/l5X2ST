"""L5X to Structured Text converter."""

import os
from typing import Dict, List, Optional, Any, Union, Tuple, Set
from dataclasses import dataclass, field
from ordered_set import OrderedSet
import logging
import xml.etree.ElementTree as ET

import l5x

from .models import (
    IRProject, IRController, IRProgram, IRRoutine, IRTag, IRDataType, 
    IRDataTypeMember, IRFunctionBlock, IRFunctionBlockParameter,
    TagScope, RoutineType, STFile, CompilerState, Instruction, DataType, Tag, FunctionBlock
)
from .constants import (
    MAIN_PROGRAM, RESERVED_WORDS, UNIMPLEMENTED_TYPES, BIT_ACCESS_HELPER,
    AUXILIARY_FUNCTIONS, AUXILIARY_STRUCTS, CONFIGURATION,
    DUPLICATE_FBDS, L5X_TAG_TYPES, L5X_DATA_TYPES, L5X_INSTRUCTIONS, 
    ST_DATA_TYPES, ST_INSTRUCTIONS
)
from .utils import (
    replace_reserved_words, replace_bit_accesses, replace_func_calls,
    replace_booleans, fix_type_mismatches, fix_multiline_comments,
    replace_renamed_vars, format_ST_line, initialize_messages,
    clean_identifier, get_data_type_info, extract_tag_info, 
    extract_function_block_info, extract_instruction_info, 
    sanitize_identifier, get_base_data_type, _extract_data_types,
    _extract_function_blocks, extract_program_logic_from_xml
)
from .instructions import process_routine, process_routines
from .st2l5x import ST2L5XConverter, convert_st_to_l5x, convert_st_to_l5x_string

logger = logging.getLogger(__name__)

class L5X2STConverter:
    """Converts L5X files to Structured Text."""
    
    def __init__(self):
        """Initialize the converter."""
        self.state = CompilerState()
    
    def parse_l5x_file(self, l5x_file: str) -> STFile:
        """Parse a single L5X file and convert to ST."""
        print(f"Parsing: {l5x_file}")
        
        # Load the L5X project
        prj = l5x.Project(l5x_file)
        
        # Generate structure declarations
        struct_decs = self._generate_struct_decs(prj)
        
        # Generate function declarations
        func_decs = self._generate_func_decs(prj)
        
        # Generate variable declarations
        var_decs = self._generate_var_decs(prj)
        
        # Generate program block
        prog_block = self._generate_prog_block(prj)
        
        return STFile(struct_decs, func_decs, var_decs, prog_block, l5x_file)
    
    def parse_l5x_directory(self, l5x_dir: str) -> STFile:
        """Parse all L5X files in a directory and convert to consolidated ST."""
        st_file = STFile("", "", "", "", "Consolidated Program")
        l5x_files = []
        
        # Find all L5X files
        for root, dirs, files in os.walk(l5x_dir):
            for file in files:
                if file.upper().endswith('.L5X'):
                    l5x_files.append(os.path.join(root, file))
        
        # Sort files (assumes P1, P2, etc. naming)
        l5x_files.sort(key=str.lower)
        
        # Process each file
        for l5x_file in l5x_files:
            st = self.parse_l5x_file(l5x_file)
            st_file.add_st_content(st)
            self.state.reset_for_new_controller()
        
        return st_file
    
    def _generate_struct_decs(self, prj) -> str:
        """Generate structure declarations from L5X project."""
        struct_decs = "(*Structure Declarations*)\n"
        
        # Process auxiliary structs
        for struct_name, struct_def in AUXILIARY_STRUCTS.items():
            if struct_name not in self.state.struct_names:
                struct_decs += f"{struct_def}\n\n"
                self.state.add_struct(struct_name, "auxiliary")
        
        # Process module structs
        struct_decs += self._process_module_structs(prj)
        
        # Process data types from the project
        if hasattr(prj, 'controller') and hasattr(prj.controller, 'datatypes'):
            for dtype_name in prj.controller.datatypes:
                dtype = prj.controller.datatypes[dtype_name]
                if dtype_name not in self.state.struct_names:
                    struct_def = self._convert_datatype_to_struct(dtype_name, dtype)
                    if struct_def:
                        struct_decs += f"{struct_def}\n\n"
                        self.state.add_struct(dtype_name, "project")
        
        return struct_decs
    
    def _process_module_structs(self, prj) -> str:
        """Process module structures from the project."""
        # This is a simplified version - module processing is complex
        return "(*Module structures would be processed here*)\n"
    
    def _convert_datatype_to_struct(self, dtype_name: str, dtype) -> Optional[str]:
        """Convert a data type to a struct definition."""
        if not hasattr(dtype, '__getitem__'):
            return None
        
        struct_def = f"TYPE {dtype_name}:\n\tSTRUCT\n"
        
        for member_name in dtype:
            member = dtype[member_name]
            member_type = getattr(member, 'DataType', 'BOOL')
            if member_type in UNIMPLEMENTED_TYPES:
                member_type = UNIMPLEMENTED_TYPES[member_type]
            struct_def += f"\t\t{member_name}: {member_type};\n"
        
        struct_def += "\tEND_STRUCT;\nEND_TYPE"
        return struct_def
    
    def _generate_func_decs(self, prj) -> str:
        """Generate function declarations from L5X project."""
        func_decs = "(*Function Declarations*)\n"
        
        # Process auxiliary functions
        for func_name, func_def in AUXILIARY_FUNCTIONS.items():
            if func_name not in self.state.fbd_names:
                func_decs += f"{func_def}\n\n"
                self.state.add_function(func_name, "auxiliary")
        
        # Process function blocks from the project
        if hasattr(prj, 'controller') and hasattr(prj.controller, 'functionblocks'):
            for fb_name in prj.controller.functionblocks:
                fb = prj.controller.functionblocks[fb_name]
                if fb_name not in self.state.fbd_names:
                    fb_def = self._convert_functionblock_to_function(fb_name, fb)
                    if fb_def:
                        func_decs += f"{fb_def}\n\n"
                        self.state.add_function(fb_name, "project")
        
        return func_decs
    
    def _convert_functionblock_to_function(self, fb_name: str, fb) -> Optional[str]:
        """Convert a function block to a function definition."""
        # This is a simplified version - FB conversion is complex
        return f"FUNCTION {fb_name}: BOOL\n\t(*Function block {fb_name} converted to function*)\n\t{fb_name} := TRUE;\nEND_FUNCTION"
    
    def _generate_var_decs(self, prj) -> str:
        """Generate variable declarations from L5X project."""
        var_decs = "PROGRAM prog0\nVAR\n"
        
        # Process controller tags
        if hasattr(prj, 'controller') and hasattr(prj.controller, 'tags'):
            var_decs += "\t(*Controller Tags*)\n"
            for tag_name in prj.controller.tags:
                tag = prj.controller.tags[tag_name]
                var_name = tag_name
                dtype = getattr(tag, 'DataType', 'BOOL')
                
                # Handle reserved words
                if var_name in RESERVED_WORDS:
                    var_name = RESERVED_WORDS[var_name]
                
                # Handle unimplemented types
                if dtype in UNIMPLEMENTED_TYPES:
                    dtype = UNIMPLEMENTED_TYPES[dtype]
                
                # Handle FBD timers
                if dtype == "FBD_TIMER":
                    var_name = f"{var_name}{self.state.current_controller}_TMR"
                    dtype = "TON"
                    self.state.fbd_timers.append(var_name)
                
                # Handle duplicate FBDs
                if dtype in DUPLICATE_FBDS:
                    dtype = f"{dtype}{self.state.current_controller}"
                
                # Add variable if not already present
                if var_name.lower() not in self.state.var_names:
                    var_decs += f"\t\t{var_name}: {dtype};\n"
                    self.state.add_variable(var_name, dtype, tag_name)
        
        # Process main program tags
        if hasattr(prj, 'programs') and MAIN_PROGRAM in prj.programs:
            main_prog = prj.programs[MAIN_PROGRAM]
            if hasattr(main_prog, 'tags') and main_prog.tags:
                var_decs += "\t(*Main Program Tags*)\n"
                for tag_name in main_prog.tags:
                    tag = main_prog.tags[tag_name]
                    var_name = tag_name
                    dtype = getattr(tag, 'DataType', 'BOOL')
                    
                    # Handle reserved words
                    if var_name in RESERVED_WORDS:
                        var_name = RESERVED_WORDS[var_name]
                    
                    # Handle unimplemented types
                    if dtype in UNIMPLEMENTED_TYPES:
                        dtype = UNIMPLEMENTED_TYPES[dtype]
                    
                    # Handle FBD timers
                    if dtype == "FBD_TIMER":
                        var_name = f"{var_name}{self.state.current_controller}_TMR"
                        dtype = "TON"
                        self.state.fbd_timers.append(var_name)
                    
                    # Handle duplicate FBDs
                    if dtype in DUPLICATE_FBDS:
                        dtype = f"{dtype}{self.state.current_controller}"
                    
                    # Add variable if not already present
                    if var_name.lower() not in self.state.var_names:
                        var_decs += f"\t\t{var_name}: {dtype};\n"
                        self.state.add_variable(var_name, dtype, tag_name)
        
        # Add bit access helper
        if BIT_ACCESS_HELPER.lower() not in self.state.var_names:
            var_decs += f"\t(*Bit Access Helper*)\n\t\t{BIT_ACCESS_HELPER}: DWORD;\n"
            self.state.add_variable(BIT_ACCESS_HELPER, "DWORD", BIT_ACCESS_HELPER)
        
        var_decs += "END_VAR\n"
        return var_decs
    
    def _generate_prog_block(self, prj) -> str:
        """Generate the main program block from L5X project."""
        prog_block = ""
        
        # Initialize messages
        if hasattr(prj, 'controller') and hasattr(prj.controller, 'tags'):
            prog_block += initialize_messages(prj.controller.tags)
        
        # Process main program routine
        if hasattr(prj, 'programs') and MAIN_PROGRAM in prj.programs:
            main_prog = prj.programs[MAIN_PROGRAM]
            if hasattr(main_prog, 'routines') and hasattr(main_prog, 'main_routine_name'):
                main_routine = main_prog.routines[main_prog.main_routine_name]
                prog_block += process_routine(main_routine, prj, "")
        
        # Add program termination
        prog_block += "\nEND_PROGRAM\n"
        prog_block += CONFIGURATION
        
        return prog_block
    
    def convert_file(self, input_file: str, output_file: str, l5k_overlay_path: Optional[str] = None) -> None:
        """
        Convert a single L5X file to ST.
        
        Args:
            input_file: Path to input L5X file
            output_file: Path to output ST file
            l5k_overlay_path: Optional path to L5K file for additional context
        """
        st_file = self.parse_l5x_file(input_file)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(str(st_file))
    
    def convert_directory(self, input_dir: str, output_file: str) -> None:
        """Convert all L5X files in a directory to consolidated ST."""
        st_file = self.parse_l5x_directory(input_dir)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(str(st_file))

    def convert_l5x_to_st(self, l5x_file_path: str, l5k_overlay_path: Optional[str] = None) -> str:
        """
        Convert an L5X file to Structured Text.
        
        Args:
            l5x_file_path: Path to the L5X file
            l5k_overlay_path: Optional path to L5K file for additional context
            
        Returns:
            Generated ST code as string
        """
        try:
            # Parse L5X file
            project = l5x.Project(l5x_file_path)
            
            # Use IR converter for proper L5K overlay support
            from .ir_converter import IRConverter
            ir_converter = IRConverter()
            
            # Convert to IR with optional L5K overlay
            ir_project = ir_converter.l5x_to_ir(project, l5k_overlay_path)
            
            # Debug: Print IR project structure
            print(f"DEBUG: IR Project controller: {ir_project.controller.name}")
            print(f"DEBUG: IR Project tags: {len(ir_project.controller.tags)}")
            print(f"DEBUG: IR Project programs: {len(ir_project.programs)}")
            print(f"DEBUG: IR Project tasks: {len(ir_project.tasks)}")
            print(f"DEBUG: IR Project modules: {len(ir_project.modules)}")
            
            # Check if L5K overlay was applied
            if l5k_overlay_path and ir_project.metadata.get('l5k_overlay_applied'):
                print(f"DEBUG: L5K overlay applied successfully")
                print(f"DEBUG: L5K tags added: {ir_project.metadata.get('l5k_tags_added', 0)}")
                print(f"DEBUG: L5K tasks added: {ir_project.metadata.get('l5k_tasks_added', 0)}")
                print(f"DEBUG: L5K programs added: {ir_project.metadata.get('l5k_programs_added', 0)}")
                print(f"DEBUG: L5K modules added: {ir_project.metadata.get('l5k_modules_added', 0)}")
            
            # Generate ST code from IR
            st_code = self._generate_st_from_ir(ir_project)
            
            return st_code
            
        except Exception as e:
            logger.error(f"Error converting L5X to ST: {e}")
            raise
    
    def _extract_tags(self, project: Any) -> List[Tag]:
        """Extract tags from L5X project."""
        tags = []
        try:
            controller = project.controller
            print(f"DEBUG: _extract_tags: controller={controller}")
            if hasattr(controller, 'tags'):
                tag_dict = controller.tags
                print(f"DEBUG: _extract_tags: tag_dict type={type(tag_dict)} names={getattr(tag_dict, 'names', None)}")
                for tag_name in getattr(tag_dict, 'names', []):
                    print(f"DEBUG: _extract_tags: accessing tag_name={tag_name}")
                    tag_data = tag_dict[tag_name]
                    print(f"DEBUG: _extract_tags: got tag_data for {tag_name}, type={type(tag_data)}")
                    tag_info = extract_tag_info(tag_name, tag_data)
                    if tag_info:
                        tags.append(tag_info)
        except Exception as e:
            logger.error(f"Error extracting tags: {e}")
            print(f"DEBUG: Exception in _extract_tags: {e}")
        return tags
    
    def _extract_data_types(self, project: Any) -> List[DataType]:
        """Extract data types from L5X project."""
        return _extract_data_types(project)
    
    def _extract_function_blocks(self, project: Any) -> List[FunctionBlock]:
        """Extract function blocks from L5X project."""
        return _extract_function_blocks(project)
    
    def _extract_programs(self, project: Any) -> List[Dict[str, Any]]:
        """Extract programs and routines from L5X project."""
        programs = []
        try:
            programs_dict = project.programs
            print(f"DEBUG: _extract_programs: programs_dict type={type(programs_dict)} names={getattr(programs_dict, 'names', None)}")
            for prog_name in getattr(programs_dict, 'names', []):
                print(f"DEBUG: _extract_programs: accessing prog_name={prog_name}")
                prog_data = programs_dict[prog_name]
                print(f"DEBUG: _extract_programs: got prog_data for {prog_name}, type={type(prog_data)}")
                programs.append({
                    'name': prog_name,
                    'data': prog_data
                })
        except Exception as e:
            logger.error(f"Error extracting programs: {e}")
            print(f"DEBUG: Exception in _extract_programs: {e}")
        return programs
    
    def _generate_st_code(self, controller: Any, tags: List[Tag], 
                         data_types: List[DataType], function_blocks: List[FunctionBlock], 
                         programs: List[Dict[str, Any]], program_logic: str) -> str:
        """Generate Structured Text code from extracted data."""
        st_lines = []
        
        # Add header
        st_lines.append("// Generated Structured Text Code")
        st_lines.append("// Converted from L5X file")
        st_lines.append("")
        
        # Add data type declarations
        if data_types:
            st_lines.append("// Data Type Declarations")
            for dt in data_types:
                st_lines.append(f"TYPE {dt.name} : {dt.base_type};")
                if dt.description:
                    st_lines.append(f"// {dt.description}")
            st_lines.append("END_TYPE")
            st_lines.append("")
        
        # Add variable declarations
        if tags:
            st_lines.append("// Variable Declarations")
            st_lines.append("VAR")
            for tag in tags:
                st_lines.append(f"    {tag.name} : {tag.data_type};")
                if tag.description:
                    st_lines.append(f"    // {tag.description}")
            st_lines.append("END_VAR")
            st_lines.append("")
        
        # Add function blocks
        if function_blocks:
            st_lines.append("// Function Blocks")
            for fb in function_blocks:
                st_lines.append(f"FUNCTION_BLOCK {fb.name}")
                if fb.inputs:
                    st_lines.append("VAR_INPUT")
                    for input_var in fb.inputs:
                        st_lines.append(f"    {input_var['name']} : {input_var['type']};")
                    st_lines.append("END_VAR")
                
                if fb.outputs:
                    st_lines.append("VAR_OUTPUT")
                    for output_var in fb.outputs:
                        st_lines.append(f"    {output_var['name']} : {output_var['type']};")
                    st_lines.append("END_VAR")
                
                if fb.variables:
                    st_lines.append("VAR")
                    for var in fb.variables:
                        st_lines.append(f"    {var['name']} : {var['type']};")
                    st_lines.append("END_VAR")
                
                if fb.code:
                    st_lines.append("// Implementation")
                    for line in fb.code:
                        st_lines.append(f"    {line}")
                
                st_lines.append("END_FUNCTION_BLOCK")
                st_lines.append("")
        
        # Add program logic
        if program_logic:
            st_lines.append("// Program Logic")
            st_lines.append("PROGRAM MainProgram")
            st_lines.append("VAR")
            st_lines.append("    // Program variables declared above")
            st_lines.append("END_VAR")
            st_lines.append("")
            st_lines.append("// Main program logic")
            st_lines.extend(program_logic.split('\n'))
            st_lines.append("END_PROGRAM")
            st_lines.append("")
        
        return "\n".join(st_lines)
    
    def _generate_st_from_ir(self, ir_project) -> str:
        """Generate Structured Text code from IR project."""
        st_lines = []
        
        # Add header
        st_lines.append("// Generated Structured Text Code")
        st_lines.append("// Converted from L5X file")
        if ir_project.metadata.get('l5k_overlay_applied'):
            st_lines.append("// Enhanced with L5K overlay context")
        st_lines.append("")
        
        # Add task definitions if available
        if ir_project.tasks:
            st_lines.append("// Task Definitions")
            for task in ir_project.tasks:
                task_name = task.get('name', 'UnknownTask')
                task_type = task.get('type', 'CONTINUOUS')
                priority = task.get('priority', 10)
                watchdog = task.get('watchdog', 500)
                interval = task.get('interval', '')
                
                st_lines.append(f"TASK {task_name} (Type := {task_type}, Priority := {priority}, Watchdog := {watchdog})")
                if interval:
                    st_lines.append(f"    Rate := {interval};")
                st_lines.append("END_TASK")
                st_lines.append("")
        
        # Add data type declarations
        if ir_project.controller.data_types:
            st_lines.append("// Data Type Declarations")
            for dt in ir_project.controller.data_types:
                st_lines.append(f"TYPE {dt.name} :")
                st_lines.append("    STRUCT")
                for member in dt.members:
                    st_lines.append(f"        {member.name} : {member.data_type};")
                st_lines.append("    END_STRUCT;")
                st_lines.append("END_TYPE")
                st_lines.append("")
        
        # Add variable declarations
        if ir_project.controller.tags:
            st_lines.append("// Variable Declarations")
            st_lines.append("VAR")
            for tag in ir_project.controller.tags:
                # Add tag with enhanced information from L5K overlay
                tag_line = f"    {tag.name} : {tag.data_type}"
                if tag.initial_value:
                    tag_line += f" := {tag.initial_value}"
                tag_line += ";"
                st_lines.append(tag_line)
                
                # Add description if available
                if tag.description:
                    st_lines.append(f"    // {tag.description}")
                
                # Add external access info if available
                if tag.external_access:
                    st_lines.append(f"    // External Access: {tag.external_access}")
            st_lines.append("END_VAR")
            st_lines.append("")
        
        # Add function blocks
        if ir_project.controller.function_blocks:
            st_lines.append("// Function Blocks")
            for fb in ir_project.controller.function_blocks:
                st_lines.append(f"FUNCTION_BLOCK {fb.name}")
                
                # Add input parameters
                input_params = [p for p in fb.parameters if p.parameter_type == "Input"]
                if input_params:
                    st_lines.append("VAR_INPUT")
                    for param in input_params:
                        st_lines.append(f"    {param.name} : {param.data_type};")
                    st_lines.append("END_VAR")
                
                # Add output parameters
                output_params = [p for p in fb.parameters if p.parameter_type == "Output"]
                if output_params:
                    st_lines.append("VAR_OUTPUT")
                    for param in output_params:
                        st_lines.append(f"    {param.name} : {param.data_type};")
                    st_lines.append("END_VAR")
                
                # Add local variables
                if fb.local_variables:
                    st_lines.append("VAR")
                    for var in fb.local_variables:
                        st_lines.append(f"    {var.name} : {var.data_type};")
                    st_lines.append("END_VAR")
                
                # Add implementation
                if fb.implementation:
                    st_lines.append("// Implementation")
                    st_lines.extend(fb.implementation.split('\n'))
                
                st_lines.append("END_FUNCTION_BLOCK")
                st_lines.append("")
        
        # Add program logic
        if ir_project.programs:
            for program in ir_project.programs:
                st_lines.append(f"// Program: {program.name}")
                if program.description:
                    st_lines.append(f"// Description: {program.description}")
                
                # Add task association if available
                if hasattr(program, 'task_name') and program.task_name:
                    st_lines.append(f"// Associated Task: {program.task_name}")
                
                st_lines.append(f"PROGRAM {program.name}")
                st_lines.append("VAR")
                st_lines.append("    // Program variables declared above")
                st_lines.append("END_VAR")
                st_lines.append("")
                
                # Add routines
                for routine in program.routines:
                    st_lines.append(f"// Routine: {routine.name} ({routine.routine_type.value})")
                    if routine.description:
                        st_lines.append(f"// {routine.description}")
                    
                    # Add routine content
                    if routine.content:
                        st_lines.extend(routine.content.split('\n'))
                    
                    st_lines.append("")
                
                st_lines.append("END_PROGRAM")
                st_lines.append("")
        
        # Add module information if available
        if ir_project.modules:
            st_lines.append("// Module Configuration")
            for module in ir_project.modules:
                module_name = module.get('name', 'UnknownModule')
                module_type = module.get('type', 'Unknown')
                slot = module.get('slot', 0)
                st_lines.append(f"MODULE {module_name} (Type := {module_type}, Slot := {slot})")
                
                # Add configuration if available
                config = module.get('configuration', {})
                for key, value in config.items():
                    st_lines.append(f"    {key} := {value};")
                
                st_lines.append("END_MODULE")
                st_lines.append("")
        
        return "\n".join(st_lines)

    def convert_l5x_xml_to_st(self, l5x_xml: str) -> Dict[str, str]:
        """
        Convert L5X XML string to Structured Text.
        
        Args:
            l5x_xml: L5X XML content as string
            
        Returns:
            Dictionary with 'variables' and 'program_logic' keys
        """
        try:
            # Parse XML string
            import tempfile
            import os
            
            # Create temporary file with a short name
            with tempfile.NamedTemporaryFile(mode='w', suffix='.l5x', delete=False, prefix='temp_') as temp_file:
                temp_file.write(l5x_xml)
                temp_file_path = temp_file.name
            
            try:
                # Convert using existing method
                st_code = self.convert_l5x_to_st(temp_file_path)
                
                # Parse the ST code to extract variables and program logic
                variables, program_logic = self._parse_st_code_sections(st_code)
                
                return {
                    'variables': variables,
                    'program_logic': program_logic
                }
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"Error converting L5X XML to ST: {e}")
            return {
                'variables': f"// Error: {e}",
                'program_logic': f"// Error: {e}"
            }
    
    def _parse_st_code_sections(self, st_code: str) -> Tuple[str, str]:
        """Parse ST code to separate variables and program logic sections."""
        lines = st_code.split('\n')
        variables = []
        program_logic = []
        in_var_section = False
        in_program_section = False
        
        for line in lines:
            if 'VAR' in line and 'END_VAR' not in line:
                in_var_section = True
                in_program_section = False
                variables.append(line)
            elif 'END_VAR' in line:
                in_var_section = False
                variables.append(line)
            elif 'PROGRAM' in line:
                in_program_section = True
                in_var_section = False
                program_logic.append(line)
            elif in_var_section:
                variables.append(line)
            elif in_program_section or (line.strip() and not line.startswith('//') and not line.startswith('(*')):
                program_logic.append(line)
        
        return '\n'.join(variables), '\n'.join(program_logic)

    def convert_enhanced_roundtrip(self, l5x_file_path: str, l5k_overlay_path: Optional[str] = None) -> ET.Element:
        """
        Enhanced roundtrip conversion: L5X → ST → L5X with complete tag preservation.
        
        Args:
            l5x_file_path: Path to the L5X file
            l5k_overlay_path: Optional path to L5K file for additional context
            
        Returns:
            Enhanced L5X XML element with preserved tags and metadata
        """
        try:
            # Step 1: Convert L5X to ST with L5K overlay
            st_code = self.convert_l5x_to_st(l5x_file_path, l5k_overlay_path)
            
            # Step 2: Extract original tag information for preservation
            project = l5x.Project(l5x_file_path)
            original_tags = self._extract_original_tags(project)
            
            # Step 3: Use enhanced ST2L5X converter with tag preservation
            enhanced_converter = ST2L5XConverter()
            
            # Preserve original tag scopes and metadata
            enhanced_converter.preserve_tag_scopes(original_tags)
            
            # Set L5K context if available
            l5k_context = None
            if l5k_overlay_path:
                from .l5k_overlay import L5KOverlay
                l5k_overlay = L5KOverlay(l5k_overlay_path)
                l5k_context = l5k_overlay.get_summary()
                enhanced_converter.set_l5k_context(l5k_context)
            
            # Step 4: Convert ST back to L5X with enhanced preservation
            enhanced_l5x_xml = enhanced_converter.parse_st_code(st_code, l5k_context)
            
            return enhanced_l5x_xml
            
        except Exception as e:
            logger.error(f"Error in enhanced roundtrip conversion: {e}")
            raise
    
    def _extract_original_tags(self, project) -> Dict[str, Dict]:
        """Extract original tag information for preservation."""
        original_tags = {}
        
        try:
            # Extract controller tags
            if hasattr(project, 'controller') and hasattr(project.controller, 'tags'):
                for tag_name in project.controller.tags:
                    tag = project.controller.tags[tag_name]
                    original_tags[tag_name] = {
                        'scope': 'Controller',
                        'data_type': getattr(tag, 'DataType', 'Unknown'),
                        'description': getattr(tag, 'Description', ''),
                        'external_access': getattr(tag, 'ExternalAccess', ''),
                        'radix': getattr(tag, 'Radix', ''),
                        'constant': getattr(tag, 'Constant', False),
                        'alias_for': getattr(tag, 'AliasFor', ''),
                        'array_dimensions': getattr(tag, 'Dimension', ''),
                        'initial_value': getattr(tag, 'Value', ''),
                        'tag_type': getattr(tag, 'TagType', 'Base'),
                        'usage': getattr(tag, 'Usage', '')
                    }
            
            # Extract program tags
            if hasattr(project, 'programs'):
                for prog_name in project.programs:
                    program = project.programs[prog_name]
                    if hasattr(program, 'tags'):
                        for tag_name in program.tags:
                            tag = program.tags[tag_name]
                            original_tags[tag_name] = {
                                'scope': 'Program',
                                'program': prog_name,
                                'data_type': getattr(tag, 'DataType', 'Unknown'),
                                'description': getattr(tag, 'Description', ''),
                                'external_access': getattr(tag, 'ExternalAccess', ''),
                                'radix': getattr(tag, 'Radix', ''),
                                'constant': getattr(tag, 'Constant', False),
                                'alias_for': getattr(tag, 'AliasFor', ''),
                                'array_dimensions': getattr(tag, 'Dimension', ''),
                                'initial_value': getattr(tag, 'Value', ''),
                                'tag_type': getattr(tag, 'TagType', 'Base'),
                                'usage': getattr(tag, 'Usage', '')
                            }
                            
        except Exception as e:
            logger.error(f"Error extracting original tags: {e}")
        
        return original_tags 


def convert_st_to_l5x_file(st_code: str, output_file: str) -> None:
    """
    Convert Structured Text code to L5X file.
    
    Args:
        st_code: The Structured Text code to convert
        output_file: Path to the output L5X file
    """
    try:
        # Convert ST to L5X XML
        l5x_xml = convert_st_to_l5x_string(st_code)
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n')
            f.write(l5x_xml)
        
        logger.info(f"Successfully converted ST to L5X: {output_file}")
        
    except Exception as e:
        logger.error(f"Error converting ST to L5X: {e}")
        raise


def convert_st_to_l5x_element(st_code: str) -> ET.Element:
    """
    Convert Structured Text code to L5X XML element.
    
    Args:
        st_code: The Structured Text code to convert
        
    Returns:
        L5X XML element
    """
    try:
        return convert_st_to_l5x(st_code)
    except Exception as e:
        logger.error(f"Error converting ST to L5X element: {e}")
        raise 


def convert_enhanced_roundtrip_file(l5x_file_path: str, output_file: str, l5k_overlay_path: Optional[str] = None) -> None:
    """
    Enhanced roundtrip conversion: L5X → ST → L5X with complete tag preservation.
    
    Args:
        l5x_file_path: Path to the input L5X file
        output_file: Path to the output enhanced L5X file
        l5k_overlay_path: Optional path to L5K file for additional context
    """
    try:
        converter = L5X2STConverter()
        enhanced_l5x_xml = converter.convert_enhanced_roundtrip(l5x_file_path, l5k_overlay_path)
        
        # Write enhanced L5X to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n')
            f.write(ET.tostring(enhanced_l5x_xml, encoding='unicode', method='xml'))
        
        logger.info(f"Successfully completed enhanced roundtrip conversion: {output_file}")
        
    except Exception as e:
        logger.error(f"Error in enhanced roundtrip conversion: {e}")
        raise 