#!/usr/bin/env python3
"""
Example script demonstrating the new IR export functionality and interactive querying API.
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import the l5x_st_compiler
sys.path.insert(0, str(Path(__file__).parent.parent))

from l5x_st_compiler import IRConverter, export_ir_to_json, InteractiveIRQuery


def main():
    """Demonstrate the new IR export and querying functionality."""
    
    # Check if an L5X file was provided
    if len(sys.argv) < 2:
        print("Usage: python ir_export_example.py <path_to_l5x_file>")
        print("Example: python ir_export_example.py sampledata/P1.L5X")
        return
    
    l5x_file = sys.argv[1]
    
    if not os.path.exists(l5x_file):
        print(f"Error: File {l5x_file} not found.")
        return
    
    try:
        print(f"📖 Loading L5X file: {l5x_file}")
        
        # Import l5x module (you'll need to install it)
        try:
            import l5x
        except ImportError:
            print("Error: l5x module not found. Please install it with: pip install l5x")
            return
        
        # Load the L5X project
        project = l5x.Project(l5x_file)
        
        # Convert to IR
        print("🔄 Converting to Intermediate Representation...")
        ir_converter = IRConverter()
        ir_project = ir_converter.l5x_to_ir(project)
        
        print(f"✅ IR conversion completed:")
        print(f"  - Controller: {ir_project.controller.name}")
        print(f"  - Programs: {len(ir_project.programs)}")
        print(f"  - Controller tags: {len(ir_project.controller.tags)}")
        
        # Example 1: Export IR to JSON
        print("\n📤 Example 1: Exporting IR to JSON")
        output_file = "ir_export_example.json"
        
        export_data = export_ir_to_json(
            ir_project=ir_project,
            output_path=output_file,
            include=["tags", "control_flow", "data_types", "interactions"],
            pretty_print=True
        )
        
        print(f"✅ Exported IR to {output_file}")
        
        # Example 2: Interactive querying
        print("\n🔍 Example 2: Interactive Querying")
        query = InteractiveIRQuery(ir_project)
        
        # Get project summary
        summary = query.get_project_summary()
        print(f"📊 Project Summary:")
        print(f"  - Controller: {summary['controller']['name']}")
        print(f"  - Total tags: {summary['tags']['total_tags']}")
        print(f"  - Programs: {summary['programs']['count']}")
        print(f"  - Routines: {summary['routines']['count']}")
        
        # Get tag statistics
        tag_stats = query.get_tag_statistics()
        print(f"\n📈 Tag Statistics:")
        print(f"  - By scope: {dict(tag_stats['by_scope'])}")
        print(f"  - By type: {dict(tag_stats['by_type'])}")
        
        # Find tags by prefix (if any exist)
        if ir_project.controller.tags:
            first_tag = ir_project.controller.tags[0]
            prefix = first_tag.name.split('_')[0] if '_' in first_tag.name else first_tag.name[:3]
            
            print(f"\n🔍 Finding tags with prefix '{prefix}':")
            matching_tags = query.find_tags_by_prefix(prefix)
            for tag in matching_tags[:5]:  # Show first 5
                print(f"  - {tag.name} ({tag.data_type}, {tag.scope.value})")
        
        # Example 3: Control flow analysis
        print(f"\n🔄 Example 3: Control Flow Analysis")
        for program in ir_project.programs:
            if program.routines:
                routine = program.routines[0]
                print(f"  Analyzing routine: {program.name}.{routine.name}")
                
                control_flow = query.get_control_flow(routine.name, program.name)
                if control_flow:
                    print(f"    Type: {control_flow.get('type', 'unknown')}")
                    if 'control_flow' in control_flow:
                        cf_items = control_flow['control_flow']
                        print(f"    Control flow items: {len(cf_items)}")
                        for item in cf_items[:3]:  # Show first 3
                            print(f"      - {item.get('type', 'unknown')}: {item.get('condition', 'N/A')}")
                break
        
        # Example 4: Cross-references (if any tags exist)
        if ir_project.controller.tags:
            first_tag = ir_project.controller.tags[0]
            print(f"\n🔗 Example 4: Cross-references for tag '{first_tag.name}'")
            
            dependencies = query.get_dependencies(first_tag.name)
            print(f"  Referenced by: {dependencies['referenced_by']}")
            
            cross_refs = query.find_cross_references(first_tag.name)
            if cross_refs['programs']:
                print(f"  Found in {len(cross_refs['programs'])} programs")
            else:
                print(f"  No cross-references found")
        
        print(f"\n✅ All examples completed successfully!")
        print(f"📁 Check the generated {output_file} file for the full export.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 