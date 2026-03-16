#version 330 core

layout(location = 0) in vec2 in_position;

uniform mat4 u_projection;
uniform vec2 u_offset;
uniform float u_zoom;

void main() {
    // Apply 2D pan and zoom transformation
    vec2 world_pos = in_position;
    vec2 view_pos = (world_pos - u_offset) * u_zoom;

    gl_Position = u_projection * vec4(view_pos, 0.0, 1.0);
}
