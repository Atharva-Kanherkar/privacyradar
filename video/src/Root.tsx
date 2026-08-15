import { Composition } from "remotion";
import { LaunchVideo } from "./LaunchVideo";

export const Root = () => (
  <Composition
    id="Launch"
    component={LaunchVideo}
    durationInFrames={750}
    fps={30}
    width={1080}
    height={1920}
  />
);
