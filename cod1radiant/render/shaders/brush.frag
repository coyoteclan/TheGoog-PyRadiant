#version 330 core

in vec3 v_position;
in vec3 v_normal;
in vec2 v_texcoord;

uniform sampler2D u_texture;
uniform vec3 u_color;
uniform bool u_use_texture;
uniform bool u_selected;
uniform vec3 u_light_dir;

out vec4 fragColor;

void main() {
    vec3 normal = normalize(v_normal);

    // Simple directional lighting
    float ambient = 0.3;
    float diffuse = max(dot(normal, normalize(u_light_dir)), 0.0) * 0.7;
    float lighting = ambient + diffuse;

    vec3 color;
    float alpha = 1.0;

    if (u_use_texture) {
        vec4 texColor = texture(u_texture, v_texcoord);
        color = texColor.rgb;
        alpha = texColor.a;

        // Alpha test - discard fully transparent pixels
        if (alpha < 0.01) {
            discard;
        }
    } else {
        color = u_color;
    }

    color *= lighting;

    // Selection highlight
    if (u_selected) {
        color = mix(color, vec3(1.0, 0.3, 0.3), 0.3);
    }

    fragColor = vec4(color, alpha);
}
