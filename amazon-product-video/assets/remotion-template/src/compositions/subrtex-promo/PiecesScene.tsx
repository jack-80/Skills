import { interpolate, useCurrentFrame } from "remotion";
import { BRAND, TYPE } from "./VideoComposition";
import { ImageCard, PopText, SceneFrame } from "./Shared";

// Scene 3 (7-11s): 7 pieces, one perfect fit
export const PiecesScene: React.FC = () => {
  const frame = useCurrentFrame();
  const items = ["1 sofa cover", "3 seat cushion covers", "3 backrest covers"];
  return (
    <SceneFrame>
      <PopText text="7 pieces." delay={4} size={118} fontFamily={TYPE.heading} />
      <PopText
        text="One perfect fit."
        delay={14}
        size={100}
        color={BRAND.accent}
        fontFamily={TYPE.heading}
      />
      <div style={{ height: 36 }} />
      {items.map((t, i) => {
        const o = interpolate(frame, [26 + i * 9, 38 + i * 9], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        const x = interpolate(frame, [26 + i * 9, 44 + i * 9], [-40, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        return (
          <div
            key={t}
            style={{
              opacity: o,
              transform: `translateX(${x}px)`,
              fontFamily: TYPE.body,
              fontWeight: 700,
              fontSize: 46,
              color: BRAND.ink,
              marginBottom: 14,
            }}
          >
            <span style={{ color: BRAND.accent2 }}>✓ </span>
            {t}
          </div>
        );
      })}
      <div style={{ height: 30 }} />
      <ImageCard src="assets/alt6.jpg" delay={50} ratio={1} width={760} />
    </SceneFrame>
  );
};
