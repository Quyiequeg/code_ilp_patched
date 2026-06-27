import math
from pathlib import Path
import hiveplot
import generator as gr
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
import statistics

WIDTH = 1000
HEIGHT = 1000
CENTER_X = WIDTH / 2   # Koordinatenursprung horizontal
CENTER_Y = HEIGHT / 2  # Koordinatenursprung vertikal
AXIS_OFFSET = 50       # Mindestabstand der Achsen vom Zentrum (px)
MAX_RADIUS = min(WIDTH, HEIGHT) / 2 - 75  # Maximale Achsenlänge (px)

def translate_polar_to_carthesian(radius: float, angle: float, center_x: float = CENTER_X, center_y: float = CENTER_Y) -> tuple[float, float]:
    """ Umrechnung der Polarkoordinate in ein karthesisches Tupel.
    """
    angle = math.radians(angle)
    x = center_x + radius * math.cos(angle)
    y = center_y + radius * math.sin(angle)
    return x, y

def draw_basis(layout, node_groups: dict[int, list[str | int]], edges: list[tuple[int | str, int | str]], degree: bool = False, id_to_label_map: dict[int, str] | None = None, unordered: bool = False, intra_edges: list[tuple[int | str, int | str]] | None = None, axes_labels: bool = True) -> tuple[list[str], list[str], list[str], list[str]]:

    def shorten_label(name: str) -> str:
        import re
        name = re.sub(r'\s*\d+', '', name).strip()
        tokens = name.split()
        if not tokens:
            return name
        last = tokens[-1]
        first_initial = tokens[0][0] + "."
        return f"{first_initial} {last}"

    if degree: # falls filter aktiv prioritätsliste erstellen
        degrees = dict(layout.graph.degree())
        priority_nodes = []
        for axis in node_groups:
            real_nodes = [node for node in node_groups[axis] if isinstance(node, int)]
            if not real_nodes:
                continue
            axis_degrees = [degrees[node] for node in real_nodes]
            medi = statistics.median(axis_degrees)
            for node in real_nodes:
                if degrees[node] >= medi:
                    priority_nodes.append(node)
        priority_set = set(priority_nodes)
    svg_axes = []
    svg_nodes = []
    svg_edges = []
    svg_labels = []
    rendered_node_positions = {}
    for i, (axis, nodes) in enumerate(node_groups.items()):
        real_nodes = []
        virtual_nodes = []
        angle = 270 + i * (360 / len(node_groups)) # theta
        x_end, y_end = translate_polar_to_carthesian(MAX_RADIUS, angle, CENTER_X, CENTER_Y)
        x_start, y_start = translate_polar_to_carthesian(AXIS_OFFSET, angle, CENTER_X, CENTER_Y)
        x_label, y_label = translate_polar_to_carthesian(AXIS_OFFSET * 0.85, angle, CENTER_X, CENTER_Y)
        svg_axes.append(f'<line x1="{x_start}" y1="{y_start}" x2="{x_end}" y2="{y_end}" stroke="black" stroke-width="1"/>')
        if axes_labels:
            if axis > 0: # originale beschriften
                svg_axes.append(f'<text x="{x_label}" y="{y_label}" text-anchor="middle" dominant-baseline="middle" font-size="10" fill="#4f4f4f">'f'A<tspan dy="3" font-size="6">{axis}</tspan>'f'</text>')
            else: # expandierte teile beschriften
                svg_axes.append(f'<text x="{x_label}" y="{y_label}" text-anchor="middle" dominant-baseline="middle" font-size="9" fill="#7e7e7e">'f'A<tspan dy="3" font-size="5">{axis}</tspan>'f'</text>')
        for node in nodes:
            if isinstance(node, int):
                real_nodes.append(node)
            elif isinstance(node, str):
                virtual_nodes.append(node)
        for j, real in enumerate(real_nodes, start=1):
            radius = AXIS_OFFSET + j * (MAX_RADIUS - AXIS_OFFSET) / (len(real_nodes) + 1)
            x, y = translate_polar_to_carthesian(radius, angle, CENTER_X, CENTER_Y)
            rendered_node_positions[real] = (x, y) # koordinaten speichern
            if degree and real in priority_set: # wenn prio und filteroption gesetzt
                svg_nodes.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#d77b7b"/>')
            else: # alle knoten
                svg_nodes.append(f'<circle cx="{x}" cy="{y}" r="3" fill="#d77b7b"/>')
            if unordered or real > 0: # auch expandierte achsen oder nur originale
                LABEL_OFFSET = 6
                fontsize = 6
                if id_to_label_map: # nur wenn übergeben, sonst knotenID
                    label_text = shorten_label(id_to_label_map[abs(real)])
                else:
                    label_text = str(real)
                angle_radius = math.radians(angle) # bogenmaß aus polar
                cos_angle = math.cos(angle_radius) # richtungsvektor der achse, x
                sin_angle = math.sin(angle_radius) # richtungsvektor der achse, y
                flipped = False # auf rechte seite der horizontalen setzen
                if cos_angle < 0:
                    flipped = True 
                if real > 0: # 
                    rotation = (angle - 270) % 360 + 240
                else:
                    rotation = (angle - 270) % 360 - 67.5
                if flipped: # auf linke seite der horizontalen spiegeln
                    rotation += 180
                if flipped:
                    if real > 0: # originale achse
                        lx = x + LABEL_OFFSET * sin_angle
                        ly = y - LABEL_OFFSET * cos_angle
                    else:
                        lx = x - LABEL_OFFSET * sin_angle
                        ly = y + LABEL_OFFSET * cos_angle
                else: # expandierte achse
                    if real > 0:
                        lx = x + LABEL_OFFSET * sin_angle
                        ly = y - LABEL_OFFSET * cos_angle
                    else:
                        lx = x - LABEL_OFFSET * sin_angle
                        ly = y + LABEL_OFFSET * cos_angle

                anchor = "end" if cos_angle < 0 else "start"

                if unordered and degree:
                    if real in priority_set:
                        svg_labels.append(f'<text x="{lx}" y="{ly}" font-size="{fontsize}" 'f'text-anchor="{anchor}" dominant-baseline="central" 'f'transform="rotate({rotation},{lx},{ly})">{label_text}</text>')
                else:
                    svg_labels.append(f'<text x="{lx}" y="{ly}" font-size="{fontsize}" 'f'text-anchor="{anchor}" dominant-baseline="central" 'f'transform="rotate({rotation},{lx},{ly})">{label_text}</text>')
        for j, virtual in enumerate(virtual_nodes, start=1):
            parts = virtual.split('_')
            is_mirror = len(parts) == 4 and int(parts[3] ) < 0
            if is_mirror:
                # Spiegel-Dummy: gleiche Position wie der Original-Dummy auf dieser Achse
                original = f"d_{parts[1]}_{parts[2]}_{-int(parts[3])}"
                ox, oy = rendered_node_positions[original]
                orig_radius = math.hypot(ox - CENTER_X, oy - CENTER_Y)
                x, y = translate_polar_to_carthesian(orig_radius, angle, CENTER_X, CENTER_Y)
            else:
                radius = MAX_RADIUS + j * 50 / (len(virtual_nodes) + 1)
                x, y = translate_polar_to_carthesian(radius, angle, CENTER_X, CENTER_Y)
            rendered_node_positions[virtual] = (x, y)
            svg_nodes.append(f'<circle cx="{x}" cy="{y}" r="0" fill="#AED6F1"/>')
            
            
            
            # radius = MAX_RADIUS + j * 50 / (len(virtual_nodes) + 1)
            # x, y = translate_polar_to_carthesian(radius, angle, CENTER_X, CENTER_Y)
            # rendered_node_positions[virtual] = (x, y)
            # svg_nodes.append(f'<circle cx="{x}" cy="{y}" r="0" fill="#AED6F1"/>')
    for edge in edges:
        u_x, u_y = rendered_node_positions[edge[0]]
        v_x, v_y = rendered_node_positions[edge[1]]
        x_mid = (u_x + v_x) / 2
        y_mid = (u_y + v_y) / 2
        both_real = False
        both_virtual = False
        if isinstance(edge[0], int) and isinstance(edge[1], int): #intra/inter
            both_real = True
        if isinstance(edge[0], str) and isinstance(edge[1], str): # achsenverbindung original zu expandiert
            both_virtual = True

        dx = x_mid - CENTER_X # richtungsvektor ursprung zu mitte, x
        dy = y_mid - CENTER_Y # richtungsvektor ursprung zu mitte, y
        dist = math.hypot(dx, dy)

        if both_real:
            pull = dist * 0.15
        elif both_virtual:
            pull = dist * 0.1
        else:
            pull = min(85, dist * 0.3)          
        if dist > 0:
            x_fix = x_mid + (dx / dist) * pull
            y_fix = y_mid + (dy / dist) * pull
        else: # fall back gerade zeichnen
            x_fix, y_fix = x_mid, y_mid
        svg_edges.append(f'<path d="M {u_x},{u_y} Q {x_fix},{y_fix} {v_x},{v_y}" 'f'fill="none" stroke="gray" stroke-width="1" opacity="0.5"/>')

    if intra_edges is not None:
        for edge in intra_edges:
            u_x, u_y = rendered_node_positions[edge[0]]
            v_x, v_y = rendered_node_positions[edge[1]]
            dx = v_x - u_x
            dy = v_y - u_y
            x_mid = (u_x + v_x) / 2
            y_mid = (u_y + v_y) / 2
            alpha = 0.5
            x_fix = x_mid - dy * alpha
            y_fix = y_mid + dx * alpha
            svg_edges.append(f'<path d="M {u_x},{u_y} Q {x_fix},{y_fix} {v_x},{v_y}" fill="none" stroke="gray" stroke-width="1.2" opacity="0.5"/>')

    return svg_axes, svg_nodes, svg_edges, svg_labels

def render_svg(filename: Path | str, width: int, height: int, elements: list[str]) -> None:
    """ Setzt den Header der .svg Datei und hängt die Graphenelemente an und setzt die Schlussklausel. Datei wird neu erstellt bzw. überschrieben, falls sie bereits existiert.
    """
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', *elements,'</svg>',]
    with open(filename, "w", encoding="utf-8") as file:
        file.write("\n".join(svg))

def hiveplot_renderer(name: str, layout: HivePlotLayout, debug_dir: Path, degree: bool = True, expanded: bool = False, intra: bool = False, mode: str = "debug", node_labels: bool =True, axes_labels: bool =True, unordered: bool = False) -> Path:
    """ Pipeline die das Rendern des fertig berechneten Hiveplotlayouts in eine Scalable Vector Graphics (.svg) realisiert.
    """
    id_to_label_map = layout.id_to_name
    if expanded:
        node_groups = layout.node_groups_expanded
    else:
        node_groups = layout.node_groups
    elements = ["<rect width='100%' height='100%' fill='white'/>"] # weißer hintergrund
    # elements = [] # kein hintergrund
    if intra:
        ax, nod, ed, lab = draw_basis(layout, node_groups, list(layout.edges()), id_to_label_map=id_to_label_map, unordered=unordered, degree=degree, intra_edges=layout.intra_axis_edges,
                                    axes_labels=axes_labels)
    else:
        ax, nod, ed, lab = draw_basis(layout, node_groups, list(layout.edges()), id_to_label_map=id_to_label_map, unordered = unordered, degree=degree,  axes_labels=axes_labels)
    elements.extend(ax)
    elements.extend(ed)
    elements.extend(nod)
    if node_labels:
        elements.extend(lab)

    filename = debug_dir / (name + ".svg")
    render_svg(filename, WIDTH, HEIGHT, elements)
    return filename

    

if __name__ == "__main__":
    from partitioning import (
    clauset_newman_moore_communities,
    louvain_community_detection,
    )
    from dblp_parser import (
        build_node_identity_maps,
    )
    from ordering import (
        native_order,
        node_groups,
        brute_force_ordering,
        reordered_node_groups,
        node_to_axis_maps,
    )
    import crossing_minimization as cm
    from ip_model import (
        ip_model_pipeline
    )

    from hiveplot import HivePlotLayout
    from renderer import hiveplot_renderer
    import re
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF
    gr.settings(fr"E:\Programming Workspace\Python\BA-Sauerteig\output\ba\beispiel_vor_3a.svg", node_pt=8, line_pt=3, text_pt=25, draw_dummys=False)
    drawing = svg2rlg(r"E:\Programming Workspace\Python\BA-Sauerteig\output\ba\beispiel_vor_3a.svg")
    renderPDF.drawToFile(drawing, r"E:\Programming Workspace\Python\BA-Sauerteig\output\ba\beispiel_vor_3a.pdf")