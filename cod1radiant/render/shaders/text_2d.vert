#version 330 core

layout(location = 0) in vec2 in_position;
layout(location = 1) in vec2 in_texcoord;

out vec2 v_texcoord;

uniform mat4 u_projection;
uniform vec2 u_offset;
uniform float u_zoom;
uniform bool u_screen_space;  // If true, position is in screen pixels, not world coords

void main() {
    vec2 pos;
    if (u_screen_space) {
        // Direct screen space (pixels) - projection converts to NDC
        pos = in_position;
    } else {
        // World space - apply pan/zoom
        pos = (in_position - u_offset) * u_zoom;
    }

    gl_Position = u_projection * vec4(pos, 0.0, 1.0);
    v_texcoord = in_texcoord;
}
