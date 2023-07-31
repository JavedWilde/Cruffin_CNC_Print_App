import Helpers
fontFile = f'Fonts/SVGFONT ({0}).svg'
gcode = Helpers.GetGcode("David",fontFile,5,8,0.9,750,750,25,6)
with open('drawing.gcode','w+') as f:
    f.write(gcode)

