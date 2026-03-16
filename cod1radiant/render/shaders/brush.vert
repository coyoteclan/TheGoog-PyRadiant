#version 330 core

layout(location = 0) in vec3 in_position;
layout(location = 1) in vec3 in_normal;
layout(location = 2) in vec2 in_texcoord;

uniform mat4 u_mvp;
uniform mat4 u_model;

out vec3 v_position;
out vec3 v_normal;
out vec2 v_texcoord;

void main() {
    v_position = (u_model * vec4(in_position, 1.0)).xyz;
    v_normal = mat3(u_model) * in_normal;
    v_texcoord = in_texcoord;
    gl_Position = u_mvp * vec4(in_position, 1.0);
}
