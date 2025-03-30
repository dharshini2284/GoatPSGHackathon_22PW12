import sys
import random
import tkinter as tk
from tkinter import messagebox, scrolledtext
import json
import os
import matplotlib.pyplot as plt
import networkx as nx

# Ensure the logs directory exists
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "fleet_logs.txt")
os.makedirs(LOG_DIR, exist_ok=True)

# Clear log file for each execution
with open(LOG_FILE, "w", encoding="utf-8") as log_file:
    log_file.write("")

# Custom class to log messages
class DualLogger:
    def __init__(self, text_widget):
        self.terminal = sys.stdout
        self.text_widget = text_widget
        self.log_file = open(LOG_FILE, "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.terminal.flush()
        self.text_widget.insert(tk.END, message)
        self.text_widget.see(tk.END)
        self.log_file.write(message)
        self.log_file.flush()

    def flush(self):
        self.terminal.flush()
        self.log_file.flush()

    def close(self):
        self.log_file.close()

# Loading navigation graph
def load_nav_graph(filename):
    try:
        with open(filename, 'r') as file:
            data = json.load(file)
    except Exception as e:
        print(f"Error loading navigation graph: {e}")
        return None, None
    level = list(data["levels"].values())[0]
    return level["vertices"], level["lanes"]

# Function to assign vertex types
def get_vertex_type(attrs):
    if "charging" in attrs and attrs["charging"]:
        return "charging"
    elif "name" in attrs:
        return "named"
    return "regular"

# Tkinter Log Window
def create_log_window():
    root = tk.Tk()
    root.title("Fleet Management System - Logs")
    root.geometry("600x400")

    log_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=70, height=20)
    log_text.pack(pady=10)

    sys.stdout = DualLogger(log_text)
    sys.stderr = DualLogger(log_text)

    return root

# Generating a random color for each robot
def random_color():
    return f'#{random.randint(0, 255):02x}{random.randint(0, 255):02x}{random.randint(0, 255):02x}'

# Draw the navigation graph and handle robot spawning/movement
def draw_graph(vertices, lanes):
    if not vertices or not lanes:
        print("Error: No valid vertices or lanes to draw.")
        return

    G = nx.Graph()
    pos = {}
    fig, ax = plt.subplots(figsize=(8, 6))

    robots = {}
    robot_colors = {}
    robot_status = {}
    robot_tasks = {}
    selected_robot = None

    # Add vertices with positions
    for i, (x, y, attrs) in enumerate(vertices):
        G.add_node(i)
        pos[i] = (x, y)
        vertex_type = get_vertex_type(attrs)

        color = "lightblue"
        if vertex_type == "charging":
            color = "green"
        elif vertex_type == "named":
            color = "orange"

        nx.draw_networkx_nodes(G, pos, nodelist=[i], node_color=color, node_size=500)

    # Add edges
    for start, end, _ in lanes:
        G.add_edge(start, end)

    nx.draw_networkx_edges(G, pos, edge_color='gray')
    nx.draw_networkx_labels(G, pos, font_size=10)

    def draw_static_graph():
        plt.clf()
        nx.draw(G, pos, with_labels=False, node_size=500, node_color='lightblue', edge_color='gray')

        # Identify and mark intersections (nodes with 3+ edges)
        intersections = [node for node in G.nodes if len(G[node]) >= 3]

        # Draw named locations in blue and bold
        for i, (_, _, attrs) in enumerate(vertices):
            if "name" in attrs:
                plt.text(pos[i][0], pos[i][1] + 0.15, attrs["name"], fontsize=9, ha='center', color='blue', fontweight='bold')

        # Mark intersections with "X" in red
        for node in intersections:
            plt.text(pos[node][0], pos[node][1], "X", fontsize=12, ha='center', color='red', fontweight='bold')

        # Draw robot positions
        for rid, loc in robots.items():
            plt.scatter(pos[loc][0], pos[loc][1], s=600, color=robot_colors[rid], edgecolors="black", zorder=3)
            plt.text(pos[loc][0], pos[loc][1] + 0.1, f"R{rid}", fontsize=9, ha='center', color='black', bbox=dict(facecolor='white', alpha=0.6))

        # Show node numbers again
        nx.draw_networkx_labels(G, pos, font_size=10, font_color="black")

        plt.draw()

    def process_robot_tasks(robot_id):
        while robot_tasks[robot_id]:
            next_destination = robot_tasks[robot_id].pop(0)
            path = find_shortest_path(robots[robot_id], next_destination)
            if path:
                move_robot(robot_id, path)
            else:
                print(f"Skipping task for robot {robot_id} due to no valid path.")

    def move_robot(robot_id, path):
        robot_status[robot_id] = "Moving"
        print(f"Robot {robot_id} moving along path: {path}")

        for node in path:
            plt.clf()
            draw_static_graph()
            plt.scatter(pos[node][0], pos[node][1], s=600, color=robot_colors[robot_id], edgecolors="black", zorder=3)
            plt.pause(0.5)

        robots[robot_id] = path[-1]
        robot_status[robot_id] = "Idle"
        print(f"Robot {robot_id} reached destination: {path[-1]}")
        process_robot_tasks(robot_id)

    def find_shortest_path(start, end):
        try:
            path = nx.shortest_path(G, source=start, target=end)
            print(f"Computed shortest path from {start} to {end}: {path}")
            return path
        except nx.NetworkXNoPath:
            print(f"No path found between {start} and {end}")
            messagebox.showwarning("Path Error", "No valid path available between selected nodes.")
            return []

    def on_click(event):
        nonlocal selected_robot
        if event.xdata is None or event.ydata is None:
            return

        clicked_node = min(pos, key=lambda i: (pos[i][0] - event.xdata) ** 2 + (pos[i][1] - event.ydata) ** 2)
        print(f"Clicked on node: {clicked_node}")

        if selected_robot is None:
            robot_id = len(robots) + 1
            robots[robot_id] = clicked_node
            robot_colors[robot_id] = random_color()
            robot_status[robot_id] = "Idle"
            robot_tasks[robot_id] = []
            print(f"Spawned robot {robot_id} at node {clicked_node} with color {robot_colors[robot_id]}")
            selected_robot = robot_id  # Auto-select for movement
        else:
            robot_tasks[selected_robot].append(clicked_node)
            print(f"Added task for robot {selected_robot}: Move to {clicked_node}")

            if robot_status[selected_robot] == "Idle":
                process_robot_tasks(selected_robot)

            selected_robot = None

        draw_static_graph()
        plt.draw()

    fig.canvas.mpl_connect('button_press_event', on_click)
    plt.title("Navigation Graph - Click to Spawn & Move Robots")
    plt.show()

# Main execution
if __name__ == "__main__":
    log_window = create_log_window()
    vertices, lanes = load_nav_graph("data\\nav_graph_3.json")
    draw_graph(vertices, lanes)
    log_window.mainloop()
