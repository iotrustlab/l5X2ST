"""
Tests for the IR export functionality.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from l5x_st_compiler.export_ir import (
    export_ir_to_json, ControlFlowAnalyzer, InteractionAnalyzer,
    ExportComponent
)
from l5x_st_compiler.models import (
    IRProject, IRController, IRProgram, IRRoutine, IRTag,
    IRDataType, IRFunctionBlock, TagScope, RoutineType
)
from l5x_st_compiler.query import InteractiveIRQuery


class TestControlFlowAnalyzer:
    """Test the ControlFlowAnalyzer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = ControlFlowAnalyzer()
    
    def test_analyze_st_control_flow(self):
        """Test ST control flow analysis."""
        st_content = """
        IF LIT101 > 800 THEN
            P101 := ON;
        ELSIF LIT101 > 600 THEN
            P101 := OFF;
        ELSE
            P101 := P101;
        END_IF;
        """
        
        routine = IRRoutine(
            name="TestRoutine",
            routine_type=RoutineType.ST,
            content=st_content
        )
        
        result = self.analyzer.analyze_routine_control_flow(routine)
        
        assert result["type"] == "structured_text"
        assert len(result["control_flow"]) >= 3  # IF, ELSIF, ELSE
    
    def test_analyze_ladder_control_flow(self):
        """Test ladder logic control flow analysis."""
        ladder_content = """
        |--[LIT101]--[>800]--(P101)--;
        |--[LIT102]--[<600]--(P102)--;
        """
        
        routine = IRRoutine(
            name="TestRoutine",
            routine_type=RoutineType.RLL,
            content=ladder_content
        )
        
        result = self.analyzer.analyze_routine_control_flow(routine)
        
        assert result["type"] == "ladder_logic"
        assert len(result["control_flow"]) >= 1


class TestInteractionAnalyzer:
    """Test the InteractionAnalyzer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = InteractionAnalyzer()
    
    def test_analyze_interactions(self):
        """Test interaction analysis."""
        # Create a simple IR project for testing
        controller = IRController(
            name="TestController",
            tags=[
                IRTag(name="GlobalTag1", data_type="BOOL", scope=TagScope.CONTROLLER),
                IRTag(name="GlobalTag2", data_type="INT", scope=TagScope.CONTROLLER)
            ]
        )
        
        program1 = IRProgram(
            name="Program1",
            tags=[
                IRTag(name="LocalTag1", data_type="BOOL", scope=TagScope.PROGRAM),
                IRTag(name="GlobalTag1", data_type="BOOL", scope=TagScope.CONTROLLER)  # Shared
            ],
            routines=[
                IRRoutine(
                    name="MainRoutine",
                    routine_type=RoutineType.ST,
                    content="GlobalTag1 := ON; LocalTag1 := GlobalTag2;"
                )
            ]
        )
        
        program2 = IRProgram(
            name="Program2",
            tags=[
                IRTag(name="LocalTag2", data_type="BOOL", scope=TagScope.PROGRAM),
                IRTag(name="GlobalTag1", data_type="BOOL", scope=TagScope.CONTROLLER)  # Shared
            ],
            routines=[
                IRRoutine(
                    name="MainRoutine",
                    routine_type=RoutineType.ST,
                    content="GlobalTag1 := OFF;"
                )
            ]
        )
        
        ir_project = IRProject(
            controller=controller,
            programs=[program1, program2]
        )
        
        result = self.analyzer.analyze_interactions(ir_project)
        
        assert "interactions" in result
        assert len(result["interactions"]) >= 1  # Should find cross-program interaction via GlobalTag1


class TestExportIR:
    """Test the export_ir_to_json function."""
    
    def test_export_tags_only(self):
        """Test exporting only tags."""
        controller = IRController(
            name="TestController",
            tags=[
                IRTag(name="Tag1", data_type="BOOL", scope=TagScope.CONTROLLER),
                IRTag(name="Tag2", data_type="INT", scope=TagScope.CONTROLLER)
            ]
        )
        
        ir_project = IRProject(controller=controller)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = f.name
        
        try:
            result = export_ir_to_json(
                ir_project=ir_project,
                output_path=output_path,
                include=["tags"],
                pretty_print=True
            )
            
            assert "tags" in result
            assert "metadata" in result
            assert result["tags"]["summary"]["total_controller_tags"] == 2
            
            # Verify file was created
            assert Path(output_path).exists()
            
            # Verify JSON is valid
            with open(output_path, 'r') as f:
                data = json.load(f)
                assert "tags" in data
                
        finally:
            Path(output_path).unlink(missing_ok=True)
    
    def test_export_all_components(self):
        """Test exporting all components."""
        controller = IRController(
            name="TestController",
            tags=[
                IRTag(name="Tag1", data_type="BOOL", scope=TagScope.CONTROLLER)
            ],
            data_types=[
                IRDataType(name="TestType", base_type="BOOL")
            ],
            function_blocks=[
                IRFunctionBlock(name="TestFB", description="Test function block")
            ]
        )
        
        program = IRProgram(
            name="TestProgram",
            routines=[
                IRRoutine(
                    name="MainRoutine",
                    routine_type=RoutineType.ST,
                    content="Tag1 := ON;"
                )
            ]
        )
        
        ir_project = IRProject(
            controller=controller,
            programs=[program]
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = f.name
        
        try:
            result = export_ir_to_json(
                ir_project=ir_project,
                output_path=output_path,
                include=["tags", "control_flow", "data_types", "function_blocks", "interactions", "routines", "programs"],
                pretty_print=True
            )
            
            # Check that all components are present
            assert "tags" in result
            assert "control_flow" in result
            assert "data_types" in result
            assert "function_blocks" in result
            assert "interactions" in result
            assert "routines" in result
            assert "programs" in result
            
        finally:
            Path(output_path).unlink(missing_ok=True)


class TestInteractiveIRQuery:
    """Test the InteractiveIRQuery class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        controller = IRController(
            name="TestController",
            tags=[
                IRTag(name="LIT101", data_type="REAL", scope=TagScope.CONTROLLER),
                IRTag(name="P101", data_type="BOOL", scope=TagScope.CONTROLLER),
                IRTag(name="TEMP_001", data_type="REAL", scope=TagScope.CONTROLLER)
            ]
        )
        
        program = IRProgram(
            name="TestProgram",
            tags=[
                IRTag(name="LocalVar1", data_type="BOOL", scope=TagScope.PROGRAM)
            ],
            routines=[
                IRRoutine(
                    name="MainRoutine",
                    routine_type=RoutineType.ST,
                    content="LIT101 := 100.0; P101 := ON;"
                )
            ]
        )
        
        self.ir_project = IRProject(
            controller=controller,
            programs=[program]
        )
        
        self.query = InteractiveIRQuery(self.ir_project)
    
    def test_find_tags_by_prefix(self):
        """Test finding tags by prefix."""
        lit_tags = self.query.find_tags_by_prefix("LIT")
        assert len(lit_tags) == 1
        assert lit_tags[0].name == "LIT101"
        
        temp_tags = self.query.find_tags_by_prefix("TEMP")
        assert len(temp_tags) == 1
        assert temp_tags[0].name == "TEMP_001"
    
    def test_get_tag(self):
        """Test getting a specific tag."""
        tag = self.query.get_tag("LIT101")
        assert tag is not None
        assert tag.name == "LIT101"
        assert tag.data_type == "REAL"
        
        # Test non-existent tag
        tag = self.query.get_tag("NonExistentTag")
        assert tag is None
    
    def test_get_project_summary(self):
        """Test getting project summary."""
        summary = self.query.get_project_summary()
        
        assert summary["controller"]["name"] == "TestController"
        assert summary["tags"]["total_tags"] == 4  # 3 controller + 1 program
        assert summary["programs"]["count"] == 1
        assert summary["routines"]["count"] == 1
    
    def test_get_tag_statistics(self):
        """Test getting tag statistics."""
        stats = self.query.get_tag_statistics()
        
        assert "by_scope" in stats
        assert "by_type" in stats
        assert "by_prefix" in stats
        
        # Check that we have both controller and program scoped tags
        assert TagScope.CONTROLLER.value in stats["by_scope"]
        assert TagScope.PROGRAM.value in stats["by_scope"]
    
    def test_get_control_flow(self):
        """Test getting control flow for a routine."""
        control_flow = self.query.get_control_flow("MainRoutine", "TestProgram")
        
        assert control_flow is not None
        assert control_flow["type"] == "structured_text"
    
    def test_get_dependencies(self):
        """Test getting tag dependencies."""
        dependencies = self.query.get_dependencies("LIT101")
        
        assert "tag_name" in dependencies
        assert "referenced_by" in dependencies
        assert "tag_info" in dependencies
        assert dependencies["tag_name"] == "LIT101"


if __name__ == "__main__":
    pytest.main([__file__]) 