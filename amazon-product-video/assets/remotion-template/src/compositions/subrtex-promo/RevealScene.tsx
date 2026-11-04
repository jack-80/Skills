import { interpolate, useCurrentFrame } from "remotion";
import { BRAND, TYPE } from "./VideoComposition";
import { ImageCard, PopText, SceneFrame, Tag } from "./Shared";

// Scene 2 (3-7s): product hero reveal
export const RevealScene: React.FC = () => {
  const frame = useCurrentFrame();
  const badgeOpacity = interpolate(frame, [48, 62], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const badgeY = interpolate(frame, [48, 66], [30, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <SceneFrame>
      <Tag text="SUBRTEX" delay={4} />
      <ImageCard src="assets/main.jpg" delay={6} ratio={1500 / 769} />
      <div style={{ height: 40 }} />
      <PopText text="7-Piece Stretch" delay={20} size={92} fontFamily={TYPE.heading} />
      <PopText
        text="Sofa Cover Set"
        delay={30}
        size={92}
        color={BRAND.accent2}
        fontFamily={TYPE.heading}
      />
      <div
        style={{
          marginTop: 36,
          display: "flex",
          gap: 18,
          opacity: badgeOpacity,
          transform: `translateY(${badgeY}px)`,
        }}
      >
        <div
          style={{
            backgroundColor: "rgba(255,255,255,0.08)",
            border: "2px solid rgba(255,255,255,0.16)",
            borderRadius: 999,
            padding: "14px 28px",
            fontFamily: TYPE.body,
            fontWeight: 700,
            fontSize: 34,
            color: BRAND.ink,
          }}
        >
          <span style={{ color: BRAND.accent2 }}>★ 4.3</span> · 4,300+ ratings
        </div>
        <div
          style={{
            backgroundColor: "rgba(255,255,255,0.08)",
            border: "2px solid rgba(255,255,255,0.16)",
            borderRadius: 999,
            padding: "14px 28px",
            fontFamily: TYPE.body,
            fontWeight: 700,
            fontSize: 34,
            color: BRAND.ink,
          }}
        >
          OEKO-TEX® certified
        </div>
      </div>
    </SceneFrame>
  );
};
