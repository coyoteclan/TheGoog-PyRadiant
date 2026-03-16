#version 330 core

in vec4 v_color;
in vec2 v_uv;

out vec4 frag_color;

uniform int u_shape;  // 0=square, 1=circle, 2=diamond, 3=cross

void main() {
    vec2 uv = v_uv - 0.5;  // Center UV coordinates
    float dist = length(uv);

    if (u_shape == 1) {
        // Circle: discard outside radius
        if (dist > 0.5) {
            discard;
        }
        // Soft edge
        float alpha = smoothstep(0.5, 0.4, dist);
        frag_color = vec4(v_color.rgb, v_color.a * alpha);
    }
    else if (u_shape == 2) {
        // Diamond: discard outside diamond shape
        float diamond = abs(uv.x) + abs(uv.y);
        if (diamond > 0.5) {
            discard;
        }
        float alpha = smoothstep(0.5, 0.4, diamond);
        frag_color = vec4(v_color.rgb, v_color.a * alpha);
    }
    else if (u_shape == 3) {
        // Cross shape
        float cross_width = 0.15;
        bool in_h = abs(uv.y) < cross_width && abs(uv.x) < 0.5;
        bool in_v = abs(uv.x) < cross_width && abs(uv.y) < 0.5;
        if (!in_h && !in_v) {
            discard;
        }
        frag_color = v_color;
    }
    else {
        // Square (default)
        frag_color = v_color;
    }
}
