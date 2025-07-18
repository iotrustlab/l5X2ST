"""Command-line interface for the L5X-ST compiler."""

import argparse
import sys
from pathlib import Path
import logging
import click
from datetime import datetime
import xml.etree.ElementTree as ET

from .l5x2st import L5X2STConverter, convert_st_to_l5x_file
from .st2l5x import ST2L5XConverter, convert_st_to_l5x_string
from .ir_converter import IRConverter
from .models import RoundTripInfo


def validate_ir(ir_project) -> list:
    """Validate IR for required structure. Returns list of error strings."""
    errors = []
    if not ir_project.controller or not ir_project.controller.name:
        errors.append("Controller missing or unnamed.")
    if not ir_project.controller.tags:
        errors.append("No controller tags found.")
    if not ir_project.programs:
        errors.append("No programs found.")
    for prog in ir_project.programs:
        if not prog.routines:
            errors.append(f"Program '{prog.name}' has no routines.")
    return errors


def l5x2st_main():
    """Main entry point for L5X to ST conversion."""
    parser = argparse.ArgumentParser(
        description='Convert L5X files to Structured Text.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  l5x2st -i project.L5X -o output.st
  l5x2st -d l5x_files -o consolidated.st
  l5x2st -i project.L5X -o output.st --use-ir
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '-i', '--input',
        metavar='L5X_FILE',
        help='Input L5X file to convert'
    )
    group.add_argument(
        '-d', '--directory',
        metavar='L5X_DIR',
        help='Directory containing L5X files to convert'
    )
    
    parser.add_argument(
        '-o', '--output',
        metavar='ST_FILE',
        default='output.st',
        help='Output ST file (default: output.st)'
    )
    
    parser.add_argument(
        '--use-ir',
        action='store_true',
        help='Use IR/guardrail mode for round-trip conversion (L5X→IR→ST→IR→L5X)'
    )
    
    parser.add_argument(
        '--l5k-overlay',
        metavar='L5K_FILE',
        help='L5K file to provide additional project context (tags, tasks, programs, modules)'
    )
    
    parser.add_argument(
        '--legacy',
        action='store_true',
        help='Use legacy conversion mode (basic tag generation without preservation)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    try:
        if args.use_ir:
            print("[INFO] IR/guardrail mode enabled: L5X→IR→ST with validation.")
            ir_converter = IRConverter()
            
            if args.input:
                # Convert single file with IR
                if not Path(args.input).exists():
                    print(f"Error: Input file '{args.input}' not found.")
                    sys.exit(1)
                
                if args.verbose:
                    print(f"Converting {args.input} to {args.output} using IR mode")
                
                # L5X → IR → ST
                import l5x
                project = l5x.Project(args.input)
                ir_project = ir_converter.l5x_to_ir(project, args.l5k_overlay)
                
                # Generate ST from IR
                l5x2st = L5X2STConverter()
                st_code = l5x2st.convert_l5x_to_st(args.input, args.l5k_overlay)
                
                with open(args.output, 'w') as f:
                    f.write(st_code)
                
                print(f"[INFO] IR validation passed. Wrote ST code to {args.output}")
                
            elif args.directory:
                print("Error: IR mode not yet supported for directory conversion.")
                sys.exit(1)
        else:
            # Standard conversion
            converter = L5X2STConverter()
            
            if args.input:
                # Convert single file
                if not Path(args.input).exists():
                    print(f"Error: Input file '{args.input}' not found.")
                    sys.exit(1)
                
                if args.verbose:
                    print(f"Converting {args.input} to {args.output}")
                    if args.l5k_overlay:
                        print(f"Using L5K overlay: {args.l5k_overlay}")
                    if args.legacy:
                        print("Using legacy conversion mode (basic tag generation)")
                    else:
                        print("Using tag preservation mode (recommended)")
                
                if args.legacy:
                    # Use legacy conversion (basic tag generation)
                    st_code = converter.convert_l5x_to_st(args.input, args.l5k_overlay)
                    with open(args.output, 'w', encoding='utf-8') as f:
                        f.write(st_code)
                else:
                    # Use enhanced roundtrip conversion (default - tag preservation)
                    from .l5x2st import convert_enhanced_roundtrip_file
                    convert_enhanced_roundtrip_file(args.input, args.output, args.l5k_overlay)
                    print(f"Tag preservation conversion completed: {args.output}")
                
            elif args.directory:
                # Convert directory
                if not Path(args.directory).exists():
                    print(f"Error: Input directory '{args.directory}' not found.")
                    sys.exit(1)
                
                if args.verbose:
                    print(f"Converting all L5X files in {args.directory} to {args.output}")
                
                converter.convert_directory(args.directory, args.output)
            
            print(f"Successfully converted to {args.output}")
        
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@click.command()
@click.option('--input', '-i', 'input_file', required=True, help='Input ST file')
@click.option('--output', '-o', 'output_file', required=True, help='Output L5X file')
@click.option('--use-ir', is_flag=True, help='Use IR/guardrail mode for round-trip conversion')
@click.option('--legacy', is_flag=True, help='Use legacy conversion mode (basic tag generation without preservation)')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def st2l5x(input_file: str, output_file: str, use_ir: bool, legacy: bool, verbose: bool):
    """Convert Structured Text (ST) to L5X format."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    try:
        if use_ir:
            click.echo("[INFO] IR/guardrail mode enabled: ST→IR→L5X with validation.")
            
            # Read ST file
            with open(input_file, 'r', encoding='utf-8') as f:
                st_code = f.read()
            
            # Convert ST to L5X with IR validation
            st2l5x_converter = ST2L5XConverter()
            l5x_xml = convert_st_to_l5x_string(st_code)
            
            # Validate IR before writing L5X
            ir_converter = IRConverter()
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.L5X', delete=False) as temp_file:
                temp_file.write(l5x_xml)
                temp_l5x_path = temp_file.name
            
            try:
                import l5x
                project = l5x.Project(temp_l5x_path)
                ir_project = ir_converter.l5x_to_ir(project)
                errors = validate_ir(ir_project)
                
                if errors:
                    click.echo("[ERROR] IR validation failed:", err=True)
                    for err in errors:
                        click.echo(f"  - {err}", err=True)
                    sys.exit(1)
                
                # Write validated L5X
                with open(output_file, 'w') as f:
                    f.write(l5x_xml)
                
                click.echo(f"✅ IR validation passed. Successfully converted {input_file} to {output_file}")
                
            finally:
                if os.path.exists(temp_l5x_path):
                    os.unlink(temp_l5x_path)
        else:
            # Standard conversion
            with open(input_file, 'r', encoding='utf-8') as f:
                st_code = f.read()
            
            if legacy:
                # Use legacy conversion (basic tag generation)
                st2l5x_converter = ST2L5XConverter()
                l5x_xml = st2l5x_converter.parse_st_code(st_code)
                
                # Write legacy L5X
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n')
                    f.write(ET.tostring(l5x_xml, encoding='unicode', method='xml'))
                
                click.echo(f"✅ Legacy conversion completed: {output_file}")
            else:
                # Standard conversion
                convert_st_to_l5x_file(st_code, output_file)
                click.echo(f"✅ Successfully converted {input_file} to {output_file}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@click.command()
@click.option('--input', '-i', 'input_file', required=True, help='Input L5X file')
@click.option('--output', '-o', 'output_file', required=True, help='Output JSON file')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def extract_io(input_file: str, output_file: str, verbose: bool):
    """Extract I/O tag definitions from L5X file and output as JSON."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    try:
        import json
        import l5x
        
        click.echo(f"📖 Reading L5X file: {input_file}")
        
        # Load L5X project
        project = l5x.Project(input_file)
        
        # Extract I/O tags using IRConverter
        ir_converter = IRConverter()
        io_tags = ir_converter.extract_io_tags(project)
        
        # Prepare output data
        output_data = {
            'source_file': input_file,
            'extraction_time': datetime.now().isoformat(),
            'total_io_tags': len(io_tags),
            'io_tags': io_tags
        }
        
        # Write JSON output
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        click.echo(f"✅ Extracted {len(io_tags)} I/O tags to {output_file}")
        
        # Print summary
        input_count = sum(1 for tag in io_tags if tag['direction'] == 'Input')
        output_count = sum(1 for tag in io_tags if tag['direction'] == 'Output')
        
        click.echo(f"📊 Summary:")
        click.echo(f"  - Input tags: {input_count}")
        click.echo(f"  - Output tags: {output_count}")
        
        if verbose:
            click.echo(f"\n📋 I/O Tags:")
            for tag in io_tags:
                click.echo(f"  - {tag['name']} ({tag['direction']}, {tag['data_type']})")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point for the combined tool."""
    parser = argparse.ArgumentParser(
        description='L5X-ST Compiler - Convert between L5X and Structured Text formats.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert L5X to ST (default - tag preservation mode)
  l5x-st-compiler l5x2st -i project.L5X -o output.st
  
  # Convert L5X to ST (legacy mode - basic tag generation)
  l5x-st-compiler l5x2st -i project.L5X -o output.st --legacy
  
  # Convert L5X to ST (tag preservation with L5K overlay)
  l5x-st-compiler l5x2st -i project.L5X -o output.st --l5k-overlay overlay.L5K
  
  # Convert L5X to ST (IR/guardrail mode)
  l5x-st-compiler l5x2st -i project.L5X -o output.st --use-ir
  
  # Convert ST to L5X (default - tag preservation mode)
  l5x-st-compiler st2l5x -i program.st -o output.L5X
  
  # Convert ST to L5X (legacy mode - basic tag generation)
  l5x-st-compiler st2l5x -i program.st -o output.L5X --legacy
  
  # Convert ST to L5X (IR/guardrail mode)
  l5x-st-compiler st2l5x -i program.st -o output.L5X --use-ir
  
  # Extract I/O tags from L5X file
  l5x-st-compiler extract-io -i Control.L5X -o io_mapping.json
  
  # Convert directory of L5X files
  l5x-st-compiler l5x2st -d l5x_files -o consolidated.st
        """
    )
    
    parser.add_argument(
        'command',
        choices=['l5x2st', 'st2l5x', 'extract-io'],
        help='Command to execute'
    )
    
    # Parse the command
    args, remaining = parser.parse_known_args()
    
    # Route to appropriate command
    if args.command == 'l5x2st':
        # Temporarily replace sys.argv for the subcommand
        original_argv = sys.argv
        sys.argv = ['l5x2st'] + remaining
        try:
            l5x2st_main()
        finally:
            sys.argv = original_argv
    elif args.command == 'st2l5x':
        # For st2l5x, we need to parse the remaining arguments manually
        # since it uses click
        import tempfile
        import os
        
        # Parse the remaining arguments
        st2l5x_parser = argparse.ArgumentParser()
        st2l5x_parser.add_argument('--input', '-i', required=True)
        st2l5x_parser.add_argument('--output', '-o', required=True)
        st2l5x_parser.add_argument('--use-ir', action='store_true')
        st2l5x_parser.add_argument('--legacy', action='store_true')
        st2l5x_parser.add_argument('--verbose', '-v', action='store_true')
        
        try:
            st2l5x_args = st2l5x_parser.parse_args(remaining)
            
            # Call the st2l5x function directly, bypassing click
            if st2l5x_args.verbose:
                logging.basicConfig(level=logging.DEBUG)
            
            try:
                from l5x_st_compiler.l5x2st import L5X2STConverter
                l5x2st_converter = L5X2STConverter()
                if st2l5x_args.use_ir:
                    print("[INFO] IR/guardrail mode enabled: ST→IR→L5X with validation.")
                    
                    # Read ST file
                    with open(st2l5x_args.input, 'r', encoding='utf-8') as f:
                        st_code = f.read()
                    
                    # Split ST code into variables and program logic
                    variables, program_logic = l5x2st_converter._parse_st_code_sections(st_code)
                    
                    # Convert ST to L5X with IR validation
                    st2l5x_converter = ST2L5XConverter()
                    l5x_xml = convert_st_to_l5x_string(variables + "\n\n" + program_logic)
                    
                    # Validate IR before writing L5X
                    ir_converter = IRConverter()
                    import tempfile
                    import os
                    
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.L5X', delete=False) as temp_file:
                        temp_file.write(l5x_xml)
                        temp_l5x_path = temp_file.name
                    
                    try:
                        import l5x
                        project = l5x.Project(temp_l5x_path)
                        ir_project = ir_converter.l5x_to_ir(project)
                        errors = validate_ir(ir_project)
                        
                        if errors:
                            print("[ERROR] IR validation failed:")
                            for err in errors:
                                print(f"  - {err}")
                            sys.exit(1)
                        
                        # Write validated L5X
                        with open(st2l5x_args.output, 'w') as f:
                            f.write(l5x_xml)
                        
                        print(f"✅ IR validation passed. Successfully converted {st2l5x_args.input} to {st2l5x_args.output}")
                        
                    finally:
                        if os.path.exists(temp_l5x_path):
                            os.unlink(temp_l5x_path)
                else:
                    # Standard conversion
                    with open(st2l5x_args.input, 'r', encoding='utf-8') as f:
                        st_code = f.read()
                    
                    if st2l5x_args.legacy:
                        # Use legacy conversion (basic tag generation)
                        st2l5x_converter = ST2L5XConverter()
                        l5x_xml = st2l5x_converter.parse_st_code(st_code)
                        
                        # Write legacy L5X
                        with open(st2l5x_args.output, 'w', encoding='utf-8') as f:
                            f.write('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n')
                            f.write(ET.tostring(l5x_xml, encoding='unicode', method='xml'))
                        
                        print(f"✅ Legacy conversion completed: {st2l5x_args.output}")
                    else:
                        # Standard conversion
                        convert_st_to_l5x_file(st_code, st2l5x_args.output)
                        print(f"✅ Successfully converted {st2l5x_args.input} to {st2l5x_args.output}")
                
            except Exception as e:
                print(f"❌ Error: {e}")
                sys.exit(1)
            
        except SystemExit:
            # If argparse fails, show help
            st2l5x_parser.print_help()
            sys.exit(1)
    elif args.command == 'extract-io':
        # Parse the remaining arguments for extract-io
        extract_io_parser = argparse.ArgumentParser()
        extract_io_parser.add_argument('--input', '-i', required=True)
        extract_io_parser.add_argument('--output', '-o', required=True)
        extract_io_parser.add_argument('--verbose', '-v', action='store_true')
        
        try:
            extract_io_args = extract_io_parser.parse_args(remaining)
            
            # Call the extract_io function directly, bypassing click
            if extract_io_args.verbose:
                logging.basicConfig(level=logging.DEBUG)
            
            try:
                import json
                import l5x
                from datetime import datetime
                
                print(f"📖 Reading L5X file: {extract_io_args.input}")
                
                # Load L5X project
                project = l5x.Project(extract_io_args.input)
                
                # Extract I/O tags using IRConverter
                ir_converter = IRConverter()
                io_tags = ir_converter.extract_io_tags(project)
                
                # Prepare output data
                output_data = {
                    'source_file': extract_io_args.input,
                    'extraction_time': datetime.now().isoformat(),
                    'total_io_tags': len(io_tags),
                    'io_tags': io_tags
                }
                
                # Write JSON output
                with open(extract_io_args.output, 'w') as f:
                    json.dump(output_data, f, indent=2)
                
                print(f"✅ Extracted {len(io_tags)} I/O tags to {extract_io_args.output}")
                
                # Print summary
                input_count = sum(1 for tag in io_tags if tag['direction'] == 'Input')
                output_count = sum(1 for tag in io_tags if tag['direction'] == 'Output')
                
                print(f"📊 Summary:")
                print(f"  - Input tags: {input_count}")
                print(f"  - Output tags: {output_count}")
                
                if extract_io_args.verbose:
                    print(f"\n📋 I/O Tags:")
                    for tag in io_tags:
                        print(f"  - {tag['name']} ({tag['direction']}, {tag['data_type']})")
                
            except Exception as e:
                print(f"❌ Error: {e}")
                if extract_io_args.verbose:
                    import traceback
                    traceback.print_exc()
                sys.exit(1)
            
        except SystemExit:
            # If argparse fails, show help
            extract_io_parser.print_help()
            sys.exit(1)


if __name__ == '__main__':
    main() 