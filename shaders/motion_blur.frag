#version 130

uniform sampler2D p3d_Texture0;
uniform float blurAmount;

in vec2 texcoord;
out vec4 fragColor;

void main() {
    vec4 current = texture(p3d_Texture0, texcoord);
    
    // Sample previous frame with slight offset for motion effect
    vec2 motionVec = vec2(sin(texcoord.y * 3.14159) * 0.01, 0.0) * blurAmount;
    vec4 previous = texture(p3d_Texture0, texcoord + motionVec);
    
    // Blend current and previous frames
    fragColor = mix(current, previous, blurAmount * 0.5);
    
    // Add subtle trail effect
    fragColor.rgb += previous.rgb * blurAmount * 0.3;
}