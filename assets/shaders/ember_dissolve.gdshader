shader_type canvas_item;
// Screen transition: chunky pixel cells burn in with a glowing ember edge.
// progress 0 = fully clear, 1 = fully covered.
uniform float progress : hint_range(0.0, 1.0) = 0.0;
uniform vec2 cells = vec2(54.0, 96.0);
uniform vec4 cover : source_color = vec4(0.05, 0.03, 0.06, 1.0);
uniform vec4 ember : source_color = vec4(1.0, 0.55, 0.15, 1.0);

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void fragment() {
	vec2 cell = floor(UV * cells);
	// noise plus a gentle bottom-to-top sweep so embers rise
	float n = hash(cell) * 0.7 + (1.0 - UV.y) * 0.3;
	float p = progress * 1.15;
	if (n < p - 0.12) {
		COLOR = cover;
	} else if (n < p) {
		COLOR = mix(ember, vec4(1.0, 0.9, 0.5, 1.0), step(p - 0.05, n));
	} else {
		COLOR = vec4(0.0);
	}
}
