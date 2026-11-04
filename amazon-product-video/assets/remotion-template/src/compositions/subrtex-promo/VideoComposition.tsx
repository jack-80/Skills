import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import { HookScene } from "./HookScene";
import { RevealScene } from "./RevealScene";
import { PiecesScene } from "./PiecesScene";
import { RealLifeScene } from "./RealLifeScene";
import { FabricScene } from "./FabricScene";
import { CtaScene } from "./CtaScene";

// ============ EDITABLE CONSTANTS ============
export const BRAND = {
  bg: "#0B0B10",
  ink: "#FFFFFF",
  accent: "#FF5A1F", // hot orange
  accent2: "#FFD60A", // vivid yellow
  muted: "#9BA1AD",
};

export const TYPE = {
  heading: '"Arial Black", "Helvetica Neue", Arial, sans-serif',
  body: '"Helvetica Neue", Arial, sans-serif',
};

export const TIMING = {
  fps: 30,
  hook: 90,
  reveal: 120,
  pieces: 120,
  realLife: 120,
  fabric: 120,
  cta: 150,
};
// ============================================

export const SubrtexPromo: React.FC = () => {
  let t = 0;
  const seq = (dur: number) => {
    const from = t;
    t += dur;
    return { from, dur };
  };
  const s1 = seq(TIMING.hook);
  const s2 = seq(TIMING.reveal);
  const s3 = seq(TIMING.pieces);
  const s4 = seq(TIMING.realLife);
  const s5 = seq(TIMING.fabric);
  const s6 = seq(TIMING.cta);

  return (
    <AbsoluteFill style={{ backgroundColor: BRAND.bg }}>
      <Sequence from={s1.from} durationInFrames={s1.dur}>
        <HookScene />
        <Audio src={staticFile("vo/vo-1.mp3")} />
      </Sequence>
      <Sequence from={s2.from} durationInFrames={s2.dur}>
        <RevealScene />
        <Audio src={staticFile("vo/vo-2.mp3")} />
      </Sequence>
      <Sequence from={s3.from} durationInFrames={s3.dur}>
        <PiecesScene />
        <Audio src={staticFile("vo/vo-3.mp3")} />
      </Sequence>
      <Sequence from={s4.from} durationInFrames={s4.dur}>
        <RealLifeScene />
        <Audio src={staticFile("vo/vo-4.mp3")} />
      </Sequence>
      <Sequence from={s5.from} durationInFrames={s5.dur}>
        <FabricScene />
        <Audio src={staticFile("vo/vo-5.mp3")} />
      </Sequence>
      <Sequence from={s6.from} durationInFrames={s6.dur}>
        <CtaScene />
        <Audio src={staticFile("vo/vo-6.mp3")} />
      </Sequence>
    </AbsoluteFill>
  );
};
