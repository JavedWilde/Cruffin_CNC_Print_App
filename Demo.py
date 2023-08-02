import random
import Helpers
import re
import matplotlib.pyplot as plt
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
    x_values, y_values = [0], [0]
    z_axis_up = False

    gcode_commands = re.findall(r"[Gg]\d+\s?(?:[Ff]\d+)?\s?(?:[Xx]?(-?\d+\.?\d*)\s?)?(?:[Yy]?(-?\d+\.?\d*)\s?)?(?:[Zz]?(-?\d+\.?\d*))?[;]?", gcode_text)
    for command in gcode_commands:
        if command[0]:
            x = float(command[0])
        if command[1]:
            y = float(command[1])
        if command[2]:
            z = float(command[2])
            if z < 0:
                z_axis_up = False
            elif z >= 0:
                z_axis_up = True
        
        if not z_axis_up:
            x_values.append(x)
            y_values.append(y)

    return x_values, y_values

def plot_gcode_preview(gcode_text, filename):
    x_values, y_values = parse_gcode(gcode_text)

    plt.figure(figsize=(8, 6))
    plt.plot(x_values, y_values, 'b-')
    plt.xlabel('X (mm)')
    plt.ylabel('Y (mm)')
    plt.title('G-code Preview from Top View')
    #plt.grid()
    plt.savefig(filename)
    plt.close()

# for i,msg in enumerate(greeting_messages):
#     if len(msg) > 25:
#         msg = msg[:24]
#     fontFile = f'Fonts/SVGFONT ({0}).svg'
#     gcode = Helpers.GetGcode(msg,fontFile,0,0,0.9,750,750,25,6, True)
#     #with open('drawing.gcode','w+') as f:
#     #    f.write(gcode)

#     plot_gcode_preview(gcode, f"_Preview3/{i}.png")

fontFile = f'Fonts/SVGFONT ({0}).svg'
gcode = Helpers.GetGcode("Happy Birthday Aprajita",fontFile,5,8,0.9,750,750,25,6, True)
# with open('drawing.gcode','w+') as f:
#     f.write(gcode)
plot_gcode_preview(gcode, f"_FontPreview/{0}.png")