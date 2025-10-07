shader_file = 'shader.py'

with open(shader_file,'r',encoding='utf8') as w:
    shader_script = w.read().splitlines()
    vars_ = '\n'.join([f'{b}={a}' for a,b in enumerate('EMPTY,WHITE,GREY,BLACK,PEACH,PINK,PURPLE,RED,ORANGE,YELLOW,LIGHTGREEN,GREEN,DARKBLUE,BLUE,LIGHTBLUE,BROWN,DARKBROWN'.split(','))])
    x = f'from math import *\n{vars_}\ndef shader(x,y,z,extent):\n' + '\n'.join(['    '+i for i in shader_script])
    exec(x)
