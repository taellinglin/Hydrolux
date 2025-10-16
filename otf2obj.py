import freetype
import numpy as np
import os
import math

class FontToMeshConverter:
    def __init__(self, font_path):
        try:
            self.face = freetype.Face(font_path)
            self.face.set_char_size(48 * 64)  # 48pt size
        except:
            print(f"Could not load font {font_path}, using fallback")
            self.face = None
    
    def ear_clip_triangulate(self, points):
        """Simple ear clipping triangulation for convex/concave polygons"""
        if len(points) < 3:
            return []
        
        # Convert to list of indices
        indices = list(range(len(points)))
        triangles = []
        
        while len(indices) > 3:
            n = len(indices)
            found_ear = False
            
            for i in range(n):
                # Get three consecutive vertices
                a = indices[(i - 1) % n]
                b = indices[i]
                c = indices[(i + 1) % n]
                
                # Check if this is an ear (convex vertex that doesn't contain other vertices)
                if self.is_convex(points[a], points[b], points[c]) and not self.contains_other_vertices(points, indices, a, b, c):
                    triangles.append([a, b, c])
                    indices.pop(i)
                    found_ear = True
                    break
            
            if not found_ear:
                # Fallback: just triangulate as fan
                for i in range(1, len(indices) - 1):
                    triangles.append([indices[0], indices[i], indices[i + 1]])
                break
        
        if len(indices) == 3:
            triangles.append(indices)
        
        return triangles
    
    def is_convex(self, a, b, c):
        """Check if vertex b is convex"""
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        return cross > 0
    
    def contains_other_vertices(self, points, indices, a, b, c):
        """Check if triangle abc contains any other vertices"""
        for i in indices:
            if i != a and i != b and i != c:
                if self.point_in_triangle(points[i], points[a], points[b], points[c]):
                    return True
        return False
    
    def point_in_triangle(self, p, a, b, c):
        """Check if point p is inside triangle abc"""
        def sign(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
        
        d1 = sign(p, a, b)
        d2 = sign(p, b, c)
        d3 = sign(p, c, a)
        
        has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
        has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
        
        return not (has_neg and has_pos)
    
    def process_outline(self, outline):
        """Process freetype outline into clean contours"""
        points = np.array(outline.points, dtype=np.float32) / 64.0
        tags = outline.tags
        contours = outline.contours
        
        all_contours = []
        start = 0
        
        for contour_end in contours:
            contour_points = []
            contour_tags = []
            
            # Extract this contour
            for i in range(start, contour_end + 1):
                contour_points.append((points[i][0], points[i][1]))
                contour_tags.append(tags[i])
            
            # Handle bezier curves - convert to line segments
            processed_points = self.bezier_to_lines(contour_points, contour_tags)
            
            if len(processed_points) > 2:
                all_contours.append(processed_points)
            
            start = contour_end + 1
        
        return all_contours
    
    def bezier_to_lines(self, points, tags, segments=8):
        """Convert bezier curves to line segments"""
        result = []
        n = len(points)
        
        for i in range(n):
            current_point = points[i]
            current_tag = tags[i]
            
            # Add the current point
            result.append(current_point)
            
            # If this is an off-curve point and next is also off-curve, we have a quadratic bezier
            if current_tag & 1 == 0:  # Off-curve point
                next_idx = (i + 1) % n
                next_tag = tags[next_idx]
                
                if next_tag & 1 == 0:  # Next is also off-curve
                    # We need the on-curve point after next (quadratic bezier)
                    on_curve_idx = (i + 2) % n
                    if tags[on_curve_idx] & 1:  # On-curve point
                        # Add bezier segments
                        p0 = current_point
                        p1 = points[next_idx]
                        p2 = points[on_curve_idx]
                        
                        for j in range(1, segments):
                            t = j / segments
                            # Quadratic bezier formula
                            x = (1-t)**2 * p0[0] + 2*(1-t)*t * p1[0] + t**2 * p2[0]
                            y = (1-t)**2 * p0[1] + 2*(1-t)*t * p1[1] + t**2 * p2[1]
                            result.append((x, y))
        
        return result
    
    def char_to_mesh(self, char, extrude_depth=0.1):
        """Convert a character to a 3D mesh with proper triangulation"""
        if not self.face:
            return self.create_fallback_mesh(char)
            
        self.face.load_char(char)
        outline = self.face.glyph.outline
        
        vertices = []
        faces = []
        
        # Process outline into clean contours
        contours = self.process_outline(outline)
        
        if not contours:
            return self.create_fallback_mesh(char)
        
        # Triangulate each contour
        for contour in contours:
            if len(contour) < 3:
                continue
                
            # Triangulate the contour
            contour_triangles = self.ear_clip_triangulate(contour)
            
            if not contour_triangles:
                # Fallback: convex hull triangulation
                contour_triangles = []
                for i in range(1, len(contour) - 1):
                    contour_triangles.append([0, i, i + 1])
            
            # Add front face vertices and faces
            front_start_idx = len(vertices)
            for point in contour:
                vertices.append((point[0], point[1], 0))
            
            for tri in contour_triangles:
                faces.append([front_start_idx + tri[0], front_start_idx + tri[1], front_start_idx + tri[2]])
            
            # Add back face vertices and faces (reverse winding)
            back_start_idx = len(vertices)
            for point in contour:
                vertices.append((point[0], point[1], -extrude_depth))
            
            for tri in contour_triangles:
                faces.append([back_start_idx + tri[2], back_start_idx + tri[1], back_start_idx + tri[0]])
        
        # Add side faces for extrusion
        for contour in contours:
            n = len(contour)
            front_start_idx = len(vertices) - 2 * sum(len(c) for c in contours)  # Adjust index
            back_start_idx = front_start_idx + n
            
            for i in range(n):
                next_i = (i + 1) % n
                faces.extend([
                    [front_start_idx + i, front_start_idx + next_i, back_start_idx + next_i],
                    [front_start_idx + i, back_start_idx + next_i, back_start_idx + i]
                ])
        
        if len(vertices) == 0:
            return self.create_fallback_mesh(char)
        
        return np.array(vertices, dtype=np.float32), np.array(faces, dtype=np.int32)
    
    def create_fallback_mesh(self, char):
        """Create a simple geometric mesh as fallback"""
        # Create a simple extruded letter shape
        if char in 'il1|':
            # Thin characters
            vertices = [
                (-0.1, -0.4, 0), (0.1, -0.4, 0), (0.1, 0.4, 0), (-0.1, 0.4, 0),  # front
                (-0.1, -0.4, -0.1), (0.1, -0.4, -0.1), (0.1, 0.4, -0.1), (-0.1, 0.4, -0.1)   # back
            ]
        elif char in 'mwMW':
            # Wide characters
            vertices = [
                (-0.4, -0.3, 0), (0.4, -0.3, 0), (0.4, 0.3, 0), (-0.4, 0.3, 0),  # front
                (-0.4, -0.3, -0.1), (0.4, -0.3, -0.1), (0.4, 0.3, -0.1), (-0.4, 0.3, -0.1)   # back
            ]
        else:
            # Standard characters
            vertices = [
                (-0.3, -0.3, 0), (0.3, -0.3, 0), (0.3, 0.3, 0), (-0.3, 0.3, 0),  # front
                (-0.3, -0.3, -0.1), (0.3, -0.3, -0.1), (0.3, 0.3, -0.1), (-0.3, 0.3, -0.1)   # back
            ]
        
        # Define faces for a cube
        faces = [
            [0, 1, 2], [0, 2, 3],  # front
            [4, 6, 5], [4, 7, 6],  # back
            [0, 4, 5], [0, 5, 1],  # bottom
            [1, 5, 6], [1, 6, 2],  # right
            [2, 6, 7], [2, 7, 3],  # top
            [3, 7, 4], [3, 4, 0]   # left
        ]
        
        return np.array(vertices, dtype=np.float32), np.array(faces, dtype=np.int32)
    
    def save_char_mesh(self, char, output_dir):
        """Save character mesh as OBJ"""
        try:
            vertices, faces = self.char_to_mesh(char)
            
            if len(vertices) == 0:
                print(f"No vertices generated for '{char}', using fallback")
                vertices, faces = self.create_fallback_mesh(char)
                
            os.makedirs(output_dir, exist_ok=True)
            filename = os.path.join(output_dir, f"char_{ord(char):04d}.obj")
            
            with open(filename, 'w') as f:
                f.write(f"# Character mesh for '{char}'\n")
                f.write(f"# {len(vertices)} vertices, {len(faces)} faces\n")
                
                for v in vertices:
                    f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
                
                for face in faces:
                    f.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")
            
            print(f"Saved '{char}' to {filename} ({len(vertices)} vertices, {len(faces)} faces)")
            return True
            
        except Exception as e:
            print(f"Error processing '{char}': {e}")
            # Create fallback mesh
            vertices, faces = self.create_fallback_mesh(char)
            
            os.makedirs(output_dir, exist_ok=True)
            filename = os.path.join(output_dir, f"char_{ord(char):04d}.obj")
            
            with open(filename, 'w') as f:
                f.write(f"# Fallback mesh for '{char}'\n")
                for v in vertices:
                    f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
                for face in faces:
                    f.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")
            
            print(f"Saved fallback for '{char}' to {filename}")
            return True

# Convert all ASCII letters
if __name__ == "__main__":
    font_path = "./font.otf"
    if not os.path.exists(font_path):
        # Try to find a system font
        if os.name == 'nt':  # Windows
            font_path = "C:/Windows/Fonts/arial.ttf"
        elif os.name == 'posix':  # Linux/Mac
            font_path = "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
        else:
            font_path = "./font.otf"
    
    converter = FontToMeshConverter(font_path)
    
    # Convert all lowercase and uppercase letters
    chars_to_convert = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    
    print(f"Converting font: {font_path}")
    for char in chars_to_convert:
        converter.save_char_mesh(char, "./font_meshes")
    
    print("Font conversion complete!")