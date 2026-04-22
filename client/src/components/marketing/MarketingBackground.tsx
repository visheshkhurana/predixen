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
    </div>
  );
}
