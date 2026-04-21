type StatCardProps = {
  label: string;
  value: string;
  description: string;
};

export function StatCard({ label, value, description }: StatCardProps) {
  return (
    <div className="stat-card">
      <div className="stat-card-top">
        <div className="stat-label">{label}</div>
        <span className="stat-chip">Live</span>
      </div>
      <div className="stat-value">{value}</div>
      <p className="muted">{description}</p>
    </div>
  );
}
