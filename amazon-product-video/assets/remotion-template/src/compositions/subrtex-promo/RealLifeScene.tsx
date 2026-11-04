import { interpolate, useCurrentFrame } from "remotion";
import { BRAND, TYPE } from "./VideoComposition";
import { ImageCard, PopText, SceneFrame } from "./Shared";

// Scene 4 (11-15s): built for real life — pets, kids, spills
export const RealLifeScene: React.FC = () => {
  const frame = useCurrentFrame();
  const chips = ["Pets", "Kids", "Spills", "Daily wear"];
  return (
    <SceneFrame>
      <PopText text="Built for" delay={4} size={110} fontFamily={TYPE.heading} />
      <PopText
        text="real life."
        delay={14}
        size={110}
        color={BRAND.accent2}
        fontFamily={TYPE.heading}
        italic
      />
      <div style={{ height: 30 }} />
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        {chips.map((c, i) => {
          const o = interpolate(frame, [24 + i * 8, 34 + i * 8], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <div
              key={c}
              style={{
                opacity: o,
                backgroundColor: BRAND.accent,
                color: "#0B0B10",
                fontFamily: TYPE.heading,
                fontSize: 40,
                padding: "12px 30px",
                borderRadius: 999,
                textTransform: "uppercase",
              }}
            >
              {c}
            </div>
          );
        })}
      </div>
      <div style={{ height: 34 }} />
      <ImageCard src="assets/alt2.jpg" delay={40} ratio={1} width={860} />
      <div
        style={{
          marginTop: 30,
          fontFamily: TYPE.body,
          fontSize: 40,
          fontWeight: 700,
          color: BRAND.muted,
          textAlign: "center",
          opacity: interpolate(frame, [66, 80], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        Elastic bottoms keep every piece{" "}
        <span style={{ color: BRAND.ink }}>locked in place</span>
      </div>
    </SceneFrame>
  );
};
