export function SimBackgroundOrbs({ color = "blue" }: { color?: "blue" | "amber" | "green" }) {
  const palette: Record<string, [string, string]> = {
    blue: ["rgba(79,125,249,0.05)", "rgba(167,139,250,0.03)"],
    amber: ["rgba(245,158,11,0.05)", "rgba(234,88,12,0.03)"],
    green: ["rgba(52,211,153,0.05)", "rgba(16,185,129,0.03)"],
  };
  const [c1, c2] = palette[color];

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden z-0">
      <div
        className="absolute w-[500px] h-[350px] rounded-full blur-[100px] top-[10%] right-[5%]"
        style={{ background: c1, animation: "fc-drift1 25s ease-in-out infinite" }}
      />
      <div
        className="absolute w-[400px] h-[300px] rounded-full blur-[80px] bottom-[15%] left-[3%]"
        style={{ background: c2, animation: "fc-drift2 30s ease-in-out infinite" }}
      />
    </div>
  );
}
