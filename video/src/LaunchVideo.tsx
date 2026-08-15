import {
  AbsoluteFill,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Geist";

const { fontFamily } = loadFont("normal", {
  weights: ["500", "600", "700"],
});

const BG = "#0a0a0a";
const INK = "#f5f5f5";
const MUTED = "#8a8a8a";
const PANEL = "#141414";
const RULE = "#262626";

const Mark = ({ size }: { size: number }) => (
  <svg width={size} height={size} viewBox="0 0 512 512">
    <path
      d="M256 26 L282 44 C330 74 388 88 448 92 L448 268 C448 366 372 448 256 492 C140 448 64 366 64 268 L64 92 C124 88 182 74 230 44 Z"
      fill="#171E2C"
    />
    <circle cx="256" cy="276" r="148" fill="none" stroke="#FFFFFF" strokeWidth="24" />
    <path d="M256 276 L336 29 L472 131 Z" fill="#29DE8D" />
    <circle cx="380" cy="148" r="17" fill="none" stroke="#171E2C" strokeWidth="9" />
    <circle cx="256" cy="276" r="36" fill="#29DE8D" />
  </svg>
);

// Restrained rise-and-settle entrance. No rotation, no overshoot chaos.
const Rise = ({
  children,
  delay = 0,
  size = 96,
  color = INK,
  weight = 700,
}: {
  children: React.ReactNode;
  delay?: number;
  size?: number;
  color?: string;
  weight?: number;
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 200 } });
  return (
    <div
      style={{
        fontFamily,
        fontWeight: weight,
        fontSize: size,
        color,
        letterSpacing: "-0.03em",
        lineHeight: 1.08,
        textAlign: "center",
        transform: `translateY(${interpolate(s, [0, 1], [46, 0])}px)`,
        opacity: s,
      }}
    >
      {children}
    </div>
  );
};

// Slow cinematic push-in, never static, never violent.
const useDrift = (durationInFrames: number, amount = 0.035) => {
  const frame = useCurrentFrame();
  return 1 + (frame / durationInFrames) * amount;
};

// Reel-safe stage: clear of caption and UI zones.
const Stage = ({
  children,
  drift = 1,
}: {
  children: React.ReactNode;
  drift?: number;
}) => (
  <AbsoluteFill
    style={{
      justifyContent: "center",
      alignItems: "center",
      paddingTop: 200,
      paddingBottom: 360,
      paddingLeft: 76,
      paddingRight: 76,
      flexDirection: "column",
      gap: 36,
      transform: `scale(${drift})`,
    }}
  >
    {children}
  </AbsoluteFill>
);

const RapidWords = () => {
  const frame = useCurrentFrame();
  const words = ["your voice.", "your location.", "your messages.", "your face."];
  const beat = 27;
  const index = Math.min(Math.floor(frame / beat), words.length - 1);
  const local = frame - index * beat;
  const { fps } = useVideoConfig();
  const s = spring({ frame: local, fps, config: { damping: 200 } });
  return (
    <Stage drift={useDrift(108)}>
      <div
        style={{
          fontFamily,
          fontWeight: 700,
          fontSize: 124,
          color: INK,
          letterSpacing: "-0.03em",
          textAlign: "center",
          transform: `translateY(${interpolate(s, [0, 1], [40, 0])}px)`,
          opacity: s,
        }}
      >
        {words[index]}
      </div>
      <div
        style={{
          fontFamily,
          fontWeight: 500,
          fontSize: 34,
          color: MUTED,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
        }}
      >
        {index + 1} / {words.length}
      </div>
    </Stage>
  );
};

const QUOTE =
  "“When your device detects an audio activation command, like ‘Hey Google,’ Google records your voice and audio plus a few seconds before the activation.”";

const Receipt = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const cardIn = spring({ frame, fps, config: { damping: 200 } });
  const chars = Math.floor(
    interpolate(frame, [10, 105], [0, QUOTE.length], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }),
  );
  const captionIn = spring({ frame: frame - 112, fps, config: { damping: 200 } });
  const stampIn = spring({ frame: frame - 128, fps, config: { damping: 16 } });
  return (
    <Stage drift={useDrift(175, 0.03)}>
      <div
        style={{
          position: "relative",
          width: 920,
          background: "#111111",
          border: `1px solid ${RULE}`,
          borderRadius: 24,
          padding: 56,
          transform: `translateY(${interpolate(cardIn, [0, 1], [120, 0])}px)`,
          opacity: cardIn,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          <div
            style={{
              width: 84,
              height: 84,
              borderRadius: 18,
              background: "#ffffff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily,
              fontWeight: 700,
              fontSize: 48,
              color: "#4285F4",
            }}
          >
            G
          </div>
          <div>
            <div style={{ fontFamily, fontWeight: 700, fontSize: 42, color: INK }}>
              Google
            </div>
            <div
              style={{
                fontFamily,
                fontWeight: 600,
                fontSize: 26,
                color: MUTED,
                letterSpacing: "0.1em",
                textTransform: "uppercase",
              }}
            >
              Voice recordings
            </div>
          </div>
        </div>
        <div
          style={{
            marginTop: 40,
            fontFamily,
            fontWeight: 500,
            fontSize: 39,
            lineHeight: 1.45,
            color: INK,
            borderLeft: `2px solid ${INK}`,
            paddingLeft: 30,
            minHeight: 350,
          }}
        >
          {QUOTE.slice(0, chars)}
        </div>
        <div
          style={{
            marginTop: 26,
            fontFamily,
            fontWeight: 500,
            fontSize: 27,
            color: MUTED,
            opacity: captionIn,
          }}
        >
          Google&apos;s actual privacy policy. Word for word.
        </div>
        <div
          style={{
            position: "absolute",
            top: -30,
            right: 40,
            fontFamily,
            fontWeight: 600,
            fontSize: 28,
            color: BG,
            background: INK,
            borderRadius: 10,
            padding: "12px 26px",
            letterSpacing: "0.14em",
            textTransform: "uppercase",
            transform: `scale(${stampIn})`,
          }}
        >
          Caught in 4K
        </div>
      </div>
    </Stage>
  );
};

const CHIPS = [
  { company: "Stripe", takes: "your biometrics" },
  { company: "Amazon", takes: "children's data" },
  { company: "Meta", takes: "a profile of you" },
  { company: "Spotify", takes: "your location" },
  { company: "Netflix", takes: "your messages" },
];

const ChipStorm = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <Stage drift={useDrift(120, 0.03)}>
      <div
        style={{
          fontFamily,
          fontWeight: 700,
          fontSize: 76,
          color: INK,
          letterSpacing: "-0.03em",
          textAlign: "center",
          opacity: spring({ frame, fps, config: { damping: 200 } }),
        }}
      >
        And it&apos;s not just Google.
      </div>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 22,
          marginTop: 18,
          width: 880,
        }}
      >
        {CHIPS.map((chip, index) => {
          const s = spring({
            frame: frame - 12 - index * 11,
            fps,
            config: { damping: 200 },
          });
          return (
            <div
              key={chip.company}
              style={{
                display: "flex",
                alignItems: "baseline",
                justifyContent: "space-between",
                background: PANEL,
                border: `1px solid ${RULE}`,
                borderRadius: 16,
                padding: "26px 38px",
                transform: `translateY(${interpolate(s, [0, 1], [60, 0])}px)`,
                opacity: s,
              }}
            >
              <span style={{ fontFamily, fontWeight: 700, fontSize: 40, color: INK }}>
                {chip.company}
              </span>
              <span style={{ fontFamily, fontWeight: 500, fontSize: 36, color: MUTED }}>
                {chip.takes}
              </span>
            </div>
          );
        })}
      </div>
      <div
        style={{
          fontFamily,
          fontWeight: 500,
          fontSize: 30,
          color: MUTED,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          opacity: spring({ frame: frame - 80, fps, config: { damping: 200 } }),
        }}
      >
        All from their own policies
      </div>
    </Stage>
  );
};

const PITCH = [
  "Every claim carries the exact quote.",
  "Alerts the moment a policy changes.",
  "Ask anything. Answers cite the receipts.",
];

const Pitch = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <Stage drift={useDrift(84, 0.03)}>
      <Rise size={86}>PrivacyRadar reads the fine print.</Rise>
      <div style={{ display: "flex", flexDirection: "column", gap: 28, marginTop: 16 }}>
        {PITCH.map((line, index) => {
          const s = spring({
            frame: frame - 14 - index * 13,
            fps,
            config: { damping: 200 },
          });
          return (
            <div
              key={line}
              style={{
                fontFamily,
                fontWeight: 500,
                fontSize: 44,
                color: MUTED,
                textAlign: "center",
                transform: `translateY(${interpolate(s, [0, 1], [40, 0])}px)`,
                opacity: s,
              }}
            >
              {line}
            </div>
          );
        })}
      </div>
    </Stage>
  );
};

const Outro = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 100 } });
  const ping = (frame % 45) / 45;
  return (
    <Stage>
      <div style={{ position: "relative", width: 380, height: 380 }}>
        <div
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "50%",
            border: `3px solid ${INK}`,
            transform: `scale(${1 + ping * 0.8})`,
            opacity: (1 - ping) * 0.5,
          }}
        />
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transform: `scale(${pop})`,
          }}
        >
          <Mark size={320} />
        </div>
      </div>
      <Rise delay={6} size={92}>
        PrivacyRadar
      </Rise>
      <div
        style={{
          fontFamily,
          fontWeight: 500,
          fontSize: 42,
          color: MUTED,
          opacity: spring({ frame: frame - 16, fps, config: { damping: 200 } }),
        }}
      >
        See what they take from you.
      </div>
      <div
        style={{
          fontFamily,
          fontWeight: 600,
          fontSize: 34,
          color: INK,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          opacity: spring({ frame: frame - 28, fps, config: { damping: 200 } }),
        }}
      >
        Link in bio
      </div>
    </Stage>
  );
};

const Hook = () => (
  <Stage drift={useDrift(60)}>
    <Rise size={116}>
      Your apps know
      <br />
      too much about you.
    </Rise>
  </Stage>
);

const Tease = () => (
  <Stage drift={useDrift(60)}>
    <Rise size={100}>Sounds exaggerated?</Rise>
    <Rise delay={20} size={100}>
      We have the receipts.
    </Rise>
  </Stage>
);

export const LaunchVideo = () => {
  return (
    <AbsoluteFill style={{ background: BG }}>
      {/* S1: hook */}
      <Sequence durationInFrames={60}>
        <Hook />
      </Sequence>

      {/* S2: rapid-fire */}
      <Sequence from={60} durationInFrames={108}>
        <RapidWords />
      </Sequence>

      {/* S3: receipts tease */}
      <Sequence from={168} durationInFrames={60}>
        <Tease />
      </Sequence>

      {/* S4: the receipt */}
      <Sequence from={228} durationInFrames={175}>
        <Receipt />
      </Sequence>

      {/* S5: the pattern */}
      <Sequence from={403} durationInFrames={120}>
        <ChipStorm />
      </Sequence>

      {/* S6: pitch */}
      <Sequence from={523} durationInFrames={84}>
        <Pitch />
      </Sequence>

      {/* S7: outro */}
      <Sequence from={607} durationInFrames={83}>
        <Outro />
      </Sequence>
    </AbsoluteFill>
  );
};
