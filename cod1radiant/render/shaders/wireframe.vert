#version 330 core

layout(location = 0) in vec3 in_position;
layout(location = 1) in vec3 in_normal;

uniform mat4 u_mvp;
uniform vec3 u_camera_pos;
uniform int u_backface_culling;  // Use int instead of bool for better compatibility

flat out float v_visible;  // Use flat to prevent interpolation

void main() {
    gl_Position = u_mvp * vec4(in_position, 1.0);

    if (u_backface_culling != 0) {
        // Calculate view direction from vertex to camera
        vec3 view_dir = normalize(u_camera_pos - in_position);
        // Check if face normal points towards camera
        // Note: MAP format normals may point inward (into the solid), so we check both signs
        float dot_result = dot(normalize(in_normal), view_dir);
        // visible if |dot| > threshold (face is roughly perpendicular or facing camera)
        // For MAP format with inward normals: dot < 0 means face is visible
        v_visible = dot_result < 0.0 ? 1.0 : 0.0;
    } else {
        v_visible = 1.0;
    }
}
