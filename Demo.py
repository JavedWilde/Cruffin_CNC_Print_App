import Helpers
fontFile = f'Fonts/SVGFONT ({0}).svg'
gcode = Helpers.GetGcode("Happy 6 Month Anniversary",fontFile,5,8,0.9,750,750,25,6, True)
with open('drawing.gcode','w+') as f:
    f.write(gcode)