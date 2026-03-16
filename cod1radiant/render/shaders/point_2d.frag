#version 330 core

in vec4 v_color;

out vec4 fragColor;

void main() {
    // Draw circular points
    vec2 coord = gl_PointCoord - vec2(0.5);
    if (length(coord) > 0.5) {
        discard;
    }
    fragColor = v_color;
}
