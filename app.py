from importlib import reload
import pygame
import time
from pygame._sdl2.video import Window # Keep this for later access if needed
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import importlib
import math
from watchertest import watcher
import shader_wrapper

import os

import json

WINDOW_STATE_FILE = "window_state.json"


# Default values
DEFAULT_WIDTH = 1920//2
DEFAULT_HEIGHT = 1080-70
WINDOW_X = 1920//2
WINDOW_Y = 30

get_shader_has_changed = watcher(shader_wrapper.shader_file)

# --- CONFIGURAÇÕES ---
EXTENT = 5
VOXEL_SIZE = 1
ZOOM = -30.0
SENSITIVITY = 0.3
CUBE_LIST_ID = 0

# --- PALETA DE CORES (16 cores + vazio) ---
PALETTE = [
    (0.0,   0.0,   0.0,   0.0),   # 0 = vazio (transparent)
    (0.910, 0.933, 0.969, 1.0),   # 1  -> #E8EEF7 (very light bluish-gray)
    (0.561, 0.627, 0.710, 1.0),   # 2  -> #8FA0B5 (muted blue-gray)
    (0.067, 0.071, 0.075, 1.0),   # 3  -> #111213 (very dark charcoal)
    (0.953, 0.714, 0.690, 1.0),   # 4  -> #F3B6B0 (soft pink)
    (0.902, 0.490, 0.741, 1.0),   # 5  -> #E67DBD (pink/magenta)
    (0.569, 0.188, 0.486, 1.0),   # 6  -> #91307C (purple)
    (0.867, 0.227, 0.227, 1.0),   # 7  -> #DD3A3A (red)
    (0.945, 0.545, 0.188, 1.0),   # 8  -> #F18B30 (orange)
    (0.957, 0.824, 0.302, 1.0),   # 9  -> #F4D24D (yellow/orange)
    (0.776, 0.882, 0.255, 1.0),   # 10 -> #C6E141 (lime green)
    (0.478, 0.761, 0.255, 1.0),   # 11 -> #7AC241 (green)
    (0.165, 0.153, 0.251, 1.0),   # 12 -> #2A2740 (dark indigo)
    (0.149, 0.200, 0.420, 1.0),   # 13 -> #26336B (deep blue)
    (0.514, 0.663, 0.886, 1.0),   # 14 -> #83A9E2 (light blue)
    (0.725, 0.416, 0.400, 1.0),   # 15 -> #B96A66 (warm brown/red)
    (0.353, 0.180, 0.180, 1.0),   # 16 -> #5A2E2E (dark maroon)
]

# --- GEOMETRIA DO CUBO ---
def _define_cube_geometry():
    h = VOXEL_SIZE / 2.0
    vertices = (
        (h, h, -h), (h, -h, -h), (-h, -h, -h), (-h, h, -h),
        (h, h, h), (h, -h, h), (-h, -h, h), (-h, h, h)
    )
    faces = [
        ((0, 0, -1), (0, 1, 2, 3)),
        ((0, 0, 1), (4, 5, 6, 7)),
        ((1, 0, 0), (0, 4, 5, 1)),
        ((-1, 0, 0), (3, 7, 6, 2)),
        ((0, 1, 0), (0, 3, 7, 4)),
        ((0, -1, 0), (1, 2, 6, 5))
    ]
    glBegin(GL_QUADS)
    for normal, face in faces:
        glNormal3fv(normal)
        for vertex in face:
            glVertex3fv(vertices[vertex])
    glEnd()


def compile_cube_display_list():
    global CUBE_LIST_ID
    CUBE_LIST_ID = glGenLists(1)
    glNewList(CUBE_LIST_ID, GL_COMPILE)
    _define_cube_geometry()
    glEndList()
    return CUBE_LIST_ID


# --- OPENGL SETUP ---
def setup_opengl(width, height):
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, width / height, 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glEnable(GL_DEPTH_TEST)
    glShadeModel(GL_SMOOTH)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_POSITION, (50, 50, 50, 1))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (1, 1, 1, 1))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.2, 0.2, 0.2, 1))
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glEnable(GL_NORMALIZE)

# --- LOOP PRINCIPAL ---
def main_loop():
    global shader
    must_reset = False
    os.environ['SDL_VIDEO_WINDOW_POS'] = f"{WINDOW_X},{WINDOW_Y}"
    pygame.init()
    display = (DEFAULT_WIDTH, DEFAULT_HEIGHT)
    screen = pygame.display.set_mode(display,  DOUBLEBUF | OPENGL | RESIZABLE)
    pygame.display.set_caption("Voxel Shader Modular (Python + OpenGL)")

    window = Window.from_display_module()
    pos_x, pos_y = window.position

    setup_opengl(*display)

    # --- gera voxels ---
    active_voxels = []
    print("Gerando voxels a partir do shader...")
    for x in range(-EXTENT, EXTENT + 1):
        for y in range(-EXTENT, EXTENT + 1):
            for z in range(-EXTENT, EXTENT + 1):
                value = int(shader_wrapper.shader(x, y, z, EXTENT)) % 16
                if value is not None and 0 < value < len(PALETTE):
                    pos = (x * VOXEL_SIZE, y * VOXEL_SIZE, z * VOXEL_SIZE)
                    color = PALETTE[value]
                    active_voxels.append({'pos': pos, 'color': color})
    print(f"{len(active_voxels)} voxels gerados.")

    compile_cube_display_list()

    # --- parâmetros de câmera ---
    yaw = 45.0       # rotação horizontal
    pitch = 30.0     # rotação vertical
    radius = 25.0    # distância da câmera
    sensitivity = 0.3
    mouse_down = False
    last_mouse_pos = (0, 0)

    # centro da cena (pode ajustar dinamicamente se quiser)
    center = [0.0, 0.0, 0.0]

    clock = pygame.time.Clock()
    running = True
    reset = False

    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == VIDEORESIZE:
                setup_opengl( event.w,event.h)
            elif event.type == KEYDOWN and event.key == K_r:
                active_voxels.clear()
                for x in range(-EXTENT, EXTENT + 1):
                    for y in range(-EXTENT, EXTENT + 1):
                        for z in range(-EXTENT, EXTENT + 1):
                            try:
                                value = int(shader_wrapper.shader(x, y, z, EXTENT)) % 16
                            except Exception as e:
                                print(time.strftime('%c',e,end='\r'))
                                value = 0
                            if value and 0 < value < len(PALETTE):
                                pos = (x * VOXEL_SIZE, y * VOXEL_SIZE, z * VOXEL_SIZE)
                                color = PALETTE[value]
                                active_voxels.append({'pos': pos, 'color': color})
                print(f"{len(active_voxels)} voxels após reload.")
            elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                mouse_down = True
                last_mouse_pos = event.pos
            elif event.type == MOUSEBUTTONUP and event.button == 1:
                mouse_down = False
            elif event.type == MOUSEMOTION and mouse_down:
                dx, dy = event.pos[0] - last_mouse_pos[0], event.pos[1] - last_mouse_pos[1]
                yaw -= dx * sensitivity
                pitch += dy * sensitivity
                pitch = max(-89, min(89, pitch))
                last_mouse_pos = event.pos
            elif event.type == MOUSEWHEEL:
                radius -= event.y * 1.0
                radius = max(5.0, min(80.0, radius))

        # calcula posição da câmera em coordenadas esféricas
        cam_x = center[0] + radius * math.cos(math.radians(pitch)) * math.sin(math.radians(yaw))
        cam_y = center[1] + radius * math.sin(math.radians(pitch))
        cam_z = center[2] + radius * math.cos(math.radians(pitch)) * math.cos(math.radians(yaw))

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # câmera orbitando o centro
        gluLookAt(cam_x, cam_y, cam_z, center[0], center[1], center[2], 0, 1,0)

        # desenha os voxels centrados
        glPushMatrix()

        for v in active_voxels:
            glPushMatrix()
            glTranslatef(*v['pos'])
            glColor4fv(v['color'])
            glCallList(CUBE_LIST_ID)
            glPopMatrix()

        glPopMatrix()

        pygame.display.flip()
        clock.tick(60)
        
        shader_changed = get_shader_has_changed()
        if shader_changed:
            importlib.reload(shader_wrapper)
            reset = True
            running = False

    glDeleteLists(CUBE_LIST_ID, 1)
    pygame.quit()
    return reset

if __name__ == "__main__":
    must_reset = False
    while 1:
        print(main_loop())