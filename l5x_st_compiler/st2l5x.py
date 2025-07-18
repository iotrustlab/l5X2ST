"""
Enhanced Structured Text (ST) to L5X Converter

This module converts Structured Text code back to L5X XML format with enhanced
tag preservation capabilities, enabling high-fidelity round-trip conversion
between L5X and ST.
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Optional, Set, Any
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ST2L5XConverter:
    """Enhanced converter that preserves tag scopes, metadata, and supports L5K overlays."""
    
    def __init__(self):
        self.variables: Dict[str, Dict] = {}  # Variable declarations
        self.program_logic: List[str] = []  # ST statements
        self.function_blocks: Dict[str, Dict] = {}  # Function block instances
        self.data_types: Dict[str, str] = {}  # Data type mappings
        self.tag_scope_preservation: Dict[str, Dict] = {}  # Track original tag scopes
        self.tag_metadata: Dict[str, Dict] = {}  # Track tag metadata
        self.l5k_context: Optional[Dict] = None  # L5K overlay context
        
    def preserve_tag_scopes(self, original_tags: Dict[str, Dict]):
        """Preserve original tag scopes and metadata for roundtrip conversion."""
        self.tag_scope_preservation = {}
        self.tag_metadata = {}
        
        for tag_name, tag_info in original_tags.items():
            self.tag_scope_preservation[tag_name] = {
                'scope': tag_info.get('scope', 'Controller'),
                'program': tag_info.get('program'),
                'data_type': tag_info.get('data_type', 'Unknown'),
                'description': tag_info.get('description', ''),
                'external_access': tag_info.get('external_access', ''),
                'radix': tag_info.get('radix', ''),
                'constant': tag_info.get('constant', False),
                'alias_for': tag_info.get('alias_for', ''),
                'array_dimensions': tag_info.get('array_dimensions', ''),
                'initial_value': tag_info.get('initial_value', ''),
                'tag_type': tag_info.get('tag_type', 'Base'),
                'usage': tag_info.get('usage', '')
            }
            self.tag_metadata[tag_name] = tag_info
    
    def set_l5k_context(self, l5k_context: Dict):
        """Set L5K overlay context for enhanced tag preservation."""
        self.l5k_context = l5k_context
        
    def parse_st_code(self, st_code: str, l5k_context: Optional[Dict] = None) -> ET.Element:
        """Enhanced ST code parsing with L5K overlay support and complete tag preservation."""
        try:
            # Set L5K context if provided
            if l5k_context:
                self.set_l5k_context(l5k_context)
            
            # Clear previous data
            self.variables.clear()
            self.program_logic.clear()
            self.function_blocks.clear()
            
            # Parse ST code
            self._parse_variable_declarations(st_code)
            self._parse_program_logic(st_code)
            
            # Generate enhanced L5X XML
            return self._generate_enhanced_l5x_xml()
            
        except Exception as e:
            logger.error(f"Error parsing ST code: {e}")
            return self._create_error_xml(f"Failed to parse ST code - {e}")
    
    def _parse_variable_declarations(self, st_code: str):
        """Enhanced variable declarations parsing with metadata preservation."""
        self.user_types = set()
        var_match = re.search(r'VAR\s*(.*?)END_VAR', st_code, re.DOTALL | re.IGNORECASE)
        if not var_match:
            logger.warning("No VAR section found in ST code")
            return
        var_section = var_match.group(1)
        var_lines = var_section.split('\n')
        for line in var_lines:
            line = line.strip()
            if not line or line.startswith('//') or line.startswith('(*'):
                continue
            # IEC 61131-3: identifier : type [ := initial_value ];
            # Array: identifier : ARRAY [lower..upper] OF type [ := initial_value ];
            array_match = re.match(r'(\w+)\s*:\s*ARRAY\s*\[(.*?)\]\s*OF\s*(\w+)\s*(?::=\s*([^;]+))?;', line, re.IGNORECASE)
            if array_match:
                var_name = array_match.group(1)
                array_range = array_match.group(2)
                base_type = array_match.group(3)
                initial_value = array_match.group(4)
                
                # Use preserved metadata if available
                preserved_info = self.tag_scope_preservation.get(var_name, {})
                
                self.variables[var_name] = {
                    'name': var_name,
                    'type': preserved_info.get('data_type', base_type),
                    'array_range': array_range,
                    'scope': preserved_info.get('scope', 'Controller'),
                    'initial_value': initial_value.strip() if initial_value else preserved_info.get('initial_value', ''),
                    'is_array': True,
                    'description': preserved_info.get('description', ''),
                    'external_access': preserved_info.get('external_access', ''),
                    'radix': preserved_info.get('radix', ''),
                    'constant': preserved_info.get('constant', False),
                    'tag_type': preserved_info.get('tag_type', 'Base')
                }
                if base_type not in self._basic_types():
                    self.user_types.add(base_type)
                continue
            # Regular variable: identifier : type [ := initial_value ];
            var_match = re.match(r'(\w+)\s*:\s*([\w\[\]\.]+)\s*(?::=\s*([^;]+))?;', line)
            if var_match:
                var_name = var_match.group(1)
                var_type = var_match.group(2)
                initial_value = var_match.group(3)
                
                # Use preserved metadata if available
                preserved_info = self.tag_scope_preservation.get(var_name, {})
                
                self.variables[var_name] = {
                    'name': var_name,
                    'type': preserved_info.get('data_type', var_type),
                    'scope': preserved_info.get('scope', 'Controller'),
                    'initial_value': initial_value.strip() if initial_value else preserved_info.get('initial_value', ''),
                    'is_array': False,
                    'description': preserved_info.get('description', ''),
                    'external_access': preserved_info.get('external_access', ''),
                    'radix': preserved_info.get('radix', ''),
                    'constant': preserved_info.get('constant', False),
                    'tag_type': preserved_info.get('tag_type', 'Base')
                }
                if var_type not in self._basic_types():
                    self.user_types.add(var_type)
                continue
            # Could add STRUCT, user-defined, etc. here
            logger.debug(f"Unparsed VAR line: {line}")
    
    def _parse_program_logic(self, st_code: str):
        """Parse program logic statements from ST code (IEC 61131-3 compliant)."""
        lines = []
        for line in st_code.split('\n'):
            # Remove single-line and multi-line comments
            line = re.sub(r'//.*$', '', line)
            line = re.sub(r'\(\*.*?\*\)', '', line, flags=re.DOTALL)
            line = line.strip()
            if line:
                lines.append(line)
        in_var_section = False
        for line in lines:
            if re.match(r'VAR\b', line, re.IGNORECASE):
                in_var_section = True
                continue
            elif re.match(r'END_VAR\b', line, re.IGNORECASE):
                in_var_section = False
                continue
            if not in_var_section and line and not line.startswith('//'):
                # Assignment: identifier := expression;
                assign_match = re.match(r'(\w+(?:\[.*?\])?)\s*:=\s*(.+);', line)
                if assign_match:
                    self.program_logic.append(line)
                    continue
                # Function/FB call: FBName(param1 := value1, ...);
                fb_call_match = re.match(r'(\w+)\s*\((.*)\);', line)
                if fb_call_match:
                    self.program_logic.append(line)
                    continue
                # Control structures (IF, FOR, WHILE, etc.)
                ctrl_match = re.match(r'(IF|ELSIF|ELSE|END_IF|FOR|END_FOR|WHILE|END_WHILE|CASE|END_CASE|REPEAT|END_REPEAT|EXIT|RETURN|CONTINUE|THEN|DO|TO|BY|OF|UNTIL|AND|OR|NOT|TRUE|FALSE)', line, re.IGNORECASE)
                if ctrl_match:
                    self.program_logic.append(line)
                    continue
                # Otherwise, just add the line
                self.program_logic.append(line)
    
    def _split_variables(self):
        """Enhanced variable splitting with scope preservation."""
        controller_tags = {}
        program_tags = {}
        for var_name, var_info in self.variables.items():
            # Use preserved scope if available, otherwise use naming convention
            scope = var_info.get('scope', 'Controller')
            if scope == 'Controller':
                controller_tags[var_name] = var_info
            else:
                program_tags[var_name] = var_info
        return controller_tags, program_tags

    def _generate_enhanced_l5x_xml(self) -> ET.Element:
        """Generate enhanced L5X XML structure with complete tag preservation."""
        root = ET.Element('RSLogix5000Content')
        root.set('SchemaRevision', '1.0')
        root.set('SoftwareRevision', '20.01')
        root.set('TargetName', 'Generated_Controller')
        root.set('TargetType', 'Controller')
        root.set('ContainsContext', 'true')
        
        controller = ET.SubElement(root, 'Controller')
        controller.set('Name', 'Generated_Controller')
        controller.set('ProcessorType', '1756-L71')
        controller.set('MajorRev', '20')
        controller.set('MinorRev', '11')
        controller.set('TimeSlice', '20')
        controller.set('ShareUnusedTimeSlice', '1')
        controller.set('ProjectCreationDate', '2024-01-01T00:00:00')
        controller.set('LastModifiedDate', '2024-01-01T00:00:00')
        controller.set('SFCExecutionControl', 'CurrentActive')
        controller.set('SFCRestartPosition', 'MostRecent')
        controller.set('SFCLastScan', 'DontScan')
        controller.set('ProjectSN', '16#0000_0000')
        
        data_types = ET.SubElement(controller, 'DataTypes')
        self._add_basic_data_types(data_types)
        
        controller_tags, program_tags = self._split_variables()
        
        # Create controller tags with enhanced preservation
        tags_elem = ET.SubElement(controller, 'Tags')
        for var_name, var_info in controller_tags.items():
            tag = self._create_enhanced_tag_element(var_name, var_info)
            tags_elem.append(tag)
        
        # Create programs with program-scoped tags
        programs = ET.SubElement(controller, 'Programs')
        main_program = self._create_enhanced_main_program(program_tags)
        programs.append(main_program)
        
        tasks = ET.SubElement(controller, 'Tasks')
        main_task = self._create_main_task()
        tasks.append(main_task)
        
        return root
    
    def _create_enhanced_tag_element(self, tag_name: str, tag_info: Dict) -> ET.Element:
        """Create an enhanced tag element with complete metadata preservation."""
        tag = ET.Element('Tag')
        tag.set('Name', tag_name)
        
        # Set data type (use preserved if available)
        data_type = tag_info.get('type', 'DINT')
        if data_type == 'Unknown':
            data_type = 'DINT'  # Default fallback
        tag.set('DataType', data_type)
        
        # Set scope (preserve original scope)
        scope = tag_info.get('scope', 'Controller')
        if scope == 'Controller':
            tag.set('Scope', 'Controller')
        else:
            tag.set('Scope', 'Program')
            program_name = tag_info.get('program')
            if program_name:
                tag.set('Program', program_name)
        
        # ENHANCED: Add TagType attribute (fixes library compatibility)
        tag_type = tag_info.get('tag_type', 'Base')
        tag.set('TagType', tag_type)
        
        # Add array dimensions if available
        if tag_info.get('is_array'):
            tag.set('Dimension', tag_info['array_range'])
        
        # Add description if available
        description = tag_info.get('description', '')
        if description:
            desc = ET.SubElement(tag, 'Description')
            desc.text = description
        
        # Add external access if available
        external_access = tag_info.get('external_access', '')
        if external_access:
            tag.set('ExternalAccess', external_access)
        
        # Add radix if available
        radix = tag_info.get('radix', '')
        if radix:
            tag.set('Radix', radix)
        
        # Add constant flag if available
        constant = tag_info.get('constant', False)
        if constant:
            tag.set('Constant', 'true')
        
        # Add alias information if available
        alias_for = tag_info.get('alias_for', '')
        if alias_for:
            tag.set('AliasFor', alias_for)
        
        # Add initial value if available
        initial_value = tag_info.get('initial_value', '')
        if initial_value:
            value_elem = ET.SubElement(tag, 'Value')
            value_elem.text = initial_value
        
        # Add usage if available
        usage = tag_info.get('usage', '')
        if usage:
            tag.set('Usage', usage)
        
        # Add empty Data element to prevent "Decoded data content not found" errors
        data = ET.SubElement(tag, 'Data')
        data.set('Format', 'Decorated')
        data.set('Use', 'Context')
        value = ET.SubElement(data, 'Value')
        value.set('DataType', data_type)
        if tag_info.get('is_array'):
            value.set('Radix', 'Decimal')
            value.text = '0'
        else:
            value.set('Radix', 'Decimal')
            value.text = '0'
        
        return tag
    
    def _create_enhanced_main_program(self, program_tags: Dict) -> ET.Element:
        """Create enhanced main program with program-scoped tags."""
        main_program = ET.Element('Program')
        main_program.set('Name', 'MainProgram')
        main_program.set('TestEdits', 'false')
        main_program.set('MainRoutineName', 'MainRoutine')
        main_program.set('ScheduledPrograms', '')
        
        # Create program tags with enhanced preservation
        program_tags_elem = ET.SubElement(main_program, 'Tags')
        for var_name, var_info in program_tags.items():
            tag = self._create_enhanced_tag_element(var_name, var_info)
            program_tags_elem.append(tag)
        
        # Create routines
        routines = ET.SubElement(main_program, 'Routines')
        main_routine = self._create_st_routine('MainRoutine')
        routines.append(main_routine)
        
        return main_program
    
    def _add_basic_data_types(self, data_types_elem: ET.Element):
        """Add basic IEC data types to the L5X."""
        basic_types = [
            ('BOOL', 'BOOL'),
            ('SINT', 'SINT'),
            ('INT', 'INT'),
            ('DINT', 'DINT'),
            ('LINT', 'LINT'),
            ('USINT', 'USINT'),
            ('UINT', 'UINT'),
            ('UDINT', 'UDINT'),
            ('ULINT', 'ULINT'),
            ('REAL', 'REAL'),
            ('LREAL', 'LREAL'),
            ('STRING', 'STRING'),
            ('TIME', 'TIME'),
            ('DATE', 'DATE'),
            ('TOD', 'TOD'),
            ('DT', 'DT')
        ]
        
        for type_name, base_type in basic_types:
            data_type = ET.SubElement(data_types_elem, 'DataType')
            data_type.set('Name', type_name)
            data_type.set('Use', 'Target')
            data_type.set('Family', base_type)
            data_type.set('Class', 'User')
    
    def _create_main_program(self, program_tags) -> ET.Element:
        """Create main program (legacy method for backward compatibility)."""
        return self._create_enhanced_main_program(program_tags)
    
    def _create_st_routine(self, routine_name: str) -> ET.Element:
        """Create ST routine with enhanced content."""
        routine = ET.Element('Routine')
        routine.set('Name', routine_name)
        routine.set('Type', 'ST')
        routine.set('Use', 'Context')
        
        st_content = ET.SubElement(routine, 'STContent')
        st_content.set('Use', 'Context')
        
        # Add formatted ST code
        st_code = self._format_st_code()
        st_content.text = st_code
        
        return routine
    
    def _format_st_code(self) -> str:
        """Format ST code for routine content."""
        lines = []
        lines.append("// Generated Structured Text Code")
        lines.append("// Enhanced with tag preservation")
        lines.append("")
        
        # Add variable declarations
        if self.variables:
            lines.append("VAR")
            for var_name, var_info in self.variables.items():
                var_type = var_info['type']
                if var_info.get('is_array'):
                    array_range = var_info['array_range']
                    line = f"    {var_name} : ARRAY [{array_range}] OF {var_type};"
                else:
                    line = f"    {var_name} : {var_type};"
                lines.append(line)
            lines.append("END_VAR")
            lines.append("")
        
        # Add program logic
        for statement in self.program_logic:
            lines.append(statement)
        
        return '\n'.join(lines)
    
    def _create_main_task(self) -> ET.Element:
        """Create main task."""
        task = ET.Element('Task')
        task.set('Name', 'MainTask')
        task.set('Type', 'Continuous')
        task.set('Priority', '10')
        task.set('Watchdog', '500')
        task.set('DisableUpdateOutputs', 'false')
        task.set('InhibitTask', 'false')
        task.set('EventID', '0')
        
        schedule = ET.SubElement(task, 'Schedule')
        schedule.set('Type', 'Continuous')
        
        programs = ET.SubElement(task, 'Programs')
        program = ET.SubElement(programs, 'Program')
        program.set('Name', 'MainProgram')
        program.set('Type', 'Program')
        
        return task
    
    def _create_error_xml(self, error_message: str) -> ET.Element:
        """Create error XML structure."""
        root = ET.Element('RSLogix5000Content')
        root.set('SchemaRevision', '1.0')
        root.set('SoftwareRevision', '20.01')
        root.set('TargetName', 'Error_Controller')
        root.set('TargetType', 'Controller')
        root.set('ContainsContext', 'true')
        
        controller = ET.SubElement(root, 'Controller')
        controller.set('Name', 'Error_Controller')
        
        error_tag = ET.SubElement(controller, 'Tag')
        error_tag.set('Name', 'ConversionError')
        error_tag.set('DataType', 'STRING')
        error_tag.set('TagType', 'Base')
        error_tag.set('Scope', 'Controller')
        
        error_value = ET.SubElement(error_tag, 'Value')
        error_value.text = error_message
        
        return root
    
    def convert_st_to_l5x(self, variables: str, program_logic: str) -> str:
        """Convert ST code to L5X string (legacy method for backward compatibility)."""
        st_code = f"VAR\n{variables}\nEND_VAR\n\n{program_logic}"
        xml_element = self.parse_st_code(st_code)
        return ET.tostring(xml_element, encoding='unicode', method='xml')
    
    def _basic_types(self):
        """Return set of basic IEC data types."""
        return {
            'BOOL', 'SINT', 'INT', 'DINT', 'LINT', 'USINT', 'UINT', 'UDINT', 'ULINT',
            'REAL', 'LREAL', 'STRING', 'TIME', 'DATE', 'TOD', 'DT'
        }


def convert_st_to_l5x(st_code: str) -> ET.Element:
    """Convert ST code to L5X XML element (legacy function for backward compatibility)."""
    converter = ST2L5XConverter()
    return converter.parse_st_code(st_code)


def convert_st_to_l5x_string(st_code: str) -> str:
    """Convert ST code to L5X XML string (legacy function for backward compatibility)."""
    converter = ST2L5XConverter()
    xml_element = converter.parse_st_code(st_code)
    return ET.tostring(xml_element, encoding='unicode', method='xml') 