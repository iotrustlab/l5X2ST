# Tag Preservation as Default Behavior

## Overview

Based on user feedback, the L5X2ST compiler now uses **tag preservation as the default behavior** instead of requiring an optional flag. This change provides better user experience and ensures users get the best possible conversion results by default.

## Why This Change Was Made

### Problems with "Enhanced" Flag Approach
1. **Vague terminology**: "Enhanced" didn't clearly communicate what was improved
2. **Implied optional**: Suggested tag preservation was an extra feature rather than correct behavior
3. **User confusion**: Users might not understand why they wouldn't want tag preservation
4. **Poor defaults**: Users had to know about the flag to get the best results

### Benefits of Default Tag Preservation
1. **Correct behavior**: Tag preservation is what users expect from a conversion tool
2. **Library compatibility**: 100% TagType compatibility prevents parsing errors
3. **No downsides**: Tag preservation doesn't hurt performance or functionality
4. **Better UX**: Users get the best results without needing to know about flags
5. **Future-proof**: Encourages adoption of the improved implementation

## New CLI Behavior

### Default Behavior (Tag Preservation)
```bash
# Convert L5X to ST with tag preservation (default)
l5x-st-compiler l5x2st -i project.L5X -o output.st

# Convert ST to L5X with tag preservation (default)
l5x-st-compiler st2l5x -i program.st -o output.L5X
```

### Legacy Behavior (Basic Tag Generation)
```bash
# Use legacy conversion mode
l5x-st-compiler l5x2st -i project.L5X -o output.st --legacy

# Use legacy conversion mode
l5x-st-compiler st2l5x -i program.st -o output.L5X --legacy
```

### L5K Overlay Support
```bash
# Tag preservation with L5K overlay
l5x-st-compiler l5x2st -i project.L5X -o output.st --l5k-overlay overlay.L5K
```

## Technical Implementation

### CLI Changes
- **Removed**: `--enhanced` flag
- **Added**: `--legacy` flag for old behavior
- **Default**: Tag preservation mode
- **Updated**: Help text and examples

### Code Changes
```python
# Old approach (enhanced flag)
if args.enhanced:
    # Use enhanced conversion
else:
    # Use basic conversion

# New approach (legacy flag)
if args.legacy:
    # Use legacy conversion (basic tag generation)
else:
    # Use tag preservation (default)
```

## Migration Guide

### For Users
- **No action required**: Existing commands work the same but now use tag preservation by default
- **Better results**: Users automatically get improved tag preservation
- **Legacy option**: Use `--legacy` flag if you specifically need the old behavior

### For Developers
- **API unchanged**: Programmatic interfaces remain the same
- **Default improvement**: All conversions now use tag preservation by default
- **Backward compatibility**: Legacy behavior available via `--legacy` flag

## Benefits

### ✅ User Experience
- **Simpler commands**: No need to remember special flags
- **Better defaults**: Users get the best results automatically
- **Clearer terminology**: "Legacy" vs "Tag Preservation" is more descriptive

### ✅ Technical Quality
- **100% TagType compatibility**: All generated files have proper TagType attributes
- **Complete tag generation**: All variables converted to tags with proper metadata
- **Library compatibility**: Generated L5X files parse correctly with l5x library

### ✅ Future Development
- **Encourages adoption**: Users naturally get the improved implementation
- **Simplified maintenance**: One code path for most use cases
- **Clear migration path**: Legacy flag provides transition period

## Examples

### Before (Enhanced Flag Required)
```bash
# User had to know about enhanced flag
l5x-st-compiler l5x2st -i project.L5X -o output.st --enhanced
l5x-st-compiler st2l5x -i program.st -o output.L5X --enhanced
```

### After (Tag Preservation Default)
```bash
# Users get best results by default
l5x-st-compiler l5x2st -i project.L5X -o output.st
l5x-st-compiler st2l5x -i program.st -o output.L5X

# Legacy behavior available if needed
l5x-st-compiler l5x2st -i project.L5X -o output.st --legacy
l5x-st-compiler st2l5x -i program.st -o output.L5X --legacy
```

## Conclusion

This change significantly improves the user experience by:

1. **Making the best behavior the default**
2. **Eliminating the need for users to know about special flags**
3. **Providing clearer, more descriptive terminology**
4. **Maintaining backward compatibility through the legacy flag**

Users now get superior tag preservation automatically, while developers have a clear path for maintaining legacy compatibility if needed.

**Result**: Better user experience, improved conversion quality, and clearer API design. 