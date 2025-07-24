"""
Interactive querying API for IR components.
Provides convenient methods for exploring and analyzing IR structure.
"""

import re
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict

from .models import (
    IRProject, IRController, IRProgram, IRRoutine, IRTag, IRDataType,
    IRFunctionBlock, TagScope, RoutineType
)


class InteractiveIRQuery:
    """Interactive query interface for IR components."""
    
    def __init__(self, ir_project: IRProject):
        """
        Initialize the query interface with an IR project.
        
        Args:
            ir_project: The IR project to query
        """
        self.ir_project = ir_project
        self._build_indexes()
    
    def _build_indexes(self):
        """Build search indexes for efficient querying."""
        # Tag indexes
        self._tag_index = {}
        self._tag_by_prefix = defaultdict(list)
        self._tag_by_type = defaultdict(list)
        self._tag_by_scope = defaultdict(list)
        
        # Program indexes
        self._program_index = {}
        self._routine_index = {}
        
        # Data type indexes
        self._data_type_index = {}
        
        # Function block indexes
        self._function_block_index = {}
        
        # Build tag indexes
        for tag in self.ir_project.controller.tags:
            self._tag_index[tag.name] = tag
            self._tag_by_scope[tag.scope].append(tag)
            
            # Index by prefix (case-insensitive)
            for prefix in self._get_tag_prefixes(tag.name):
                self._tag_by_prefix[prefix.lower()].append(tag)
            
            # Index by data type
            self._tag_by_type[tag.data_type].append(tag)
        
        # Build program indexes
        for program in self.ir_project.programs:
            self._program_index[program.name] = program
            
            # Index program tags
            for tag in program.tags:
                self._tag_index[tag.name] = tag
                self._tag_by_scope[tag.scope].append(tag)
                
                for prefix in self._get_tag_prefixes(tag.name):
                    self._tag_by_prefix[prefix.lower()].append(tag)
                
                self._tag_by_type[tag.data_type].append(tag)
            
            # Build routine indexes
            for routine in program.routines:
                routine_key = f"{program.name}.{routine.name}"
                self._routine_index[routine_key] = routine
                self._routine_index[routine.name] = routine
        
        # Build data type indexes
        for data_type in self.ir_project.controller.data_types:
            self._data_type_index[data_type.name] = data_type
        
        # Build function block indexes
        for fb in self.ir_project.controller.function_blocks:
            self._function_block_index[fb.name] = fb
    
    def _get_tag_prefixes(self, tag_name: str) -> List[str]:
        """Extract possible prefixes from a tag name."""
        prefixes = []
        parts = tag_name.split('_')
        
        for i in range(1, len(parts) + 1):
            prefixes.append('_'.join(parts[:i]))
        
        return prefixes
    
    def find_tags_by_prefix(self, prefix: str) -> List[IRTag]:
        """
        Find tags that start with the given prefix.
        
        Args:
            prefix: The prefix to search for (case-insensitive)
            
        Returns:
            List of matching tags
        """
        prefix_lower = prefix.lower()
        matches = []
        
        for tag_prefix, tags in self._tag_by_prefix.items():
            if tag_prefix.startswith(prefix_lower):
                matches.extend(tags)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_matches = []
        for tag in matches:
            if tag.name not in seen:
                seen.add(tag.name)
                unique_matches.append(tag)
        
        return unique_matches
    
    def find_tags_by_type(self, data_type: str) -> List[IRTag]:
        """
        Find tags with the specified data type.
        
        Args:
            data_type: The data type to search for
            
        Returns:
            List of matching tags
        """
        return self._tag_by_type.get(data_type, [])
    
    def find_tags_by_scope(self, scope: TagScope) -> List[IRTag]:
        """
        Find tags with the specified scope.
        
        Args:
            scope: The scope to search for
            
        Returns:
            List of matching tags
        """
        return self._tag_by_scope.get(scope, [])
    
    def get_tag(self, tag_name: str) -> Optional[IRTag]:
        """
        Get a specific tag by name.
        
        Args:
            tag_name: The name of the tag
            
        Returns:
            The tag if found, None otherwise
        """
        return self._tag_index.get(tag_name)
    
    def get_control_flow(self, routine_name: str, program_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get control flow information for a routine.
        
        Args:
            routine_name: The name of the routine
            program_name: Optional program name for disambiguation
            
        Returns:
            Control flow information if found, None otherwise
        """
        from .export_ir import ControlFlowAnalyzer
        
        routine = None
        if program_name:
            routine_key = f"{program_name}.{routine_name}"
            routine = self._routine_index.get(routine_key)
        else:
            routine = self._routine_index.get(routine_name)
        
        if routine:
            analyzer = ControlFlowAnalyzer()
            return analyzer.analyze_routine_control_flow(routine)
        
        return None
    
    def get_dependencies(self, tag_name: str) -> Dict[str, Any]:
        """
        Get dependencies for a specific tag.
        
        Args:
            tag_name: The name of the tag
            
        Returns:
            Dictionary containing dependency information
        """
        from .export_ir import InteractionAnalyzer
        
        analyzer = InteractionAnalyzer()
        analyzer._build_tag_maps(self.ir_project)
        
        dependencies = {
            "tag_name": tag_name,
            "referenced_by": list(analyzer.tag_references.get(tag_name, set())),
            "tag_info": self.get_tag(tag_name)
        }
        
        return dependencies
    
    def get_program(self, program_name: str) -> Optional[IRProgram]:
        """
        Get a specific program by name.
        
        Args:
            program_name: The name of the program
            
        Returns:
            The program if found, None otherwise
        """
        return self._program_index.get(program_name)
    
    def get_routine(self, routine_name: str, program_name: Optional[str] = None) -> Optional[IRRoutine]:
        """
        Get a specific routine by name.
        
        Args:
            routine_name: The name of the routine
            program_name: Optional program name for disambiguation
            
        Returns:
            The routine if found, None otherwise
        """
        if program_name:
            routine_key = f"{program_name}.{routine_name}"
            return self._routine_index.get(routine_key)
        else:
            return self._routine_index.get(routine_name)
    
    def get_data_type(self, data_type_name: str) -> Optional[IRDataType]:
        """
        Get a specific data type by name.
        
        Args:
            data_type_name: The name of the data type
            
        Returns:
            The data type if found, None otherwise
        """
        return self._data_type_index.get(data_type_name)
    
    def get_function_block(self, fb_name: str) -> Optional[IRFunctionBlock]:
        """
        Get a specific function block by name.
        
        Args:
            fb_name: The name of the function block
            
        Returns:
            The function block if found, None otherwise
        """
        return self._function_block_index.get(fb_name)
    
    def search_tags(self, pattern: str, case_sensitive: bool = False) -> List[IRTag]:
        """
        Search tags using a regex pattern.
        
        Args:
            pattern: The regex pattern to search for
            case_sensitive: Whether the search should be case sensitive
            
        Returns:
            List of matching tags
        """
        flags = 0 if case_sensitive else re.IGNORECASE
        regex = re.compile(pattern, flags)
        
        matches = []
        for tag in self._tag_index.values():
            if regex.search(tag.name):
                matches.append(tag)
        
        return matches
    
    def get_project_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the entire project.
        
        Returns:
            Dictionary containing project summary
        """
        summary = {
            "controller": {
                "name": self.ir_project.controller.name,
                "description": self.ir_project.controller.description
            },
            "tags": {
                "controller_tags": len(self.ir_project.controller.tags),
                "program_tags": sum(len(p.tags) for p in self.ir_project.programs),
                "total_tags": len(self._tag_index)
            },
            "programs": {
                "count": len(self.ir_project.programs),
                "names": [p.name for p in self.ir_project.programs]
            },
            "routines": {
                "count": sum(len(p.routines) for p in self.ir_project.programs),
                "by_type": defaultdict(int)
            },
            "data_types": {
                "count": len(self.ir_project.controller.data_types),
                "names": [dt.name for dt in self.ir_project.controller.data_types]
            },
            "function_blocks": {
                "count": len(self.ir_project.controller.function_blocks),
                "names": [fb.name for fb in self.ir_project.controller.function_blocks]
            }
        }
        
        # Count routines by type
        for program in self.ir_project.programs:
            for routine in program.routines:
                summary["routines"]["by_type"][routine.routine_type.value] += 1
        
        return summary
    
    def get_tag_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about tags in the project.
        
        Returns:
            Dictionary containing tag statistics
        """
        stats = {
            "by_scope": defaultdict(int),
            "by_type": defaultdict(int),
            "by_prefix": defaultdict(int)
        }
        
        for tag in self._tag_index.values():
            stats["by_scope"][tag.scope.value] += 1
            stats["by_type"][tag.data_type] += 1
            
            # Count by common prefixes
            if tag.name:
                prefix = tag.name.split('_')[0] if '_' in tag.name else tag.name
                stats["by_prefix"][prefix] += 1
        
        return stats
    
    def find_cross_references(self, tag_name: str) -> Dict[str, Any]:
        """
        Find all cross-references for a tag across programs and routines.
        
        Args:
            tag_name: The name of the tag to search for
            
        Returns:
            Dictionary containing cross-reference information
        """
        references = {
            "tag_name": tag_name,
            "programs": [],
            "routines": []
        }
        
        tag_name_lower = tag_name.lower()
        
        for program in self.ir_project.programs:
            program_refs = []
            
            for routine in program.routines:
                routine_refs = []
                content_lower = routine.content.lower()
                
                if tag_name_lower in content_lower:
                    routine_refs.append({
                        "routine_name": routine.name,
                        "routine_type": routine.routine_type.value,
                        "content_snippet": self._extract_context(routine.content, tag_name)
                    })
                
                if routine_refs:
                    program_refs.append({
                        "routine_name": routine.name,
                        "references": routine_refs
                    })
            
            if program_refs:
                references["programs"].append({
                    "program_name": program.name,
                    "routines": program_refs
                })
        
        return references
    
    def _extract_context(self, content: str, tag_name: str, context_lines: int = 2) -> List[str]:
        """
        Extract context around tag references.
        
        Args:
            content: The content to search in
            tag_name: The tag name to find
            context_lines: Number of lines of context to include
            
        Returns:
            List of context lines
        """
        lines = content.split('\n')
        context = []
        
        for i, line in enumerate(lines):
            if tag_name.lower() in line.lower():
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                context.extend(lines[start:end])
        
        return context[:10]  # Limit to 10 lines max
    
    def export_selected_components(self, components: List[str], output_path: str) -> Dict[str, Any]:
        """
        Export selected components to JSON using the export_ir module.
        
        Args:
            components: List of components to export
            output_path: Path to the output JSON file
            
        Returns:
            Dictionary containing the exported data
        """
        from .export_ir import export_ir_to_json
        
        return export_ir_to_json(
            ir_project=self.ir_project,
            output_path=output_path,
            include=components,
            pretty_print=True
        ) 