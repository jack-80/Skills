import { interpolate, useCurrentFrame } from "remotion";
import { BRAND, TYPE } from "./VideoComposition";
import { ImageCard, PopText, SceneFrame } from "./Shared";

// Scene 5 (15-19s): soft, stretchy, washable fabric
export const FabricScene: React.FC = () => {
  const frame = useCurrentFrame();
  const specs = ["95% polyester · 5% spandex", "Fits fabric & leather sofas", "Machine washable"];
  return (
    <SceneFrame>
      <PopText text="Soft. Stretchy." delay={4} size={104} fontFamily={TYPE.heading} />
      <PopText
        text="Washable."
        delay={14}
        size={104}
        color={BRAND.accent}
        fontFamily={TYPE.heading}
      />
      <div style={{ height: 34 }} />
      <ImageCard src="assets/alt5.jpg" delay={24} ratio={1} width={860} />
      <div style={{ height: 32 }} />
      {specs.map((t, i) => {
        const o = interpolate(frame, [52 + i * 9, 62 + i * 9], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        return (
          <div
            key={t}
            style={{
              opacity: o,
              fontFamily: TYPE.body,
              fontWeight: 700,
              fontSize: 42,
              color: BRAND.ink,
              textAlign: "center",
              marginBottom: 10,
            }}
          >
            {t}
          </div>
        );
      })}
    </SceneFrame>
  );
};
