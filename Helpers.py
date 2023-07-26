from svgpathtools import Path, parse_path
import svgwrite
import xml.etree.ElementTree as ET
from svg_to_gcode.svg_parser import parse_string
from svg_to_gcode.compiler import Compiler, interfaces
import math

def GetGlyphDictionary(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()
    glyphs = root.findall(".//*[@unicode]")
    dict = {}
    for glyph in glyphs[::-1]:
        try:
            d = glyph.attrib['d']
        except:
            continue
        
        try:
            horiz_adv_x = glyph.attrib['horiz-adv-x']
        except:
            horiz_adv_x = str(0)
        dict[glyph.attrib['unicode']] = [d,horiz_adv_x]
    return dict

def GenerateGcode(move_speed, cut_speed, svg):
    gcode_compiler = Compiler(
        interfaces.Gcode,
        movement_speed=move_speed,
        cutting_speed=cut_speed,
        pass_depth=0,
    )

    curves = parse_string(svg)  # Parse an svg file into geometric curves

    gcode_compiler.append_curves(curves)
    gcode = gcode_compiler.compile(passes=1)

    # gcode_compiler.compile_to_file("drawing.gcode", passes=1)
    # save the gcode to a file
    return gcode

def GetSvg(paths):
    xmin, xmax, ymin, ymax = Path(*[seg for pa in paths for seg in pa]).bbox()
    dx = xmax - xmin
    dy = ymax - ymin
    viewbox = f'{xmin} {ymin} {dx} {dy}'
    attr = {
        'width': '50%',
        'height': '50%',
        'viewBox': viewbox,
        'preserveAspectRatio': 'xMinYMin meet'
    }
    dwg = svgwrite.Drawing()
    for path in paths:
        dwg.add(dwg.path(d=path.d(), stroke='black', fill='none'))
    svg_string = dwg.tostring()
    # svg_string = wsvg(paths=paths,
    #         svg_attributes=attr, filename=None)
    return svg_string
    
    
def CheckAr(paths):
    xmin, xmax, ymin, ymax = Path(*[seg for pa in paths for seg in pa]).bbox()
    return (xmax - xmin)/(ymax - ymin)

def Process_gcode(gcode):

    def limit_decimal(value, decimal_points=4):
        return format(value, f'.{decimal_points}f')

    lines = gcode.split(";\n")
    modified_lines = []

    for line in lines:
        if line.startswith(('G0', 'G1')):
            x_value = None
            y_value = None
            x_index = 0
            y_index = 0
            # Extract X and Y values from the line
            commands = line.split()
            for i, command in enumerate(commands):
                if command.startswith('X'):
                    x_index = i
                    x_value = float(command[1:])
                elif command.startswith('Y'):
                    y_index = i
                    y_value = float(command[1:])

            if x_value is not None:
                commands[x_index] = f'X{limit_decimal(x_value)}'

            if y_value is not None:
                commands[y_index] = f'Y{limit_decimal(y_value)}'

            modified_line = ''.join(commands).strip()
            modified_lines.append(modified_line)
        else:
            modified_lines.append(line)

    modified_gcode = ";\n".join(modified_lines)
    return modified_gcode

def GcodeScale(gcode, xScale,yScale):
    min_x = float('inf')
    max_x = float('-inf')
    min_y = float('inf')
    max_y = float('-inf')

    lines = gcode.split(";\n")
    modified_lines = []
    for line in lines:
        if line.startswith(('G0', 'G1')):  # Look for lines starting with G0 or G1
            x = None
            y = None

            # Extract X and Y values from the line
            for command in line.split():
                if command.startswith('X'):
                    x = float(command[1:])
                elif command.startswith('Y'):
                    y = float(command[1:])

            if x is not None and y is not None:
                x_replace = x * xScale
                y_replace = y * yScale
                # Replace the old X and Y values with the modified values
                line = line.replace(f'X{x}', f'X{x_replace:.5f}').replace(f'Y{y}', f'Y{y_replace:.5f}')
                min_x = min(min_x, x_replace)
                max_x = max(max_x, x_replace)
                min_y = min(min_y, y_replace)
                max_y = max(max_y, y_replace)
            else:
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)

        modified_lines.append(line)

    modified_gcode = ";\n".join(modified_lines)
    return [modified_gcode,[min_x,max_x,min_y,max_y]]

def GcodeMove(gcode, xMove,yMove):
    min_x = float('inf')
    max_x = float('-inf')
    min_y = float('inf')
    max_y = float('-inf')

    lines = gcode.split(";\n")
    modified_lines = []
    for line in lines:
        if line.startswith(('G0', 'G1')):  # Look for lines starting with G0 or G1
            x = None
            y = None

            # Extract X and Y values from the line
            for command in line.split():
                if command.startswith('X'):
                    x = float(command[1:])
                elif command.startswith('Y'):
                    y = float(command[1:])

            if x is not None and y is not None:
                x_replace = x + xMove
                y_replace = y + yMove
                # Replace the old X and Y values with the modified values
                line = line.replace(f'X{x}', f'X{x_replace:.5f}').replace(f'Y{y}', f'Y{y_replace:.5f}')
                min_x = min(min_x, x_replace)
                max_x = max(max_x, x_replace)
                min_y = min(min_y, y_replace)
                max_y = max(max_y, y_replace)
            else:
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)

        modified_lines.append(line)

    modified_gcode = ";\n".join(modified_lines)
    return [modified_gcode,[min_x,max_x,min_y,max_y]]

def GetSingleLine(text, fontDict):
    paths = []
    pointer = 0
    for char in text:
        if char == ' ':
            pointer += 400
            continue

        d = parse_path(fontDict[char][0]).translated(complex(pointer,0))
        pointer = d.bbox()[1]
        paths.append(d)
    return paths

def GetMultiLine(text, fontDict):
    words = text.split(' ')
    word_splice_index = math.ceil(len(words)/2)
    split_index = len(" ".join(words[:word_splice_index]))

    #calculating values for positioning alignment, couldnt get a reference cuz it was acting weird
    pointer = [0,0]
    line1_extremes = [0,0]
    line2_extremes = [0,0]
    for char in text[split_index+1:]:
        if char == ' ':
            pointer[0] += 400
            continue

        d = parse_path(fontDict[char][0]).translated(complex(pointer[0],pointer[1]))
        pointer[0] = d.bbox()[1]
        if(d.bbox()[1]>line2_extremes[0]): line2_extremes[0] = d.bbox()[1]
        if(d.bbox()[3]>line2_extremes[1]): line2_extremes[1] = d.bbox()[3]

    pointer = [0, line2_extremes[1] + 200]

    for char in text[:split_index]:
        if char == ' ':
            pointer[0] += 400
            continue

        d = parse_path(fontDict[char][0]).translated(complex(pointer[0],pointer[1]))
        pointer[0] = d.bbox()[1]
        if(d.bbox()[1]>line1_extremes[0]): line1_extremes[0] = d.bbox()[1]
        if(d.bbox()[3]>line1_extremes[1]): line1_extremes[1] = d.bbox()[3]

    #actually moving and adding letters to path list for rendering
    paths = []
    pointer = [(line1_extremes[0]/2) - (line2_extremes[0]/2),0]
    for char in text[split_index+1:]:
        if char == ' ':
            pointer[0] += 400
            continue

        d = parse_path(fontDict[char][0]).translated(complex(pointer[0],pointer[1]))
        pointer[0] = d.bbox()[1]
        if(d.bbox()[1]>line2_extremes[0]): line2_extremes[0] = d.bbox()[1]
        if(d.bbox()[3]>line2_extremes[1]): line2_extremes[1] = d.bbox()[3]
        paths.append(d)
    
    pointer = [0,line2_extremes[1] + 400]

    for char in text[:split_index]:
        if char == ' ':
            pointer[0] += 400
            continue
        d = parse_path(fontDict[char][0]).translated(complex(pointer[0],pointer[1]))
        pointer[0] = d.bbox()[1]
        if(d.bbox()[1]>line1_extremes[0]): line1_extremes[0] = d.bbox()[1]
        if(d.bbox()[3]>line1_extremes[1]): line1_extremes[1] = d.bbox()[3]
        paths.append(d)

    return paths

def GetGcode(text, fontFile, xOffset, yOffset, scale, move_speed, cut_speed, letterLimit, arThres):
    
    bed_sizes = {
        'small' : [70,25],
        'large' : [70,45]
    }
    fontDict = GetGlyphDictionary(fontFile)

    if len(text)>letterLimit:
        print('Thats wat she said')
        return False

    #single line attempt
    final_paths = GetSingleLine(text, fontDict)

    active_bed_size = bed_sizes['small']

    if CheckAr(final_paths) > arThres and len(text.split(' ')) > 1:
        active_bed_size = bed_sizes['large']
        final_paths = GetMultiLine(text, fontDict)
    
    print(active_bed_size)

    gcode = GenerateGcode(move_speed, cut_speed, GetSvg(final_paths))
    gcode, bbox = GcodeScale(gcode,1,-1)
    gcode, bbox = GcodeMove(gcode,(bbox[0] * -1) + 1,(bbox[2] * -1) + 1)
    scalefactor = active_bed_size[0]/bbox[1]
    if((bbox[3] * scalefactor)>active_bed_size[1]):
        scalefactor = active_bed_size[1]/bbox[3]
    gcode, bbox = GcodeScale(gcode,scalefactor * scale,scalefactor * scale)
    x_center_move = (active_bed_size[0] - bbox[1])/2
    y_center_move = (active_bed_size[1] - bbox[3])/2
    gcode, bbox = GcodeMove(gcode,xOffset + x_center_move, yOffset + y_center_move)

#     # Add Border
#     gcode += f'''

# G1 F{move_speed} X0 Y0;\n

# G0 F1000 Z-1;\n

# G1 F{cut_speed} X0 Y{active_bed_size[1]};\n
# G1 X{active_bed_size[0]} Y{active_bed_size[1]};\n
# G1 X{active_bed_size[0]} Y0;\n
# G1 X0 Y0;\n

# G0 F1000 Z1;\n
#     '''

    gcode += f"\nG1 F{move_speed} X10 Y60;\n"

    temp_gcode = gcode.split("\n")
    gcode = ""

    isSkip = False
    for idx, line in enumerate(temp_gcode):
        if isSkip:
            isSkip = False
            continue

        if line.startswith("M3 S255"):
            gcode += "G0 F1000 Z-2;\n"
            if idx + 1 < len(temp_gcode) and "F" not in temp_gcode[idx + 1] and (temp_gcode[idx + 1].startswith("G0") or temp_gcode[idx + 1].startswith("G1")):
                gcode += temp_gcode[idx + 1].replace("G0", "G0 F" + str(cut_speed)).replace("G1", "G1 F" + str(cut_speed)) + "\n"
                isSkip = True
        elif line.startswith("M5"):
            gcode += "G0 F1000 Z2;\n"
            if idx + 1 < len(temp_gcode) and "F" not in temp_gcode[idx + 1] and (temp_gcode[idx + 1].startswith("G0") or temp_gcode[idx + 1].startswith("G1")):
                gcode += temp_gcode[idx + 1].replace("G0", "G0 F" + str(move_speed)).replace("G1", "G1 F" + str(move_speed)) + "\n"
                isSkip = True
        else:
            gcode += line + "\n"

    gcode = Process_gcode(gcode)
    return gcode
