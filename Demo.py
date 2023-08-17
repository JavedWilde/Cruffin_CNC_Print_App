import random
import Helpers
import re
import matplotlib.pyplot as plt
from kivy.graphics.texture import Texture
from matplotlib.backends.backend_agg import FigureCanvasAgg
from PIL import Image, ImageDraw
greeting_messages = [
    "Happy birthday to you",
    "Cheers to your retirement",
    "Enjoy your special day",
    "Wishing you love and joy",
    "Merry Christmas dear friend",
    "Happy new year to you",
    "Have a great anniversary",
    "Happy Thanksgiving everyone",
    "Have a lovely Easter",
    "Enjoy your graduation day",
    "Have a warm Hanukkah",
    "Have a joyful Kwanzaa",
    "Happy Diwali to you",
    "Eid Mubarak my friend",
    "Happy Chinese New Year",
    "Have an amazing day",
    "Celebrate your achievements",
    "Happy first day at work",
    "Best wishes on promotion",
    "Stay blessed always",
    "Love on Valentine's Day",
    "Success on your venture",
    "Happy Mother's Day mom",
    "Happy Father's Day dad",
    "Happy Siblings Day bro",
    "Happy Women's Day to you",
    "Wishing a lovely Halloween",
    "Happy Name Day to you",
    "Well done on your success",
    "Congrats on your graduation",
    "Best wishes for baby shower",
    "Happy Healthy Heart Day",
    "Enjoy your house warming",
    "Proud of your achievement",
    "Happy Veteran's Day dad",
    "Happy Labor Day to you",
    "Happy Flag Day everyone",
    "Wishing a peaceful Memorial Day",
    "Happy Indigenous People's Day",
    "Pleased with your success",
    "Happy Friendship Day buddy",
    "Happy Fourth of July",
    "Happy Patriot Day dad",
    "Great job on the promotion",
    "Happy Presidents Day",
    "Have a sweet Valentine's",
    "Wishing a joyful life",
    "Happy Cinco de Mayo",
    "Happy Palm Sunday to you",
    "Happy Rose Day sweetheart",
    "Wishing a blessed life",
    "Happy Rustic Day",
    "Happy Holi to all",
    "Have a memorable trip",
    "Success on your launch",
    "Warm wishes this Christmas",
    "Happy Yom Kippur dad",
    "Happy Rosh Hashanah mom",
    "Celebrate every Earth Day",
    "Enjoy your reunion party",
    "Congrats on a job well done",
    "Wishing a blessed Ramadan",
    "Happy Pongal to you",
    "Enjoy your new journey",
    "Happy to celebrate together",
    "Enjoy your farewell party",
    "Congrats on your engagement",
    "Congrats on your wedding",
    "Happy Martin Luther Day",
    "Happy Bastille Day to all",
    "Have a happy weekend",
    "Happy Spring Day everyone",
    "Happy Earth Hour to all",
    "Happy Arbor Day everyone",
    "Wishing a pleasant summer",
    "Happy Teacher's Day sir",
    "Wishing a beautiful autumn",
    "Happy Children's Day kids",
    "Wishing a blessed Lent",
    "Let's celebrate this day",
    "Have a delightful picnic",
    "Create amazing Halloween memories",
    "Happy St Patrick's Day",
    "Happy Boxing Day all",
    "Welcome December with joy",
    "Celebrate the victory",
    "Happy Canada Day friend",
    "Happy Good Friday everyone",
    "Happy Hanukkah to everyone",
    "Best wishes for now",
    "Keep up the good work",
    "Bask in your achievement",
    "Good luck on your journey",
    "Happy Tu Bishvat friends",
    "Happy Passover to you",
    "Welcome the newborn baby",
    "Congrats on your achievement",
    "Wishing a merry time",
    "Happy Sweetest Day dear",
    "Congrats on your award",
]

def parse_gcode(gcode_text):
    x, y, z = 0, 0, 0
    x_values, y_values = [], []
    pen_down = False

    gcode_commands = re.findall(r"[Gg]\d+\s?(?:[Ff]\d+)?\s?(?:[Xx]?(-?\d+\.?\d*)\s?)?(?:[Yy]?(-?\d+\.?\d*)\s?)?(?:[Zz]?(-?\d+\.?\d*))?[;]?", gcode_text)
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

    return x_values, y_values

def plot_gcode_preview(gcode_text, filename):
    x_values, y_values = parse_gcode(gcode_text)
    
    fig, ax = plt.subplots()

    # Calculate the data range for x and y
    x_range = max(x for x in x_values if x is not None) - min(x for x in x_values if x is not None)
    y_range = max(y for y in y_values if y is not None) - min(y for y in y_values if y is not None)

    # Set the figure size based on the data range
    fig.set_size_inches(x_range*0.1, y_range*0.1)
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

    ax.plot(x_values, y_values, 'b-')  # Set the line color to white
    ax.set_xlim(min(x for x in x_values if x is not None),
                max(x for x in x_values if x is not None))
    ax.set_ylim(min(y for y in y_values if y is not None),
                max(y for y in y_values if y is not None))
    
    ax.set_xticks([])  # Remove x-axis ticks and labels
    ax.set_yticks([])  # Remove y-axis ticks and labels

    plt.savefig(filename, facecolor='black')  # Set the background color for the saved image
    plt.close()
def create_png(gcode_text, output_path, width, height):
    path = parse_gcode(gcode_text)

    # Filter out None values before calculating min/max
    valid_coords = [coord for coord in path if coord is not None]
    
    if valid_coords:
        min_x = min(coord[0] for coord in valid_coords)
        max_x = max(coord[0] for coord in valid_coords)
        min_y = min(coord[1] for coord in valid_coords)
        max_y = max(coord[1] for coord in valid_coords)
    else:
        min_x = max_x = min_y = max_y = 0
    
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    prev_x, prev_y = None, None
    for coord in path:
        if coord is not None:
            x, y = coord
            x = int((x - min_x) / (max_x - min_x) * (width - 1))
            y = int((y - min_y) / (max_y - min_y) * (height - 1))
            if prev_x is not None and prev_y is not None:
                draw.line([(prev_x, prev_y), (x, y)], fill=(0, 0, 0))
            prev_x, prev_y = x, y
        elif coord is None:
            prev_x, prev_y = None, None
    
    img.save(output_path, 'PNG')

# for i,msg in enumerate(greeting_messages):
#     if len(msg) > 25:
#         msg = msg[:24]
#     fontFile = f'Fonts/SVGFONT ({0}).svg'
#     gcode = Helpers.GetGcode(msg,fontFile,0,0,0.9,750,750,25,6, True)
#     #with open('drawing.gcode','w+') as f:
#     #    f.write(gcode)

#     plot_gcode_preview(gcode, f"_Preview3/{i}.png")
fontFile = f'Fonts/SVGFONT ({4}).svg'
gcode = Helpers.GetGcode("Happy Birthday Aprajita",fontFile,5,10,1,750,750,25,6, True, 70, 40,10,10)
create_png(gcode, f"_FontPreview/{0}.png", 512, 256)
#plot_gcode_preview(gcode, f"_FontPreview/{0}.png")