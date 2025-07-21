import math
import tkinter as tk
import numpy as np
import time

class Constants:
    """Game configuration constants"""
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 800
    
    # Rendering settings
    NUM_RAYS = 800
    FOV = math.pi / 3  # 60 degrees field of view
    RENDER_DISTANCE = 20
    
    # Movement settings
    MOVEMENT_SPEED = 0.15
    ROTATION_SPEED = 0.08
    
    # Visual settings
    WALL_HEIGHT_SCALE = 600
    MIN_BRIGHTNESS = 0.2
    
    # Colors
    SKY_COLOR = "#87CEEB"
    FLOOR_COLOR = "#D2B48C"
    WALL_BASE_COLOR = "#D3D3D3"

class Player:
    """Handles player position, rotation and movement"""
    
    def __init__(self, x=2.0, y=2.0, direction=math.pi/4):
        self.x = x
        self.y = y
        self.direction = direction
        
    def move(self, dx, dy):
        """Move player by delta x and y"""
        self.x += dx
        self.y += dy
        
    def rotate(self, angle_delta):
        """Rotate player by angle delta"""
        self.direction += angle_delta
        # Keep angle in 0-2π range
        self.direction = self.direction % (2 * math.pi)

class GameMap:
    """Handles map data and collision detection"""
    
    def __init__(self, arena_data):
        self.arena = arena_data
        self.height = len(arena_data)
        self.width = len(arena_data[0]) if self.height > 0 else 0
        
    def is_wall(self, x, y):
        """Check if position contains a wall"""
        try:
            grid_x, grid_y = int(x), int(y)
            if 0 <= grid_x < self.height and 0 <= grid_y < self.width:
                return self.arena[grid_x][grid_y] != 0
            return True  # Consider out-of-bounds as walls
        except (IndexError, ValueError):
            return True
            
    def is_valid_position(self, x, y):
        """Check if position is valid for player movement"""
        return not self.is_wall(x, y)

class RaycastRenderer:
    """Handles all rendering operations"""
    
    def __init__(self, canvas, width, height):
        self.canvas = canvas
        self.width = width
        self.height = height
        
    def clear_screen(self):
        """Clear the canvas and draw sky/floor"""
        self.canvas.delete("all")
        
        # Draw sky
        self.canvas.create_rectangle(
            0, 0, self.width, self.height // 2,
            fill=Constants.SKY_COLOR, outline=""
        )
        
        # Draw floor
        self.canvas.create_rectangle(
            0, self.height // 2, self.width, self.height,
            fill=Constants.FLOOR_COLOR, outline=""
        )
        
    def cast_ray(self, game_map, start_x, start_y, angle):
        """Cast a single ray and return distance to wall"""
        ray_dx = math.cos(angle)
        ray_dy = math.sin(angle)
        
        distance = 0.0
        step_size = 0.05
        
        x, y = start_x, start_y
        
        while distance < Constants.RENDER_DISTANCE:
            x += ray_dx * step_size
            y += ray_dy * step_size
            distance += step_size
            
            if game_map.is_wall(x, y):
                return distance
                
        return Constants.RENDER_DISTANCE
        
    def calculate_wall_brightness(self, distance):
        """Calculate wall brightness based on distance"""
        if distance <= 0:
            return 1.0
        
        brightness = 1.0 - (distance / Constants.RENDER_DISTANCE)
        return max(Constants.MIN_BRIGHTNESS, brightness)
        
    def get_wall_color(self, brightness):
        """Get wall color based on brightness level"""
        base_color = 0x69  # Base gray value
        color_value = int(base_color * brightness)
        return f"#{color_value:02x}{color_value:02x}{color_value:02x}"
        
    def draw_wall_slice(self, x, wall_height, distance):
        """Draw a single vertical wall slice"""
        brightness = self.calculate_wall_brightness(distance)
        wall_color = self.get_wall_color(brightness)
        
        # Calculate wall position
        wall_top = (self.height - wall_height) // 2
        wall_bottom = (self.height + wall_height) // 2
        
        # Draw the wall slice
        slice_width = self.width // Constants.NUM_RAYS
        self.canvas.create_rectangle(
            x, wall_top, x + slice_width, wall_bottom,
            fill=wall_color, outline=""
        )
        
    def render_scene(self, player, game_map):
        """Render the complete 3D scene"""
        self.clear_screen()
        
        # Calculate ray angles
        start_angle = player.direction - Constants.FOV / 2
        angle_step = Constants.FOV / Constants.NUM_RAYS
        
        for i in range(Constants.NUM_RAYS):
            ray_angle = start_angle + i * angle_step
            
            # Cast ray and get distance
            distance = self.cast_ray(game_map, player.x, player.y, ray_angle)
            
            # Apply fish-eye correction
            corrected_distance = distance * math.cos(ray_angle - player.direction)
            
            # Calculate wall height
            if corrected_distance > 0:
                wall_height = Constants.WALL_HEIGHT_SCALE / corrected_distance
            else:
                wall_height = Constants.WALL_HEIGHT_SCALE
                
            # Limit wall height to screen
            wall_height = min(wall_height, self.height)
            
            # Draw wall slice
            x_position = i * (self.width // Constants.NUM_RAYS)
            self.draw_wall_slice(x_position, wall_height, corrected_distance)

class InputHandler:
    """Handles continuous input for smooth movement"""
    
    def __init__(self, root):
        self.root = root
        self.keys_pressed = set()
        self.setup_key_bindings()
        
    def setup_key_bindings(self):
        """Setup key press and release event handlers"""
        self.root.bind('<KeyPress>', self.on_key_press)
        self.root.bind('<KeyRelease>', self.on_key_release)
        self.root.focus_set()  # Ensure window has focus for key events
        
    def on_key_press(self, event):
        """Handle key press events"""
        self.keys_pressed.add(event.keysym.lower())
        
    def on_key_release(self, event):
        """Handle key release events"""
        self.keys_pressed.discard(event.keysym.lower())
        
    def is_key_pressed(self, key):
        """Check if a specific key is currently pressed"""
        return key.lower() in self.keys_pressed

class Game:
    """Main game class that orchestrates everything"""
    
    def __init__(self):
        # Initialize game components
        self.setup_window()
        self.setup_game_objects()
        self.setup_input()
        
        # Game loop control
        self.running = True
        self.last_update_time = time.time()
        self.target_fps = 60
        
    def setup_window(self):
        """Initialize the tkinter window and canvas"""
        self.root = tk.Tk()
        self.root.title("Enhanced 2.5D Raycasting Engine")
        self.root.geometry(f"{Constants.WINDOW_WIDTH}x{Constants.WINDOW_HEIGHT}")
        self.root.resizable(False, False)
        
        self.canvas = tk.Canvas(
            self.root,
            width=Constants.WINDOW_WIDTH,
            height=Constants.WINDOW_HEIGHT,
            bg=Constants.SKY_COLOR
        )
        self.canvas.pack()
        
    def setup_game_objects(self):
        """Initialize game objects"""
        # Game map
        arena_data = [
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            [1, 0, 0, 0, 0, 0, 0, 0, 0, 1],
            [1, 0, 0, 0, 0, 0, 0, 0, 0, 1],
            [1, 0, 0, 1, 1, 1, 0, 0, 0, 1],
            [1, 0, 0, 0, 0, 0, 0, 0, 0, 1],
            [1, 0, 0, 0, 0, 0, 0, 1, 0, 1],
            [1, 0, 0, 1, 0, 0, 0, 0, 0, 1],
            [1, 0, 0, 0, 0, 0, 0, 0, 0, 1],
            [1, 0, 0, 0, 1, 0, 0, 0, 0, 1],
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        ]
        
        self.game_map = GameMap(arena_data)
        self.player = Player(2.0, 2.0, math.pi/4)
        self.renderer = RaycastRenderer(
            self.canvas, Constants.WINDOW_WIDTH, Constants.WINDOW_HEIGHT
        )
        
    def setup_input(self):
        """Setup input handling"""
        self.input_handler = InputHandler(self.root)
        
        # Bind escape key to quit
        self.root.bind('<Escape>', lambda e: self.quit_game())
        
    def update_player_movement(self):
        """Update player position based on currently pressed keys"""
        moved = False
        
        # Movement keys
        if self.input_handler.is_key_pressed('w'):
            dx = math.cos(self.player.direction) * Constants.MOVEMENT_SPEED
            dy = math.sin(self.player.direction) * Constants.MOVEMENT_SPEED
            self.try_move_player(dx, dy)
            moved = True
            
        if self.input_handler.is_key_pressed('s'):
            dx = -math.cos(self.player.direction) * Constants.MOVEMENT_SPEED
            dy = -math.sin(self.player.direction) * Constants.MOVEMENT_SPEED
            self.try_move_player(dx, dy)
            moved = True
            
        if self.input_handler.is_key_pressed('a'):
            dx = math.sin(self.player.direction) * Constants.MOVEMENT_SPEED
            dy = -math.cos(self.player.direction) * Constants.MOVEMENT_SPEED
            self.try_move_player(dx, dy)
            moved = True
            
        if self.input_handler.is_key_pressed('d'):
            dx = -math.sin(self.player.direction) * Constants.MOVEMENT_SPEED
            dy = math.cos(self.player.direction) * Constants.MOVEMENT_SPEED
            self.try_move_player(dx, dy)
            moved = True
            
        # Rotation keys
        if self.input_handler.is_key_pressed('left'):
            self.player.rotate(-Constants.ROTATION_SPEED)
            moved = True
            
        if self.input_handler.is_key_pressed('right'):
            self.player.rotate(Constants.ROTATION_SPEED)
            moved = True
            
        return moved
        
    def try_move_player(self, dx, dy):
        """Attempt to move player with collision detection"""
        new_x = self.player.x + dx
        new_y = self.player.y + dy
        
        # Check collision for new position
        if self.game_map.is_valid_position(new_x, new_y):
            self.player.move(dx, dy)
            
    def update(self):
        """Main game update loop"""
        current_time = time.time()
        
        # Update player movement
        moved = self.update_player_movement()
        
        # Render scene if something changed or enough time has passed
        if moved or (current_time - self.last_update_time) > (1.0 / self.target_fps):
            self.renderer.render_scene(self.player, self.game_map)
            self.last_update_time = current_time
            
        # Schedule next update
        if self.running:
            self.root.after(16, self.update)  # ~60 FPS
            
    def quit_game(self):
        """Quit the game"""
        self.running = False
        self.root.quit()
        
    def run(self):
        """Start the game loop"""
        # Initial render
        self.renderer.render_scene(self.player, self.game_map)
        
        # Start update loop
        self.update()
        
        # Start tkinter main loop
        self.root.mainloop()

def main():
    """Main entry point"""
    try:
        game = Game()
        game.run()
    except KeyboardInterrupt:
        print("\nGame interrupted by user")
    except Exception as e:
        print(f"Game error: {e}")

if __name__ == "__main__":
    main()
