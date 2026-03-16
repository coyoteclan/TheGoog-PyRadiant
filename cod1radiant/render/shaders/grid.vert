#version 330 core

layout(location = 0) in vec3 in_position;

uniform mat4 u_mvp;

out vec3 v_position;

void main() {
    v_position = in_position;
    gl_Position = u_mvp * vec4(in_position, 1.0);
}
