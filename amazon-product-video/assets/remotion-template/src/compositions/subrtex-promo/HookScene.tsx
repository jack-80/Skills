import { interpolate, useCurrentFrame } from "remotion";
import { BRAND, TYPE } from "./VideoComposition";
import { PopText, SceneFrame, Tag } from "./Shared";

// Scene 1 (0-3s): pattern-interrupt hook with screen shake
export const HookScene: React.FC = () => {
  const frame = useCurrentFrame();

  // subtle shake that kicks in with the second line
  const shakeAmp = interpolate(frame, [22, 30, 60], [0, 14, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const shakeX = Math.sin(frame * 2.1) * shakeAmp;
  const shakeY = Math.cos(frame * 1.7) * shakeAmp * 0.6;

  const strike = interpolate(frame, [55, 65], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <SceneFrame>
      <div
        style={{
          transform: `translate(${shakeX}px, ${shakeY}px)`,
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
        }}
      >
        <Tag text="Home Hack" delay={4} />
        <PopText text="Your sofa" delay={8} size={120} fontFamily={TYPE.heading} />
        <PopText
          text="looks tired?"
          delay={24}
          size={120}
          color={BRAND.accent}
          fontFamily={TYPE.heading}
          italic
        />
        <div
          style={{
            marginTop: 48,
            height: 14,
            width: `${strike}%`,
            maxWidth: 620,
            backgroundColor: BRAND.accent2,
            borderRadius: 999,
          }}
        />
        <div
          style={{
            marginTop: 44,
            fontFamily: TYPE.body,
            fontSize: 44,
            color: BRAND.muted,
            opacity: interpolate(frame, [60, 74], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        >
          Don't replace it. <span style={{ color: BRAND.ink, fontWeight: 700 }}>Re-cover it.</span>
        </div>
      </div>
    </SceneFrame>
  );
};
