interface HeaderProps {
  opportunityCount: number;
}

export function Header({ opportunityCount }: HeaderProps) {
  const refreshTime = new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit"
  }).format(new Date());

  return (
    <header className="topbar panel reveal">
      <div>
        <p className="eyebrow">Unveni</p>
        <h1>AI options operating surface</h1>
      </div>
      <div className="statusRail">
        <div className="statusChip">
          <span className="statusDot statusDotPaper" />
          Paper mode
        </div>
        <div className="statusChip">
          <span className="statusDot statusDotData" />
          Delayed OPRA-safe analytics
        </div>
        <div className="statusChip">{opportunityCount} ranked setups</div>
        <div className="statusChip">Refreshed {refreshTime}</div>
      </div>
    </header>
  );
}

