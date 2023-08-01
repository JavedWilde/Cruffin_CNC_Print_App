def word_wrapper(string, width):
    new_string=""
    while len(string)>width:
        #find the position of nearest whitespace char to left of "width"
        index=width-1
        #check the char in the index of string of given width
        #if it is space then continue
        #else reduce the index to check for the space.
        try:
            while not string[index].isspace():
                index=index-1
        except:
            index=index
        #remove the line from original string and add it to the new string
        line=string[0:index] + "\n"#separated individual linelines
        new_string=new_string+line#add those line to new_string variable
        string=''+string[index+1:]#updating the string to the remaining words
    #finally string will be left with less than the width.
    #adding those to the output
    return new_string+string

def word_wrap(text, limit):
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

# Example usage:
max_limit = 10
input_text = "Happy 6 month anniversary"
wrapped_text = word_wrap(input_text, max_limit)
print(wrapped_text)