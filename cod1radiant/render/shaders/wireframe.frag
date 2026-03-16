#version 330 core

flat in float v_visible;  // Match flat from vertex shader

uniform vec4 u_color;

out vec4 fragColor;

void main() {
    // Discard fragments for back-facing edges
    if (v_visible < 0.5) {
        discard;
    }
    fragColor = u_color;
}
