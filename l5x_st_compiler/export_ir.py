"""
Export Intermediate Representation (IR) components to structured JSON files.
This module supports exporting selected components for downstream semantic mapping.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
from datetime import datetime
from enum import Enum

from .models import (
    IRProject, IRController, IRProgram, IRRoutine, IRTag, IRDataType,
    IRFunctionBlock, TagScope, RoutineType
)

logger = logging.getLogger(__name__)


class ExportComponent(Enum):
    """Components that can be exported."""
    TAGS = "tags"
    CONTROL_FLOW = "control_flow"
    DATA_TYPES = "data_types"
    FUNCTION_BLOCKS = "function_blocks"
    INTERACTIONS = "interactions"
    ROUTINES = "routines"
    PROGRAMS = "programs"


class ControlFlowAnalyzer:
    """Analyzes control flow in routines and programs."""
    
    def __init__(self):
        self.branch_keywords = {
            'IF', 'THEN', 'ELSE', 'ELSIF', 'END_IF',
            'CASE', 'OF', 'END_CASE',
            'FOR', 'TO', 'DO', 'END_FOR',
            'WHILE', 'END_WHILE',
            'REPEAT', 'UNTIL', 'END_REPEAT'
        }
        
        self.action_keywords = {
            ':=', '=', 'SET', 'RESET', 'TON', 'TOF', 'CTU', 'CTD'
        }
    
    def analyze_routine_control_flow(self, routine: IRRoutine) -> Dict[str, Any]:
        """Analyze control flow in a single routine."""
        if routine.routine_type == RoutineType.ST:
            return self._analyze_st_control_flow(routine.content)
        elif routine.routine_type == RoutineType.RLL:
            return self._analyze_ladder_control_flow(routine.content)
        elif routine.routine_type == RoutineType.FBD:
            return self._analyze_fbd_control_flow(routine.content)
        else:
            return {"type": "unknown", "content": routine.content}
    
    def _analyze_st_control_flow(self, content: str) -> Dict[str, Any]:
        """Analyze Structured Text control flow."""
        lines = content.split('\n')
        control_flow = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('//'):
                continue
                
            # Detect IF-THEN-ELSE structures
            if line.upper().startswith('IF '):
                condition = line[3:].strip()
                if condition.endswith('THEN'):
                    condition = condition[:-4].strip()
                control_flow.append({
                    "type": "branch",
                    "condition": condition,
                    "actions": []
                })
            elif line.upper().startswith('ELSIF '):
                condition = line[6:].strip()
                if condition.endswith('THEN'):
                    condition = condition[:-4].strip()
                control_flow.append({
                    "type": "branch",
                    "condition": condition,
                    "actions": []
                })
            elif line.upper() == 'ELSE':
                control_flow.append({
                    "type": "branch",
                    "condition": "else",
                    "actions": []
                })
            elif line.upper() in ['END_IF', 'END_CASE', 'END_FOR', 'END_WHILE', 'END_REPEAT']:
                continue
            elif ':' in line and any(keyword in line.upper() for keyword in self.action_keywords):
                # This is likely an assignment or action
                if control_flow:
                    control_flow[-1]["actions"].append(line.strip())
                else:
                    control_flow.append({
                        "type": "action",
                        "actions": [line.strip()]
                    })
        
        return {
            "type": "structured_text",
            "control_flow": control_flow
        }
    
    def _analyze_ladder_control_flow(self, content: str) -> Dict[str, Any]:
        """Analyze Ladder Logic control flow."""
        # Simplified ladder analysis - extract rung conditions and outputs
        lines = content.split('\n')
        control_flow = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            
            # Look for rung patterns (simplified)
            if '|' in line and '--' in line:
                # This looks like a ladder rung
                parts = line.split('--')
                if len(parts) >= 2:
                    condition = parts[0].replace('|', '').strip()
                    action = parts[1].replace('|', '').strip()
                    control_flow.append({
                        "type": "rung",
                        "condition": condition,
                        "actions": [action] if action else []
                    })
        
        return {
            "type": "ladder_logic",
            "control_flow": control_flow
        }
    
    def _analyze_fbd_control_flow(self, content: str) -> Dict[str, Any]:
        """Analyze Function Block Diagram control flow."""
        # Simplified FBD analysis
        return {
            "type": "function_block_diagram",
            "content": content,
            "note": "FBD control flow analysis requires detailed parsing of block connections"
        }


class InteractionAnalyzer:
    """Analyzes cross-program and cross-controller interactions."""
    
    def __init__(self):
        self.tag_references: Dict[str, Set[str]] = {}
        self.program_tags: Dict[str, Set[str]] = {}
    
    def analyze_interactions(self, ir_project: IRProject) -> Dict[str, Any]:
        """Analyze interactions between programs and controllers."""
        # Build tag reference maps
        self._build_tag_maps(ir_project)
        
        interactions = []
        
        # Analyze cross-program interactions
        for program in ir_project.programs:
            program_tags = self.program_tags.get(program.name, set())
            
            for other_program in ir_project.programs:
                if program.name == other_program.name:
                    continue
                    
                other_tags = self.program_tags.get(other_program.name, set())
                shared_tags = program_tags.intersection(other_tags)
                
                if shared_tags:
                    interactions.append({
                        "source": f"{ir_project.controller.name}.{program.name}",
                        "target": f"{ir_project.controller.name}.{other_program.name}",
                        "via": list(shared_tags),
                        "type": "cross_program"
                    })
        
        # Analyze controller-level tag usage
        controller_tags = {tag.name for tag in ir_project.controller.tags}
        for program in ir_project.programs:
            program_tags = self.program_tags.get(program.name, set())
            used_controller_tags = program_tags.intersection(controller_tags)
            
            if used_controller_tags:
                interactions.append({
                    "source": f"{ir_project.controller.name}.{program.name}",
                    "target": f"{ir_project.controller.name}",
                    "via": list(used_controller_tags),
                    "type": "program_to_controller"
                })
        
        return {
            "interactions": interactions,
            "summary": {
                "total_interactions": len(interactions),
                "cross_program_interactions": len([i for i in interactions if i["type"] == "cross_program"]),
                "program_controller_interactions": len([i for i in interactions if i["type"] == "program_to_controller"])
            }
        }
    
    def _build_tag_maps(self, ir_project: IRProject):
        """Build maps of tag references and program ownership."""
        # Initialize maps
        self.tag_references.clear()
        self.program_tags.clear()
        
        # Map controller tags
        for tag in ir_project.controller.tags:
            self.tag_references[tag.name] = set()
        
        # Map program tags and analyze references
        for program in ir_project.programs:
            program_tag_names = set()
            
            # Add program's own tags
            for tag in program.tags:
                program_tag_names.add(tag.name)
                self.tag_references[tag.name] = set()
            
            # Add local variables
            for tag in program.local_variables:
                program_tag_names.add(tag.name)
                self.tag_references[tag.name] = set()
            
            # Analyze routine content for tag references
            for routine in program.routines:
                self._analyze_routine_references(routine, program.name)
            
            self.program_tags[program.name] = program_tag_names
    
    def _analyze_routine_references(self, routine: IRRoutine, program_name: str):
        """Analyze tag references in routine content."""
        content = routine.content.lower()
        
        # Simple pattern matching for tag references
        # This is a simplified approach - in practice, you'd want proper parsing
        for tag_name in self.tag_references.keys():
            if tag_name.lower() in content:
                self.tag_references[tag_name].add(program_name)


def export_ir_to_json(
    ir_project: IRProject,
    output_path: str,
    include: Optional[List[str]] = None,
    pretty_print: bool = True
) -> Dict[str, Any]:
    """
    Export selected components of the IR to JSON format.
    
    Args:
        ir_project: The IR project to export
        output_path: Path to the output JSON file
        include: List of components to include (tags, control_flow, data_types, etc.)
        pretty_print: Whether to format JSON with indentation
        
    Returns:
        Dictionary containing the exported data
    """
    if include is None:
        include = ["tags", "control_flow"]
    
    # Convert string components to enum values
    export_components = []
    for component in include:
        try:
            export_components.append(ExportComponent(component))
        except ValueError:
            logger.warning(f"Unknown export component: {component}")
    
    # Initialize export data
    export_data = {
        "metadata": {
            "export_time": datetime.now().isoformat(),
            "source_controller": ir_project.controller.name,
            "exported_components": include,
            "total_programs": len(ir_project.programs),
            "total_routines": sum(len(p.routines) for p in ir_project.programs)
        }
    }
    
    # Export tags
    if ExportComponent.TAGS in export_components:
        export_data["tags"] = _export_tags(ir_project)
    
    # Export data types
    if ExportComponent.DATA_TYPES in export_components:
        export_data["data_types"] = _export_data_types(ir_project)
    
    # Export function blocks
    if ExportComponent.FUNCTION_BLOCKS in export_components:
        export_data["function_blocks"] = _export_function_blocks(ir_project)
    
    # Export control flow
    if ExportComponent.CONTROL_FLOW in export_components:
        export_data["control_flow"] = _export_control_flow(ir_project)
    
    # Export routines
    if ExportComponent.ROUTINES in export_components:
        export_data["routines"] = _export_routines(ir_project)
    
    # Export programs
    if ExportComponent.PROGRAMS in export_components:
        export_data["programs"] = _export_programs(ir_project)
    
    # Export interactions
    if ExportComponent.INTERACTIONS in export_components:
        analyzer = InteractionAnalyzer()
        export_data["interactions"] = analyzer.analyze_interactions(ir_project)
    
    # Write to file
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        if pretty_print:
            json.dump(export_data, f, indent=2, default=str)
        else:
            json.dump(export_data, f, default=str)
    
    logger.info(f"Exported IR to {output_path}")
    return export_data


def _export_tags(ir_project: IRProject) -> Dict[str, Any]:
    """Export tag information."""
    controller_tags = []
    for tag in ir_project.controller.tags:
        controller_tags.append({
            "name": tag.name,
            "data_type": tag.data_type,
            "scope": tag.scope.value,
            "value": tag.value,
            "description": tag.description,
            "external_access": tag.external_access,
            "radix": tag.radix,
            "constant": tag.constant,
            "alias_for": tag.alias_for,
            "array_dimensions": tag.array_dimensions,
            "initial_value": tag.initial_value,
            "user_defined_type": tag.user_defined_type
        })
    
    program_tags = {}
    for program in ir_project.programs:
        program_tags[program.name] = []
        for tag in program.tags:
            program_tags[program.name].append({
                "name": tag.name,
                "data_type": tag.data_type,
                "scope": tag.scope.value,
                "value": tag.value,
                "description": tag.description,
                "external_access": tag.external_access,
                "radix": tag.radix,
                "constant": tag.constant,
                "alias_for": tag.alias_for,
                "array_dimensions": tag.array_dimensions,
                "initial_value": tag.initial_value,
                "user_defined_type": tag.user_defined_type
            })
    
    return {
        "controller_tags": controller_tags,
        "program_tags": program_tags,
        "summary": {
            "total_controller_tags": len(controller_tags),
            "total_program_tags": sum(len(tags) for tags in program_tags.values())
        }
    }


def _export_data_types(ir_project: IRProject) -> Dict[str, Any]:
    """Export data type information."""
    data_types = []
    for dt in ir_project.controller.data_types:
        members = []
        for member in dt.members:
            members.append({
                "name": member.name,
                "data_type": member.data_type,
                "description": member.description,
                "radix": member.radix,
                "external_access": member.external_access,
                "array_dimensions": member.array_dimensions,
                "initial_value": member.initial_value
            })
        
        data_types.append({
            "name": dt.name,
            "base_type": dt.base_type,
            "members": members,
            "description": dt.description,
            "is_enum": dt.is_enum,
            "enum_values": dt.enum_values
        })
    
    return {
        "data_types": data_types,
        "summary": {
            "total_data_types": len(data_types)
        }
    }


def _export_function_blocks(ir_project: IRProject) -> Dict[str, Any]:
    """Export function block information."""
    function_blocks = []
    for fb in ir_project.controller.function_blocks:
        parameters = []
        for param in fb.parameters:
            parameters.append({
                "name": param.name,
                "data_type": param.data_type,
                "parameter_type": param.parameter_type,
                "description": param.description,
                "required": param.required,
                "array_dimensions": param.array_dimensions,
                "initial_value": param.initial_value
            })
        
        local_variables = []
        for var in fb.local_variables:
            local_variables.append({
                "name": var.name,
                "data_type": var.data_type,
                "parameter_type": var.parameter_type,
                "description": var.description,
                "required": var.required,
                "array_dimensions": var.array_dimensions,
                "initial_value": var.initial_value
            })
        
        function_blocks.append({
            "name": fb.name,
            "description": fb.description,
            "parameters": parameters,
            "local_variables": local_variables,
            "implementation": fb.implementation
        })
    
    return {
        "function_blocks": function_blocks,
        "summary": {
            "total_function_blocks": len(function_blocks)
        }
    }


def _export_control_flow(ir_project: IRProject) -> Dict[str, Any]:
    """Export control flow information."""
    analyzer = ControlFlowAnalyzer()
    
    routines = {}
    for program in ir_project.programs:
        routines[program.name] = {}
        for routine in program.routines:
            routines[program.name][routine.name] = {
                "type": routine.routine_type.value,
                "description": routine.description,
                "control_flow": analyzer.analyze_routine_control_flow(routine)
            }
    
    return {
        "routines": routines,
        "summary": {
            "total_programs": len(routines),
            "total_routines": sum(len(r) for r in routines.values())
        }
    }


def _export_routines(ir_project: IRProject) -> Dict[str, Any]:
    """Export routine information."""
    routines = {}
    for program in ir_project.programs:
        routines[program.name] = []
        for routine in program.routines:
            local_vars = []
            for var in routine.local_variables:
                local_vars.append({
                    "name": var.name,
                    "data_type": var.data_type,
                    "scope": var.scope.value,
                    "value": var.value,
                    "description": var.description
                })
            
            parameters = []
            for param in routine.parameters:
                parameters.append({
                    "name": param.name,
                    "data_type": param.data_type,
                    "parameter_type": param.parameter_type,
                    "description": param.description,
                    "required": param.required
                })
            
            routines[program.name].append({
                "name": routine.name,
                "type": routine.routine_type.value,
                "description": routine.description,
                "content": routine.content,
                "local_variables": local_vars,
                "parameters": parameters,
                "return_type": routine.return_type
            })
    
    return {
        "routines": routines,
        "summary": {
            "total_programs": len(routines),
            "total_routines": sum(len(r) for r in routines.values())
        }
    }


def _export_programs(ir_project: IRProject) -> Dict[str, Any]:
    """Export program information."""
    programs = []
    for program in ir_project.programs:
        routine_names = [r.name for r in program.routines]
        
        programs.append({
            "name": program.name,
            "description": program.description,
            "main_routine": program.main_routine,
            "routines": routine_names,
            "tag_count": len(program.tags),
            "local_variable_count": len(program.local_variables)
        })
    
    return {
        "programs": programs,
        "summary": {
            "total_programs": len(programs)
        }
    } 