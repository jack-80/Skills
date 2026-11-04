import {
  AbsoluteFill,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BRAND } from "./VideoComposition";

// Full-screen scene wrapper: bold dark background + subtle animated
// gradient blobs + fast entrance fade. Children are laid out in a column.
export const SceneFrame: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const drift = interpolate(frame, [0, 150], [0, 120], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: BRAND.bg, opacity }}>
      {/* animated accent blobs for depth */}
      <div
        style={{
          position: "absolute",
          width: 900,
          height: 900,
          borderRadius: 9999,
          background:
            "radial-gradient(circle, rgba(255,90,31,0.22) 0%, rgba(255,90,31,0) 70%)",
          top: -260 + drift,
          left: -300,
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 900,
          height: 900,
          borderRadius: 9999,
          background:
            "radial-gradient(circle, rgba(255,214,10,0.14) 0%, rgba(255,214,10,0) 70%)",
          bottom: -320 + drift,
          right: -320,
        }}
      />
      <AbsoluteFill
        style={{
          padding: 80,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
        }}
      >
        {children}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// Kinetic word block: spring pop-in + slight rise
export const PopText: React.FC<{
  text: string;
  delay?: number;
  size?: number;
  color?: string;
  fontFamily?: string;
  italic?: boolean;
}> = ({ text, delay = 0, size = 110, color = BRAND.ink, fontFamily, italic }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({
    frame: frame - delay,
    fps,
    config: { damping: 12, stiffness: 160, mass: 0.9 },
  });
  const scale = interpolate(s, [0, 1], [0.6, 1]);
  const y = interpolate(s, [0, 1], [80, 0]);
  const opacity = interpolate(s, [0, 0.4], [0, 1], {
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        fontFamily: fontFamily ?? '"Arial Black", Arial, sans-serif',
        fontSize: size,
        fontStyle: italic ? "italic" : "normal",
        color,
        lineHeight: 1.02,
        letterSpacing: -1,
        transform: `translateY(${y}px) scale(${scale})`,
        opacity,
        textTransform: "uppercase",
      }}
    >
      {text}
    </div>
  );
};

// Small tag pill (top-left label)
export const Tag: React.FC<{ text: string; delay?: number }> = ({
  text,
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [delay, delay + 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        opacity,
        alignSelf: "flex-start",
        backgroundColor: BRAND.accent,
        color: "#0B0B10",
        fontFamily: '"Arial Black", Arial, sans-serif',
        fontSize: 30,
        letterSpacing: 3,
        padding: "10px 26px",
        borderRadius: 999,
        textTransform: "uppercase",
        marginBottom: 28,
      }}
    >
      {text}
    </div>
  );
};

// Image card with spring zoom + rounded corners + border
export const ImageCard: React.FC<{
  src: string;
  delay?: number;
  width?: number;
  ratio?: number; // width/height
}> = ({ src, delay = 0, width = 920, ratio }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({
    frame: frame - delay,
    fps,
    config: { damping: 14, stiffness: 120, mass: 1 },
  });
  const scale = interpolate(s, [0, 1], [1.15, 1]);
  const opacity = interpolate(s, [0, 0.35], [0, 1], {
    extrapolateRight: "clamp",
  });
  // slow ken-burns after entrance
  const kb = interpolate(frame, [delay, delay + 200], [1, 1.06], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        width,
        aspectRatio: ratio ? `${ratio}` : undefined,
        borderRadius: 36,
        overflow: "hidden",
        border: `4px solid rgba(255,255,255,0.12)`,
        boxShadow: "0 30px 80px rgba(0,0,0,0.55)",
        opacity,
        alignSelf: "center",
      }}
    >
      <Img
        src={staticFile(src)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale * kb})`,
          display: "block",
        }}
      />
    </div>
  );
};
