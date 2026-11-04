import { Composition } from "remotion";
import { SubrtexPromo } from "./compositions/subrtex-promo/VideoComposition";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="subrtex-promo"
        component={SubrtexPromo}
        durationInFrames={720}
        fps={30}
        width={1080}
        height={1920}
      />
    </>
  );
};
