from svgpathtools import Path, parse_path
import svgwrite
import xml.etree.ElementTree as ET
from svg_to_gcode.svg_parser import parse_string
from svg_to_gcode.compiler import Compiler, interfaces
import math
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.factory import Factory
from kivy.clock import Clock
import threading
import re
from matplotlib.backends.backend_agg import FigureCanvasAgg
import matplotlib.pyplot as plt
import numpy as np
import matplotlib
from kivy.logger import Logger


import re
import sys
import os.path
from math import *
from copy import *

matplotlib.use("Agg")


class ImageButton(ButtonBehavior, Image):
    def __init__(self, **kwargs):
        super(ImageButton, self).__init__(**kwargs)

    def on_press(self):
        pass

    def on_release(self):
        pass


class LongpressButton(Factory.Button):
    __events__ = ("on_long_press",)

    long_press_time = Factory.NumericProperty(1)

    def on_state(self, instance, value):
        if value == "down":
            lpt = self.long_press_time
            self._clockev = Clock.schedule_once(self._do_long_press, lpt)
        else:
            self._clockev.cancel()

    def _do_long_press(self, dt):
        self.dispatch("on_long_press")

    def on_long_press(self, *largs):
        pass


class MyPausableThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}):
        self._event = threading.Event()
        if target:
            args = ((lambda: self._event.wait()),) + args
        super(MyPausableThread, self).__init__(group, target, name, args, kwargs)

    def pause(self):
        self._event.clear()

    def resume(self):
        self._event.set()


def clamp(num, min, max):
    return min if num < min else max if num > max else num


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolate on the scale given by a to b, using t as the point on that scale.
    Examples
    --------
        50 == lerp(0, 100, 0.5)
        4.2 == lerp(1, 5, 0.8)
    """
    return (1 - t) * a + t * b


def plot_gcode_kivy_texture(gcode_text):
    x, y, z = 0, 0, 0
    x_values, y_values = [], []
    pen_down = False
    gcode_commands = re.findall(
        r"[Gg]\d+\s?(?:[Ff]\d+)?\s?(?:[Xx]?(-?\d+\.?\d*)\s?)?(?:[Yy]?(-?\d+\.?\d*)\s?)?(?:[Zz]?(-?\d+\.?\d*))?[;]?",
        gcode_text,
    )
    for command in gcode_commands:
        if command[0]:
            x = float(command[0])
        if command[1]:
            y = float(command[1])
        if command[2]:
            z = float(command[2])
            if z < 0:
                pen_down = True
            elif z > 0:
                pen_down = False
        if pen_down and (command[0] or command[1] or command[2]):
            x_values.append(x)
            y_values.append(y)
        elif not pen_down:
            x_values.append(None)
            y_values.append(None)

    fig, ax = plt.subplots()

    # Calculate the data range for x and y
    x_range = max(x for x in x_values if x is not None) - min(
        x for x in x_values if x is not None
    )
    y_range = max(y for y in y_values if y is not None) - min(
        y for y in y_values if y is not None
    )

    # Set the figure size based on the data range
    fig.set_size_inches(x_range * 0.1, y_range * 0.1)

    # Adjust the spacing around the plot
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

    ax.plot(x_values, y_values, "b-")  # Set the line color to white
    ax.set_xlim(
        min(x for x in x_values if x is not None),
        max(x for x in x_values if x is not None),
    )
    ax.set_ylim(
        min(y for y in y_values if y is not None),
        max(y for y in y_values if y is not None),
    )

    ax.set_xticks([])  # Remove x-axis ticks and labels
    ax.set_yticks([])  # Remove y-axis ticks and labels

    canvas = FigureCanvasAgg(fig)
    canvas.draw()

    # Convert the plot to a NumPy array and flip on both axes
    width, height = fig.get_size_inches() * fig.dpi
    plot_array = np.frombuffer(canvas.tostring_rgb(), dtype="uint8").reshape(
        int(height), int(width), 3
    )
    flipped_array = np.flipud(plot_array)
    # plt.close()
    rgba_array = np.dstack(
        (flipped_array, np.full_like(flipped_array[..., :1], 255, dtype=np.uint8))
    )
    return rgba_array


def GetGlyphDictionary(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()
    glyphs = root.findall(".//*[@unicode]")
    dict = {}
    for glyph in glyphs[::-1]:
        try:
            d = glyph.attrib["d"]
        except:
            continue

        try:
            horiz_adv_x = glyph.attrib["horiz-adv-x"]
        except:
            horiz_adv_x = str(0)
        dict[glyph.attrib["unicode"]] = [d, horiz_adv_x]
    return dict


def word_wrapper(text, limit):
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        if len(current_line) + len(word) <= limit:
            current_line += word + " "
        else:
            lines.append(current_line.strip())
            current_line = word + " "

    if current_line:
        lines.append(current_line.strip())

    return "\n".join(lines)


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
    viewbox = f"{xmin} {ymin} {dx} {dy}"
    attr = {
        "width": "50%",
        "height": "50%",
        "viewBox": viewbox,
        "preserveAspectRatio": "xMinYMin meet",
    }
    dwg = svgwrite.Drawing()
    for path in paths:
        dwg.add(dwg.path(d=path.d(), stroke="black", fill="none"))
    svg_string = dwg.tostring()
    # svg_string = wsvg(paths=paths,
    #         svg_attributes=attr, filename=None)
    return svg_string


def CheckAr(paths):
    xmin, xmax, ymin, ymax = Path(*[seg for pa in paths for seg in pa]).bbox()
    return (xmax - xmin) / (ymax - ymin)


def Process_gcode(gcode):
    def limit_decimal(value, decimal_points=4):
        return format(value, f".{decimal_points}f")

    lines = gcode.split(";\n")
    modified_lines = []

    for line in lines:
        if line.startswith(("G0", "G1")):
            x_value = None
            y_value = None
            x_index = 0
            y_index = 0
            # Extract X and Y values from the line
            commands = line.split()
            for i, command in enumerate(commands):
                if command.startswith("X"):
                    x_index = i
                    x_value = float(command[1:])
                elif command.startswith("Y"):
                    y_index = i
                    y_value = float(command[1:])

            if x_value is not None:
                commands[x_index] = f"X{limit_decimal(x_value)}"

            if y_value is not None:
                commands[y_index] = f"Y{limit_decimal(y_value)}"

            modified_line = "".join(commands).strip()
            modified_lines.append(modified_line)
        else:
            modified_lines.append(line)

    modified_gcode = ";\n".join(modified_lines)
    return modified_gcode


def GcodeScale(gcode, xScale, yScale):
    min_x = float("inf")
    max_x = float("-inf")
    min_y = float("inf")
    max_y = float("-inf")

    lines = gcode.split(";\n")
    modified_lines = []
    for line in lines:
        if line.startswith(("G0", "G1")):  # Look for lines starting with G0 or G1
            x = None
            y = None

            # Extract X and Y values from the line
            for command in line.split():
                if command.startswith("X"):
                    x = float(command[1:])
                elif command.startswith("Y"):
                    y = float(command[1:])

            if x is not None and y is not None:
                x_replace = x * xScale
                y_replace = y * yScale
                # Replace the old X and Y values with the modified values
                line = line.replace(f"X{x}", f"X{x_replace:.5f}").replace(
                    f"Y{y}", f"Y{y_replace:.5f}"
                )
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
    return [modified_gcode, [min_x, max_x, min_y, max_y]]


def GcodeMove(gcode, xMove, yMove):
    min_x = float("inf")
    max_x = float("-inf")
    min_y = float("inf")
    max_y = float("-inf")

    lines = gcode.split(";\n")
    modified_lines = []
    for line in lines:
        if line.startswith(("G0", "G1")):  # Look for lines starting with G0 or G1
            x = None
            y = None

            # Extract X and Y values from the line
            for command in line.split():
                if command.startswith("X"):
                    x = float(command[1:])
                elif command.startswith("Y"):
                    y = float(command[1:])

            if x is not None and y is not None:
                x_replace = x + xMove
                y_replace = y + yMove
                # Replace the old X and Y values with the modified values
                line = line.replace(f"X{x}", f"X{x_replace:.5f}").replace(
                    f"Y{y}", f"Y{y_replace:.5f}"
                )
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
    return [modified_gcode, [min_x, max_x, min_y, max_y]]


def GetSingleLine(text, fontDict):
    paths = []
    pointer = 0
    for char in text:
        if char == " ":
            pointer += 400
            continue

        d = parse_path(fontDict[char][0]).translated(complex(pointer, 0))
        pointer = d.bbox()[1]
        paths.append(d)
    return paths


def GetMultiLine(text, fontDict):
    words = text.split(" ")
    word_splice_index = math.ceil(len(words) / 2)
    split_index = len(" ".join(words[:word_splice_index]))

    # calculating values for positioning alignment, couldnt get a reference cuz it was acting weird
    pointer = [0, 0]
    line1_extremes = [0, 0]
    line2_extremes = [0, 0]
    for char in text[split_index + 1 :]:
        if char == " ":
            pointer[0] += 400
            continue

        d = parse_path(fontDict[char][0]).translated(complex(pointer[0], pointer[1]))
        pointer[0] = d.bbox()[1]
        if d.bbox()[1] > line2_extremes[0]:
            line2_extremes[0] = d.bbox()[1]
        if d.bbox()[3] > line2_extremes[1]:
            line2_extremes[1] = d.bbox()[3]

    pointer = [0, line2_extremes[1] + 200]

    for char in text[:split_index]:
        if char == " ":
            pointer[0] += 400
            continue

        d = parse_path(fontDict[char][0]).translated(complex(pointer[0], pointer[1]))
        pointer[0] = d.bbox()[1]
        if d.bbox()[1] > line1_extremes[0]:
            line1_extremes[0] = d.bbox()[1]
        if d.bbox()[3] > line1_extremes[1]:
            line1_extremes[1] = d.bbox()[3]

    # actually moving and adding letters to path list for rendering
    paths = []
    pointer = [(line1_extremes[0] / 2) - (line2_extremes[0] / 2), 0]
    for char in text[split_index + 1 :]:
        if char == " ":
            pointer[0] += 400
            continue

        d = parse_path(fontDict[char][0]).translated(complex(pointer[0], pointer[1]))
        pointer[0] = d.bbox()[1]
        if d.bbox()[1] > line2_extremes[0]:
            line2_extremes[0] = d.bbox()[1]
        if d.bbox()[3] > line2_extremes[1]:
            line2_extremes[1] = d.bbox()[3]
        paths.append(d)

    pointer = [0, line2_extremes[1] + 400]

    for char in text[:split_index]:
        if char == " ":
            pointer[0] += 400
            continue
        d = parse_path(fontDict[char][0]).translated(complex(pointer[0], pointer[1]))
        pointer[0] = d.bbox()[1]
        if d.bbox()[1] > line1_extremes[0]:
            line1_extremes[0] = d.bbox()[1]
        if d.bbox()[3] > line1_extremes[1]:
            line1_extremes[1] = d.bbox()[3]
        paths.append(d)

    return paths


def GetPaths(full_text, fontDict, limit):
    space_space = 400
    text_list = word_wrapper(full_text, limit).split("\n")
    paths = []
    line_extremes = [[0, 0] for _ in text_list]  # empty list of line extremes
    x_extreme_index = 0
    pointer = [0, 0]

    # Calculate extreme x and y for each line
    for line_index in reversed(range(0, len(text_list))):
        for char in text_list[line_index]:
            if char == " ":
                pointer[0] += space_space
                continue

            d = parse_path(fontDict[char][0]).translated(
                complex(pointer[0], pointer[1])
            )
            pointer[0] = d.bbox()[1]
            if d.bbox()[1] > line_extremes[line_index][0]:
                line_extremes[line_index][0] = d.bbox()[1]
                if d.bbox()[1] > line_extremes[x_extreme_index][0]:
                    x_extreme_index = line_index
            if d.bbox()[3] > line_extremes[line_index][1]:
                line_extremes[line_index][1] = d.bbox()[3]
        pointer = [0, line_extremes[line_index][1] + space_space]

    # actually spawning the words
    previous_line_extreme_y = 0
    for line_index in reversed(range(0, len(text_list))):
        pointer = [
            (line_extremes[x_extreme_index][0] - line_extremes[line_index][0]) / 2,
            previous_line_extreme_y,
        ]
        for char in text_list[line_index]:
            if char == " ":
                pointer[0] += space_space
                continue
            d = parse_path(fontDict[char][0]).translated(
                complex(pointer[0], pointer[1])
            )
            pointer[0] = d.bbox()[1]
            paths.append(d)
        previous_line_extreme_y = line_extremes[line_index][1] + space_space

    return paths


def GetGcode(text,fontid,xOffset,yOffset,scale,move_speed,cut_speed,letterLimit,wordwrapLimit,border,bed_size_x,bed_size_y,x_padding,y_padding,bedout = 85):
    processing_Scale = 1
    if len(text) <= wordwrapLimit:
        processing_Scale = lerp(0.5, 1, clamp(len(text) / wordwrapLimit, 0, 1))

    active_bed_size = [bed_size_x, bed_size_y]
    
    fontDict = GetGlyphDictionary(f"Fonts/SVGFONT ({fontid}).svg")

    if len(text) > letterLimit:
        Logger.error("Thats wat she said")
        return None

    final_paths = GetPaths(text, fontDict, wordwrapLimit)

    gcode = GenerateGcode(move_speed, cut_speed, GetSvg(final_paths))
    gcode, bbox = GcodeScale(gcode, 1, -1)
    gcode, bbox = GcodeMove(gcode, (bbox[0] * -1) + 1, (bbox[2] * -1) + 1)
    scalefactor = (active_bed_size[0] - (x_padding * 2)) / bbox[1]
    if (bbox[3] * scalefactor) > (active_bed_size[1] - (y_padding * 2)):
        scalefactor = (active_bed_size[1] - (y_padding * 2)) / bbox[3]

    gcode, bbox = GcodeScale(gcode, scalefactor * scale * processing_Scale, scalefactor * scale * processing_Scale)

    x_center_move = (active_bed_size[0] - bbox[1]) / 2
    y_center_move = y_padding if len(text) <= wordwrapLimit else (active_bed_size[1] - bbox[3])/2
    gcode, bbox = GcodeMove(gcode, xOffset + x_center_move, yOffset + y_center_move)

    if border:
        # Add Border
        gcode += f"""
G1 F{move_speed} X{xOffset + 0} Y{yOffset + 0};
G0 F1000 Z-1;
G1 F{cut_speed} X{xOffset + 0} Y{yOffset+active_bed_size[1]};
G1 X{xOffset + active_bed_size[0]} Y{yOffset + active_bed_size[1]};
G1 X{ xOffset + active_bed_size[0]} Y{yOffset + 0};
G1 X{xOffset + 0} Y{yOffset + 0};
G0 F1000 Z1;\n"""

    gcode += "G0 F1000 Z1;\n"

    gcode += f"\nG1 F{move_speed} X10 Y{bedout};\n"

    temp_gcode = gcode.split("\n")
    gcode = ""

    isSkip = False
    for idx, line in enumerate(temp_gcode):
        if isSkip:
            isSkip = False
            continue

        if line.startswith("M3 S255"):
            gcode += "G0 F1000 Z-1;\n"
            if (
                idx + 1 < len(temp_gcode)
                and "F" not in temp_gcode[idx + 1]
                and (
                    temp_gcode[idx + 1].startswith("G0")
                    or temp_gcode[idx + 1].startswith("G1")
                )
            ):
                gcode += (
                    temp_gcode[idx + 1]
                    .replace("G0", "G0 F" + str(cut_speed))
                    .replace("G1", "G1 F" + str(cut_speed))
                    + "\n"
                )
                isSkip = True
        elif line.startswith("M5"):
            gcode += "G0 F1000 Z1;\n"
            if (
                idx + 1 < len(temp_gcode)
                and "F" not in temp_gcode[idx + 1]
                and (
                    temp_gcode[idx + 1].startswith("G0")
                    or temp_gcode[idx + 1].startswith("G1")
                )
            ):
                gcode += (
                    temp_gcode[idx + 1]
                    .replace("G0", "G0 F" + str(move_speed))
                    .replace("G1", "G1 F" + str(move_speed))
                    + "\n"
                )
                isSkip = True
        else:
            gcode += line + "\n"

    gcode = Process_gcode(gcode)

    return GcodePreProcess(gcode)





# Get command line options
# TODO: implement all other command line switches and return them with opts[]
# TODO: opts[0] = infile, opts[1] = outfile, opts[2] = ? ...


def unit_conv(val) : # Converts value to mm
    return(val)

def fout_conv(val) : # Returns converted value as rounded string for output file.
    return( str(round(val,2)) )

def GcodePreProcess(fin):
    # -= SETTINGS =-
    mm_per_arc_segment = 0.1 # mm per arc segment   
    verbose = True  # Verbose flag to show all progress
    remove_unsupported = True   # Removal flag for all unsupported statements

    
    # Initialize parser state
    gc = { 'current_xyz' : [0,0,0], 
        'feed_rate' : 0,         # F0
        'motion_mode' : 'SEEK',  # G00
        'plane_axis' : [0,1,2],  # G17
        'inches_mode' : False,   # G21
        'inverse_feedrate_mode' : False, # G94
        'absolute_mode' : True}  # G90

    # Open g-code file
    fout = []

    # Iterate through g-code file
    l_count = 0
    for line in fin.split(';'):
        l_count += 1 # Iterate line counter
        
        # Strip comments/spaces/tabs/new line and capitalize. Comment MSG not supported.
        block = re.sub('\s|\(.*?\)','',line).upper() 
        block = re.sub('\\\\','',block) # Strip \ block delete character
        block = re.sub('%','',block) # Strip % program start/stop character
        
        if len(block) == 0 :  # Ignore empty blocks
            
            print ("Skipping: " + line.strip())
            
        else :  # Process valid g-code clean block. Assumes no block delete characters or comments
            
            g_cmd = re.findall(r'[^0-9\.\-]+',block) # Extract block command characters
            g_num = re.findall(r'[0-9\.\-]+',block) # Extract block numbers
            
            # G-code block error checks
            # if len(g_cmd) != len(g_num) : print block; raise Exception('Invalid block. Unbalanced word and values.')
            if 'N' in g_cmd :
                if g_cmd[0]!='N': raise Exception('Line number must be first command in line.')
                if g_cmd.count('N') > 1: raise Exception('More than one line number in block.')
                g_cmd = g_cmd[1:]  # Remove line number word
                g_num = g_num[1:]
            # Block item repeat checks? (0<=n'M'<5, G/M modal groups)
            
            # Initialize block state
            blk = { 'next_action' : 'DEFAULT',
                    'absolute_override' : False,
                    'target_xyz' : deepcopy(gc['current_xyz']),
                    'offset_ijk' : [0,0,0],
                    'radius_mode' : False, 
                    'unsupported': [] }

            # Pass 1
            for cmd,num in zip(g_cmd,g_num) :
                fnum = float(num)
                inum = int(fnum)
                if cmd is 'G' :
                    if   inum is 0 : gc['motion_mode'] = 'SEEK'
                    elif inum is 1 : gc['motion_mode'] = 'LINEAR'
                    elif inum is 2 : gc['motion_mode'] = 'CW_ARC'
                    elif inum is 3 : gc['motion_mode'] = 'CCW_ARC'
                    elif inum is 4 : blk['next_action'] = 'DWELL'
                    elif inum is 17 : gc['plane_axis'] = [0,1,2]    # Select XY Plane
                    elif inum is 18 : gc['plane_axis'] = [0,2,1]    # Select XZ Plane
                    elif inum is 19 : gc['plane_axis'] = [1,2,0]    # Select YZ Plane
                    elif inum is 20 : gc['inches_mode'] = True      
                    elif inum is 21 : gc['inches_mode'] = False
                    elif inum in [28,30] : blk['next_action'] = 'GO_HOME'
                    elif inum is 53 : blk['absolute_override'] = True
                    elif inum is 80 : gc['motion_mode'] = 'MOTION_CANCEL'
                    elif inum is 90 : gc['absolute_mode'] = True
                    elif inum is 91 : gc['absolute_mode'] = False
                    elif inum is 92 : blk['next_action'] = 'SET_OFFSET'
                    elif inum is 93 : gc['inverse_feedrate_mode'] = True
                    elif inum is 94 : gc['inverse_feedrate_mode'] = False
                    else : 
                        print ('Unsupported command ' + cmd + num + ' on line ' + str(l_count) )
                        if remove_unsupported : blk['unsupported'].append(zip(g_cmd,g_num).index((cmd,num)))
                elif cmd is 'M' :
                    if   inum in [0,1] : pass   # Program Pause
                    elif inum in [2,30,60] : pass   # Program Completed
                    elif inum is 3 : pass   # Spindle Direction 1
                    elif inum is 4 : pass   # Spindle Direction -1
                    elif inum is 5 : pass   # Spindle Direction 0
                    else : 
                        print ('Unsupported command ' + cmd + num + ' on line ' + str(l_count) )
                        if remove_unsupported : blk['unsupported'].append(zip(g_cmd,g_num).index((cmd,num)))
                elif cmd is 'T' : pass      # Tool Number
                
            # Pass 2
            for cmd,num in zip(g_cmd,g_num) :
                fnum = float(num)         
                if   cmd is 'F' : gc['feed_rate'] = unit_conv(fnum)   # Feed Rate
                elif cmd in ['I','J','K'] : blk['offset_ijk'][ord(cmd)-ord('I')] = unit_conv(fnum) # Arc Center Offset
                elif cmd is 'P' : p = fnum  # Misc value parameter
                elif cmd is 'R' : r = unit_conv(fnum); blk['radius_mode'] = True    # Arc Radius Mode
                elif cmd is 'S' : pass      # Spindle Speed
                elif cmd in ['X','Y','Z'] : # Target Coordinates
                    if (gc['absolute_mode'] | blk['absolute_override']) :
                        blk['target_xyz'][ord(cmd)-ord('X')] = unit_conv(fnum)
                    else :
                        blk['target_xyz'][ord(cmd)-ord('X')] += unit_conv(fnum)

            # Execute actions
            if   blk['next_action'] is 'GO_HOME' : 
                gc['current_xyz'] = deepcopy(blk['target_xyz']) # Update position      
            elif blk['next_action'] is 'SET_OFFSET' : 
                pass 
            elif blk['next_action'] is 'DWELL' :
                if p < 0 : raise Exception('Dwell time negative.')
            else : # 'DEFAULT'
                if gc['motion_mode'] is 'SEEK' : 
                    gc['current_xyz'] = deepcopy(blk['target_xyz']) # Update position
                elif gc['motion_mode'] is 'LINEAR' :
                    gc['current_xyz'] = deepcopy(blk['target_xyz']) # Update position
                elif gc['motion_mode'] in ['CW_ARC','CCW_ARC'] :
                    axis = gc['plane_axis']
                    
                    # Convert radius mode to ijk mode
                    if blk['radius_mode'] :
                        x = blk['target_xyz'][axis[0]]-gc['current_xyz'][axis[0]]
                        y = blk['target_xyz'][axis[1]]-gc['current_xyz'][axis[1]]
                        if not (x==0 and y==0) : raise Exception('Same target and current XYZ not allowed in arc radius mode.') 
                        h_x2_div_d = -sqrt(4 * r*r - x*x - y*y)/hypot(x,y)
                        if isnan(h_x2_div_d) : raise Exception('Floating point error in arc conversion')
                        if gc['motion_mode'] is 'CCW_ARC' : h_x2_div_d = -h_x2_div_d
                        if r < 0 : h_x2_div_d = -h_x2_div_d
                        blk['offset_ijk'][axis[0]] = (x-(y*h_x2_div_d))/2;
                        blk['offset_ijk'][axis[1]] = (y+(x*h_x2_div_d))/2;
                                
                    # Compute arc center, radius, theta, and depth parameters
                    theta_start = atan2(-blk['offset_ijk'][axis[0]], -blk['offset_ijk'][axis[1]])
                    theta_end = atan2(blk['target_xyz'][axis[0]] - blk['offset_ijk'][axis[0]] - gc['current_xyz'][axis[0]], \
                                    blk['target_xyz'][axis[1]] - blk['offset_ijk'][axis[1]] - gc['current_xyz'][axis[1]])
                    if theta_end < theta_start : theta_end += 2*pi
                    radius = hypot(blk['offset_ijk'][axis[0]], blk['offset_ijk'][axis[1]])
                    depth = blk['target_xyz'][axis[2]]-gc['current_xyz'][axis[2]]
                    center_x = gc['current_xyz'][axis[0]]-sin(theta_start)*radius
                    center_y = gc['current_xyz'][axis[1]]-cos(theta_start)*radius
                    
                    # Compute arc incremental linear segment parameters
                    angular_travel = theta_end-theta_start
                    if gc['motion_mode'] is 'CCW_ARC' : angular_travel = angular_travel-2*pi
                    millimeters_of_travel = hypot(angular_travel*radius, fabs(depth))
                    if millimeters_of_travel is 0 : raise Exception('G02/03 arc travel is zero')
                    segments = int(round(millimeters_of_travel/mm_per_arc_segment))
                    if segments is 0 : raise Exception('G02/03 zero length arc segment')
    #        ???    # if gc['inverse_feedrate_mode'] : gc['feed_rate'] *= segments
                    theta_per_segment = angular_travel/segments
                    depth_per_segment = depth/segments
                    
                    # Generate arc linear segments
                    if verbose: print ('Converting: '+ block + ' : ' + str(l_count))
                    fout.append('G01F'+fout_conv(gc['feed_rate']))
                    if not gc['absolute_mode'] : fout.append('G90')    
                    arc_target = [0,0,0]
                    for i in range(1,segments+1) :
                        if i < segments : 
                            arc_target[axis[0]] = center_x + radius * sin(theta_start + i*theta_per_segment)
                            arc_target[axis[1]] = center_y + radius * cos(theta_start + i*theta_per_segment)
                            arc_target[axis[2]] = gc['current_xyz'][axis[2]] + i*depth_per_segment
                        else : 
                            arc_target = deepcopy(blk['target_xyz']) # Last segment at target_xyz
                        # Write only changed variables. 
                        if arc_target[0] != gc['current_xyz'][0] : fout.append('X'+fout_conv(arc_target[0]))
                        if arc_target[1] != gc['current_xyz'][1] : fout.append('Y'+fout_conv(arc_target[1]))
                        if arc_target[2] != gc['current_xyz'][2] : fout.append('Z'+fout_conv(arc_target[2]))
                        fout.append('\n')            
                        gc['current_xyz'] = deepcopy(arc_target) # Update position
                    if not gc['absolute_mode'] : fout.append('G91\n')    
                    
            # Rebuild original gcode block sans line numbers, extra characters, and unsupported commands
            if gc['motion_mode'] not in ['CW_ARC','CCW_ARC'] :
                if remove_unsupported and len(blk['unsupported']) : 
                    for i in blk['unsupported'][::-1] : del g_cmd[i]; del g_num[i]
                out_block = "".join([i+j for (i,j) in zip(g_cmd,g_num)]) 
                if len(out_block) : 
                    if verbose : print ("Writing: " + out_block + ' : ' + str(l_count))
                    fout.append(out_block + '\n')

    print ('Done!')
    return '\n'.join([str(elem) for elem in fout])