#version 130

uniform sampler2D scene_texture;
uniform float time;

in vec2 texcoord;
out vec4 fragColor;

void main() {
    vec2 uv = texcoord - 0.5;
    float angle = atan(uv.y, uv.x);
    float radius = length(uv);
    
    // Kaleidoscope with 16 segments
    float segments = 16.0;
    angle = mod(angle, 6.28318 / segments);
    angle = abs(angle - 3.14159 / segments);
    
    // Zooming effect - pulse between 2.5x and 3.5x scale
    float zoom = 2.5 + 0.5 * sin(time * 1.5);
    
    // Scale with zoom effect
    vec2 newUV = vec2(cos(angle), sin(angle)) * radius * zoom + 0.5;
    
    // Use texture wrapping to eliminate borders
    newUV = fract(newUV);
    
    vec4 scene_color = texture(scene_texture, newUV);
    
    // Set dark pixels to pure black - use a slightly higher threshold
    // to catch more of the grey background
    if (length(scene_color.rgb) < 0.2) {
        fragColor = vec4(0.0, 0.0, 0.0, 1.0);
    } else {
        fragColor = scene_color;
    }
}