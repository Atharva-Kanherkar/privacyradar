import {
  AbsoluteFill,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Inter";

const { fontFamily } = loadFont("normal", {
  weights: ["500", "700", "900"],
});

const BG = "#0a0a0a";
const INK = "#ededed";
const MUTED = "#a3a3a3";
const GREEN = "#29DE8D";
const PANEL = "#1a1a1a";
const RULE = "#262626";

const Mark = ({ size }: { size: number }) => (
  <svg width={size} height={size} viewBox="0 0 512 512">
    <path
      d="M256 26 L282 44 C330 74 388 88 448 92 L448 268 C448 366 372 448 256 492 C140 448 64 366 64 268 L64 92 C124 88 182 74 230 44 Z"
      fill="#171E2C"
    />
    <circle cx="256" cy="276" r="148" fill="none" stroke="#FFFFFF" strokeWidth="24" />
    <path d="M256 276 L336 29 L472 131 Z" fill={GREEN} />
    <circle cx="380" cy="148" r="17" fill="none" stroke="#171E2C" strokeWidth="9" />
    <circle cx="256" cy="276" r="36" fill={GREEN} />
  </svg>
);

const Slam = ({
  children,
  delay = 0,
  size = 120,
  color = INK,
}: {
  children: React.ReactNode;
  delay?: number;
  size?: number;
  color?: string;
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 12, stiffness: 200 } });
  return (
    <div
      style={{
        fontFamily,
        fontWeight: 900,
        fontSize: size,
        color,
        letterSpacing: "-0.04em",
        lineHeight: 1.02,
        textAlign: "center",
        transform: `scale(${interpolate(s, [0, 1], [2.4, 1])}) rotate(${interpolate(s, [0, 1], [-6, 0])}deg)`,
        opacity: s,
      }}
    >
      {children}
    </div>
  );
};

const Center = ({ children }: { children: React.ReactNode }) => (
  <AbsoluteFill
    style={{
      justifyContent: "center",
      alignItems: "center",
      padding: 80,
      flexDirection: "column",
      gap: 40,
    }}
  >
    {children}
  </AbsoluteFill>
);

// S2: rapid-fire words, one per beat
const RapidWords = () => {
  const frame = useCurrentFrame();
  const words = ["your voice.", "your location.", "your DMs.", "your face."];
  const beat = 30;
  const index = Math.min(Math.floor(frame / beat), words.length - 1);
  const local = frame - index * beat;
  const { fps } = useVideoConfig();
  const s = spring({ frame: local, fps, config: { damping: 11, stiffness: 260 } });
  return (
    <Center>
      <div
        style={{
          fontFamily,
          fontWeight: 900,
          fontSize: 150,
          color: index % 2 === 0 ? INK : GREEN,
          letterSpacing: "-0.04em",
          textAlign: "center",
          transform: `scale(${interpolate(s, [0, 1], [3, 1])})`,
          opacity: s,
        }}
      >
        {words[index]}
      </div>
    </Center>
  );
};

// S4: the receipt — Google's real policy quote, typed out
const QUOTE =
  "“When your device detects an audio activation command, like ‘Hey Google,’ Google records your voice and audio plus a few seconds before the activation.”";

const Receipt = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const cardIn = spring({ frame, fps, config: { damping: 14 } });
  const chars = Math.floor(interpolate(frame, [12, 120], [0, QUOTE.length], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  }));
  const captionIn = spring({ frame: frame - 125, fps, config: { damping: 14 } });
  return (
    <Center>
      <div
        style={{
          width: 900,
          background: "#111111",
          border: `2px solid ${RULE}`,
          borderRadius: 28,
          padding: 56,
          transform: `translateY(${interpolate(cardIn, [0, 1], [400, 0])}px)`,
          opacity: cardIn,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          <div
            style={{
              width: 88,
              height: 88,
              borderRadius: 20,
              background: "#ffffff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily,
              fontWeight: 900,
              fontSize: 52,
              color: "#4285F4",
            }}
          >
            G
          </div>
          <div>
            <div style={{ fontFamily, fontWeight: 700, fontSize: 44, color: INK }}>
              Google
            </div>
            <div style={{ fontFamily, fontWeight: 700, fontSize: 30, color: GREEN }}>
              🎙️ voice recordings
            </div>
          </div>
        </div>
        <div
          style={{
            marginTop: 40,
            fontFamily,
            fontWeight: 500,
            fontSize: 40,
            fontStyle: "italic",
            lineHeight: 1.4,
            color: INK,
            borderLeft: `4px solid ${GREEN}`,
            paddingLeft: 28,
            minHeight: 340,
          }}
        >
          {QUOTE.slice(0, chars)}
        </div>
        <div
          style={{
            marginTop: 28,
            fontFamily,
            fontWeight: 700,
            fontSize: 30,
            color: MUTED,
            opacity: captionIn,
          }}
        >
          — google&apos;s ACTUAL privacy policy. word for word.
        </div>
      </div>
    </Center>
  );
};

// S5: chip storm — real companies, real disclosed categories
const CHIPS = [
  { company: "Stripe", takes: "biometrics 🫣" },
  { company: "Amazon", takes: "children's data" },
  { company: "Meta", takes: "an inferred profile of u" },
  { company: "Spotify", takes: "your location" },
  { company: "Netflix", takes: "your messages" },
];

const ChipStorm = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <Center>
      <div
        style={{
          fontFamily,
          fontWeight: 900,
          fontSize: 84,
          color: INK,
          letterSpacing: "-0.04em",
          textAlign: "center",
          opacity: spring({ frame, fps, config: { damping: 14 } }),
        }}
      >
        and it&apos;s not just google
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 26, marginTop: 30 }}>
        {CHIPS.map((chip, index) => {
          const s = spring({
            frame: frame - 14 - index * 12,
            fps,
            config: { damping: 12, stiffness: 220 },
          });
          return (
            <div
              key={chip.company}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 22,
                background: PANEL,
                border: `2px solid ${RULE}`,
                borderRadius: 18,
                padding: "26px 38px",
                transform: `translateX(${interpolate(s, [0, 1], [index % 2 === 0 ? -900 : 900, 0])}px)`,
                opacity: s,
              }}
            >
              <span style={{ fontFamily, fontWeight: 900, fontSize: 44, color: INK }}>
                {chip.company}
              </span>
              <span style={{ fontFamily, fontWeight: 700, fontSize: 36, color: MUTED }}>
                takes
              </span>
              <span style={{ fontFamily, fontWeight: 900, fontSize: 44, color: GREEN }}>
                {chip.takes}
              </span>
            </div>
          );
        })}
      </div>
    </Center>
  );
};

// S6: what PrivacyRadar does
const PITCH = [
  "reads the fine print so u don't have to",
  "every claim = the exact quote 🧾",
  "pings u when policies change 🔔",
];

const Pitch = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <Center>
      <div
        style={{
          fontFamily,
          fontWeight: 900,
          fontSize: 96,
          color: GREEN,
          letterSpacing: "-0.04em",
          textAlign: "center",
          opacity: spring({ frame, fps }),
        }}
      >
        PrivacyRadar
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 30, marginTop: 20 }}>
        {PITCH.map((line, index) => {
          const s = spring({
            frame: frame - 12 - index * 16,
            fps,
            config: { damping: 13 },
          });
          return (
            <div
              key={line}
              style={{
                fontFamily,
                fontWeight: 700,
                fontSize: 52,
                color: INK,
                textAlign: "center",
                transform: `translateY(${interpolate(s, [0, 1], [80, 0])}px)`,
                opacity: s,
              }}
            >
              {line}
            </div>
          );
        })}
      </div>
    </Center>
  );
};

// S7: outro with radar ping
const Outro = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 10, stiffness: 160 } });
  const ping = (frame % 45) / 45;
  return (
    <Center>
      <div style={{ position: "relative", width: 420, height: 420 }}>
        <div
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "50%",
            border: `6px solid ${GREEN}`,
            transform: `scale(${1 + ping * 0.9})`,
            opacity: 1 - ping,
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
          <Mark size={360} />
        </div>
      </div>
      <Slam delay={8} size={110}>
        <span style={{ color: INK }}>Privacy</span>
        <span style={{ color: GREEN }}>Radar</span>
      </Slam>
      <div
        style={{
          fontFamily,
          fontWeight: 700,
          fontSize: 46,
          color: MUTED,
          opacity: spring({ frame: frame - 20, fps }),
        }}
      >
        see what they take from you
      </div>
      <div
        style={{
          fontFamily,
          fontWeight: 900,
          fontSize: 52,
          color: INK,
          opacity: spring({ frame: frame - 32, fps }),
        }}
      >
        link in bio ✨
      </div>
    </Center>
  );
};

export const LaunchVideo = () => {
  return (
    <AbsoluteFill style={{ background: BG }}>
      {/* S1: hook */}
      <Sequence durationInFrames={75}>
        <Center>
          <Slam size={130}>
            ur apps know
            <br />
            <span style={{ color: GREEN }}>WAY</span> too much 👀
          </Slam>
        </Center>
      </Sequence>

      {/* S2: rapid-fire what they take */}
      <Sequence from={75} durationInFrames={120}>
        <RapidWords />
      </Sequence>

      {/* S3: receipts tease */}
      <Sequence from={195} durationInFrames={75}>
        <Center>
          <Slam size={110}>sounds fake?</Slam>
          <Slam delay={25} size={110}>
            we got the <span style={{ color: GREEN }}>receipts</span> 🧾
          </Slam>
        </Center>
      </Sequence>

      {/* S4: the Google quote */}
      <Sequence from={270} durationInFrames={180}>
        <Receipt />
      </Sequence>

      {/* S5: chip storm */}
      <Sequence from={450} durationInFrames={120}>
        <ChipStorm />
      </Sequence>

      {/* S6: pitch */}
      <Sequence from={570} durationInFrames={90}>
        <Pitch />
      </Sequence>

      {/* S7: outro */}
      <Sequence from={660} durationInFrames={90}>
        <Outro />
      </Sequence>
    </AbsoluteFill>
  );
};
