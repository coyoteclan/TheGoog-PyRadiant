#version 330 core

in vec2 v_texcoord;
out vec4 fragColor;

uniform sampler2D u_texture;
uniform vec4 u_color;
uniform bool u_use_texture;

void main() {
    if (u_use_texture) {
        vec4 tex = texture(u_texture, v_texcoord);
        // Use texture alpha, multiply by color
        fragColor = vec4(u_color.rgb, tex.a * u_color.a);
    } else {
        fragColor = u_color;
    }
}
