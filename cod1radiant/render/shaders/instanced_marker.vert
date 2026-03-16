#version 330 core

// Quad vertices (unit quad, will be scaled and billboarded)
layout(location = 0) in vec2 in_vertex;  // -0.5 to 0.5 quad

// Per-instance data
layout(location = 1) in vec3 in_position;  // World position
layout(location = 2) in vec4 in_color;     // RGBA color
layout(location = 3) in float in_size;     // Marker size

uniform mat4 u_view;
uniform mat4 u_projection;
uniform vec3 u_camera_right;  // Camera right vector for billboarding
uniform vec3 u_camera_up;     // Camera up vector for billboarding

out vec4 v_color;
out vec2 v_uv;

void main() {
    // Billboard: orient quad to face camera
    vec3 world_pos = in_position
                   + u_camera_right * in_vertex.x * in_size
                   + u_camera_up * in_vertex.y * in_size;

    gl_Position = u_projection * u_view * vec4(world_pos, 1.0);
    v_color = in_color;
    v_uv = in_vertex + 0.5;  // Convert -0.5..0.5 to 0..1
}
