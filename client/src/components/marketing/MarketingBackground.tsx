const particles = [
  { size: 4, top: "8%", left: "12%", anim: "fc-float1", dur: "18s", delay: "0s" },
  { size: 3, top: "15%", left: "85%", anim: "fc-float2", dur: "22s", delay: "2s" },
  { size: 5, top: "25%", left: "45%", anim: "fc-twinkle", dur: "4s", delay: "1s" },
  { size: 3, top: "35%", left: "72%", anim: "fc-float3", dur: "20s", delay: "3s" },
  { size: 4, top: "42%", left: "18%", anim: "fc-float2", dur: "24s", delay: "5s" },
  { size: 6, top: "48%", left: "55%", anim: "fc-twinkle", dur: "5s", delay: "0.5s" },
  { size: 3, top: "55%", left: "90%", anim: "fc-float1", dur: "19s", delay: "4s" },
  { size: 4, top: "62%", left: "30%", anim: "fc-float3", dur: "21s", delay: "1.5s" },
  { size: 5, top: "68%", left: "78%", anim: "fc-twinkle", dur: "3.5s", delay: "2.5s" },
  { size: 3, top: "75%", left: "8%", anim: "fc-float2", dur: "23s", delay: "6s" },
  { size: 4, top: "82%", left: "62%", anim: "fc-float1", dur: "17s", delay: "3.5s" },
  { size: 3, top: "88%", left: "40%", anim: "fc-twinkle", dur: "4.5s", delay: "1.8s" },
  { size: 5, top: "20%", left: "65%", anim: "fc-float3", dur: "26s", delay: "7s" },
  { size: 3, top: "50%", left: "5%", anim: "fc-float1", dur: "20s", delay: "8s" },
  { size: 4, top: "92%", left: "22%", anim: "fc-float2", dur: "25s", delay: "4.5s" },
  { size: 3, top: "10%", left: "52%", anim: "fc-twinkle", dur: "6s", delay: "0.8s" },
  { size: 5, top: "38%", left: "95%", anim: "fc-float3", dur: "22s", delay: "2.2s" },
  { size: 3, top: "72%", left: "48%", anim: "fc-float1", dur: "18s", delay: "5.5s" },
];

export function MarketingBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
      <div
        className="absolute w-[600px] h-[400px] rounded-full blur-[120px] top-[5%] right-[10%]"
        style={{ background: "rgba(16,185,129,0.04)", animation: "fc-drift1 25s ease-in-out infinite" }}
      />
      <div
        className="absolute w-[500px] h-[350px] rounded-full blur-[100px] top-[30%] left-[5%]"
        style={{ background: "rgba(139,92,246,0.03)", animation: "fc-drift2 30s ease-in-out infinite" }}
      />
      <div
        className="absolute w-[450px] h-[300px] rounded-full blur-[110px] bottom-[10%] right-[15%]"
        style={{ background: "rgba(14,165,233,0.03)", animation: "fc-drift1 28s ease-in-out infinite" }}
      />

      {particles.map((p, i) => (
        <div
          key={i}
          className="absolute rounded-full"
          style={{
            width: p.size,
            height: p.size,
            top: p.top,
            left: p.left,
            background: "rgba(148,163,184,0.5)",
            animation: `${p.anim} ${p.dur} ease-in-out infinite`,
            animationDelay: p.delay,
          }}
        />
      ))}
    </div>
  );
}
