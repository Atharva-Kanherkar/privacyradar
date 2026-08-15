import {
  AbsoluteFill,
  Sequence,
  interpolate,
  random,
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
const PANEL = "#161616";
const RULE = "#2a2a2a";

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

// Impact shake right after a slam lands, then settles.
const useShake = (hitFrame: number, strength = 14) => {
  const frame = useCurrentFrame();
  const t = frame - hitFrame;
  if (t < 0 || t > 10) return { x: 0, y: 0 };
  const decay = 1 - t / 10;
  return {
    x: (random(`sx-${t}`) - 0.5) * 2 * strength * decay,
    y: (random(`sy-${t}`) - 0.5) * 2 * strength * decay,
  };
};

// Constant slow punch-in so no frame is ever static.
const useDrift = (durationInFrames: number, amount = 0.06) => {
  const frame = useCurrentFrame();
  return 1 + (frame / durationInFrames) * amount;
};

// Two-frame flash at scene start: classic hype-edit transition.
const Flash = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 3], [0.9, 0], {
    extrapolateRight: "clamp",
  });
  return <AbsoluteFill style={{ background: GREEN, opacity }} />;
};

const Slam = ({
  children,
  delay = 0,
  size = 120,
  color = INK,
  shake = true,
}: {
  children: React.ReactNode;
  delay?: number;
  size?: number;
  color?: string;
  shake?: boolean;
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 11, stiffness: 240 } });
  const kick = useShake(delay + 5, shake ? 12 : 0);
  return (
    <div
      style={{
        fontFamily,
        fontWeight: 900,
        fontSize: size,
        color,
        letterSpacing: "-0.04em",
        lineHeight: 1.04,
        textAlign: "center",
        transform: `translate(${kick.x}px, ${kick.y}px) scale(${interpolate(s, [0, 1], [2.6, 1])}) rotate(${interpolate(s, [0, 1], [-5, 0])}deg)`,
        opacity: s,
      }}
    >
      {children}
    </div>
  );
};

// Reel-safe stage: keeps content clear of the caption/UI zones.
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
      paddingLeft: 70,
      paddingRight: 70,
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
  const words = ["they take ur voice.", "ur location.", "ur DMs.", "ur face."];
  const beat = 27;
  const index = Math.min(Math.floor(frame / beat), words.length - 1);
  const local = frame - index * beat;
  const { fps } = useVideoConfig();
  const s = spring({ frame: local, fps, config: { damping: 10, stiffness: 300 } });
  const kick = useShake(index * beat + 4, 16);
  return (
    <Stage drift={useDrift(108)}>
      <div
        style={{
          fontFamily,
          fontWeight: 900,
          fontSize: index === 0 ? 110 : 150,
          color: index % 2 === 0 ? INK : GREEN,
          letterSpacing: "-0.04em",
          textAlign: "center",
          transform: `translate(${kick.x}px, ${kick.y}px) scale(${interpolate(s, [0, 1], [3.2, 1])})`,
          opacity: s,
        }}
      >
        {words[index]}
      </div>
    </Stage>
  );
};

const QUOTE =
  "“When your device detects an audio activation command, like ‘Hey Google,’ Google records your voice and audio plus a few seconds before the activation.”";

const Receipt = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const cardIn = spring({ frame, fps, config: { damping: 14 } });
  const chars = Math.floor(
    interpolate(frame, [10, 105], [0, QUOTE.length], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }),
  );
  const captionIn = spring({ frame: frame - 112, fps, config: { damping: 14 } });
  const stampIn = spring({ frame: frame - 130, fps, config: { damping: 9, stiffness: 300 } });
  const kick = useShake(134, 18);
  return (
    <Stage drift={useDrift(180, 0.04)}>
      <div
        style={{
          position: "relative",
          width: 920,
          background: "#111111",
          border: `2px solid ${RULE}`,
          borderRadius: 28,
          padding: 56,
          transform: `translate(${kick.x}px, ${kick.y + interpolate(cardIn, [0, 1], [500, 0])}px)`,
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
              voice recordings
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
            marginTop: 26,
            fontFamily,
            fontWeight: 700,
            fontSize: 29,
            color: MUTED,
            opacity: captionIn,
          }}
        >
          — google&apos;s ACTUAL privacy policy. word for word.
        </div>
        <div
          style={{
            position: "absolute",
            top: -46,
            right: -30,
            fontFamily,
            fontWeight: 900,
            fontSize: 54,
            color: GREEN,
            border: `6px solid ${GREEN}`,
            borderRadius: 16,
            padding: "10px 26px",
            background: BG,
            transform: `rotate(-8deg) scale(${stampIn})`,
            letterSpacing: "0.02em",
          }}
        >
          CAUGHT IN 4K
        </div>
      </div>
    </Stage>
  );
};

const CHIPS = [
  { company: "Stripe", takes: "ur biometrics" },
  { company: "Amazon", takes: "kids' data" },
  { company: "Meta", takes: "a whole profile of u" },
  { company: "Spotify", takes: "ur location" },
  { company: "Netflix", takes: "ur messages" },
];

const ChipStorm = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const verdict = spring({ frame: frame - 85, fps, config: { damping: 9, stiffness: 280 } });
  return (
    <Stage drift={useDrift(120, 0.05)}>
      <div
        style={{
          fontFamily,
          fontWeight: 900,
          fontSize: 82,
          color: INK,
          letterSpacing: "-0.04em",
          textAlign: "center",
          opacity: spring({ frame, fps, config: { damping: 14 } }),
        }}
      >
        and it&apos;s not just google
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 24, marginTop: 16 }}>
        {CHIPS.map((chip, index) => {
          const s = spring({
            frame: frame - 10 - index * 11,
            fps,
            config: { damping: 12, stiffness: 240 },
          });
          return (
            <div
              key={chip.company}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 20,
                background: PANEL,
                border: `2px solid ${RULE}`,
                borderRadius: 18,
                padding: "24px 36px",
                transform: `translateX(${interpolate(s, [0, 1], [index % 2 === 0 ? -1000 : 1000, 0])}px)`,
                opacity: s,
              }}
            >
              <span style={{ fontFamily, fontWeight: 900, fontSize: 42, color: INK }}>
                {chip.company}
              </span>
              <span style={{ fontFamily, fontWeight: 700, fontSize: 34, color: MUTED }}>
                takes
              </span>
              <span style={{ fontFamily, fontWeight: 900, fontSize: 42, color: GREEN }}>
                {chip.takes}
              </span>
            </div>
          );
        })}
      </div>
      <div
        style={{
          fontFamily,
          fontWeight: 900,
          fontSize: 96,
          color: GREEN,
          letterSpacing: "-0.03em",
          transform: `rotate(-3deg) scale(${verdict})`,
        }}
      >
        diabolical.
      </div>
    </Stage>
  );
};

const PITCH = [
  "every claim = the exact quote",
  "alerts the moment policies change",
  "thinking they'll tell u themselves? delulu.",
];

const Pitch = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <Stage drift={useDrift(84, 0.05)}>
      <div
        style={{
          fontFamily,
          fontWeight: 900,
          fontSize: 92,
          color: GREEN,
          letterSpacing: "-0.04em",
          textAlign: "center",
          opacity: spring({ frame, fps }),
        }}
      >
        PrivacyRadar
      </div>
      <div
        style={{
          fontFamily,
          fontWeight: 700,
          fontSize: 48,
          color: INK,
          textAlign: "center",
          opacity: spring({ frame: frame - 8, fps }),
        }}
      >
        reads the fine print. standing on business.
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 26, marginTop: 14 }}>
        {PITCH.map((line, index) => {
          const s = spring({
            frame: frame - 16 - index * 13,
            fps,
            config: { damping: 13 },
          });
          return (
            <div
              key={line}
              style={{
                fontFamily,
                fontWeight: 700,
                fontSize: 44,
                color: index === PITCH.length - 1 ? GREEN : MUTED,
                textAlign: "center",
                transform: `translateY(${interpolate(s, [0, 1], [70, 0])}px)`,
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
  const pop = spring({ frame, fps, config: { damping: 10, stiffness: 170 } });
  const ping = (frame % 40) / 40;
  return (
    <Stage>
      <div style={{ position: "relative", width: 400, height: 400 }}>
        <div
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "50%",
            border: `6px solid ${GREEN}`,
            transform: `scale(${1 + ping})`,
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
          <Mark size={340} />
        </div>
      </div>
      <Slam delay={6} size={104} shake={false}>
        <span style={{ color: INK }}>Privacy</span>
        <span style={{ color: GREEN }}>Radar</span>
      </Slam>
      <div
        style={{
          fontFamily,
          fontWeight: 700,
          fontSize: 44,
          color: MUTED,
          opacity: spring({ frame: frame - 16, fps }),
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
          opacity: spring({ frame: frame - 28, fps }),
        }}
      >
        link in bio.
      </div>
    </Stage>
  );
};

const Hook = () => (
  <Stage drift={useDrift(60)}>
    <Slam size={132}>
      ur apps are
      <br />
      lowkey ur <span style={{ color: GREEN }}>opps</span>
    </Slam>
  </Stage>
);

const Tease = () => (
  <Stage drift={useDrift(60)}>
    <Slam size={112}>sounds like cap?</Slam>
    <Slam delay={20} size={112}>
      we caught them <span style={{ color: GREEN }}>in 4K</span>
    </Slam>
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
        <Flash />
        <RapidWords />
      </Sequence>

      {/* S3: caught in 4k tease */}
      <Sequence from={168} durationInFrames={60}>
        <Flash />
        <Tease />
      </Sequence>

      {/* S4: the receipt */}
      <Sequence from={228} durationInFrames={175}>
        <Flash />
        <Receipt />
      </Sequence>

      {/* S5: chip storm + verdict */}
      <Sequence from={403} durationInFrames={120}>
        <Flash />
        <ChipStorm />
      </Sequence>

      {/* S6: pitch */}
      <Sequence from={523} durationInFrames={84}>
        <Flash />
        <Pitch />
      </Sequence>

      {/* S7: outro */}
      <Sequence from={607} durationInFrames={83}>
        <Flash />
        <Outro />
      </Sequence>
    </AbsoluteFill>
  );
};
