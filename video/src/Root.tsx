import { Composition } from "remotion";
import { LaunchVideo } from "./LaunchVideo";

export const Root = () => (
  <Composition
    id="Launch"
    component={LaunchVideo}
    durationInFrames={690}
    fps={30}
    width={1920}
    height={1080}
  />
);
