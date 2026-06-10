import math
from pathlib import Path
import src.hiveplot

WIDTH = 800
HEIGHT = 800
CENTER_X = WIDTH / 2
CENTER_Y = HEIGHT / 2
AXIS_OFFSET = 50
# CENTER_X_OFFSET = CENTER_X + 25
# CENTER_Y_OFFSET = CENTER_Y + 25
MAX_RADIUS = min(WIDTH, HEIGHT) / 2 - 50 # kantenlängen einschränken

def translate_polar_to_carthesian(radius, angle, center_x=CENTER_X, center_y=CENTER_Y):
    angle = math.radians(angle)
    x = center_x + radius * math.cos(angle)
    y = center_y + radius * math.sin(angle)
    return x, y

def draw_basis(node_groups, edges, intra_edges = None): 
    svg_axes = []
    svg_nodes = []
    svg_edges = []
    rendered_node_positions = {}
    for i, (axis, nodes) in enumerate(node_groups.items()): # achsen anlegen
        real_nodes = []
        virtual_nodes = []
        angle = 270 + i * (360/len(node_groups)) # erste achse nördlich und alle anderen relativ dazu
        x_end, y_end = translate_polar_to_carthesian(MAX_RADIUS, angle, CENTER_X, CENTER_Y)
        x_start, y_start = translate_polar_to_carthesian(AXIS_OFFSET, angle, CENTER_X, CENTER_Y)
        x_label, y_label = translate_polar_to_carthesian(37, angle, CENTER_X, CENTER_Y) # leicht versetztes achsenlabel
        svg_axes.append(f'<line x1="{x_start}" y1="{y_start}" x2="{x_end}" y2="{y_end}" stroke="black" stroke-width="1"/>')
        svg_axes.append(f'<text x="{x_label}" y="{y_label}" text-anchor="middle" dominant-baseline="middle" font-size="12">{axis}</text>')
        for node in nodes:
            if isinstance(node, int):
                real_nodes.append(node)
            elif isinstance(node, str):
                virtual_nodes.append(node)
        for j, real in enumerate(real_nodes, start=1):
            radius = AXIS_OFFSET + j * (MAX_RADIUS - AXIS_OFFSET) / (len(real_nodes) + 1)
            x, y = translate_polar_to_carthesian(radius, angle, CENTER_X, CENTER_Y)
            rendered_node_positions[real] = (x, y)
            svg_nodes.append(f'<circle cx="{x}" cy="{y}" r="2" fill="#e01414"/>')
        for j, virtual in enumerate(virtual_nodes, start=1):
            radius = MAX_RADIUS + j * 50/ (len(virtual_nodes) + 1) # (MAX_RADIUS + 50 - MAX_RADIUS)
            x, y = translate_polar_to_carthesian(radius, angle, CENTER_X, CENTER_Y)
            rendered_node_positions[virtual] = (x, y)
            svg_nodes.append(f'<circle cx="{x}" cy="{y}" r="0" fill="#e01414"/>')
    for edge in edges:
        u_x, u_y = rendered_node_positions[edge[0]]
        v_x, v_y = rendered_node_positions[edge[1]]
        x_mid = (u_x + v_x) /2
        y_mid = (u_y + v_y) /2
        if (isinstance(edge[0], int) and isinstance(edge[1], int)) or (isinstance(edge[0], str) and isinstance(edge[1], str)): # beide real oder virtuell
            alpha = -0.15
        elif (isinstance(edge[0], str) and isinstance(edge[1], int)) or (isinstance(edge[1], str) and isinstance(edge[0], int)): # mixed
            alpha = -0.5
        x_fix = x_mid + (CENTER_X - x_mid) * alpha
        y_fix = y_mid + (CENTER_Y - y_mid) * alpha
        svg_edges.append(f'<path d="M {u_x},{u_y} Q {x_fix},{y_fix} {v_x},{v_y}" fill="none" stroke="gray" stroke-width="1.2" opacity="0.5"/>')
    if intra_edges is not None:
        for edge in intra_edges:
            u_x, u_y = rendered_node_positions[edge[0]]
            v_x, v_y = rendered_node_positions[edge[1]]
            dx = v_x - u_x # senkrecht zur achse versetzen, da auf gleicher achse
            dy = v_y - u_y  
            x_mid = (u_x + v_x) /2
            y_mid = (u_y + v_y) /2
            alpha = 1
            x_fix = x_mid - dy * 0.3
            y_fix = y_mid + dx * 0.3
            svg_edges.append(f'<path d="M {u_x},{u_y} Q {x_fix},{y_fix} {v_x},{v_y}" fill="none" stroke="gray" stroke-width="1.2" opacity="0.5"/>')
    return svg_axes, svg_nodes, svg_edges

def draw_nodes():
    pass

def draw_edges():
    pass

def write_info_text():
    pass

def render_svg(filename, width, height, elements):
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', *elements,'</svg>',]
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))

def hiveplot_renderer(name, layout: HivePlotLayout, expanded=False, intra=False):
    intra=intra
    if expanded:
        node_groups = layout.node_groups_expanded
    else:
        node_groups = layout.node_groups
    elements = ["<rect width='100%' height='100%' fill='white'/>"] # weißer hintergrund
    if intra:
        ax, nod, ed = draw_basis(node_groups, layout.edges(), layout.intra_axis_edges)
    else:
        ax, nod, ed = draw_basis(node_groups, layout.edges())
    elements.extend(ax)
    elements.extend(ed)
    elements.extend(nod)
    output = Path("output/debug")
    filename = output / (name + ".svg")
    output.mkdir(parents=True, exist_ok=True)
    render_svg(filename, WIDTH, HEIGHT, elements)

if __name__ == "__main__":
    from src.graphs import sample_graph_multipartite, sample_graph_selfconstructed_extended
    import src.hiveplot as hpl
    graph_mode = 3
    G = sample_graph_selfconstructed_extended(graph_mode)
    a_order = [0, 1, 5, 4, 2, ]
    ng = {0: [1, 2, 0, 'd_4_11_1', 'd_5_11_1'], 1: [3, 4, 5, 'd_0_24_1'], 5: [19, 20, 21, 22, 24, 23, 25, 27, 28, 26, 'd_5_18_1'], 4: [14, 16, 15, 13, 17, 18], 2: [7, 6, 8, 'd_9_16_1'], 3: [9, 10, 11, 12, 'd_1_7_1', 'd_2_8_1']}
    layout = hpl.HivePlotLayout(
        graph=G,
        axis_order = a_order,
        num_axes=len(a_order),
        node_groups=ng,
    )
    hiveplot_renderer("test", layout)