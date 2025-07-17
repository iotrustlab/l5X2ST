"""
Intermediate Representation converter for L5X-ST round-trip conversion.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import xml.etree.ElementTree as ET

from .models import (
    IRProject, IRController, IRProgram, IRRoutine, IRTag, IRDataType, 
    IRDataTypeMember, IRFunctionBlock, IRFunctionBlockParameter,
    TagScope, RoutineType, ConversionMetadata, ComponentMapping, RoundTripInfo
)
from .utils import extract_tag_info, get_data_type
from .ladder_logic import translate_ladder_to_st
from .fbd_translator import translate_fbd_to_st
from .l5k_overlay import L5KOverlay

logger = logging.getLogger(__name__)


class IRConverter:
    """Converts between L5X files and Intermediate Representation."""
    
    def __init__(self):
        self.conversion_metadata = ConversionMetadata(
            source_file="",
            conversion_time=datetime.now().isoformat(),
            converter_version="1.0.0"
        )
        self.component_mappings: List[ComponentMapping] = []
    
    def l5x_to_ir(self, project, l5k_overlay_path: Optional[str] = None) -> IRProject:
        """
        Convert L5X project to Intermediate Representation.
        
        Args:
            project: L5X project object
            l5k_overlay_path: Optional path to L5K file for additional context
            
        Returns:
            IR project with optional L5K overlay applied
        """
        logger.info("Converting L5X to Intermediate Representation")
        
        # Extract controller information
        controller = self._extract_controller_ir(project)
        
        # Extract programs
        programs = self._extract_programs_ir(project)
        
        # Build IR project
        ir_project = IRProject(
            controller=controller,
            programs=programs,
            metadata={
                "original_file": getattr(project, 'source_file', 'unknown'),
                "conversion_time": self.conversion_metadata.conversion_time
            }
        )
        
        # Apply L5K overlay if provided
        if l5k_overlay_path:
            try:
                logger.info(f"Applying L5K overlay from: {l5k_overlay_path}")
                l5k_overlay = L5KOverlay(l5k_overlay_path)
                ir_project = l5k_overlay.apply_to_ir(ir_project)
                logger.info("L5K overlay applied successfully")
            except Exception as e:
                logger.warning(f"Failed to apply L5K overlay: {e}")
                # Continue without overlay if it fails
        
        # Update metadata
        self.conversion_metadata.original_components = {
            "tags": len(controller.tags),
            "data_types": len(controller.data_types),
            "function_blocks": len(controller.function_blocks),
            "programs": len(programs),
            "routines": sum(len(p.routines) for p in programs)
        }
        
        return ir_project
    
    def _extract_controller_ir(self, project) -> IRController:
        """Extract controller information to IR."""
        controller_name = getattr(project.controller, 'name', 'Unknown_Controller')
        
        # Extract controller tags
        tags = []
        if hasattr(project.controller, 'tags'):
            for tag_name in project.controller.tags.names:
                try:
                    tag_data = project.controller.tags[tag_name]
                    tag_info = self._extract_tag_ir(tag_name, tag_data, TagScope.CONTROLLER)
                    if tag_info:
                        tags.append(tag_info)
                except Exception as e:
                    logger.warning(f"Could not extract tag {tag_name}: {e}")
        
        # Extract data types from XML
        data_types = self._extract_data_types_ir(project)
        
        # Extract function blocks from XML
        function_blocks = self._extract_function_blocks_ir(project)
        
        return IRController(
            name=controller_name,
            tags=tags,
            data_types=data_types,
            function_blocks=function_blocks
        )
    
    def _extract_tag_ir(self, name: str, tag_data, scope: TagScope) -> Optional[IRTag]:
        """Extract tag information to IR."""
        try:
            # Get data type
            data_type = getattr(tag_data, 'data_type', 'UNKNOWN')
            clean_type = get_data_type(data_type)
            
            # Get value if available
            value = None
            try:
                value = str(getattr(tag_data, 'value', ''))
            except:
                pass
            
            # Get description
            description = getattr(tag_data, 'description', None)
            
            # Get external access
            external_access = getattr(tag_data, 'external_access', None)
            
            # Get radix
            radix = getattr(tag_data, 'radix', None)
            
            # Check if constant
            constant = getattr(tag_data, 'constant', False)
            
            # Check if alias
            alias_for = getattr(tag_data, 'alias_for', None)
            
            return IRTag(
                name=name,
                data_type=clean_type,
                scope=scope,
                value=value,
                description=description,
                external_access=external_access,
                radix=radix,
                constant=constant,
                alias_for=alias_for
            )
        except Exception as e:
            logger.warning(f"Error extracting tag {name}: {e}")
            return None
    
    def _extract_data_types_ir(self, project) -> List[IRDataType]:
        """Extract user-defined data types from XML."""
        data_types = []
        
        try:
            # Access the raw XML element
            controller_element = project.controller.element
            
            # Find DataType elements
            for data_type_elem in controller_element.findall('.//DataType'):
                name = data_type_elem.get('Name', 'Unknown')
                base_type = data_type_elem.get('Use', None)
                
                members = []
                for member_elem in data_type_elem.findall('.//Member'):
                    member_name = member_elem.get('Name', 'Unknown')
                    member_type = member_elem.get('DataType', 'UNKNOWN')
                    member_desc = member_elem.get('Description', None)
                    member_radix = member_elem.get('Radix', None)
                    member_external = member_elem.get('ExternalAccess', None)
                    
                    members.append(IRDataTypeMember(
                        name=member_name,
                        data_type=member_type,
                        description=member_desc,
                        radix=member_radix,
                        external_access=member_external
                    ))
                
                data_types.append(IRDataType(
                    name=name,
                    base_type=base_type,
                    members=members
                ))
                
        except Exception as e:
            logger.warning(f"Error extracting data types: {e}")
        
        return data_types
    
    def _extract_function_blocks_ir(self, project) -> List[IRFunctionBlock]:
        """Extract function blocks from XML."""
        function_blocks = []
        
        try:
            # Access the raw XML element
            controller_element = project.controller.element
            
            # Find AddOnInstruction elements
            for fb_elem in controller_element.findall('.//AddOnInstruction'):
                name = fb_elem.get('Name', 'Unknown')
                description = fb_elem.get('Description', None)
                
                parameters = []
                local_variables = []
                
                # Extract parameters
                for param_elem in fb_elem.findall('.//Parameter'):
                    param_name = param_elem.get('Name', 'Unknown')
                    param_type = param_elem.get('DataType', 'UNKNOWN')
                    param_kind = param_elem.get('Usage', 'Input')
                    param_required = param_elem.get('Required', 'true').lower() == 'true'
                    
                    parameters.append(IRFunctionBlockParameter(
                        name=param_name,
                        data_type=param_type,
                        parameter_type=param_kind,
                        required=param_required
                    ))
                
                # Extract local variables
                for var_elem in fb_elem.findall('.//LocalTag'):
                    var_name = var_elem.get('Name', 'Unknown')
                    var_type = var_elem.get('DataType', 'UNKNOWN')
                    
                    local_variables.append(IRFunctionBlockParameter(
                        name=var_name,
                        data_type=var_type,
                        parameter_type='Local'
                    ))
                
                function_blocks.append(IRFunctionBlock(
                    name=name,
                    description=description,
                    parameters=parameters,
                    local_variables=local_variables
                ))
                
        except Exception as e:
            logger.warning(f"Error extracting function blocks: {e}")
        
        return function_blocks
    
    def _extract_programs_ir(self, project) -> List[IRProgram]:
        """Extract programs to IR."""
        programs = []
        
        if hasattr(project, 'programs'):
            for prog_name in project.programs.names:
                try:
                    prog_data = project.programs[prog_name]
                    program_ir = self._extract_program_ir(prog_name, prog_data)
                    if program_ir:
                        programs.append(program_ir)
                except Exception as e:
                    logger.warning(f"Could not extract program {prog_name}: {e}")
        
        return programs
    
    def _extract_program_ir(self, name: str, program_data) -> Optional[IRProgram]:
        """Extract program information to IR."""
        try:
            # Extract program tags
            tags = []
            if hasattr(program_data, 'tags'):
                for tag_name in program_data.tags.names:
                    try:
                        tag_data = program_data.tags[tag_name]
                        tag_info = self._extract_tag_ir(tag_name, tag_data, TagScope.PROGRAM)
                        if tag_info:
                            tags.append(tag_info)
                    except Exception as e:
                        logger.warning(f"Could not extract program tag {tag_name}: {e}")
            
            # Extract routines - try API first, then fallback to XML
            routines = []
            if hasattr(program_data, 'routines'):
                try:
                    # Try API-based extraction
                    for routine_name in program_data.routines.names:
                        try:
                            routine_data = program_data.routines[routine_name]
                            # Create a mock routine object for API-based extraction
                            routine_ir = self._create_routine_from_api(routine_name, routine_data)
                            if routine_ir:
                                routines.append(routine_ir)
                        except Exception as e:
                            logger.warning(f"Could not extract routine {routine_name}: {e}")
                except Exception as e:
                    logger.warning(f"API-based routine extraction failed, trying XML: {e}")
            
            # If no routines found via API, try XML-based extraction
            if not routines and hasattr(program_data, 'element'):
                routines = self._extract_routines_from_xml(program_data.element)
            
            # Get main routine
            main_routine = getattr(program_data, 'main_routine', None)
            
            return IRProgram(
                name=name,
                tags=tags,
                routines=routines,
                main_routine=main_routine
            )
            
        except Exception as e:
            logger.warning(f"Error extracting program {name}: {e}")
            return None

    def _create_routine_from_api(self, name: str, routine_data) -> Optional[IRRoutine]:
        """Create routine from API data."""
        try:
            # Determine routine type
            routine_type = RoutineType.ST  # Default
            if hasattr(routine_data, 'type'):
                rtype = routine_data.type.upper()
                if rtype in ['RLL', 'LADDER']:
                    routine_type = RoutineType.RLL
                elif rtype == 'FBD':
                    routine_type = RoutineType.FBD
                elif rtype == 'SFC':
                    routine_type = RoutineType.SFC
            
            # Extract content from XML
            content = self._extract_routine_content_ir(routine_data)
            
            # Extract local variables
            local_variables = []
            if hasattr(routine_data, 'local_tags'):
                for var_name in routine_data.local_tags.names:
                    try:
                        var_data = routine_data.local_tags[var_name]
                        var_info = self._extract_tag_ir(var_name, var_data, TagScope.PROGRAM)
                        if var_info:
                            local_variables.append(var_info)
                    except Exception as e:
                        logger.warning(f"Could not extract local variable {var_name}: {e}")
            
            return IRRoutine(
                name=name,
                routine_type=routine_type,
                content=content,
                local_variables=local_variables
            )
            
        except Exception as e:
            logger.warning(f"Error extracting routine {name}: {e}")
            return None

    def _extract_routine_content_ir(self, routine_data) -> str:
        """Extract routine content from API data."""
        try:
            # Access the raw XML element
            routine_element = routine_data.element
            
            content_lines = []
            
            if routine_data.type.upper() in ['RLL', 'LADDER']:
                # Extract ladder logic
                for rung_elem in routine_element.findall('.//Rung'):
                    rung_text = rung_elem.get('Text', '')
                    if rung_text:
                        # Translate ladder to ST
                        st_content = translate_ladder_to_st(rung_text)
                        content_lines.append(st_content)
            
            elif routine_data.type.upper() == 'FBD':
                # Extract FBD content
                fbd_content = self._extract_fbd_content_ir(routine_element)
                if fbd_content:
                    content_lines.append(fbd_content)
            
            else:
                # Extract ST content
                for text_elem in routine_element.findall('.//Text'):
                    cdata = text_elem.find('.//CDATAContent')
                    if cdata is not None and cdata.text:
                        content_lines.append(cdata.text.strip())
            
            return '\n'.join(content_lines)
            
        except Exception as e:
            logger.warning(f"Error extracting routine content: {e}")
            return ""

    def _extract_fbd_content_ir(self, routine_element) -> str:
        """Extract FBD content and translate to ST."""
        try:
            # Find FBD elements - pass the routine element itself to the translator
            return translate_fbd_to_st(routine_element)
            
        except Exception as e:
            logger.warning(f"Error extracting FBD content: {e}")
            return ""

    def _extract_routines_from_xml(self, program_element) -> List[IRRoutine]:
        """Extract routines from XML when API-based extraction fails."""
        routines = []
        try:
            # Find Routines element
            routines_elem = program_element.find('.//Routines')
            if routines_elem is not None:
                for routine_elem in routines_elem.findall('.//Routine'):
                    routine_name = routine_elem.get('Name', 'Unknown')
                    routine_type = routine_elem.get('Type', 'ST')
                    
                    # Determine routine type
                    ir_routine_type = RoutineType.ST  # Default
                    if routine_type.upper() in ['RLL', 'LADDER']:
                        ir_routine_type = RoutineType.RLL
                    elif routine_type.upper() == 'FBD':
                        ir_routine_type = RoutineType.FBD
                    elif routine_type.upper() == 'SFC':
                        ir_routine_type = RoutineType.SFC
                    
                    # Extract content
                    content = self._extract_routine_content_from_xml(routine_elem, routine_type)
                    
                    # Create routine object
                    routine = IRRoutine(
                        name=routine_name,
                        routine_type=ir_routine_type,
                        content=content,
                        local_variables=[]  # Could be enhanced to extract local variables
                    )
                    routines.append(routine)
                    
        except Exception as e:
            logger.warning(f"Error extracting routines from XML: {e}")
        
        return routines

    def _extract_routine_content_from_xml(self, routine_elem, routine_type: str) -> str:
        """Extract routine content from XML element."""
        try:
            content_lines = []
            
            if routine_type.upper() in ['RLL', 'LADDER']:
                # Extract ladder logic
                for rung_elem in routine_elem.findall('.//Rung'):
                    rung_text = rung_elem.get('Text', '')
                    if rung_text:
                        # Translate ladder to ST
                        st_content = translate_ladder_to_st(rung_text)
                        content_lines.append(st_content)
            
            elif routine_type.upper() == 'FBD':
                # Extract FBD content
                fbd_content = self._extract_fbd_content_from_xml(routine_elem)
                if fbd_content:
                    content_lines.append(fbd_content)
            
            else:
                # Extract ST content
                for text_elem in routine_elem.findall('.//Text'):
                    cdata = text_elem.find('.//CDATAContent')
                    if cdata is not None and cdata.text:
                        content_lines.append(cdata.text.strip())
                    elif text_elem.text:
                        content_lines.append(text_elem.text.strip())
            
            return '\n'.join(content_lines)
            
        except Exception as e:
            logger.warning(f"Error extracting routine content from XML: {e}")
            return ""

    def _extract_fbd_content_from_xml(self, routine_elem) -> str:
        """Extract FBD content and translate to ST."""
        try:
            # Find FBD elements - pass the routine element itself to the translator
            return translate_fbd_to_st(routine_elem)
            
        except Exception as e:
            logger.warning(f"Error extracting FBD content from XML: {e}")
            return ""
    
    def ir_to_l5x(self, ir_project: IRProject) -> str:
        """Convert Intermediate Representation back to L5X XML."""
        logger.info("Converting IR to L5X XML")
        
        # Build XML structure
        root = ET.Element('RSLogix5000Content')
        root.set('SchemaRevision', '1.0')
        root.set('SoftwareRevision', '20.01')
        root.set('TargetName', ir_project.controller.name)
        root.set('TargetType', 'Program')
        root.set('ContainsContext', 'true')
        
        # Add controller
        controller_elem = ET.SubElement(root, 'Controller')
        controller_elem.set('Name', ir_project.controller.name)
        controller_elem.set('ProcessorType', 'Logix5580')
        controller_elem.set('MajorRev', '20')
        controller_elem.set('MinorRev', '1')
        controller_elem.set('TimeSlice', '20')
        controller_elem.set('ShareUnusedTimeSlice', '1')
        controller_elem.set('ProjectCreationDate', 'Mon Jan 01 00:00:00 2024')
        controller_elem.set('LastModifiedDate', 'Mon Jan 01 00:00:00 2024')
        controller_elem.set('SFCExecutionControl', 'CurrentActive')
        controller_elem.set('SFCRestartPosition', 'MostRecent')
        controller_elem.set('ProjectSN', '16#0000_0000')
        
        # Add data types
        if ir_project.controller.data_types:
            data_types_elem = ET.SubElement(controller_elem, 'DataTypes')
            for dt in ir_project.controller.data_types:
                self._add_data_type_to_xml(dt, data_types_elem)
        
        # Add function blocks
        if ir_project.controller.function_blocks:
            addons_elem = ET.SubElement(controller_elem, 'AddOnInstructionDefinitions')
            for fb in ir_project.controller.function_blocks:
                self._add_function_block_to_xml(fb, addons_elem)
        
        # Add controller tags
        if ir_project.controller.tags:
            tags_elem = ET.SubElement(controller_elem, 'Tags')
            for tag in ir_project.controller.tags:
                self._add_tag_to_xml(tag, tags_elem)
        
        # Add programs
        if ir_project.programs:
            programs_elem = ET.SubElement(controller_elem, 'Programs')
            for program in ir_project.programs:
                self._add_program_to_xml(program, programs_elem)
        
        # Convert to string
        return ET.tostring(root, encoding='unicode', method='xml')
    
    def _add_data_type_to_xml(self, data_type: IRDataType, parent_elem):
        """Add data type to XML."""
        dt_elem = ET.SubElement(parent_elem, 'DataType')
        dt_elem.set('Name', data_type.name)
        if data_type.base_type:
            dt_elem.set('Use', data_type.base_type)
        if data_type.description:
            dt_elem.set('Description', data_type.description)
        
        for member in data_type.members:
            member_elem = ET.SubElement(dt_elem, 'Member')
            member_elem.set('Name', member.name)
            member_elem.set('DataType', member.data_type)
            if member.description:
                member_elem.set('Description', member.description)
            if member.radix:
                member_elem.set('Radix', member.radix)
            if member.external_access:
                member_elem.set('ExternalAccess', member.external_access)
    
    def _add_function_block_to_xml(self, fb: IRFunctionBlock, parent_elem):
        """Add function block to XML."""
        fb_elem = ET.SubElement(parent_elem, 'AddOnInstructionDefinition')
        fb_elem.set('Name', fb.name)
        if fb.description:
            fb_elem.set('Description', fb.description)
        
        # Add parameters
        if fb.parameters:
            params_elem = ET.SubElement(fb_elem, 'Parameters')
            for param in fb.parameters:
                param_elem = ET.SubElement(params_elem, 'Parameter')
                param_elem.set('Name', param.name)
                param_elem.set('DataType', param.data_type)
                param_elem.set('Usage', param.parameter_type)
                param_elem.set('Required', str(param.required).lower())
        
        # Add local variables
        if fb.local_variables:
            locals_elem = ET.SubElement(fb_elem, 'LocalTags')
            for var in fb.local_variables:
                var_elem = ET.SubElement(locals_elem, 'LocalTag')
                var_elem.set('Name', var.name)
                var_elem.set('DataType', var.data_type)
    
    def _add_tag_to_xml(self, tag: IRTag, parent_elem):
        """Add tag to XML."""
        tag_elem = ET.SubElement(parent_elem, 'Tag')
        tag_elem.set('Name', tag.name)
        tag_elem.set('TagType', 'Base')
        tag_elem.set('DataType', tag.data_type)
        if tag.value:
            tag_elem.set('Value', tag.value)
        if tag.description:
            tag_elem.set('Description', tag.description)
        if tag.external_access:
            tag_elem.set('ExternalAccess', tag.external_access)
        if tag.radix:
            tag_elem.set('Radix', tag.radix)
        if tag.constant:
            tag_elem.set('Constant', 'true')
        if tag.alias_for:
            tag_elem.set('AliasFor', tag.alias_for)
    
    def _add_program_to_xml(self, program: IRProgram, parent_elem):
        """Add program to XML."""
        prog_elem = ET.SubElement(parent_elem, 'Program')
        prog_elem.set('Name', program.name)
        if program.description:
            prog_elem.set('Description', program.description)
        
        # Add program tags
        if program.tags:
            tags_elem = ET.SubElement(prog_elem, 'Tags')
            for tag in program.tags:
                self._add_tag_to_xml(tag, tags_elem)
        
        # Add routines
        if program.routines:
            routines_elem = ET.SubElement(prog_elem, 'Routines')
            for routine in program.routines:
                self._add_routine_to_xml(routine, routines_elem)
        
        # Set main routine
        if program.main_routine:
            main_elem = ET.SubElement(prog_elem, 'MainRoutineName')
            main_elem.set('Value', program.main_routine)
    
    def _add_routine_to_xml(self, routine: IRRoutine, parent_elem):
        """Add routine to XML."""
        routine_elem = ET.SubElement(parent_elem, 'Routine')
        routine_elem.set('Name', routine.name)
        routine_elem.set('Type', routine.routine_type.value)
        if routine.description:
            routine_elem.set('Description', routine.description)
        
        # Add content
        if routine.content:
            text_elem = ET.SubElement(routine_elem, 'Text')
            cdata_elem = ET.SubElement(text_elem, 'CDATAContent')
            cdata_elem.text = routine.content
    
    def calculate_fidelity_score(self, original: IRProject, converted: IRProject) -> float:
        """Calculate round-trip fidelity score."""
        total_components = 0
        matched_components = 0
        
        # Compare tags
        original_tags = {t.name: t for t in original.controller.tags}
        converted_tags = {t.name: t for t in converted.controller.tags}
        
        total_components += len(original_tags)
        for name, original_tag in original_tags.items():
            if name in converted_tags:
                converted_tag = converted_tags[name]
                if (original_tag.data_type == converted_tag.data_type and
                    original_tag.scope == converted_tag.scope):
                    matched_components += 1
        
        # Compare data types
        original_dts = {dt.name: dt for dt in original.controller.data_types}
        converted_dts = {dt.name: dt for dt in converted.controller.data_types}
        
        total_components += len(original_dts)
        for name, original_dt in original_dts.items():
            if name in converted_dts:
                converted_dt = converted_dts[name]
                if len(original_dt.members) == len(converted_dt.members):
                    matched_components += 1
        
        # Compare programs and routines
        original_progs = {p.name: p for p in original.programs}
        converted_progs = {p.name: p for p in converted.programs}
        
        total_components += len(original_progs)
        for name, original_prog in original_progs.items():
            if name in converted_progs:
                converted_prog = converted_progs[name]
                if len(original_prog.routines) == len(converted_prog.routines):
                    matched_components += 1
        
        if total_components == 0:
            return 1.0
        
        return matched_components / total_components

    def extract_io_tags(self, project) -> List[Dict[str, Any]]:
        """Extract I/O tag definitions from L5X project.
        
        Returns a list of dictionaries containing:
        - name: Tag name
        - direction: 'Input' or 'Output' (determined by tag name patterns)
        - data_type: Data type (BOOL, REAL, etc.)
        - description: Tag description if available
        - scope: Tag scope (Controller or Program)
        """
        io_tags = []
        
        # Extract controller tags
        if hasattr(project.controller, 'tags'):
            for tag_name in project.controller.tags.names:
                try:
                    tag_data = project.controller.tags[tag_name]
                    io_info = self._extract_io_tag_info(tag_name, tag_data, TagScope.CONTROLLER)
                    if io_info:
                        io_tags.append(io_info)
                except Exception as e:
                    logger.warning(f"Could not extract I/O tag {tag_name}: {e}")
        
        # Extract program tags
        if hasattr(project, 'programs'):
            for program in project.programs:
                if hasattr(program, 'tags'):
                    for tag_name in program.tags.names:
                        try:
                            tag_data = program.tags[tag_name]
                            io_info = self._extract_io_tag_info(tag_name, tag_data, TagScope.PROGRAM)
                            if io_info:
                                io_tags.append(io_info)
                        except Exception as e:
                            logger.warning(f"Could not extract I/O tag {tag_name}: {e}")
        
        return io_tags
    
    def _extract_io_tag_info(self, name: str, tag_data, scope: TagScope) -> Optional[Dict[str, Any]]:
        """Extract I/O tag information and determine direction."""
        try:
            # Get basic tag info
            data_type = getattr(tag_data, 'data_type', 'UNKNOWN')
            clean_type = get_data_type(data_type)
            description = getattr(tag_data, 'description', None)
            
            # Determine direction based on tag name patterns
            direction = self._determine_io_direction(name)
            
            # Only include tags that appear to be I/O related
            if direction:
                return {
                    'name': name,
                    'direction': direction,
                    'data_type': clean_type,
                    'description': description,
                    'scope': scope.value
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting I/O tag {name}: {e}")
            return None
    
    def _determine_io_direction(self, tag_name: str) -> Optional[str]:
        """Determine if a tag is an input or output based on naming patterns.
        
        Common patterns:
        - Input tags: often start with 'I', 'IN', 'AI', 'DI', 'SI' (Sensor Input)
        - Output tags: often start with 'O', 'OUT', 'AO', 'DO', 'SO' (Setpoint Output)
        - Feedback tags: often contain 'FB', 'FEEDBACK', 'PV' (Process Value)
        - Setpoint tags: often contain 'SP', 'SETPOINT', 'CMD' (Command)
        """
        tag_upper = tag_name.upper()
        
        # Input patterns
        input_patterns = [
            'I_', 'IN_', 'AI_', 'DI_', 'SI_',  # Direct input patterns
            'SENSOR', 'FEEDBACK', 'FB_', 'PV_',  # Sensor/feedback patterns
            'TEMP', 'PRESSURE', 'FLOW', 'LEVEL',  # Common sensor types
            'STATUS', 'ALARM', 'FAULT'  # Status indicators
        ]
        
        # Output patterns
        output_patterns = [
            'O_', 'OUT_', 'AO_', 'DO_', 'SO_',  # Direct output patterns
            'SETPOINT', 'SP_', 'CMD_', 'CONTROL',  # Control patterns
            'VALVE', 'PUMP', 'MOTOR', 'HEATER',  # Common actuator types
            'ENABLE', 'RESET', 'START', 'STOP'  # Control commands
        ]
        
        # Check input patterns
        for pattern in input_patterns:
            if tag_upper.startswith(pattern) or pattern in tag_upper:
                return 'Input'
        
        # Check output patterns
        for pattern in output_patterns:
            if tag_upper.startswith(pattern) or pattern in tag_upper:
                return 'Output'
        
        # If no clear pattern, try to infer from context
        # Tags ending with numbers are often I/O (e.g., AI_001, DO_002)
        if any(char.isdigit() for char in tag_name):
            # Check if it looks like a module tag (e.g., Local:1:I.Data.0)
            if ':' in tag_name and any(part.isdigit() for part in tag_name.split(':')):
                # Try to determine from the module type
                if any(module_type in tag_upper for module_type in ['I.', 'AI.', 'DI.']):
                    return 'Input'
                elif any(module_type in tag_upper for module_type in ['O.', 'AO.', 'DO.']):
                    return 'Output'
        
        # If we can't determine, return None (not an I/O tag)
        return None 