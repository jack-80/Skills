import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { BRAND, TYPE } from "./VideoComposition";
import { PopText, SceneFrame } from "./Shared";

// Scene 6 (19-24s): call to action
export const CtaScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const btnSpring = spring({
    frame: frame - 44,
    fps,
    config: { damping: 11, stiffness: 170, mass: 0.9 },
  });
  const btnScale = interpolate(btnSpring, [0, 1], [0.5, 1]);
  const btnOpacity = interpolate(btnSpring, [0, 0.4], [0, 1], {
    extrapolateRight: "clamp",
  });
  // gentle pulse after landing
  const pulse = 1 + 0.03 * Math.sin((frame - 70) / 6) * (frame > 70 ? 1 : 0);

  const starsOpacity = interpolate(frame, [64, 78], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const subOpacity = interpolate(frame, [86, 100], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <SceneFrame>
      <PopText text="Small change." delay={4} size={108} fontFamily={TYPE.heading} />
      <PopText
        text="Big difference."
        delay={16}
        size={108}
        color={BRAND.accent2}
        fontFamily={TYPE.heading}
        italic
      />
      <div style={{ height: 64 }} />
      <div
        style={{
          alignSelf: "center",
          opacity: btnOpacity,
          transform: `scale(${btnScale * pulse})`,
          backgroundColor: BRAND.accent,
          borderRadius: 999,
          padding: "34px 64px",
          boxShadow: "0 24px 60px rgba(255,90,31,0.45)",
        }}
      >
        <div
          style={{
            fontFamily: TYPE.heading,
            fontSize: 56,
            color: "#0B0B10",
            textTransform: "uppercase",
            letterSpacing: 1,
          }}
        >
          Search "SUBRTEX" on Amazon
        </div>
      </div>
      <div
        style={{
          marginTop: 52,
          textAlign: "center",
          fontSize: 72,
          letterSpacing: 8,
          color: BRAND.accent2,
          opacity: starsOpacity,
        }}
      >
        ★★★★★
      </div>
      <div
        style={{
          marginTop: 26,
          textAlign: "center",
          fontFamily: TYPE.body,
          fontWeight: 700,
          fontSize: 40,
          color: BRAND.muted,
          opacity: subOpacity,
        }}
      >
        4 sizes · Multiple colors · Light Gray shown
      </div>
    </SceneFrame>
  );
};
