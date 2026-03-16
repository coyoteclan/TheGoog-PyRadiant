#version 330 core

in vec3 v_position;

uniform vec4 u_color;

out vec4 fragColor;

void main() {
    fragColor = u_color;
}
